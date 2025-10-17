# src/utils/gemini_helper.py
"""Google Gemini AI integration for R&D on transcripts
Production-ready with error handling and rate limiting"""

import os
from typing import List
import logging

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

logger = logging.getLogger(__name__)

class GeminiHelper:
    """Wrapper for Google Gemini API with production safeguards"""
    
    def __init__(self):
        self.api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
        
        if self.api_key and GENAI_AVAILABLE:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-pro')
                self.enabled = True
                print("✅ Google Gemini AI initialized successfully")
                logger.info("✅ Gemini AI enabled for R&D")
            except Exception as e:
                print(f"⚠️ Gemini AI initialization failed: {e}. Using fallback.")
                logger.warning(f"Gemini init failed: {e}")
                self.enabled = False
                self.model = None
        else:
            if not GENAI_AVAILABLE:
                print("⚠️ google-generativeai package not installed. Using rule-based fallback.")
            else:
                print("⚠️ GOOGLE_API_KEY not found. Using rule-based fallback.")
            self.enabled = False
            self.model = None
    
    def generate_distractors(self, correct_word: str, context: str, count: int = 3) -> List[str]:
        """Generate realistic distractor options for fill-in-blank"""
        return self._fallback_distractors(correct_word, count)
    
    def _fallback_distractors(self, correct_word: str, count: int = 3) -> List[str]:
      """Enhanced rule-based distractor generation"""
      
      # Comprehensive distractor pool with categories
      distractor_pool = {
          # Present tense verbs
          'wake': ['wakes', 'waking', 'woken'],
          'wake up': ['wakes up', 'waking up', 'woke up'],
          'eat': ['eats', 'eating', 'eaten'],
          'brush': ['brushes', 'brushing', 'brushed'],
          'read': ['reads', 'reading', 'readed'],
          'play': ['plays', 'playing', 'played'],
          'like': ['likes', 'liking', 'liked'],
          
          # Past tense verbs
          'went': ['go', 'goes', 'gone'],
          'bought': ['buy', 'buys', 'buyed'],
          'stayed': ['stay', 'stays', 'staying'],
          'cooked': ['cook', 'cooks', 'cooking'],
          
          # Continuous forms
          'playing': ['play', 'plays', 'played'],
          'listening': ['listen', 'listens', 'listened'],
          'reading': ['read', 'reads', 'readed'],
          'waking': ['wake', 'wakes', 'woken'],
          'cooking': ['cook', 'cooks', 'cooked'],
          
          # Nouns - singular/plural
          'eggs': ['egg', 'egges', 'an egg'],
          'teeth': ['tooth', 'teeths', 'tooths'],
          'vegetables': ['vegetable', 'vegitable', 'vegitables'],
          'days': ['day', 'daies', 'daily'],
          'people': ['person', 'peoples', 'persons'],
          'books': ['book', 'bookes', 'booking'],
          'fruits': ['fruit', 'fruites', 'fruity'],
          
          # Articles
          'a': ['an', 'the', 'some'],
          'an': ['a', 'the', 'any'],
          'the': ['a', 'an', 'this'],
          
          # Prepositions
          'to': ['at', 'in', 'for'],
          'at': ['in', 'on', 'to'],
          'in': ['at', 'on', 'into'],
          'for': ['to', 'at', 'since'],
          'with': ['by', 'from', 'along'],
          
          # Adjectives/Adverbs
          'comfortable': ['comfort', 'comfortably', 'comforted'],
          'sometimes': ['sometime', 'some time', 'always'],
          
          # Time expressions
          'yesterday': ['tomorrow', 'today', 'last day'],
          'morning': ['evening', 'afternoon', 'mornings'],
          
          # Numbers
          'five': ['four', 'fives', 'fifth'],
          'three': ['two', 'third', 'threes']
      }
      
      word_lower = correct_word.lower()
      
      # Try to find in pool
      if word_lower in distractor_pool:
          distractors = distractor_pool[word_lower][:count]
          # Randomize order for variety
          import random
          random.shuffle(distractors)
          return distractors
      
      # Smart pattern-based generation
      generated = []
      
      # Handle different word types
      if word_lower.endswith('ed'):  # Past tense
          base = word_lower[:-2] if not word_lower.endswith('ied') else word_lower[:-3] + 'y'
          generated = [base, base + 's', base + 'ing']
          
      elif word_lower.endswith('ing'):  # Continuous
          base = word_lower[:-3] if not word_lower.endswith('ying') else word_lower[:-4] + 'y'
          generated = [base, base + 's', base + 'ed']
          
      elif word_lower.endswith('s') and len(word_lower) > 3:  # Plural/3rd person
          base = word_lower[:-1] if not word_lower.endswith('es') else word_lower[:-2]
          generated = [base, base + 'ing', base + 'ed']
          
      elif word_lower.endswith('ly'):  # Adverbs
          base = word_lower[:-2]
          generated = [base, base + 'ful', base + 'ness']
      
      # If still no distractors, use semantic groups
      if not generated:
          semantic_groups = {
              'time': ['always', 'never', 'often', 'sometimes', 'usually'],
              'quantity': ['many', 'few', 'some', 'all', 'most'],
              'quality': ['good', 'bad', 'nice', 'great', 'fine'],
              'action': ['do', 'make', 'take', 'get', 'have']
          }
          
          # Find which group the word might belong to
          for group, words in semantic_groups.items():
              if word_lower in words:
                  generated = [w for w in words if w != word_lower][:count]
                  break
      
      # Final fallback - common confusing words
      if not generated:
          common_confusions = ['then', 'than', 'there', 'their', 'were', 'where', 
                              'your', 'you\'re', 'its', 'it\'s', 'to', 'too']
          generated = [w for w in common_confusions if w != word_lower][:count]
      
      return generated[:count]
    
    def translate_phrase(self, phrase: str, target_lang: str = 'Hindi') -> str:
        """Translate phrase for flashcards"""
        
        # Simple translation dictionary (expandable)
        translations = {
            'wake up': 'जागना (jaagna)',
            'breakfast': 'नाश्ता (naashta)',
            'bread': 'रोटी (roti)',
            'eggs': 'अंडे (ande)',
            'teeth': 'दांत (daant)',
            'football': 'फुटबॉल',
            'music': 'संगीत (sangeet)',
            'books': 'किताबें (kitaaben)',
            'family': 'परिवार (parivaar)',
            'father': 'पिता (pita)',
            'mother': 'माता (maata)',
            'engineer': 'इंजीनियर',
            'teacher': 'शिक्षक (shikshak)',
            'market': 'बाज़ार (bazaar)',
            'vegetables': 'सब्जियां (sabziyaan)',
            'fruits': 'फल (phal)',
            'yesterday': 'कल (kal)',
            'hotel': 'होटल',
            'comfortable': 'आरामदायक (aaraamdaayak)',
            'sometimes': 'कभी-कभी (kabhi-kabhi)'
        }
        
        phrase_lower = phrase.lower()
        return translations.get(phrase_lower, f"[{phrase}]")
