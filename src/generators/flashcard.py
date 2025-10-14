"""
Flashcard generator for vocabulary learning
"""
from typing import List, Dict
from src.utils.gemini_helper import GeminiHelper

class FlashcardGenerator:
    """Generates vocabulary flashcards"""

    def __init__(self):
        self.gemini = GeminiHelper()
        self.min_cards = 3
        self.max_cards = 4

    def generate(self, vocabulary: List[Dict], sentences: List[Dict]) -> List[Dict]:
        flashcards = []
        seen = set()
        simple = {'very', 'good', 'nice', 'bad', 'fine'}

        # sort by priority
        vocab_sorted = sorted(vocabulary,
                              key=lambda x: 1 if x.get('priority') == 'high' else 2)

        for item in vocab_sorted:
            if len(flashcards) >= self.max_cards:
                break
            word = item['word']
            if word.lower() in simple:
                continue
            if word.lower() not in seen:
                flashcards.append({
                    'word': word,
                    'translation': self.gemini.translate_phrase(word),
                    'example_sentence': item['context'],
                    'category': item.get('category', 'general'),
                    'difficulty': 'beginner'
                })
                seen.add(word.lower())
        return flashcards