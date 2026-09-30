from django.test import TestCase

from apps.records.services import ScoreError, assign_grade, validate_scores
from apps.testing import make_structure


class GradeValidationTests(TestCase):
    def setUp(self):
        make_structure()

    def test_default_grade_boundaries(self):
        self.assertEqual(assign_grade(100)[0], "A")
        self.assertEqual(assign_grade(70)[0], "A")
        self.assertEqual(assign_grade(69)[0], "B")
        self.assertEqual(assign_grade(60)[0], "B")
        self.assertEqual(assign_grade(59)[0], "C")
        self.assertEqual(assign_grade(50)[0], "C")
        self.assertEqual(assign_grade(49)[0], "D")
        self.assertEqual(assign_grade(45)[0], "D")
        self.assertEqual(assign_grade(44)[0], "F")
        self.assertEqual(assign_grade(0)[0], "F")
        self.assertEqual(float(assign_grade(70)[1]), 5)

    def test_scores_outside_range_are_rejected(self):
        with self.assertRaises(ScoreError):
            validate_scores(41, 20)
        with self.assertRaises(ScoreError):
            validate_scores(20, 61)
        with self.assertRaises(ScoreError):
            validate_scores(-1, 10)
