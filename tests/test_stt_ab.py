import unittest

from scripts.stt_ab_test import word_error_rate


class SttAbMetricTests(unittest.TestCase):
    def test_word_error_rate_exact_and_substitution(self):
        self.assertEqual(word_error_rate("adiciona café", "adiciona café"), 0)
        self.assertEqual(word_error_rate("adiciona café", "adiciona arroz"), .5)

    def test_word_error_rate_ignores_case_and_punctuation(self):
        self.assertEqual(word_error_rate("Olá, NATY!", "olá naty"), 0)
