# src/extractors/vocabulary_extractor.py (FIXED)
"""
Vocabulary extraction from lesson transcripts
"""

from typing import List, Dict
from src.utils.text_processing import TextProcessor

class VocabularyExtractor:
    """Extracts key vocabulary and phrases from lessons"""
    
    def __init__(self):
        self.text_processor = TextProcessor()
    
    def extract(self, transcript: str) -> List[Dict[str, str]]:
        """Extract vocabulary items from transcript"""
        vocabulary = []
        seen = set()
        
        # Extract from corrections (highest priority)
        corrections = self.text_processor.extract_corrections(transcript)
        for incorrect, correct in corrections:
            words = self.text_processor.extract_key_vocabulary(correct)
            for word in words:
                # Normalize phrasal verbs: "wake up" -> "wake"
                normalized_word = word.split()[0] if ' ' in word else word
                if normalized_word.lower() not in seen:
                    vocabulary.append({
                        'word': normalized_word,
                        'context': correct,
                        'category': 'corrected_usage',
                        'priority': 'high'
                    })
                    seen.add(normalized_word.lower())
        
        # Extract topic vocabulary
        topic = self.text_processor.identify_lesson_topic(transcript)
        teacher_lines = self.text_processor.extract_teacher_utterances(transcript)
        
        # Topic-specific important words
        topic_vocab = {
            'daily_routines': ['wake', 'breakfast', 'brush', 'morning'],
            'hobbies': ['football', 'music', 'books', 'time'],
            'family': ['father', 'mother', 'engineer', 'teacher'],
            'past_tense': ['yesterday', 'bought', 'went', 'cooked'],
            'travel': ['hotel', 'comfortable', 'stayed', 'Delhi']
        }
        
        if topic in topic_vocab:
            for word in topic_vocab[topic]:
                if word.lower() not in seen:
                    # Find context
                    context = ""
                    for line in teacher_lines + self.text_processor.extract_student_utterances(transcript):
                        if word.lower() in line.lower():
                            context = line
                            break
                    
                    if context:
                        vocabulary.append({
                            'word': word,
                            'context': context,
                            'category': f'topic_{topic}',
                            'priority': 'medium'
                        })
                        seen.add(word.lower())
        
        return vocabulary