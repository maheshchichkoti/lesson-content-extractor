"""
Quality assurance for generated exercises
Production-ready with comprehensive validation
"""

from typing import List, Dict
import re

class QualityChecker:
    """Validates exercise quality before output"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def validate_exercises(self, fill_in_blank: List[Dict], 
                          flashcards: List[Dict], 
                          spelling: List[Dict]) -> bool:
        """Run all quality checks"""
        self.errors = []
        self.warnings = []
        
        # Check each exercise type
        self._check_fill_in_blank(fill_in_blank)
        self._check_flashcards(flashcards)
        self._check_spelling(spelling)
        
        # Check total count
        total = len(fill_in_blank) + len(flashcards) + len(spelling)
        if total < 8:
            self.warnings.append(f"Total exercises ({total}) below minimum (8)")
        elif total > 12:
            self.warnings.append(f"Total exercises ({total}) above maximum (12)")
        
        # Report
        if self.errors:
            print(f"      ❌ {len(self.errors)} errors found")
            for error in self.errors[:3]:
                print(f"         - {error}")
        
        if self.warnings:
            print(f"      ⚠️  {len(self.warnings)} warnings")
            for warning in self.warnings[:2]:
                print(f"         - {warning}")
        
        if not self.errors and not self.warnings:
            print(f"      ✓ All quality checks passed")
        
        return len(self.errors) == 0
    
    def _check_fill_in_blank(self, exercises: List[Dict]):
        """Validate fill-in-blank exercises"""
        for i, ex in enumerate(exercises):
            # Check blank exists
            if '_____' not in ex.get('sentence', ''):
                self.errors.append(f"Fill-blank {i+1}: No blank marker")
            
            # Check options exist
            options = [
                ex.get('option_a', ''),
                ex.get('option_b', ''),
                ex.get('option_c', ''),
                ex.get('option_d', '')
            ]
            
            # Check for empty options
            empty_count = sum(1 for opt in options if not opt)
            if empty_count > 0:
                self.errors.append(f"Fill-blank {i+1}: {empty_count} empty options")
            
            # Check for duplicate options (ADDED)
            non_empty_options = [opt for opt in options if opt]
            if len(set(non_empty_options)) < len(non_empty_options):
                self.warnings.append(f"Fill-blank {i+1}: Duplicate options detected")
            
            # Check answer validity
            if ex.get('correct_answer') not in ['A', 'B', 'C', 'D']:
                self.errors.append(f"Fill-blank {i+1}: Invalid answer format")
            
            # Verify correct word is in options
            correct_word = ex.get('correct_word', '')
            if correct_word and correct_word not in options:
                self.errors.append(f"Fill-blank {i+1}: Correct word not in options")
            
            # Check sentence length
            sentence = ex.get('sentence', '')
            if len(sentence.split()) < 4:
                self.warnings.append(f"Fill-blank {i+1}: Sentence too short")
    
    def _check_flashcards(self, flashcards: List[Dict]):
        """Validate flashcards"""
        seen = set()
        for i, card in enumerate(flashcards):
            word = card.get('word', '')
            
            # Check for duplicates
            if word.lower() in seen:
                self.warnings.append(f"Flashcard {i+1}: Duplicate word '{word}'")
            seen.add(word.lower())
            
            # Check required fields
            if not word:
                self.errors.append(f"Flashcard {i+1}: Missing word")
            
            if not card.get('translation'):
                self.errors.append(f"Flashcard {i+1}: Missing translation")
            
            if not card.get('example_sentence'):
                self.warnings.append(f"Flashcard {i+1}: Missing example sentence")
            
            # Check if example contains the word
            if word and card.get('example_sentence'):
                if word.lower() not in card['example_sentence'].lower():
                    self.warnings.append(f"Flashcard {i+1}: Example doesn't contain word")
    
    def _check_spelling(self, exercises: List[Dict]):
        """Validate spelling exercises with duplicate check (FIXED)"""
        seen = set()
        for i, ex in enumerate(exercises):
            word = ex.get('word', '')
            
            # Check for missing word
            if not word:
                self.errors.append(f"Spelling {i+1}: Missing word")
                continue
            
            # Check for duplicates (ADDED)
            if word.lower() in seen:
                self.errors.append(f"Spelling {i+1}: Duplicate word '{word}'")
            seen.add(word.lower())
            
            # Check for sample sentence
            if not ex.get('sample_sentence'):
                self.warnings.append(f"Spelling {i+1}: Missing sample sentence")
            
            # Check word length (spelling words should be challenging)
            if len(word) < 4:
                self.warnings.append(f"Spelling {i+1}: Word '{word}' too simple")
            
            # Check if sample contains the word
            if word and ex.get('sample_sentence'):
                if word.lower() not in ex['sample_sentence'].lower():
                    self.warnings.append(f"Spelling {i+1}: Sample doesn't contain word")

class GlobalDeduplicator:
    """Tracks content usage across all exercises"""
    
    def __init__(self):
        self.used_sentences = set()
        self.used_words = set()
        self.used_in_exercise = {}  # tracks which exercise type used what
    
    def can_use_sentence(self, sentence: str, exercise_type: str) -> bool:
        """Check if sentence can be used"""
        sentence_clean = sentence.lower().strip()
        if sentence_clean in self.used_sentences:
            return False
        return True
    
    def mark_sentence_used(self, sentence: str, exercise_type: str):
        """Mark sentence as used"""
        sentence_clean = sentence.lower().strip()
        self.used_sentences.add(sentence_clean)
        
        if exercise_type not in self.used_in_exercise:
            self.used_in_exercise[exercise_type] = []
        self.used_in_exercise[exercise_type].append(sentence)
    
    def can_use_word(self, word: str, exercise_type: str) -> bool:
        """Check if word can be used (allows some reuse)"""
        word_clean = word.lower().strip()
        
        # Allow word to appear in max 2 different exercise types
        count = sum(1 for exercises in self.used_in_exercise.values() 
                   if any(word_clean in str(ex).lower() for ex in exercises))
        return count < 2
    
    def reset(self):
        """Reset for new lesson"""
        self.used_sentences.clear()
        self.used_words.clear()
        self.used_in_exercise.clear()