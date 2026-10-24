"""
Unit tests for metric normalization functions.
Tests clamping, ratings, inverse ratings, target ranges, higher/lower is better,
and missing/None input handling.
"""
import unittest
from well_pro.well_pro_app.services.scoring.normalization import (
    clamp,
    normalize_rating,
    normalize_inverse_rating,
    normalize_higher_is_better,
    normalize_lower_is_better,
    normalize_target_range
)


class TestNormalization(unittest.TestCase):
    def test_clamping(self):
        self.assertEqual(clamp(50), 50.0)
        self.assertEqual(clamp(-10), 0.0)
        self.assertEqual(clamp(150), 100.0)
        self.assertEqual(clamp(0), 0.0)
        self.assertEqual(clamp(100), 100.0)
        self.assertEqual(clamp("invalid", 0.0, 100.0), 0.0)

    def test_positive_rating(self):
        # 1-5 scale to 0-100: 1->0, 2->25, 3->50, 4->75, 5->100
        self.assertEqual(normalize_rating(1), 0.0)
        self.assertEqual(normalize_rating(2), 25.0)
        self.assertEqual(normalize_rating(3), 50.0)
        self.assertEqual(normalize_rating(4), 75.0)
        self.assertEqual(normalize_rating(5), 100.0)
        # Test None and invalid
        self.assertIsNone(normalize_rating(None))
        self.assertIsNone(normalize_rating("abc"))

    def test_inverse_rating(self):
        # 1-5 scale inverse (stress/loneliness): 1->100, 2->75, 3->50, 4->25, 5->0
        self.assertEqual(normalize_inverse_rating(1), 100.0)
        self.assertEqual(normalize_inverse_rating(2), 75.0)
        self.assertEqual(normalize_inverse_rating(3), 50.0)
        self.assertEqual(normalize_inverse_rating(4), 25.0)
        self.assertEqual(normalize_inverse_rating(5), 0.0)
        self.assertIsNone(normalize_inverse_rating(None))

    def test_higher_is_better(self):
        # Target 10,000 steps
        self.assertEqual(normalize_higher_is_better(10000, 10000), 100.0)
        self.assertEqual(normalize_higher_is_better(5000, 10000), 50.0)
        self.assertEqual(normalize_higher_is_better(0, 10000), 0.0)
        self.assertEqual(normalize_higher_is_better(15000, 10000), 100.0)  # Capped at 100
        self.assertEqual(normalize_higher_is_better(15000, 10000, cap_multiplier=1.2), 100.0)
        # Division by zero protection
        self.assertEqual(normalize_higher_is_better(10, 0), 100.0)
        self.assertIsNone(normalize_higher_is_better(None, 10000))

    def test_lower_is_better(self):
        # Good <= 0.15, Bad >= 0.35
        self.assertEqual(normalize_lower_is_better(0.10, 0.15, 0.35), 100.0)
        self.assertEqual(normalize_lower_is_better(0.15, 0.15, 0.35), 100.0)
        self.assertEqual(normalize_lower_is_better(0.25, 0.15, 0.35), 50.0)
        self.assertEqual(normalize_lower_is_better(0.35, 0.15, 0.35), 0.0)
        self.assertEqual(normalize_lower_is_better(0.50, 0.15, 0.35), 0.0)
        self.assertIsNone(normalize_lower_is_better(None, 0.15, 0.35))

    def test_target_range(self):
        # Optimal sleep 7-9 hours, min tolerance 4h, max tolerance 12h
        self.assertEqual(normalize_target_range(8.0, 7.0, 9.0, 4.0, 12.0), 100.0)
        self.assertEqual(normalize_target_range(7.0, 7.0, 9.0, 4.0, 12.0), 100.0)
        self.assertEqual(normalize_target_range(9.0, 7.0, 9.0, 4.0, 12.0), 100.0)
        # Below optimal: 5.5 hours (halfway between 4 and 7)
        self.assertAlmostEqual(normalize_target_range(5.5, 7.0, 9.0, 4.0, 12.0), 50.0, places=1)
        # Above optimal: 10.5 hours (halfway between 9 and 12)
        self.assertAlmostEqual(normalize_target_range(10.5, 7.0, 9.0, 4.0, 12.0), 50.0, places=1)
        # Outside tolerances
        self.assertEqual(normalize_target_range(3.0, 7.0, 9.0, 4.0, 12.0), 0.0)
        self.assertEqual(normalize_target_range(13.0, 7.0, 9.0, 4.0, 12.0), 0.0)
        self.assertIsNone(normalize_target_range(None, 7.0, 9.0, 4.0, 12.0))


if __name__ == "__main__":
    unittest.main()
