#!/usr/bin/env python3
"""
Convert final_preds.jsonl (pipeline output format) to predictions.json (eval format).
Maps 0-based line index to question_id from gold file.
"""

import json
import argparse
from pathlib import Path


def convert(final_preds_path: str, gold_path: str, output_path: str):
    # Load gold to get question_id mapping by index
    with open(gold_path, 'r', encoding='utf-8') as f:
        gold = json.load(f)
    
    # Build index -> question_id map
    idx_to_qid = {i: item['_id'] for i, item in enumerate(gold)}
    
    # Load final_preds.jsonl
    predictions = {}
    with open(final_preds_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            idx = data['id']
            pred = data['prediction']
            qid = idx_to_qid.get(idx)
            if qid:
                predictions[qid] = pred
            else:
                print(f"Warning: No gold question_id for index {idx}")
    
    # Write predictions.json format
    output = {'answer': predictions}
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"Converted {len(predictions)} predictions")
    print(f"Output: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Convert final_preds.jsonl to predictions.json')
    parser.add_argument('--final_preds', required=True, help='Path to final_preds.jsonl')
    parser.add_argument('--gold', required=True, help='Path to gold questions JSON (sampled_hotpot_questions.json)')
    parser.add_argument('--output', required=True, help='Output predictions.json path')
    
    args = parser.parse_args()
    convert(args.final_preds, args.gold, args.output)


if __name__ == '__main__':
    main()