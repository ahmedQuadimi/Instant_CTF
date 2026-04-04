from django.test import SimpleTestCase

from Scoring.utils import calculate_points


class CalculatePointsTests(SimpleTestCase):
    def test_returns_max_points_for_first_blood(self):
        self.assertEqual(calculate_points(500, 100, 0.05, 0), 500)

    def test_applies_exponential_decay(self):
        self.assertEqual(calculate_points(500, 100, 0.05, 10), 303)

    def test_never_returns_less_than_min_points(self):
        self.assertEqual(calculate_points(500, 100, 0.05, 100), 100)
