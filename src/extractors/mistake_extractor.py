"""
Student mistake identification and categorization
"""

from typing import List, Dict
from utils.text_processing import TextProcessor

class MistakeExtractor:
    """Identifies and categorizes student errors"""
    
    def __init__(self):
        self.text_processor = TextProcessor()
    
    def extract(self, transcript: str) -> List[Dict[str, str]]:
        """Extract student mistakes with corrections"""
        mistakes = []
        corrections = self.text_processor.extract_corrections(transcript)
        
        for incorrect, correct in corrections:
            if incorrect and correct:
                error_type = self._categorize_error(incorrect, correct)
                focus_word = self._identify_focus_word(incorrect, correct)
                
                mistakes.append({
                    'incorrect': incorrect,
                    'correct': correct,
                    'error_type': error_type,
                    'focus_word': focus_word,
                    'severity': 'high' if 'grammar' in error_type else 'medium'
                })
        
        return mistakes
    
    def _categorize_error(self, incorrect: str, correct: str) -> str:
        """Categorize the type of error"""
        inc_lower = incorrect.lower()
        cor_lower = correct.lower()
        
        # Past tense errors (FIXED - specific category)
        if ('yesterday' in cor_lower or 'last' in cor_lower) and \
           (('go' in inc_lower and 'went' in cor_lower) or \
            ('buy' in inc_lower and 'bought' in cor_lower) or \
            ('stay' in inc_lower and 'stayed' in cor_lower)):
            return 'grammar_past_tense'  # FIXED
        
        # Present tense errors with continuous
        if ('waking' in inc_lower and 'wake' in cor_lower) or \
           ('cooking' in inc_lower and 'cooked' in cor_lower):
            return 'grammar_verb_tense'
        
        # Subject-verb agreement (ADDED)
        if ('i eats' in inc_lower and 'i eat' in cor_lower) or \
           ('i likes' in inc_lower and 'i like' in cor_lower) or \
           ('he eat' in inc_lower and 'he eats' in cor_lower):
            return 'grammar_subject_verb_agreement'
        
        # Article errors
        if ('is engineer' in inc_lower and 'is an engineer' in cor_lower) or \
           ('is teacher' in inc_lower and 'is a teacher' in cor_lower) or \
           ('to market' in inc_lower and 'to the market' in cor_lower):
            return 'grammar_articles'
        
        # Plural errors
        if ('egg' in inc_lower and 'eggs' in cor_lower) or \
           ('vegetable' in inc_lower and 'vegetables' in cor_lower) or \
           ('day' in inc_lower and 'days' in cor_lower):
            return 'grammar_plural'
        
        # Preposition errors
        if ('listening music' in inc_lower and 'listening to music' in cor_lower) or \
           ('play football' in inc_lower and 'playing football' in cor_lower):
            return 'grammar_prepositions'
        
        # Gerund/infinitive errors (ADDED)
        if ('like play' in inc_lower and 'like playing' in cor_lower) or \
           ('enjoy to' in inc_lower and 'enjoy' in cor_lower):
            return 'grammar_gerund_infinitive'
        
        # Word form errors
        if ('comfort' in inc_lower and 'comfortable' in cor_lower) or \
           ('beauty' in inc_lower and 'beautiful' in cor_lower):
            return 'vocabulary_word_form'
        
        # Sentence structure errors (ADDED)
        if ('have five people' in inc_lower and 'are five people' in cor_lower):
            return 'grammar_sentence_structure'
        
        return 'grammar_general'
    
    def _identify_focus_word(self, incorrect: str, correct: str) -> str:
        """Identify the specific word that was corrected"""
        inc_words = set(incorrect.lower().split())
        cor_words = correct.lower().split()
        
        # Find added words (these are often the correction focus)
        for word in cor_words:
            clean_word = word.strip('.,!?"')
            if clean_word and clean_word not in inc_words:
                return clean_word
        
        # Find changed words
        inc_split = incorrect.lower().split()
        for i, word in enumerate(cor_words):
            if i < len(inc_split):
                inc_word = inc_split[i]
                if word != inc_word:
                    return word.strip('.,!?"')
        
        # Default to first meaningful word
        return cor_words[0].strip('.,!?"') if cor_words else ''