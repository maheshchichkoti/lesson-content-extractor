"""
Unit tests for content extractors
Validates extraction accuracy and edge case handling
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from extractors.vocabulary_extractor import VocabularyExtractor
from extractors.mistake_extractor import MistakeExtractor
from extractors.sentence_extractor import SentenceExtractor


class TestVocabularyExtractor(unittest.TestCase):
    """Test vocabulary extraction logic"""
    
    def setUp(self):
        self.extractor = VocabularyExtractor()
    
    def test_extracts_from_corrections(self):
        """Should extract vocabulary from teacher corrections"""
        transcript = """
Teacher: Good try! The correct sentence is "I wake up at 7 AM."
Student: I waking up at 7 AM.
"""
        vocab = self.extractor.extract(transcript)
        
        # Should extract key words
        words = [v['word'] for v in vocab]
        self.assertIn('wake', words)
    
    def test_filters_stop_words(self):
        """Should exclude common stop words"""
        transcript = """
Teacher: Correction: "I eat bread and eggs."
"""
        vocab = self.extractor.extract(transcript)
        
        words = [v['word'] for v in vocab]
        # Stop words should not be extracted
        self.assertNotIn('and', words)
        self.assertNotIn('the', words)
    
    def test_deduplication(self):
        """Should not return duplicate words"""
        transcript = """
Teacher: Correction: "I wake up at 7 AM."
Student: Then I wake up.
"""
        vocab = self.extractor.extract(transcript)
        
        words = [v['word'] for v in vocab]
        # Count occurrences of 'wake'
        wake_count = words.count('wake')
        self.assertEqual(wake_count, 1, "Word 'wake' should appear only once")


class TestMistakeExtractor(unittest.TestCase):
    """Test mistake identification logic"""
    
    def setUp(self):
        self.extractor = MistakeExtractor()
    
    def test_detects_correction_pattern(self):
        """Should detect teacher corrections"""
        transcript = """
Student: I waking up at 7 AM.
Teacher: Good try! The correct sentence is "I wake up at 7 AM."
"""
        mistakes = self.extractor.extract(transcript)
        
        self.assertGreater(len(mistakes), 0, "Should detect at least one mistake")
        self.assertEqual(mistakes[0]['correct'], "I wake up at 7 AM.")
    
    def test_categorizes_verb_tense_error(self):
        """Should categorize verb tense errors correctly"""
        transcript = """
Student: I waking up at 7 AM.
Teacher: Correction: "I wake up at 7 AM."
"""
        mistakes = self.extractor.extract(transcript)
        
        self.assertEqual(mistakes[0]['error_type'], 'grammar_verb_tense')
    
    def test_categorizes_past_tense_error(self):
        """Should categorize past tense errors"""
        transcript = """
Student: Yesterday I go to market.
Teacher: Correction: "Yesterday I went to the market."
"""
        mistakes = self.extractor.extract(transcript)
        
        self.assertIn('past_tense', mistakes[0]['error_type'])
    
    def test_extracts_focus_word(self):
        """Should identify the corrected word"""
        transcript = """
Student: I eats bread.
Teacher: Correction: "I eat bread."
"""
        mistakes = self.extractor.extract(transcript)
        
        focus = mistakes[0]['focus_word']
        self.assertEqual(focus, 'eat')


class TestSentenceExtractor(unittest.TestCase):
    """Test sentence extraction logic"""
    
    def setUp(self):
        self.extractor = SentenceExtractor()
    
    def test_extracts_corrected_sentences(self):
        """Should extract corrected sentences"""
        transcript = """
Teacher: Correction: "I wake up at 7 AM."
"""
        sentences = self.extractor.extract(transcript)
        
        self.assertGreater(len(sentences), 0)
        self.assertEqual(sentences[0]['sentence'], "I wake up at 7 AM.")
    
    def test_assigns_quality_scores(self):
        """Should assign quality scores to sentences"""
        transcript = """
Teacher: Correction: "I wake up at 7 AM."
"""
        sentences = self.extractor.extract(transcript)
        
        self.assertIn('quality_score', sentences[0])
        self.assertGreater(sentences[0]['quality_score'], 0)


if __name__ == '__main__':
    unittest.main()