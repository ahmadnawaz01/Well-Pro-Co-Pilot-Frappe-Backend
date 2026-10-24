"""
Unit tests for historical aggregation, exponential decay recency weighting,
confidence weighting, overall category score blending, and trend calculations.
"""
import unittest
import math
from datetime import date, timedelta
from well_pro.well_pro_app.services.scoring.aggregation import (
    calculate_overall_score,
    calculate_recency_weighted_score,
    calculate_trend
)


class TestAggregation(unittest.TestCase):
    def test_overall_score_complete(self):
        # Health = 80 (40%), Financial = 70 (35%), Social = 90 (25%)
        # overall = 80*0.40 + 70*0.35 + 90*0.25 = 32 + 24.5 + 22.5 = 79.0
        score, conf = calculate_overall_score(80.0, 100.0, 70.0, 100.0, 90.0, 100.0)
        self.assertEqual(score, 79.0)
        self.assertEqual(conf, 100.0)

    def test_overall_score_missing_category_renormalization(self):
        # Health = 80 (40%), Financial = 70 (35%), Social = Missing (conf=0)
        # Renormalized: (80 * 0.40 + 70 * 0.35) / (0.40 + 0.35) = 56.5 / 0.75 = 75.3
        score, conf = calculate_overall_score(80.0, 100.0, 70.0, 100.0, None, 0.0)
        self.assertEqual(score, 75.3)
        # Overall confidence is weighted: 100*0.4 + 100*0.35 + 0*0.25 = 75.0
        self.assertEqual(conf, 75.0)

    def test_overall_score_only_one_category(self):
        # Only Health data available
        score, conf = calculate_overall_score(90.0, 80.0, None, 0.0, None, 0.0)
        self.assertEqual(score, 90.0)
        self.assertEqual(conf, 32.0)  # 80 * 0.40 = 32.0

    def test_overall_score_all_missing(self):
        score, conf = calculate_overall_score(None, 0.0, None, 0.0, None, 0.0)
        self.assertIsNone(score)
        self.assertEqual(conf, 0.0)

    def test_exponential_recency_decay_weights(self):
        # Target date is today
        today = date(2026, 10, 23)
        half_life = 14.0
        decay_lambda = math.log(2.0) / half_life

        # Verify decay formula values:
        # Day 0: weight = 1.0 (100%)
        # Day 7: weight = exp(-ln(2)/14 * 7) = exp(-ln(2)/2) = 1/sqrt(2) ~= 0.7071
        # Day 14: weight = exp(-ln(2)) = 0.5 (50%)
        # Day 28: weight = 0.25 (25%)
        w0 = math.exp(-decay_lambda * 0)
        w7 = math.exp(-decay_lambda * 7)
        w14 = math.exp(-decay_lambda * 14)
        w28 = math.exp(-decay_lambda * 28)

        self.assertAlmostEqual(w0, 1.0, places=4)
        self.assertAlmostEqual(w7, 0.7071, places=4)
        self.assertAlmostEqual(w14, 0.5000, places=4)
        self.assertAlmostEqual(w28, 0.2500, places=4)

    def test_recency_weighted_period_score(self):
        today = date(2026, 10, 23)
        # Create 2 records: today score=100 (conf=100), 14 days ago score=50 (conf=100)
        records = [
            {"score_date": str(today), "score": 100.0, "conf": 100.0},
            {"score_date": str(today - timedelta(days=14)), "score": 50.0, "conf": 100.0}
        ]
        # Period score = (100 * 1.0 + 50 * 0.5) / (1.0 + 0.5) = 125 / 1.5 = 83.33 -> 83.3
        p_score, p_conf = calculate_recency_weighted_score(
            records, "score", "conf", days=30, as_of_date=today
        )
        self.assertEqual(p_score, 83.3)
        self.assertEqual(p_conf, 100.0)

    def test_confidence_weighting_in_history(self):
        # A day with high score but low confidence contributes less to period score
        today = date(2026, 10, 23)
        records = [
            # Day 0: score=50, conf=100 -> effective weight = 1.0 * 1.0 = 1.0
            {"score_date": str(today), "score": 50.0, "conf": 100.0},
            # Day 1: score=100, conf=10 -> effective weight = ~0.95 * 0.1 = 0.095
            {"score_date": str(today - timedelta(days=1)), "score": 100.0, "conf": 10.0}
        ]
        p_score, _ = calculate_recency_weighted_score(
            records, "score", "conf", days=30, as_of_date=today
        )
        # The low confidence day does not dominate; score stays close to 50
        self.assertTrue(50.0 <= p_score < 60.0)

    def test_trend_calculation(self):
        today = date(2026, 10, 23)
        # Test improving trend: recent 7 days = 90, previous 7 days = 70 (change = +20)
        improving_records = [
            {"score_date": str(today - timedelta(days=d)), "score": 90.0, "conf": 100.0}
            for d in range(0, 5)
        ] + [
            {"score_date": str(today - timedelta(days=d)), "score": 70.0, "conf": 100.0}
            for d in range(7, 12)
        ]
        trend_res = calculate_trend(improving_records, "score", "conf", as_of_date=today)
        self.assertEqual(trend_res["trend"], "improving")
        self.assertGreaterEqual(trend_res["trend_change"], 5.0)

        # Test declining trend
        declining_records = [
            {"score_date": str(today - timedelta(days=d)), "score": 60.0, "conf": 100.0}
            for d in range(0, 5)
        ] + [
            {"score_date": str(today - timedelta(days=d)), "score": 85.0, "conf": 100.0}
            for d in range(7, 12)
        ]
        trend_decl = calculate_trend(declining_records, "score", "conf", as_of_date=today)
        self.assertEqual(trend_decl["trend"], "declining")
        self.assertLessEqual(trend_decl["trend_change"], -5.0)

        # Test stable trend
        stable_records = [
            {"score_date": str(today - timedelta(days=d)), "score": 80.0, "conf": 100.0}
            for d in range(0, 5)
        ] + [
            {"score_date": str(today - timedelta(days=d)), "score": 79.0, "conf": 100.0}
            for d in range(7, 12)
        ]
        trend_stab = calculate_trend(stable_records, "score", "conf", as_of_date=today)
        self.assertEqual(trend_stab["trend"], "stable")

        # Test insufficient data
        single_record = [{"score_date": str(today), "score": 80.0, "conf": 100.0}]
        trend_insuf = calculate_trend(single_record, "score", "conf", as_of_date=today)
        self.assertEqual(trend_insuf["trend"], "insufficient_data")
        self.assertIsNone(trend_insuf["trend_change"])


if __name__ == "__main__":
    unittest.main()
