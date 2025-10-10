# src/generators/fill_in_blank.py (COMPLETE REWRITE)
"""
Fill-in-the-blank exercise generator
"""

import random
from typing import List, Dict

from utils.gemini_helper import GeminiHelper

class FillInBlankGenerator:
    """Generates fill-in-the-blank exercises"""
    
    def __init__(self):
        self.gemini = GeminiHelper()
        self.min_exercises = 3
        self.max_exercises = 4
    
    def generate(self, vocabulary: List[Dict], mistakes: List[Dict], 
                 sentences: List[Dict]) -> List[Dict]:
        """Generate fill-in-blank exercises"""
        exercises = []
        used_sentences = set()
        
        # Use corrections as primary source
        for mistake in mistakes[:self.max_exercises]:
            if len(exercises) >= self.max_exercises:
                break
                
            sentence = mistake['correct']
            target_word = mistake['focus_word']
            
            if sentence not in used_sentences and target_word:
                exercise = self._create_exercise(sentence, target_word, 'correction')
                if exercise:
                    exercises.append(exercise)
                    used_sentences.add(sentence)
        
        # Add from sentences if needed
        for sent_data in sentences:
            if len(exercises) >= self.max_exercises:
                break
                
            sentence = sent_data['sentence']
            if sentence not in used_sentences:
                # Pick a meaningful word
                words = [w for w in sentence.split() 
                        if len(w) > 3 and w.isalpha()]
                if words:
                    target = random.choice(words[:3])
                    exercise = self._create_exercise(sentence, target, 'practice')
                    if exercise:
                        exercises.append(exercise)
                        used_sentences.add(sentence)
        
        return exercises
    
    def _create_exercise(self, sentence: str, target_word: str, 
                        context: str) -> Dict:
        """Create a single exercise"""
        # Clean inputs
        sentence = sentence.strip().strip('"')
        target_word = target_word.strip('.,!?"')
        
        # Create blank
        import re
        pattern = re.compile(r'\b' + re.escape(target_word) + r'\b', re.IGNORECASE)
        if not pattern.search(sentence):
            return None
            
        blanked = pattern.sub('_____', sentence, count=1)
        
        # Get distractors
        distractors = self.gemini.generate_distractors(target_word, sentence, 3)
        
        # Create options
        options = [target_word] + distractors
        random.shuffle(options)
        
        # Ensure we have 4 options
        while len(options) < 4:
            options.append('')
        
        return {
            'exercise_id': f'FB_{len(blanked)}',
            'sentence': blanked,
            'option_a': options[0],
            'option_b': options[1],
            'option_c': options[2],
            'option_d': options[3],
            'correct_answer': chr(65 + options.index(target_word)),
            'correct_word': target_word,
            'difficulty': 'beginner',
            'context_type': context
        }