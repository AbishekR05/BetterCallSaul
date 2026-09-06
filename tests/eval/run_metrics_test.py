# tests/eval/run_metrics_test.py
import sys
sys.path.append("d:/Abishek")
from tests.eval.test_metrics import test_dcg_and_ndcg_hand_computed, test_cohen_weighted_kappa, test_query_metrics_strict_vs_lenient

if __name__ == "__main__":
    print("Running metrics unit tests...")
    test_dcg_and_ndcg_hand_computed()
    print("  [PASSED] test_dcg_and_ndcg_hand_computed")
    test_cohen_weighted_kappa()
    print("  [PASSED] test_cohen_weighted_kappa")
    test_query_metrics_strict_vs_lenient()
    print("  [PASSED] test_query_metrics_strict_vs_lenient")
    print("\nALL METRICS UNIT TESTS PASSED SUCCESSFULLY!")
