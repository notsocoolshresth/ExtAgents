"""Unit tests for src/chunkers.py — pluggable chunking strategies.

Run from repo root:
    python -m unittest discover -s tests -t .
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import chunkers
from src import utils


class WordTokenizer:
    """Deterministic tokenizer mirroring tiktoken's whitespace preservation:
    one token per maximal run of non-whitespace or of whitespace; decode rejoins
    exactly."""

    TOKEN_RE = re.compile(r"\S+|\s+")

    def encode(self, text):
        return self.TOKEN_RE.findall(text)

    def decode(self, tokens):
        return "".join(tokens)


class RealTokenizerTestCase(unittest.TestCase):
    """Base class using the production tiktoken gpt-4o encoding."""

    @classmethod
    def setUpClass(cls):
        try:
            import tiktoken

            cls.tokenizer = tiktoken.encoding_for_model("gpt-4o")
        except Exception as exc:
            raise unittest.SkipTest(f"tiktoken gpt-4o encoding unavailable: {exc}")


class TestLegacyBaseline(RealTokenizerTestCase):
    def _cases(self):
        return [
            "Short context.",
            " ".join(f"w{i}" for i in range(5000)),
            ("Alpha sentence here. " * 20) + "\n\n" + ("Beta sentence here. " * 20),
        ]

    def test_byte_identical_legacy(self):
        tok = WordTokenizer()
        for ctx in self._cases():
            for cl, il, manner in (
                (200, 500, "front"),
                (200, 300, "middle"),
                (9999, 100000, "middle"),
            ):
                with self.subTest(ctx=ctx[:24], cl=cl, il=il, manner=manner):
                    self.assertEqual(
                        chunkers.get("legacy")(tok, ctx, cl, il, manner),
                        utils.create_chunks(tok, ctx, cl, il, manner),
                    )

    def test_byte_identical_legacy_real_tokenizer(self):
        ctx = ("The quick brown fox jumps over the lazy dog. " * 40) + "\n\n" + (
            "Another paragraph containing several English sentences. " * 40
        )
        for cl, il, manner in (
            (100, 2000, "front"),
            (300, 1500, "middle"),
            (50, 100000, "middle"),
        ):
            with self.subTest(cl=cl, il=il, manner=manner):
                self.assertEqual(
                    chunkers.get("legacy")(self.tokenizer, ctx, cl, il, manner),
                    utils.create_chunks(self.tokenizer, ctx, cl, il, manner),
                )


class TestRecursiveParagraph(unittest.TestCase):
    def setUp(self):
        self.tok = WordTokenizer()

    def test_paragraphs_kept_whole_in_order(self):
        words = [f"p{i}w{j}" for i in range(3) for j in range(100)]
        paragraphs = [" ".join(words[i * 100 : (i + 1) * 100]) for i in range(3)]
        context = "\n\n".join(paragraphs)

        chunks = chunkers.get("recursive_paragraph")(
            self.tok, context, 250, 10000, "front"
        )

        flat = [w for c in chunks for w in self.tok.encode(c) if w.strip()]
        self.assertEqual(flat, words)

        word_chunks = []
        for ci, c in enumerate(chunks):
            word_chunks.extend(
                [ci] * len([w for w in self.tok.encode(c) if w.strip()])
            )
        for p in range(3):
            chunk_ids = set(word_chunks[p * 100 : (p + 1) * 100])
            self.assertEqual(len(chunk_ids), 1, f"paragraph {p} split across chunks")

    def test_boundary_placement_differs_from_legacy(self):
        context = "one two three four\n\nfive six seven eight"
        cl, il = 3, 100
        recursive = chunkers.get("recursive_paragraph")(self.tok, context, cl, il, "front")
        legacy = utils.create_chunks(self.tok, context, cl, il, "front")
        self.assertNotEqual(recursive, legacy)
        for c in recursive:
            self.assertLessEqual(len(self.tok.encode(c)), cl)

    def test_chunks_within_budget(self):
        para = " ".join(f"w{i}" for i in range(150))
        context = "\n\n".join(para for _ in range(3))
        for cl in (50, 100, 250):
            with self.subTest(cl=cl):
                chunks = chunkers.get("recursive_paragraph")(
                    self.tok, context, cl, 100000, "middle"
                )
                self.assertTrue(chunks)
                for c in chunks:
                    self.assertLessEqual(len(self.tok.encode(c)), cl)

    def test_oversized_paragraph_recurses_to_sentences(self):
        context = "Sentence one is here. " * 80
        cl = 100
        chunks = chunkers.get("recursive_paragraph")(self.tok, context, cl, 100000, "middle")
        self.assertGreater(len(chunks), 1)
        for c in chunks:
            self.assertLessEqual(len(self.tok.encode(c)), cl)

    def test_oversized_sentence_recurses_to_words(self):
        context = " ".join(f"w{i}" for i in range(400))
        cl = 100
        chunks = chunkers.get("recursive_paragraph")(self.tok, context, cl, 100000, "middle")
        self.assertTrue(chunks)
        for c in chunks:
            self.assertLessEqual(len(self.tok.encode(c)), cl)
            for w in self.tok.encode(c):
                if w.strip():
                    self.assertTrue(w.startswith("w"), f"word split mid-token: {w!r}")

    def test_giant_unbreakable_unit_slices(self):
        context = "Q" * 300
        cl = 50
        chunks = chunkers.get("recursive_paragraph")(self.tok, context, cl, 100000, "middle")
        self.assertEqual(chunks, ["Q" * 300])

    def test_manner_front_truncates_tail(self):
        words = [f"w{i}" for i in range(200)]
        context = " ".join(words)
        chunks = chunkers.get("recursive_paragraph")(self.tok, context, 500, 100, "front")
        flat = set(w for c in chunks for w in self.tok.encode(c))
        self.assertIn("w0", flat)
        self.assertNotIn("w150", flat)

    def test_manner_middle_keeps_head_and_tail(self):
        words = [f"w{i}" for i in range(200)]
        context = " ".join(words)
        chunks = chunkers.get("recursive_paragraph")(self.tok, context, 500, 100, "middle")
        flat = set(w for c in chunks for w in self.tok.encode(c))
        self.assertIn("w0", flat)
        self.assertIn("w199", flat)

    def test_empty_context(self):
        self.assertEqual(
            chunkers.get("recursive_paragraph")(self.tok, "", 100, 100, "front"), []
        )
        self.assertEqual(chunkers.get("legacy")(self.tok, "", 100, 100, "front"), [])

    def test_nonpositive_chunk_length_raises(self):
        with self.assertRaises(ValueError):
            chunkers.get("recursive_paragraph")(self.tok, "x", 0, 100, "front")


class TestRecursiveParagraphRealTokens(RealTokenizerTestCase):
    def test_budget_enforced_across_sizes(self):
        para = "Paraguay is a country in South America bounded by rivers. " * 60
        context = "\n\n".join(para for _ in range(4))
        for cl in (100, 250, 500, 1000):
            with self.subTest(cl=cl):
                chunks = chunkers.get("recursive_paragraph")(
                    self.tokenizer, context, cl, 200000, "middle"
                )
                self.assertTrue(chunks)
                for c in chunks:
                    self.assertLessEqual(len(self.tokenizer.encode(c)), cl)

    def test_long_unbroken_text_can_be_sliced(self):
        context = "Q" * 5000
        cl = 100
        chunks = chunkers.get("recursive_paragraph")(
            self.tokenizer, context, cl, 5000, "middle"
        )
        self.assertGreater(len(chunks), 1)
        for c in chunks:
            self.assertLessEqual(len(self.tokenizer.encode(c)), cl)


class TestOverlap(unittest.TestCase):
    def setUp(self):
        self.tok = WordTokenizer()

    def test_chunks_within_budget(self):
        words = [f"w{i}" for i in range(200)]
        context = " ".join(words)
        for cl in (25, 50, 100):
            with self.subTest(cl=cl):
                chunks = chunkers.get("overlap")(
                    self.tok, context, cl, 100000, "front"
                )
                self.assertTrue(chunks)
                for c in chunks:
                    self.assertLessEqual(len(self.tok.encode(c)), cl)

    def test_overlap_produces_more_chunks_than_legacy(self):
        words = [f"w{i}" for i in range(200)]
        context = " ".join(words)
        cl = 30
        overlap_chunks = chunkers.get("overlap")(
            self.tok, context, cl, 100000, "front"
        )
        legacy_chunks = utils.create_chunks(self.tok, context, cl, 100000, "front")
        self.assertGreater(len(overlap_chunks), len(legacy_chunks))

    def test_overlap_ratio_zero_matches_legacy_style(self):
        """overlap_ratio=0 should produce non-overlapping chunks (like legacy)."""
        words = [f"w{i}" for i in range(200)]
        context = " ".join(words)
        cl = 30
        chunks = chunkers.get("overlap")(
            self.tok, context, cl, 100000, "front", overlap_ratio=0.0
        )
        for c in chunks:
            self.assertLessEqual(len(self.tok.encode(c)), cl)
        # All content should be covered
        flat = [w for c in chunks for w in self.tok.encode(c) if w.strip()]
        self.assertEqual(flat, words)

    def test_overlap_covers_all_content(self):
        words = [f"w{i}" for i in range(200)]
        context = " ".join(words)
        cl = 30
        chunks = chunkers.get("overlap")(
            self.tok, context, cl, 100000, "front", overlap_ratio=0.5
        )
        # Every word should appear in at least one chunk
        all_words = set()
        for c in chunks:
            for w in self.tok.encode(c):
                if w.strip():
                    all_words.add(w)
        for w in words:
            self.assertIn(w, all_words, f"word {w} missing from overlap chunks")

    def test_boundary_straddling_evidence_recovered(self):
        """Two facts on either side of a boundary should both appear in some chunk."""
        fact_a = "the answer is blue"
        fact_b = "the answer is red"
        context = fact_a + " " + fact_b
        cl = 5  # very small chunks force splitting
        chunks = chunkers.get("overlap")(
            self.tok, context, cl, 100000, "front", overlap_ratio=0.5
        )
        all_text = " ".join(chunks)
        self.assertIn("blue", all_text)
        self.assertIn("red", all_text)

    def test_empty_context(self):
        self.assertEqual(
            chunkers.get("overlap")(self.tok, "", 100, 100, "front"), []
        )

    def test_nonpositive_chunk_length_raises(self):
        with self.assertRaises(ValueError):
            chunkers.get("overlap")(self.tok, "x", 0, 100, "front")

    def test_invalid_overlap_ratio_raises(self):
        with self.assertRaises(ValueError):
            chunkers.get("overlap")(self.tok, "x", 100, 100, "front", overlap_ratio=1.0)
        with self.assertRaises(ValueError):
            chunkers.get("overlap")(self.tok, "x", 100, 100, "front", overlap_ratio=-0.1)

    def test_manner_front_truncates_tail(self):
        words = [f"w{i}" for i in range(200)]
        context = " ".join(words)
        chunks = chunkers.get("overlap")(
            self.tok, context, 500, 100, "front", overlap_ratio=0.5
        )
        flat = set(w for c in chunks for w in self.tok.encode(c))
        self.assertIn("w0", flat)
        self.assertNotIn("w150", flat)

    def test_manner_middle_keeps_head_and_tail(self):
        words = [f"w{i}" for i in range(200)]
        context = " ".join(words)
        chunks = chunkers.get("overlap")(
            self.tok, context, 500, 100, "middle", overlap_ratio=0.5
        )
        flat = set(w for c in chunks for w in self.tok.encode(c))
        self.assertIn("w0", flat)
        self.assertIn("w199", flat)


class TestOverlapRealTokens(RealTokenizerTestCase):
    def test_budget_enforced_across_sizes(self):
        para = "Paraguay is a country in South America bounded by rivers. " * 60
        context = "\n\n".join(para for _ in range(4))
        for cl in (100, 250, 500, 1000):
            with self.subTest(cl=cl):
                chunks = chunkers.get("overlap")(
                    self.tokenizer, context, cl, 200000, "middle"
                )
                self.assertTrue(chunks)
                for c in chunks:
                    self.assertLessEqual(len(self.tokenizer.encode(c)), cl)

    def test_overlap_produces_more_chunks_than_legacy(self):
        context = ("The quick brown fox jumps over the lazy dog. " * 40) + "\n\n" + (
            "Another paragraph containing several English sentences. " * 40
        )
        cl = 200
        overlap_chunks = chunkers.get("overlap")(
            self.tokenizer, context, cl, 200000, "middle"
        )
        legacy_chunks = utils.create_chunks(
            self.tokenizer, context, cl, 200000, "middle"
        )
        self.assertGreater(len(overlap_chunks), len(legacy_chunks))


class TestSemantic(unittest.TestCase):
    """Tests for C4 semantic chunking (mocked embedder — no model download needed)."""

    def setUp(self):
        self.tok = WordTokenizer()

    def _mock_semantic_chunks(self, text, chunk_length, input_length=100000, manner="front"):
        """Call semantic_chunks with a mocked SemanticChunker.split_text."""
        from unittest.mock import patch, MagicMock

        def _split_like_semantic(t):
            """Split text on whitespace (simulates sentence-level splitting)."""
            import re
            parts = re.split(r"\s+", t)
            return [p for p in parts if p.strip()]

        with patch("src.chunkers.semantic.SemanticChunker") as MockSC:
            mock_instance = MagicMock()
            mock_instance.split_text.side_effect = _split_like_semantic
            MockSC.return_value = mock_instance

            with patch("src.chunkers.semantic._get_embedder", return_value=MagicMock()):
                return chunkers.get("semantic")(
                    self.tok, text, chunk_length, input_length, manner
                )

    def test_basic_sentence_splitting(self):
        context = "First sentence here. Second sentence here. Third sentence here."
        chunks = self._mock_semantic_chunks(context, 100)
        self.assertTrue(chunks)
        flat = " ".join(chunks)
        self.assertIn("First", flat)
        self.assertIn("Third", flat)

    def test_budget_enforced(self):
        context = ("Short sentence. " * 50).strip()
        chunks = self._mock_semantic_chunks(context, 10)
        self.assertTrue(chunks)
        for c in chunks:
            self.assertLessEqual(len(self.tok.encode(c)), 10)

    def test_oversized_chunk_gets_split(self):
        context = "A very long sentence that goes on and on. " * 20
        chunks = self._mock_semantic_chunks(context, 15)
        self.assertGreater(len(chunks), 1)
        for c in chunks:
            self.assertLessEqual(len(self.tok.encode(c)), 15)

    def test_tiny_chunks_get_merged(self):
        """Chunks under 10% of budget should be merged into neighbors."""
        from unittest.mock import patch, MagicMock

        normal_a = "This is a normal chunk with enough tokens. " * 3
        tiny = "Hi."
        normal_b = "This is another normal chunk with enough tokens. " * 3

        with patch("src.chunkers.semantic.SemanticChunker") as MockSC:
            mock_instance = MagicMock()
            mock_instance.split_text.return_value = [normal_a, tiny, normal_b]
            MockSC.return_value = mock_instance
            with patch("src.chunkers.semantic._get_embedder", return_value=MagicMock()):
                chunks = chunkers.get("semantic")(
                    self.tok, "unused", 200, 100000, "front"
                )
        # The tiny chunk should be merged (not be a separate chunk)
        self.assertLessEqual(len(chunks), 2)

    def test_empty_context(self):
        self.assertEqual(
            chunkers.get("semantic")(self.tok, "", 100, 100, "front"), []
        )

    def test_nonpositive_chunk_length_raises(self):
        with self.assertRaises(ValueError):
            chunkers.get("semantic")(self.tok, "x", 0, 100, "front")

    def test_manner_front_truncates_tail(self):
        words = [f"w{i}" for i in range(200)]
        context = " ".join(words)
        chunks = self._mock_semantic_chunks(context, 500, 100, "front")
        flat = set(w for c in chunks for w in self.tok.encode(c))
        self.assertIn("w0", flat)
        self.assertNotIn("w150", flat)

    def test_manner_middle_keeps_head_and_tail(self):
        words = [f"w{i}" for i in range(200)]
        context = " ".join(words)
        chunks = self._mock_semantic_chunks(context, 500, 100, "middle")
        flat = set(w for c in chunks for w in self.tok.encode(c))
        self.assertIn("w0", flat)
        self.assertIn("w199", flat)


class TestSemanticRealTokens(RealTokenizerTestCase):
    """Integration test — requires sentence-transformers model download."""

    def test_budget_enforced_with_real_tokenizer(self):
        try:
            import sentence_transformers  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("sentence-transformers not installed")

        context = (
            "The quick brown fox jumps over the lazy dog. "
            * 30
        ) + "\n\n" + (
            "A different paragraph about something else entirely. "
            * 30
        )
        cl = 200
        chunks = chunkers.get("semantic")(
            self.tokenizer, context, cl, 200000, "middle"
        )
        self.assertTrue(chunks)
        for c in chunks:
            self.assertLessEqual(len(self.tokenizer.encode(c)), cl)


class TestDocumentStructure(unittest.TestCase):
    """Tests for C5 document-structure-aware chunking."""

    def setUp(self):
        self.tok = WordTokenizer()

    def _section(self, label, repeats=15):
        """Build a token-countable section with a clear label word."""
        return " ".join(f"{label}{i}" for i in range(repeats))

    def test_chapter_markers_detected(self):
        context = (
            self._section("pre", 12)
            + "\n\nChapter 1\n\n"
            + self._section("ch1", 12)
        )
        chunks = chunkers.get("document_structure")(
            self.tok, context, 30, 10000, "front"
        )
        self.assertTrue(chunks)
        for c in chunks:
            self.assertLessEqual(len(self.tok.encode(c)), 30)
        # The chapter marker should begin a chunk.
        self.assertTrue(
            any(c.strip().startswith("Chapter 1") for c in chunks),
            f"no chunk starts with chapter marker: {chunks!r}",
        )

    def test_all_caps_lines_detected(self):
        context = (
            self._section("pre", 12)
            + "\n\nTHE BEGINNING\n\n"
            + self._section("mid", 12)
        )
        chunks = chunkers.get("document_structure")(
            self.tok, context, 30, 10000, "front"
        )
        self.assertTrue(
            any(c.strip().startswith("THE BEGINNING") for c in chunks),
            f"ALL-CAPS heading not a boundary: {chunks!r}",
        )

    def test_roman_numerals_detected(self):
        context = (
            self._section("pre", 12)
            + "\n\nXII\n\n"
            + self._section("mid", 12)
        )
        chunks = chunkers.get("document_structure")(
            self.tok, context, 30, 10000, "front"
        )
        self.assertTrue(
            any(c.strip().startswith("XII") for c in chunks),
            f"Roman numeral not a boundary: {chunks!r}",
        )

    def test_asterisk_separator_detected(self):
        context = (
            self._section("pre", 12)
            + "\n\n* * * * *\n\n"
            + self._section("post", 12)
        )
        chunks = chunkers.get("document_structure")(
            self.tok, context, 30, 10000, "front"
        )
        self.assertTrue(
            any(c.strip().startswith("* * * * *") for c in chunks),
            f"asterisk separator not a boundary: {chunks!r}",
        )

    def test_date_heading_detected(self):
        context = (
            self._section("pre", 12)
            + "\n\nMONDAY, JANUARY 1, 2024\n\n"
            + self._section("post", 12)
        )
        chunks = chunkers.get("document_structure")(
            self.tok, context, 30, 10000, "front"
        )
        self.assertTrue(
            any("MONDAY, JANUARY 1, 2024" in c for c in chunks),
            f"date heading not detected: {chunks!r}",
        )

    def test_part_heading_detected(self):
        context = (
            self._section("pre", 12)
            + "\n\nPart Two\n\n"
            + self._section("post", 12)
        )
        chunks = chunkers.get("document_structure")(
            self.tok, context, 30, 10000, "front"
        )
        self.assertTrue(
            any(c.strip().startswith("Part Two") for c in chunks),
            f"Part heading not a boundary: {chunks!r}",
        )

    def test_no_markers_falls_back_to_recursive_paragraph(self):
        """Structureless text should behave like C3."""
        context = "one two three four\n\nfive six seven eight"
        c5 = chunkers.get("document_structure")(
            self.tok, context, 3, 100, "front"
        )
        c3 = chunkers.get("recursive_paragraph")(
            self.tok, context, 3, 100, "front"
        )
        self.assertEqual(c5, c3)

    def test_oversized_section_gets_split(self):
        context = "Chapter 1\n\n" + self._section("big", 200)
        chunks = chunkers.get("document_structure")(
            self.tok, context, 50, 10000, "front"
        )
        self.assertGreater(len(chunks), 1)
        for c in chunks:
            self.assertLessEqual(len(self.tok.encode(c)), 50)

    def test_tiny_sections_merge_into_neighbors(self):
        context = (
            "Chapter 1\n\n"
            + self._section("a", 5)
            + "\n\nChapter 2\n\n"
            + self._section("b", 5)
        )
        chunks = chunkers.get("document_structure")(
            self.tok, context, 100, 10000, "front"
        )
        # With a large budget, two tiny chapters should fit in one chunk.
        self.assertEqual(len(chunks), 1)
        self.assertIn("Chapter 1", chunks[0])
        self.assertIn("Chapter 2", chunks[0])

    def test_manner_front_truncates_tail(self):
        words = [f"w{i}" for i in range(200)]
        context = " ".join(words)
        chunks = chunkers.get("document_structure")(
            self.tok, context, 500, 100, "front"
        )
        flat = set(w for c in chunks for w in self.tok.encode(c))
        self.assertIn("w0", flat)
        self.assertNotIn("w150", flat)

    def test_manner_middle_keeps_head_and_tail(self):
        words = [f"w{i}" for i in range(200)]
        context = " ".join(words)
        chunks = chunkers.get("document_structure")(
            self.tok, context, 500, 100, "middle"
        )
        flat = set(w for c in chunks for w in self.tok.encode(c))
        self.assertIn("w0", flat)
        self.assertIn("w199", flat)

    def test_empty_context(self):
        self.assertEqual(
            chunkers.get("document_structure")(self.tok, "", 100, 100, "front"),
            [],
        )

    def test_nonpositive_chunk_length_raises(self):
        with self.assertRaises(ValueError):
            chunkers.get("document_structure")(self.tok, "x", 0, 100, "front")


class TestDocumentStructureRealTokens(RealTokenizerTestCase):
    def test_budget_enforced_with_real_tokenizer(self):
        context = (
            "Chapter 1\n\n"
            + ("The quick brown fox jumps over the lazy dog. " * 40)
            + "\n\nChapter 2\n\n"
            + ("Another paragraph containing several English sentences. " * 40)
        )
        for cl in (100, 250, 500, 1000):
            with self.subTest(cl=cl):
                chunks = chunkers.get("document_structure")(
                    self.tokenizer, context, cl, 200000, "middle"
                )
                self.assertTrue(chunks)
                for c in chunks:
                    self.assertLessEqual(len(self.tokenizer.encode(c)), cl)


class TestRegistryAndInstall(unittest.TestCase):
    def setUp(self):
        chunkers.restore()
        self.addCleanup(chunkers.restore)

    def test_available(self):
        self.assertEqual(
            chunkers.available(),
            ["document_structure", "legacy", "overlap", "recursive_paragraph", "semantic"],
        )

    def test_unknown_chunker_raises(self):
        with self.assertRaises(ValueError):
            chunkers.get("nope")
        with self.assertRaises(ValueError):
            chunkers.install("nope")

    def test_duplicate_registration_raises(self):
        with self.assertRaises(ValueError):
            chunkers.register("legacy")(lambda *a, **k: [])

    def test_install_swaps_then_restore(self):
        tok = WordTokenizer()
        context = "one two three four\n\nfive six seven eight"
        args = (tok, context, 3, 100, "front")

        baseline = utils.create_chunks(*args)
        self.assertEqual(chunkers.get("legacy")(*args), baseline)

        active = chunkers.install("recursive_paragraph")
        self.assertIs(active, chunkers.get("recursive_paragraph"))
        self.assertIs(utils.create_chunks, chunkers.get("recursive_paragraph"))
        self.assertNotEqual(utils.create_chunks(*args), baseline)

        chunkers.restore()
        self.assertEqual(utils.create_chunks(*args), baseline)


if __name__ == "__main__":
    unittest.main()