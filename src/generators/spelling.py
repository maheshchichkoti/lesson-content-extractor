"""
Spelling exercise generator
"""
from typing import List, Dict
import re

class SpellingGenerator:
    """Generates spelling practice exercises"""

    def __init__(self):
        self.min_words = 3
        self.max_words = 4

    def generate(self, vocabulary: List[Dict], mistakes: List[Dict]) -> List[Dict]:
        spelling_words: List[Dict] = []
        seen = set()

        # ---- Priority 1: student mistakes (guaranteed first) ----
        for m in mistakes:
            w = m.get('focus_word', '')
            if w and len(w) > 2 and w.lower() not in seen:
                # Extract short example
                example = self._extract_short_example(w, m['correct'])
                spelling_words.append({
                    'word': w,
                    'sample_sentence': example,
                    'difficulty': 'medium',
                    'source': 'student_mistake'
                })
                seen.add(w.lower())

        # ---- Priority 2: challenging vocabulary ----
        challenging = {
            'comfortable', 'vegetables', 'breakfast', 'yesterday',
            'engineer', 'sometimes', 'listening', 'bought', 'stayed'
        }
        for v in vocabulary:
            if len(spelling_words) >= self.max_words: break
            w = v['word']
            if w.lower() in challenging and w.lower() not in seen:
                # Extract short example
                example = self._extract_short_example(w, v['context'])
                spelling_words.append({
                    'word': w,
                    'sample_sentence': example,
                    'difficulty': 'medium',
                    'source': 'vocabulary'
                })
                seen.add(w.lower())

        # ---- Priority 3: fill remaining slots ----
        for v in vocabulary:
            if len(spelling_words) >= self.max_words: break
            w = v['word']
            if len(w) > 4 and w.lower() not in seen:
                # Extract short example
                example = self._extract_short_example(w, v['context'])
                spelling_words.append({
                    'word': w,
                    'sample_sentence': example,
                    'difficulty': 'easy',
                    'source': 'vocabulary'
                })
                seen.add(w.lower())

        return spelling_words[:self.max_words]
    
    def _extract_short_example(self, word: str, context: str) -> str:
        """Extract a short sentence containing the word from context"""
        # Split into sentences
        sentences = re.split(r'[.!?]+', context)
        
        # Find sentence containing the word
        for sent in sentences:
            if word.lower() in sent.lower() and len(sent.strip()) > 10:
                sent = sent.strip()
                # Limit to 150 characters
                if len(sent) > 150:
                    # Try to cut at a word boundary
                    sent = sent[:147] + '...'
                return sent
        
        # Fallback: return first 150 chars of context
        if len(context) > 150:
            return context[:147].strip() + '...'
        return context.strip()