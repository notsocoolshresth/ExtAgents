import json
import re
import os
import time
import threading
import httpx
from pathlib import Path
from typing import Optional
from openai import OpenAI

# Global client and model variables
client = None
model = None

def is_local_model():
    """Check if the current model is a local model (e.g., via Ollama)"""
    global model
    if not model:
        return False
    model_lower = model.lower()
    return (
        "llama" in model_lower or "qwen" in model_lower
        or "ollama" in model_lower or "localhost" in model_lower
    )

def initialize_client(api_url, api_key, model_name):
    """Initialize client and set global variables"""
    global client, model
    client = OpenAI(
        base_url=api_url, 
        api_key=api_key,
        http_client=httpx.Client(
            base_url=api_url,
            follow_redirects=True,
        ),
    )
    model = model_name


def chat(messages: list):
    """Chat function using global client and model"""
    temperature = 0.1 if is_local_model() else 0.0
    
    while True:
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
            )
            if (
                hasattr(completion, 'choices') and 
                len(completion.choices) > 0 and 
                hasattr(completion.choices[0], 'message') and 
                completion.choices[0].message and 
                hasattr(completion.choices[0].message, 'content') and 
                completion.choices[0].message.content
            ):
                return completion.choices[0].message.content
            else:
                print("Received incomplete response, retrying...")
                time.sleep(10)
        except Exception as e:
            print(f"Error occurred: {e}")
            time.sleep(10)


def truncate_input(input, max_length, manner="middle"):
    """
    Truncate input to max_length
    
    Args:
        input: Input tokens or text to truncate
        max_length: Maximum length to keep
        manner: Truncation method - "middle" keeps first and last half, "front" keeps first part
        
    Returns:
        Truncated input
    """
    if len(input) <= max_length:
        return input
    if manner == "middle":
        return input[0 : max_length // 2] + input[-max_length // 2 :]
    elif manner == "front":
        return input[:max_length]
    else:
        return input[:max_length]


def chunk_input(input, chunk_length):
    """
    Split input into chunks of chunk_length
    
    Args:
        input: Input tokens or text to split
        chunk_length: Length of each chunk
        
    Returns:
        List of chunks
    """
    return [input[i : i + chunk_length] for i in range(0, len(input), chunk_length)]


def create_chunks(
    tokenizer,
    context: str,
    chunk_length: int,
    input_length: int,
    manner="middle",
) -> list:
    """
    Split the context into chunks
    
    Args:
        tokenizer: Tokenizer to use for encoding/decoding
        context: Text to split into chunks
        chunk_length: Length of each chunk
        input_length: Maximum input length to consider
        manner: Truncation method - "middle" or "front"
        
    Returns:
        List of text chunks
    """
    if tokenizer:
        tokens = tokenizer.encode(context)
        tokens = truncate_input(tokens, input_length, manner=manner)
        chunked_tokens = chunk_input(tokens, chunk_length)
        chunks = [tokenizer.decode(chunked_token) for chunked_token in chunked_tokens]
    else:
        print("No tokenizer provided. Using raw text.")
        chunks = chunk_input(context, chunk_length)

    return chunks


def get_info_score(info, question, task, prompt_module):
    """
    Score the extracted information based on task type
    
    Args:
        info: Extracted information to score
        question: The question being answered
        task: Task type ("en", "zh", or "rag")
        prompt_module: Module containing prompt functions
        
    Returns:
        Score from 0-100 or 0 for RAG tasks
    """
    # Score the extracted information based on task type
    if task == "rag":
        return 0  # Return default score for RAG task
    
    prompt = prompt_module.get_info_score_prompt(info, question, task)
    if not prompt:
        return 0
    
    msgs = prompt_module.create_chunked_msgs(prompt)
    while True:
        response = chat(msgs)
        score_match = re.search(r"Score:\s*(\d+)", response)
        if score_match:
            score = float(score_match.group(1).strip())
            return score
        else:
            print("Invalid response. Please provide a score between 0 and 100.")


def postprocess_prediction(prediction, question, prompt_module):
    """
    Post-process the prediction for open-source models like Llama
    to make the answers more concise.
    
    Args:
        prediction: The model's prediction to refine
        question: The question that was answered
        prompt_module: Module containing prompt functions
        
    Returns:
        Tuple of (processed_prediction, processing_time)
    """
    prompt = prompt_module.create_postprocess_prompt(prediction, question)
    
    messages = prompt_module.create_chunked_msgs(prompt)
    try:
        reduce_start_time = time.time()
        response = chat(messages)
        reduce_end_time = time.time()
        return response, (reduce_end_time - reduce_start_time)
    except Exception as e:
        print(f"Error in post-processing: {e}")
        return prediction, 0.0  # Return original prediction if processing fails


def process_info_list(info_list, tokenizer, max_tokens, task):
    """
    Truncate info list to fit within max_tokens.
    For en/zh: sort by score descending and keep top items.
    For rag: keep items in original order.

    Args:
        info_list: List of (info, score) tuples for en/zh, or list of info strings for rag
        tokenizer: Tokenizer for token counting
        max_tokens: Maximum total tokens allowed
        task: Task type ("en", "zh", or "rag")

    Returns:
        Truncated info list in the same format as input
    """
    if max_tokens <= 0:
        return info_list[:1] if info_list else info_list

    if task in ["en", "zh"]:
        sorted_list = sorted(info_list, key=lambda x: x[1], reverse=True)
        result = []
        total_tokens = 0
        for info, score in sorted_list:
            tokens = len(tokenizer.encode(info))
            if total_tokens + tokens > max_tokens and result:
                break
            result.append((info, score))
            total_tokens += tokens
        return result
    elif task == "rag":
        result = []
        total_tokens = 0
        for info in info_list:
            tokens = len(tokenizer.encode(info))
            if total_tokens + tokens > max_tokens and result:
                break
            result.append(info)
            total_tokens += tokens
        return result
    return info_list


def dump_jsonl(data, fname):
    """Write data to a jsonl file"""
    with open(fname, "w", encoding="utf8") as fout:
        for line in data:
            fout.write(json.dumps(line, ensure_ascii=False) + "\n")


def iter_jsonl(fname, cnt=None):
    """Read data from a jsonl file"""
    i = 0
    with open(fname, "r") as fin:
        for line in fin:
            if i == cnt:
                break
            yield json.loads(line)
            i += 1 