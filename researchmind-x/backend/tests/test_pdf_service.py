import unittest

from app.services.pdf_service import build_chunks, detect_heading


class PdfChunkTests(unittest.TestCase):
    def test_chunks_do_not_cross_page_boundaries(self):
        first = "First page evidence explains the method used in this study."
        second = "Second page evidence describes the limitations of the experiment."
        chunks = build_chunks([(1, ["Methodology", first]), (2, [second])])
        self.assertEqual([(c.page_number, c.text) for c in chunks], [(1, first), (2, second)])
        self.assertTrue(all(c.section == "methodology" for c in chunks))

    def test_sections_do_not_mix(self):
        chunks = build_chunks([(1, ["Methods", "A method description with enough text to form a full chunk.",
                                    "Limitations", "A limitation description with enough text to form a full chunk."])])
        self.assertEqual([c.section for c in chunks], ["methodology", "limitations"])

    def test_large_overlap_still_makes_progress(self):
        chunks = build_chunks([(1, ["long content " * 30])], max_chars=80, overlap=79)
        self.assertTrue(chunks)
        self.assertTrue(all(len(c.text) <= 80 for c in chunks))

    def test_invalid_chunk_settings_fail(self):
        for max_chars, overlap in [(0, 0), (30, 0), (80, -1), (80, 80)]:
            with self.subTest(max_chars=max_chars, overlap=overlap):
                with self.assertRaises(ValueError):
                    build_chunks([], max_chars=max_chars, overlap=overlap)

    def test_lowercase_prose_is_not_a_heading(self):
        self.assertIsNone(detect_heading("results"))
        self.assertEqual(detect_heading("3. Results"), "results")


if __name__ == "__main__":
    unittest.main()
