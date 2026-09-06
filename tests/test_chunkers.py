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


class TestRegistryAndInstall(unittest.TestCase):
    def setUp(self):
        chunkers.restore()
        self.addCleanup(chunkers.restore)

    def test_available(self):
        self.assertEqual(
            chunkers.available(), ["legacy", "overlap", "recursive_paragraph"]
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