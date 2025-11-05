"""
Sentence Builder generator - Tokenize sentences for drag-and-drop assembly
Production-ready with punctuation handling and variations
"""
from typing import List, Dict
import re
from src.utils.gemini_helper import GeminiHelper

class SentenceBuilderGenerator:
    """Generates sentence builder items from sentences"""
    
    def __init__(self):
        self.gemini = GeminiHelper()
        self.min_items = 2
        self.max_items = 4
        
        # Minimum sentence quality criteria
        self.min_words = 6
        self.max_words = 20
    
    def generate(self, sentences: List[Dict], topic_id: str, lesson_id: str) -> List[Dict]:
        """
        Generate sentence builder items from sentences
        
        Args:
            sentences: List of extracted sentences
            topic_id: Topic identifier
            lesson_id: Lesson identifier
            
        Returns:
            List of sentence items ready for database insertion
        """
        items = []
        seen_sentences = set()
        
        # Filter quality sentences
        quality_sentences = self._filter_quality_sentences(sentences)
        
        for sent_data in quality_sentences:
            if len(items) >= self.max_items:
                break
            
            sentence = sent_data.get('text', '')
            if not sentence or sentence.lower() in seen_sentences:
                continue
            
            # Tokenize sentence
            tokens = self._tokenize_sentence(sentence)
            
            if not tokens or len(tokens) < self.min_words:
                continue
            
            # Get translation
            translation = self.gemini.translate_phrase(sentence)
            
            # Create unique ID
            item_id = f"sb_{lesson_id}_{len(items) + 1}"
            
            # Generate accepted variations (for now, just the original)
            accepted = [tokens]
            
            items.append({
                'id': item_id,
                'topic_id': topic_id,
                'lesson_id': lesson_id,
                'difficulty': self._assess_difficulty(sentence, tokens),
                'english': sentence,
                'translation': translation,
                'tokens': tokens,
                'accepted': accepted,
                'distractors': None  # Optional: could add distractor words
            })
            
            seen_sentences.add(sentence.lower())
        
        return items
    
    def _filter_quality_sentences(self, sentences: List[Dict]) -> List[Dict]:
        """Filter sentences suitable for sentence building"""
        quality = []
        
        for sent in sentences:
            text = sent.get('text', '').strip()
            
            if not text:
                continue
            
            # Word count check
            word_count = len(text.split())
            if word_count < self.min_words or word_count > self.max_words:
                continue
            
            # Has proper punctuation
            if not text[-1] in '.!?':
                text += '.'
            
            # Not too complex (no multiple clauses)
            if text.count(',') > 2 or text.count(';') > 0:
                continue
            
            # Update text if modified
            sent['text'] = text
            quality.append(sent)
        
        return quality
    
    def _tokenize_sentence(self, sentence: str) -> List[str]:
        """
        Tokenize sentence into words and punctuation
        
        Example:
            "Hello, world!" -> ["Hello", ",", "world", "!"]
        """
        # Clean up extra spaces
        sentence = ' '.join(sentence.split())
        
        # Split on spaces and punctuation, keeping punctuation
        # Pattern: split on spaces, but keep punctuation as separate tokens
        tokens = []
        current_word = ''
        
        for char in sentence:
            if char.isalnum() or char in ["'", "-"]:
                # Part of a word
                current_word += char
            elif char in '.,!?;:':
                # Punctuation - save current word and punctuation separately
                if current_word:
                    tokens.append(current_word)
                    current_word = ''
                tokens.append(char)
            elif char == ' ':
                # Space - save current word
                if current_word:
                    tokens.append(current_word)
                    current_word = ''
            else:
                # Other characters (quotes, etc.) - include with word or separate
                if current_word:
                    current_word += char
                else:
                    tokens.append(char)
        
        # Add last word if any
        if current_word:
            tokens.append(current_word)
        
        return tokens
    
    def _assess_difficulty(self, sentence: str, tokens: List[str]) -> str:
        """Assess difficulty level based on sentence complexity"""
        word_count = len([t for t in tokens if t not in '.,!?;:'])
        avg_word_length = sum(len(t) for t in tokens if t.isalnum()) / max(word_count, 1)
        
        # Check for complex structures
        has_complex = any(word in sentence.lower() for word in 
                         ['although', 'however', 'therefore', 'moreover', 'furthermore'])
        
        if has_complex or word_count >= 15 or avg_word_length >= 7:
            return 'hard'
        elif word_count >= 10 or avg_word_length >= 5:
            return 'medium'
        else:
            return 'easy'
    
    def generate_with_distractors(self, sentences: List[Dict], topic_id: str, 
                                  lesson_id: str) -> List[Dict]:
        """
        Generate sentence builder items with distractor words
        (Optional enhanced version)
        """
        items = self.generate(sentences, topic_id, lesson_id)
        
        # Add distractor words to each item
        for item in items:
            tokens = item['tokens']
            distractors = self._generate_distractors(tokens)
            item['distractors'] = distractors
        
        return items
    
    def _generate_distractors(self, tokens: List[str]) -> List[str]:
        """Generate 2-3 distractor words that don't belong"""
        distractors = []
        
        # Common distractor words by type
        distractor_pool = {
            'verbs': ['running', 'jumping', 'eating', 'sleeping', 'working'],
            'nouns': ['table', 'chair', 'book', 'computer', 'phone'],
            'adjectives': ['happy', 'sad', 'big', 'small', 'beautiful'],
            'adverbs': ['quickly', 'slowly', 'carefully', 'easily', 'hardly']
        }
        
        # Pick 2-3 random distractors that aren't in the sentence
        word_tokens = [t.lower() for t in tokens if t.isalnum()]
        
        for category in distractor_pool.values():
            for word in category:
                if word not in word_tokens and len(distractors) < 3:
                    distractors.append(word)
        
        return distractors[:3]
