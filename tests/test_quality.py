"""
Unit tests for quality checker
Validates quality assurance logic
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from utils.quality_checker import QualityChecker


class TestQualityChecker(unittest.TestCase):
    """Test quality validation logic"""
    
    def setUp(self):
        self.checker = QualityChecker()
    
    def test_validates_fill_in_blank_structure(self):
        """Should validate fill-in-blank required fields"""
        valid_fib = [{
            'sentence': 'I _____ up at 7 AM.',
            'option_a': 'wake',
            'option_b': 'sleep',
            'option_c': 'work',
            'option_d': 'rest',
            'correct_answer': 'A',
            'correct_word': 'wake'
        }]
        
        result = self.checker.validate_exercises(valid_fib, [], [])
        self.assertTrue(result, "Valid exercise should pass")
    
    def test_detects_missing_blank(self):
        """Should detect missing blank in sentence"""
        invalid_fib = [{
            'sentence': 'I wake up at 7 AM.',  # No blank!
            'option_a': 'wake',
            'option_b': 'sleep',
            'option_c': 'work',
            'option_d': 'rest',
            'correct_answer': 'A',
            'correct_word': 'wake'
        }]
        
        result = self.checker.validate_exercises(invalid_fib, [], [])
        self.assertFalse(result, "Should fail when blank is missing")
    
    def test_detects_invalid_correct_answer(self):
        """Should detect invalid correct answer letter"""
        invalid_fib = [{
            'sentence': 'I _____ up.',
            'option_a': 'wake',
            'option_b': 'sleep',
            'option_c': 'work',
            'option_d': 'rest',
            'correct_answer': 'Z',  # Invalid!
            'correct_word': 'wake'
        }]
        
        result = self.checker.validate_exercises(invalid_fib, [], [])
        self.assertFalse(result, "Should fail with invalid answer letter")
    
    def test_detects_duplicate_options(self):
        """Should warn about duplicate options"""
        duplicate_fib = [{
            'sentence': 'I _____ up.',
            'option_a': 'wake',
            'option_b': 'wake',  # Duplicate!
            'option_c': 'sleep',
            'option_d': 'work',
            'correct_answer': 'A',
            'correct_word': 'wake'
        }]
        
        self.checker.validate_exercises(duplicate_fib, [], [])
        
        # Should generate warning
        self.assertGreater(len(self.checker.warnings), 0)
    
    def test_validates_flashcard_structure(self):
        """Should validate flashcard required fields"""
        valid_flashcard = [{
            'word': 'wake',
            'translation': 'जागना',
            'example_sentence': 'I wake up at 7 AM.',
            'hint': 'to stop sleeping',
            'category': 'test',
            'difficulty': 'beginner'
        }]
        
        result = self.checker.validate_exercises([], valid_flashcard, [])
        self.assertTrue(result, "Valid flashcard should pass")
    
    def test_validates_spelling_no_duplicates(self):
        """Should detect duplicate words in spelling list"""
        duplicate_spelling = [
            {'word': 'wake', 'sample_sentence': 'I wake up.'},
            {'word': 'wake', 'sample_sentence': 'Wake up now.'}  # Duplicate!
        ]
        
        result = self.checker.validate_exercises([], [], duplicate_spelling)
        self.assertFalse(result, "Should fail with duplicate spelling words")


if __name__ == '__main__':
    unittest.main()