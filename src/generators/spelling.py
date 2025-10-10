"""
Spelling exercise generator
"""
from typing import List, Dict

class SpellingGenerator:
    """Generates spelling practice exercises"""

    def __init__(self):
        self.min_words = 3
        self.max_words = 4

    def generate(self, vocabulary: List[Dict], mistakes: List[Dict]) -> List[Dict]:
        spelling_words: List[Dict] = []
        seen = set()

        # ---- Priority 1: student mistakes (guaranteed first) ----
        for m in mistakes:
            w = m.get('focus_word', '')
            if w and len(w) > 2 and w.lower() not in seen:
                spelling_words.append({
                    'word': w,
                    'sample_sentence': m['correct'],
                    'difficulty': 'medium',
                    'source': 'student_mistake'
                })
                seen.add(w.lower())

        # ---- Priority 2: challenging vocabulary ----
        challenging = {
            'comfortable', 'vegetables', 'breakfast', 'yesterday',
            'engineer', 'sometimes', 'listening', 'bought', 'stayed'
        }
        for v in vocabulary:
            if len(spelling_words) >= self.max_words: break
            w = v['word']
            if w.lower() in challenging and w.lower() not in seen:
                spelling_words.append({
                    'word': w,
                    'sample_sentence': v['context'],
                    'difficulty': 'medium',
                    'source': 'vocabulary'
                })
                seen.add(w.lower())

        # ---- Priority 3: fill remaining slots ----
        for v in vocabulary:
            if len(spelling_words) >= self.max_words: break
            w = v['word']
            if len(w) > 4 and w.lower() not in seen:
                spelling_words.append({
                    'word': w,
                    'sample_sentence': v['context'],
                    'difficulty': 'easy',
                    'source': 'vocabulary'
                })
                seen.add(w.lower())

        return spelling_words[:self.max_words]