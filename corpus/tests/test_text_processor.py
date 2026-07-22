from django.test import SimpleTestCase
from corpus.processors.text_processor import TextProcessor
import json

class TextProcessorTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tp = TextProcessor() # here we have the initialization of pymorphy

    def test_get_lemma(self):
        """Checks lemmatization"""
        # "коти" -> "кіт"
        self.assertEqual(self.tp.get_lemma("будинком"), "будинок")
        # "ПІШОВ" -> "піти" (checks low register)
        self.assertEqual(self.tp.get_lemma("ПІШОВ"), "піти")

    def test_process_sentence(self):
        """Checks the sentence to parse on tokens + analysis of parts of language"""
        text = "Мама мила раму"
        tokens = self.tp._process_sentence(text)

        # Must be 3 words
        self.assertEqual(len(tokens), 3)

        # Checks 1 word - "Мама"
        first_token = tokens[0]
        self.assertEqual(first_token['form'], 'мама')
        self.assertEqual(first_token['lemma'], 'мама')
        self.assertEqual(first_token['pos'], 'NOUN')  # Pymorphy determines - NOUN

    def test_build_kwic_exact_match(self):
        """KWIC: Checks exact match and correct list wrapping"""
        text = "Це простий тест системи."
        lemma_to_find = "тест"

        # Очікуємо список, що містить один виділений рядок (як повертає build_kwic)
        expected = ["Це простий <mark>тест</mark> системи."]
        result = self.tp.build_kwic(text, lemma_to_find)

        self.assertEqual(result, expected)

    def test_build_kwic_no_match(self):
        """KWIC: If the word doesn't exist - returns an empty list"""
        text = "Собака гавкає."
        search_term = "кіт"

        expected = []
        result = self.tp.build_kwic(text, search_term)
        self.assertEqual(result, expected)

    def test_get_raw_json(self):
        """Check the serialization in JSON"""
        data = [{"id": 1, "word": "test"}]
        json_output = self.tp.get_raw_json(data)

        # Check if valid JSON sentence
        self.assertIsInstance(json_output, str)
        self.assertIn('"word": "test"', json_output)

        # Try parsing back to verify validity
        parsed_back = json.loads(json_output)
        self.assertEqual(parsed_back[0]['id'], 1)