"""Tests for the agentic pipeline."""

import unittest
from unittest.mock import Mock, MagicMock, patch

import tiktoken

from src.agents import available, install, restore
from src.agents.context import ContextManager
from src.agents.tools import available_tools, create_all_tools
from src.agents.prompts import create_system_prompt, create_extract_prompt, create_synthesize_prompt


class TestAgentRegistry(unittest.TestCase):
    """Test agent registry functionality."""
    
    def test_available_agents(self):
        """Test that multihop agent is available."""
        agents_list = available()
        self.assertIn("multihop", agents_list)
        self.assertIn("legacy", agents_list)
    
    def test_install_restore(self):
        """Test install and restore."""
        # Install multihop
        install("multihop")
        # Restore legacy
        restore()
        # Should not raise


class TestContextManager(unittest.TestCase):
    """Test ContextManager functionality."""
    
    def setUp(self):
        self.tokenizer = tiktoken.encoding_for_model("gpt-4o")
        self.text = "This is a test document. " * 100  # ~500 tokens
        self.chunk_length = 100
        self.input_length = 1000
    
    def test_chunking(self):
        """Test that text is properly chunked."""
        ctx = ContextManager(
            full_text=self.text,
            tokenizer=self.tokenizer,
            chunk_length=self.chunk_length,
            input_length=self.input_length,
            manner="front"
        )
        
        self.assertGreater(ctx.get_num_chunks(), 0)
        self.assertLessEqual(ctx.get_token_count(), self.input_length)
    
    def test_get_chunk(self):
        """Test reading a specific chunk."""
        ctx = ContextManager(
            full_text=self.text,
            tokenizer=self.tokenizer,
            chunk_length=self.chunk_length,
            input_length=self.input_length,
            manner="front"
        )
        
        chunk = ctx.get_chunk(0)
        self.assertEqual(chunk.chunk_id, 0)
        self.assertIsInstance(chunk.text, str)
        self.assertLessEqual(chunk.token_end - chunk.token_start, self.chunk_length)
    
    def test_get_range(self):
        """Test reading an arbitrary token range."""
        ctx = ContextManager(
            full_text=self.text,
            tokenizer=self.tokenizer,
            chunk_length=self.chunk_length,
            input_length=self.input_length,
            manner="front"
        )
        
        range_result = ctx.get_range(0, 50)
        self.assertEqual(range_result.token_start, 0)
        self.assertEqual(range_result.token_end, 50)
        self.assertIsInstance(range_result.text, str)
    
    def test_search(self):
        """Test BM25 search."""
        ctx = ContextManager(
            full_text=self.text,
            tokenizer=self.tokenizer,
            chunk_length=self.chunk_length,
            input_length=self.input_length,
            manner="front"
        )
        
        results = ctx.search("test document", top_k=3)
        self.assertIsInstance(results, list)
        self.assertLessEqual(len(results), 3)
        for r in results:
            self.assertIn("chunk_id", r.__dict__)
            self.assertIn("score", r.__dict__)
            self.assertIn("preview", r.__dict__)
    
    def test_truncation_front(self):
        """Test front truncation."""
        long_text = "word " * 5000  # ~5000 tokens
        ctx = ContextManager(
            full_text=long_text,
            tokenizer=self.tokenizer,
            chunk_length=self.chunk_length,
            input_length=1000,
            manner="front"
        )
        
        self.assertEqual(ctx.get_token_count(), 1000)
    
    def test_truncation_middle(self):
        """Test middle truncation."""
        long_text = "word " * 5000  # ~5000 tokens
        ctx = ContextManager(
            full_text=long_text,
            tokenizer=self.tokenizer,
            chunk_length=self.chunk_length,
            input_length=1000,
            manner="middle"
        )
        
        self.assertEqual(ctx.get_token_count(), 1000)


class TestTools(unittest.TestCase):
    """Test tool registry and creation."""
    
    def test_available_tools(self):
        """Test that all tools are registered."""
        tools = available_tools()
        expected = ["bm25_search", "read_chunk", "read_range", "extract", "synthesize"]
        for tool in expected:
            self.assertIn(tool, tools)
    
    def test_create_all_tools(self):
        """Test creating all tool instances."""
        mock_client = Mock()
        mock_model = "test-model"
        mock_tokenizer = Mock()
        
        tools = create_all_tools(mock_client, mock_model, mock_tokenizer)
        
        self.assertEqual(len(tools), 5)
        for name in ["bm25_search", "read_chunk", "read_range", "extract", "synthesize"]:
            self.assertIn(name, tools)


class TestPrompts(unittest.TestCase):
    """Test prompt generation."""
    
    def test_create_system_prompt(self):
        """Test system prompt creation."""
        tool_descs = "- tool1: description1\n- tool2: description2"
        prompt = create_system_prompt(tool_descs)
        
        self.assertIn("multihop QA agent", prompt)
        self.assertIn("tool1", prompt)
        self.assertIn("tool2", prompt)
        self.assertIn("THOUGHT:", prompt)
        self.assertIn("ACTION:", prompt)
    
    def test_create_extract_prompt(self):
        """Test extract prompt creation."""
        prompt = create_extract_prompt("passage text", "question?", "prior evidence")
        
        self.assertIn("passage text", prompt)
        self.assertIn("question?", prompt)
        self.assertIn("prior evidence", prompt)
        self.assertIn("JSON", prompt)
    
    def test_create_synthesize_prompt(self):
        """Test synthesize prompt creation."""
        prompt = create_synthesize_prompt("evidence text", "question?")
        
        self.assertIn("evidence text", prompt)
        self.assertIn("question?", prompt)
        self.assertIn("JSON", prompt)


class TestAgentTools(unittest.TestCase):
    """Test individual tool execution."""
    
    def setUp(self):
        self.tokenizer = tiktoken.encoding_for_model("gpt-4o")
        self.text = "Einstein was born in Ulm, Germany. He developed the theory of relativity. " * 50
        self.ctx = ContextManager(
            full_text=self.text,
            tokenizer=self.tokenizer,
            chunk_length=200,
            input_length=2000,
            manner="front"
        )
    
    def test_bm25_search_tool(self):
        """Test BM25 search tool."""
        from src.agents.tools.bm25_search import BM25SearchTool
        
        tool = BM25SearchTool()
        result = tool.execute(self.ctx, query="Einstein born", top_k=3)
        
        self.assertTrue(result.success)
        self.assertIsInstance(result.data, list)
        self.assertLessEqual(len(result.data), 3)
    
    def test_read_chunk_tool(self):
        """Test read chunk tool."""
        from src.agents.tools.read_chunk import ReadChunkTool
        
        tool = ReadChunkTool()
        result = tool.execute(self.ctx, chunk_id=0)
        
        self.assertTrue(result.success)
        self.assertIn("text", result.data)
        self.assertIn("chunk_id", result.data)
    
    def test_read_range_tool(self):
        """Test read range tool."""
        from src.agents.tools.read_range import ReadRangeTool
        
        tool = ReadRangeTool()
        result = tool.execute(self.ctx, start_token=0, end_token=100)
        
        self.assertTrue(result.success)
        self.assertIn("text", result.data)
        self.assertEqual(result.data["token_start"], 0)
        self.assertEqual(result.data["token_end"], 100)


if __name__ == "__main__":
    unittest.main()