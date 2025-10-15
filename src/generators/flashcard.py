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
                # Extract short example sentence containing the word
                context = item['context']
                example = self._extract_short_example(word, context)
                
                flashcards.append({
                    'word': word,
                    'translation': self.gemini.translate_phrase(word),
                    'example_sentence': example,
                    'category': item.get('category', 'general'),
                    'difficulty': 'beginner'
                })
                seen.add(word.lower())
        return flashcards
    
    def _extract_short_example(self, word: str, context: str) -> str:
        """Extract a short sentence containing the word from context"""
        import re
        
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