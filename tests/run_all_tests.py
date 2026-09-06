# tests/run_all_tests.py
"""
Test runner for Phase 2.3 Legal Retrieval Pipeline test suite.
Runs all unit and functional test cases.
"""

import sys
import unittest

sys.path.append("d:/Abishek")

from tests.retrieval.test_preprocessing import (
    test_preprocess_valid_query,
    test_preprocess_unicode_normalization,
    test_preprocess_empty_query,
    test_preprocess_truncation
)
from tests.retrieval.test_prefix_handling import (
    test_bge_prefix_constant_exact_match,
    test_format_bge_query_applies_prefix
)
from tests.retrieval.test_filters import (
    test_empty_filters,
    test_jurisdiction_and_source_type_filter,
    test_domain_list_filter
)
from tests.retrieval.test_result_schema import test_retrieval_result_json_serialization

from src.retrieval.config import RetrievalConfig, RetrievalFilters
from src.retrieval.retriever import LegalRetriever

class Phase23UnitTests(unittest.TestCase):
    def test_01_preprocessing_valid(self):
        test_preprocess_valid_query()
        
    def test_02_preprocessing_unicode(self):
        test_preprocess_unicode_normalization()
        
    def test_03_preprocessing_empty(self):
        test_preprocess_empty_query()
        
    def test_04_preprocessing_truncation(self):
        test_preprocess_truncation()

    def test_05_bge_prefix_exact(self):
        test_bge_prefix_constant_exact_match()

    def test_06_bge_prefix_formatting(self):
        test_format_bge_query_applies_prefix()

    def test_07_filters_empty(self):
        test_empty_filters()

    def test_08_filters_jurisdiction(self):
        test_jurisdiction_and_source_type_filter()

    def test_09_filters_domains(self):
        test_domain_list_filter()

    def test_10_result_schema_json(self):
        test_retrieval_result_json_serialization()

class Phase23FunctionalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cfg = RetrievalConfig(
            use_gpu=True,
            final_k=5,
            high_confidence_threshold=0.50,
            low_confidence_threshold=0.35
        )
        cls.retriever = LegalRetriever(config=cfg)

    def test_case_1_successful_retrieval(self):
        query = "What are the rules regarding tenant security deposit refund?"
        res = self.retriever.retrieve(query)
        self.assertIsNone(res.error)
        self.assertGreater(res.returned_count, 0)
        self.assertGreaterEqual(res.results[0].similarity_score, 0.35)

    def test_case_2_metadata_filtering(self):
        query = "What is the procedure for filing an environmental clearance application?"
        filters = RetrievalFilters(jurisdiction="central")
        res = self.retriever.retrieve(query, filters=filters)
        self.assertIsNone(res.error)
        for item in res.results:
            self.assertEqual(item.provenance.jurisdiction.lower(), "central")

    def test_case_3_cross_jurisdiction(self):
        query = "land acquisition compensation procedure"
        res_unfiltered = self.retriever.retrieve(query)
        self.assertGreater(res_unfiltered.returned_count, 0)

        filters = RetrievalFilters(source_type="legislation")
        res_filtered = self.retriever.retrieve(query, filters=filters)
        self.assertIsNone(res_filtered.error)
        for item in res_filtered.results:
            self.assertEqual(item.provenance.source_type, "legislation")

    def test_case_4_legislation_retrieval(self):
        query = "Section 43 Maharashtra Rent Control Act tenant deposit"
        filters = RetrievalFilters(source_type="legislation")
        res = self.retriever.retrieve(query, filters=filters)
        self.assertGreater(res.returned_count, 0)
        self.assertEqual(res.results[0].provenance.source_type, "legislation")

    def test_case_5_judgment_retrieval(self):
        query = "High Court judgment on bail in non-bailable offense"
        filters = RetrievalFilters(source_type="judgment")
        res = self.retriever.retrieve(query, filters=filters)
        self.assertIsNone(res.error)
        if res.returned_count > 0:
            self.assertEqual(res.results[0].provenance.source_type, "judgment")

    def test_case_6_mixed_retrieval(self):
        query = "tenant eviction notice period and court rulings"
        res = self.retriever.retrieve(query)
        self.assertIsNone(res.error)
        self.assertGreater(res.returned_count, 0)
        scores = [item.similarity_score for item in res.results]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_case_7_ambiguous_question(self):
        query = "Can I do that legal thing?"
        res = self.retriever.retrieve(query)
        self.assertIsNone(res.error)
        if res.returned_count > 0:
            self.assertLess(res.results[0].similarity_score, 0.65)

    def test_case_8_no_evidence_question(self):
        query = "Quantum mechanics wave function collapse protocol in Martian colony 2099"
        cfg = RetrievalConfig(low_confidence_threshold=0.55, min_acceptable_results=1)
        res = self.retriever.retrieve(query, config=cfg)
        self.assertIsNone(res.error)
        self.assertTrue(res.insufficient_evidence)


if __name__ == "__main__":
    unittest.main(verbosity=2)
