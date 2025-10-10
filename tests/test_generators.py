"""
Unit tests for exercise generators
Validates output format and quality
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from generators.fill_in_blank import FillInBlankGenerator
from generators.flashcard import FlashcardGenerator
from generators.spelling import SpellingGenerator


class TestFillInBlankGenerator(unittest.TestCase):
    """Test fill-in-blank exercise generation"""
    
    def setUp(self):
        self.generator = FillInBlankGenerator()
    
    def test_creates_exercise_with_blank(self):
        """Should create sentence with blank marker"""
        vocabulary = [{
            'word': 'wake',
            'context': 'I wake up at 7 AM.',
            'category': 'test',
            'priority': 'high'
        }]
        mistakes = []
        sentences = []
        
        exercises = self.generator.generate(vocabulary, mistakes, sentences)
        
        if exercises:
            self.assertIn('_____', exercises[0]['sentence'])
    
    def test_includes_correct_answer(self):
        """Should include correct answer in options"""
        vocabulary = [{
            'word': 'wake',
            'context': 'I wake up at 7 AM.',
            'category': 'test',
            'priority': 'high'
        }]
        
        exercises = self.generator.generate(vocabulary, [], [])
        
        if exercises:
            ex = exercises[0]
            options = [ex['option_a'], ex['option_b'], ex['option_c'], ex['option_d']]
            self.assertIn(ex['correct_word'], options)
    
    def test_generates_four_options(self):
        """Should generate 4 options (A, B, C, D)"""
        vocabulary = [{
            'word': 'breakfast',
            'context': 'I eat breakfast.',
            'category': 'test',
            'priority': 'high'
        }]
        
        exercises = self.generator.generate(vocabulary, [], [])
        
        if exercises:
            ex = exercises[0]
            self.assertTrue(ex['option_a'])
            self.assertTrue(ex['option_b'])
            self.assertTrue(ex['option_c'])
            self.assertTrue(ex['option_d'])


class TestFlashcardGenerator(unittest.TestCase):
    """Test flashcard generation"""
    
    def setUp(self):
        self.generator = FlashcardGenerator()
    
    def test_creates_flashcard_with_required_fields(self):
        """Should create flashcard with all required fields"""
        vocabulary = [{
            'word': 'wake',
            'context': 'I wake up at 7 AM.',
            'category': 'test',
            'priority': 'high'
        }]
        
        flashcards = self.generator.generate(vocabulary, [])
        
        if flashcards:
            card = flashcards[0]
            self.assertIn('word', card)
            self.assertIn('translation', card)
            self.assertIn('example_sentence', card)
    
    def test_filters_simple_words(self):
        """Should filter out overly simple words"""
        vocabulary = [
            {'word': 'very', 'context': 'Very good.', 'category': 'test', 'priority': 'medium'},
            {'word': 'breakfast', 'context': 'I eat breakfast.', 'category': 'test', 'priority': 'high'}
        ]
        
        flashcards = self.generator.generate(vocabulary, [])
        
        words = [c['word'] for c in flashcards]
        self.assertNotIn('very', words)


class TestSpellingGenerator(unittest.TestCase):
    """Test spelling exercise generation"""
    
    def setUp(self):
        self.generator = SpellingGenerator()
    
    def test_prioritizes_mistake_words(self):
        """Should prioritize words from student mistakes"""
        vocabulary = [{
            'word': 'breakfast',
            'context': 'I eat breakfast.',
            'category': 'test',
            'priority': 'medium'
        }]
        
        mistakes = [{
            'incorrect': 'I waking up.',
            'correct': 'I wake up.',
            'focus_word': 'wake',
            'error_type': 'grammar'
        }]
        
        spelling = self.generator.generate(vocabulary, mistakes)
        
        # First word should be from mistake (higher priority)
        self.assertEqual(spelling[0]['word'], 'wake')
        self.assertEqual(spelling[0]['source'], 'student_mistake')
    
    def test_no_duplicate_words(self):
        """Should not include duplicate words"""
        vocabulary = [
            {'word': 'wake', 'context': 'I wake up.', 'category': 'test', 'priority': 'high'},
            {'word': 'wake', 'context': 'Wake up now.', 'category': 'test', 'priority': 'high'},
        ]
        
        spelling = self.generator.generate(vocabulary, [])
        
        words = [s['word'] for s in spelling]
        unique_words = set(words)
        
        self.assertEqual(len(words), len(unique_words), "Should not have duplicate words")


if __name__ == '__main__':
    unittest.main()