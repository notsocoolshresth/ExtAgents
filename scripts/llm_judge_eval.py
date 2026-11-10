#!/usr/bin/env python3
"""
LLM-as-Judge Evaluation for ExtAgents RAG predictions.
Uses a local Ollama model (default llama3.2:3b) to judge semantic correctness.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))
from src import utils


JUDGE_SYSTEM_PROMPT = """You are an evaluator. For each question, judge if the predicted answer is correct (semantically equivalent to gold). 

CRITERIA:
- Semantic match > exact string match
- Extra explanation OK if core answer correct
- "No info" / "cannot find" matches gold "no" or unanswerable
- Yes/No: "Yes, American." ≡ "yes"
- Partial entity names OK: "Kimmy Schmidt" ≡ "Kimberly Couger Kimmy Schmidt"
- Wrong entity = incorrect

OUTPUT: One line per example: "correct" or "incorrect" """


JUDGE_USER_TEMPLATE = """Evaluate these {count} question-answer pairs:

{examples}

Output one judgment per line (correct/incorrect):"""


def load_predictions(path: str) -> Dict[str, str]:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('answer', {})


def load_gold(path: str) -> List[Dict[str, Any]]:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_batch_prompt(batch: List[Dict]) -> str:
    examples = []
    for i, item in enumerate(batch, 1):
        examples.append(
            f"Example {i}:\n"
            f"Question: {item['question']}\n"
            f"Gold: {item['gold']}\n"
            f"Predicted: {item['pred']}\n"
        )
    return JUDGE_USER_TEMPLATE.format(count=len(batch), examples='\n'.join(examples))


def parse_judge_response(response: str, batch_size: int) -> List[Dict]:
    lines = [line.strip().lower() for line in response.strip().split('\n') if line.strip()]
    judgments = []
    
    for i, line in enumerate(lines[:batch_size]):
        if 'correct' in line and 'incorrect' not in line:
            judgments.append({"judgment": "correct", "reasoning": line})
        elif 'incorrect' in line:
            judgments.append({"judgment": "incorrect", "reasoning": line})
        else:
            # Try to infer
            if any(w in line for w in ['yes', 'match', 'right', 'true']):
                judgments.append({"judgment": "correct", "reasoning": line})
            else:
                judgments.append({"judgment": "incorrect", "reasoning": line})
    
    # Pad if fewer lines than batch
    while len(judgments) < batch_size:
        judgments.append({"judgment": "incorrect", "reasoning": "No judgment line"})
    
    return judgments


def run_judge_batch(client_utils, judge_model: str, batch: List[Dict]) -> List[Dict]:
    prompt = build_batch_prompt(batch)
    messages = [
        {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]
    
    # Use direct HTTP for speed and control
    import httpx
    import time
    
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            with httpx.Client(timeout=120.0) as client:
                resp = client.post(
                    "http://localhost:11434/v1/chat/completions",
                    json={
                        "model": judge_model,
                        "messages": messages,
                        "temperature": 0,
                        "max_tokens": 500
                    }
                )
            if resp.status_code == 200:
                data = resp.json()
                response = data['choices'][0]['message']['content']
                return parse_judge_response(response, len(batch))
        except Exception as e:
            if attempt < max_retries:
                time.sleep(2)
            else:
                return [{"question_id": b['question_id'], "judgment": "incorrect", "reasoning": f"Judge error: {e}"} for b in batch]
    
    return [{"question_id": b['question_id'], "judgment": "incorrect", "reasoning": "Judge failed"} for b in batch]


def evaluate(predictions: Dict, gold: List, judge_model: str, api_url: str, api_key: str, batch_size: int = 20):
    # No need to initialize utils client since we use direct HTTP
    
    # Pair predictions with gold
    paired = []
    for item in gold:
        qid = item['_id']
        if qid in predictions:
            paired.append({
                'question_id': qid,
                'question': item['question'],
                'gold': item['answer'],
                'pred': predictions[qid]
            })
    
    print(f"Evaluating {len(paired)} questions with {judge_model} (batch_size={batch_size})...")
    
    all_judgments = []
    for i in range(0, len(paired), batch_size):
        batch = paired[i:i+batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(paired) + batch_size - 1) // batch_size
        
        print(f"  Batch {batch_num}/{total_batches} ({len(batch)} items)...", end=' ', flush=True)
        start = time.time()
        
        judgments = run_judge_batch(None, judge_model, batch)
        
        elapsed = time.time() - start
        correct_count = sum(1 for j in judgments if j.get('judgment') == 'correct')
        print(f"done ({correct_count}/{len(batch)} correct, {elapsed:.1f}s)")
        
        all_judgments.extend(judgments)
    
    return paired, all_judgments


def save_results(output_dir: Path, paired: List, judgments: List):
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Detailed JSONL
    detailed_path = output_dir / 'llm_judge_detailed.jsonl'
    with open(detailed_path, 'w', encoding='utf-8') as f:
        for p, j in zip(paired, judgments):
            f.write(json.dumps({
                'question_id': p['question_id'],
                'question': p['question'],
                'gold': p['gold'],
                'pred': p['pred'],
                'judgment': j.get('judgment', 'incorrect'),
                'reasoning': j.get('reasoning', '')
            }, ensure_ascii=False) + '\n')
    
    # Summary JSON
    total = len(judgments)
    correct = sum(1 for j in judgments if j.get('judgment') == 'correct')
    accuracy = correct / total * 100 if total > 0 else 0
    
    summary = {
        'total_evaluated': total,
        'correct': correct,
        'incorrect': total - correct,
        'accuracy_percent': round(accuracy, 2),
        'judge_model': 'llama3.2:3b',
        'temperature': 0,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    summary_path = output_dir / 'llm_judge_results.json'
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    # Markdown report
    md_path = output_dir / 'llm_judge_report.md'
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(f"# LLM-as-Judge Evaluation Report\n\n")
        f.write(f"**Date:** {summary['timestamp']}\n")
        f.write(f"**Judge Model:** {summary['judge_model']}\n")
        f.write(f"**Temperature:** {summary['temperature']}\n\n")
        f.write(f"## Summary Metrics\n\n")
        f.write(f"| Metric | Value |\n")
        f.write(f"|--------|-------|\n")
        f.write(f"| Total Evaluated | {total} |\n")
        f.write(f"| LLM-Judge Accuracy | {accuracy:.2f}% |\n")
        f.write(f"| Correct | {correct} |\n")
        f.write(f"| Incorrect | {total - correct} |\n\n")
        
        f.write(f"## Per-Example Judgments\n\n")
        f.write(f"| # | Question ID | Judgment | Gold | Predicted |\n")
        f.write(f"|---|-------------|----------|------|-----------|\n")
        for idx, (p, j) in enumerate(zip(paired, judgments), 1):
            judgment = j.get('judgment', 'incorrect')
            gold_short = p['gold'][:50] + '...' if len(p['gold']) > 50 else p['gold']
            pred_short = p['pred'][:50] + '...' if len(p['pred']) > 50 else p['pred']
            f.write(f"| {idx} | {p['question_id']} | {judgment} | {gold_short} | {pred_short} |\n")
    
    print(f"\nResults saved to: {output_dir}")
    print(f"  - {detailed_path.name}")
    print(f"  - {summary_path.name}")
    print(f"  - {md_path.name}")
    
    return summary


def main():
    parser = argparse.ArgumentParser(description='LLM-as-Judge evaluation for RAG predictions')
    parser.add_argument('--predictions_path', required=True, help='Path to predictions.json')
    parser.add_argument('--gold_path', required=True, help='Path to gold answers JSON')
    parser.add_argument('--judge_model', default='llama3.2:3b', help='Ollama model for judging')
    parser.add_argument('--api_url', default='http://localhost:11434/v1', help='Ollama API URL')
    parser.add_argument('--api_key', default='ollama', help='API key')
    parser.add_argument('--batch_size', type=int, default=20, help='Batch size for judging')
    parser.add_argument('--output_dir', help='Output directory (default: <predictions_dir>/llm_judge)')
    
    args = parser.parse_args()
    
    pred_path = Path(args.predictions_path)
    if not pred_path.exists():
        print(f"ERROR: Predictions file not found: {pred_path}")
        sys.exit(1)
    
    gold_path = Path(args.gold_path)
    if not gold_path.exists():
        print(f"ERROR: Gold file not found: {gold_path}")
        sys.exit(1)
    
    output_dir = Path(args.output_dir) if args.output_dir else pred_path.parent / 'llm_judge'
    
    print("=" * 60)
    print("LLM-as-Judge Evaluation")
    print("=" * 60)
    print(f"Predictions: {pred_path}")
    print(f"Gold: {gold_path}")
    print(f"Judge Model: {args.judge_model}")
    print(f"Batch Size: {args.batch_size}")
    print(f"Output Dir: {output_dir}")
    print()
    
    predictions = load_predictions(str(pred_path))
    gold = load_gold(str(gold_path))
    
    paired, judgments = evaluate(
        predictions, gold, 
        args.judge_model, args.api_url, args.api_key, args.batch_size
    )
    
    summary = save_results(output_dir, paired, judgments)
    
    print(f"\n{'='*60}")
    print(f"FINAL ACCURACY: {summary['accuracy_percent']:.2f}% ({summary['correct']}/{summary['total_evaluated']})")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()