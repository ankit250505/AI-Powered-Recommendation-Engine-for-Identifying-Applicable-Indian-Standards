import unittest

from src.hybrid_search import HybridSearchEngine
from src.embedding_search import standard_embedding_text
from src.standards_search import load_standards, search_standards


class StandardsSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.standards = load_standards()

    def test_tmt_bars_match_reinforcement_standard_first(self):
        results = search_standards("TMT bars for RCC work", self.standards, limit=3)

        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].standard["standard_code"], "IS 1786:2008")
        self.assertIn("tmt", results[0].matched_terms)

    def test_led_street_light_match_street_luminaire_first(self):
        results = search_standards("LED street lights for road project", self.standards, limit=3)

        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].standard["standard_code"], "IS 16107 Part 2 Section 2:2017")

    def test_direct_standard_code_lookup(self):
        results = search_standards("IS 1786", self.standards, limit=3)

        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].standard["standard_code"], "IS 1786:2008")
        self.assertIn("standard_code", results[0].matched_fields)

    def test_hybrid_search_handles_reinforcement_rods_wording(self):
        engine = HybridSearchEngine(self.standards)

        results = engine.search("reinforcement rods for concrete slab", limit=3)

        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].standard["standard_code"], "IS 1786:2008")
        self.assertIn("vector_similarity", results[0].matched_fields)

    def test_hybrid_search_handles_road_lighting_fixture_wording(self):
        engine = HybridSearchEngine(self.standards)

        results = engine.search("road lighting fixtures for municipal poles", limit=3)

        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].standard["standard_code"], "IS 16107 Part 2 Section 2:2017")

    def test_embedding_text_includes_labelled_procurement_context(self):
        text = standard_embedding_text(self.standards[1])

        self.assertIn("Indian Standard: IS 1786:2008", text)
        self.assertIn("Title:", text)
        self.assertIn("Procurement Examples:", text)


if __name__ == "__main__":
    unittest.main()
