import unittest

from src.document_analysis import aggregate_clause_results, split_document_clauses
from src.standards_search import SearchResult


class DocumentAnalysisTests(unittest.TestCase):
    def test_split_document_clauses_preserves_distinct_specifications(self):
        text = (
            "1. Supply TMT reinforcement rods for the concrete slab.\n"
            "2. Provide LED street lighting fixtures for municipal poles.\n"
            "2. Provide LED street lighting fixtures for municipal poles."
        )

        clauses = split_document_clauses(text)

        self.assertEqual(len(clauses), 2)
        self.assertIn("TMT reinforcement rods", clauses[0])
        self.assertIn("LED street lighting", clauses[1])

    def test_aggregate_clause_results_keeps_supporting_evidence(self):
        standard = {"id": "STD-0002", "standard_code": "IS 1786:2008"}
        first = SearchResult(standard, 20.0, ["tmt"], ["keywords"])
        second = SearchResult(standard, 12.0, ["reinforcement"], ["title"])

        matches = aggregate_clause_results(
            [("TMT bars are required.", [first]), ("Reinforcement steel for RCC.", [second])],
            limit=5,
        )

        self.assertEqual(len(matches), 1)
        self.assertGreater(matches[0].result.score, 20.0)
        self.assertEqual(len(matches[0].evidence_clauses), 2)
        self.assertEqual(matches[0].result.matched_terms, ["reinforcement", "tmt"])


if __name__ == "__main__":
    unittest.main()
