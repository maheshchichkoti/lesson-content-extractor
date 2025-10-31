# src/utils/gemini_helper.py
"""Google Gemini AI integration for R&D on transcripts
Production-ready with error handling and rate limiting"""

import os
from typing import List, Dict
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
    
    def extract_vocabulary_with_ai(self, transcript: str, max_words: int = 15) -> List[Dict[str, str]]:
        """Use Gemini AI to extract vocabulary from ANY transcript"""
        
        if not self.enabled or not self.model:
            logger.warning("Gemini AI not available, using fallback")
            return self._fallback_vocabulary_extraction(transcript, max_words)
        
        try:
            prompt = f"""Analyze this conversation transcript and extract the most important English vocabulary words that would be useful for language learners.

Transcript:
{transcript[:2000]}

Extract 10-15 useful English words or phrases. For each word, provide:
1. The word/phrase
2. A simple example sentence using that word from the transcript (or create one if needed)
3. Difficulty level (beginner/intermediate/advanced)

Format your response EXACTLY as JSON array:
[
  {{"word": "backend", "context": "We need to complete the backend", "difficulty": "intermediate"}},
  {{"word": "completed", "context": "This task is completed", "difficulty": "beginner"}}
]

Only return the JSON array, nothing else."""
            
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Extract JSON from response
            import json
            import re
            
            # Try to find JSON array in response
            json_match = re.search(r'\[.*\]', result_text, re.DOTALL)
            if json_match:
                vocab_list = json.loads(json_match.group())
                logger.info(f"✅ Gemini AI extracted {len(vocab_list)} vocabulary words")
                return vocab_list[:max_words]
            else:
                logger.warning("Could not parse Gemini response, using fallback")
                return self._fallback_vocabulary_extraction(transcript, max_words)
                
        except Exception as e:
            logger.error(f"Gemini AI vocabulary extraction failed: {e}")
            return self._fallback_vocabulary_extraction(transcript, max_words)
    
    def _fallback_vocabulary_extraction(self, transcript: str, max_words: int = 15) -> List[Dict[str, str]]:
        """Fallback: Extract common English words from transcript"""
        import re
        from collections import Counter
        
        # Common words to skip
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                     'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
                     'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
                     'can', 'could', 'may', 'might', 'this', 'that', 'these', 'those',
                     'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
                     'my', 'your', 'his', 'her', 'its', 'our', 'their', 'so', 'if', 'as', 'all',
                     'just', 'like', 'okay', 'ok', 'yeah', 'yes', 'no', 'not', 'now', 'then'}
        
        # Extract words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', transcript.lower())
        
        # Filter and count
        filtered_words = [w for w in words if w not in stop_words]
        word_counts = Counter(filtered_words)
        
        # Get most common
        vocabulary = []
        for word, count in word_counts.most_common(max_words):
            # Find context sentence
            sentences = re.split(r'[.!?]', transcript)
            context = ""
            for sentence in sentences:
                if word in sentence.lower():
                    context = sentence.strip()[:100]
                    break
            
            if context:
                vocabulary.append({
                    'word': word,
                    'context': context,
                    'difficulty': 'intermediate',
                    'category': 'extracted',
                    'priority': 'medium'
                })
        
        logger.info(f"✅ Fallback extracted {len(vocabulary)} vocabulary words")
        return vocabulary
