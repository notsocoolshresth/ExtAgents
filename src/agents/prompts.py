"""Prompts for the agentic pipeline."""

import json


def create_system_prompt(tool_descriptions: str) -> str:
    """Create the system prompt for the agent."""
    return f"""You are a multihop QA agent. You have access to a large document (up to 1M tokens) via tools.
Your goal: answer the question by iteratively searching, reading, and extracting evidence.

Available tools:
{tool_descriptions}

Strategy:
1. Search for key entities/relations from the question using bm25_search
2. Read promising chunks using read_chunk or read_range
3. Extract relevant information using extract (MUST use the actual text from read_chunk/read_range as 'passage')
4. Repeat until you have enough evidence to answer
5. Synthesize a final answer using synthesize

Output format for each step:
THOUGHT: <your reasoning about what to do next>
ACTION: <tool_name>(<json_args>)

Example:
THOUGHT: The question asks about the birthplace of Einstein. I should search for "Einstein birthplace" first.
ACTION: bm25_search({{"query": "Einstein birthplace", "top_k": 5}})

THOUGHT: The search found chunk 42 with high score. I'll read it to get details.
ACTION: read_chunk({{"chunk_id": 42}})

THOUGHT: The chunk mentions Einstein was born in Ulm. I'll extract this information using the ACTUAL text from the chunk.
ACTION: extract({{"passage": "Albert Einstein was born in Ulm, Germany on March 14, 1879...", "question": "Where was Einstein born?", "prior_evidence": ""}})

THOUGHT: I have the answer. I'll synthesize it.
ACTION: synthesize({{"evidence": [{{"info": "Einstein was born in Ulm, Germany.", "confidence": 0.95}}], "question": "Where was Einstein born?"}})

Important:
- Always output valid JSON for tool arguments
- For extract: the 'passage' MUST be the actual text returned by read_chunk or read_range (not "..." or empty)
- Use prior_evidence in extract to avoid repeating information
- The synthesize tool should be called only once at the end
- Max 12 steps total
- Do NOT repeat the same search or read - try different queries or chunk IDs
"""


def create_extract_prompt(passage: str, question: str, prior_evidence: str = "") -> str:
    """Create prompt for extracting information from a passage."""
    prior_section = f"\nPrior evidence (do not repeat):\n{prior_evidence}\n" if prior_evidence else "\n"
    
    return f"""Extract information from the passage that helps answer the question.

Question: {question}
{prior_section}
Passage:
{passage}

Return a JSON object with:
- "info": extracted information relevant to the question (string)
- "confidence": confidence score 0.0-1.0 (float)
- "citations": list of token ranges or chunk references (list)

If no relevant information, return {{"info": "NO INFORMATION", "confidence": 0.0, "citations": []}}"""


def create_synthesize_prompt(evidence_str: str, question: str) -> str:
    """Create prompt for synthesizing final answer from evidence."""
    return f"""Synthesize a final answer from the collected evidence.

Question: {question}

Evidence:
{evidence_str}

Output ONLY the final answer as a single word, phrase, or short sentence. No explanation, no JSON, no extra text.

If the evidence is insufficient, output exactly: NO ANSWER"""


def create_agent_prompt(tool_descriptions: str) -> str:
    """Create the full agent prompt (system + few-shot)."""
    return create_system_prompt(tool_descriptions)