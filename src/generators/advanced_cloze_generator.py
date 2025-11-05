"""
Advanced Cloze generator - Multi-blank fill-in exercises
Production-ready with quality checks and error handling
"""
from typing import List, Dict, Tuple
import re
import random
from src.utils.gemini_helper import GeminiHelper

class AdvancedClozeGenerator:
    """Generates multi-blank cloze exercises from sentences"""
    
    def __init__(self):
        self.gemini = GeminiHelper()
        self.min_items = 2
        self.max_items = 4
        
        # Key word patterns to identify important words
        self.key_patterns = [
            r'\b(phrasal verbs?|idioms?|expressions?)\b',
            r'\b(formal|informal|academic|business)\b',
            r'\b(collocations?)\b'
        ]
        
        # Words to avoid as blanks
        self.skip_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'can', 'could', 'should', 'may', 'might', 'must', 'i', 'you',
            'he', 'she', 'it', 'we', 'they', 'this', 'that', 'these', 'those'
        }
    
    def generate(self, sentences: List[Dict], vocabulary: List[Dict], 
                 topic_id: str, lesson_id: str) -> List[Dict]:
        """
        Generate advanced cloze items from sentences
        
        Args:
            sentences: List of extracted sentences
            vocabulary: List of vocabulary items for context
            topic_id: Topic identifier
            lesson_id: Lesson identifier
            
        Returns:
            List of cloze items ready for database insertion
        """
        cloze_items = []
        seen_sentences = set()
        
        # Filter quality sentences
        quality_sentences = self._filter_quality_sentences(sentences)
        
        for sent_data in quality_sentences:
            if len(cloze_items) >= self.max_items:
                break
                
            sentence = sent_data.get('text', '')
            if not sentence or sentence.lower() in seen_sentences:
                continue
            
            # Generate multi-blank cloze
            result = self._create_multi_blank_cloze(sentence, vocabulary)
            
            if result:
                text_parts, options, correct, explanation = result
                
                # Create unique ID
                item_id = f"ac_{lesson_id}_{len(cloze_items) + 1}"
                
                cloze_items.append({
                    'id': item_id,
                    'topic_id': topic_id,
                    'lesson_id': lesson_id,
                    'difficulty': self._assess_difficulty(sentence, correct),
                    'text_parts': text_parts,
                    'options': options,
                    'correct': correct,
                    'explanation': explanation
                })
                
                seen_sentences.add(sentence.lower())
        
        # Ensure minimum count
        if len(cloze_items) < self.min_items and len(quality_sentences) > 0:
            # Try with relaxed criteria
            for sent_data in quality_sentences[:5]:
                if len(cloze_items) >= self.min_items:
                    break
                sentence = sent_data.get('text', '')
                if sentence.lower() not in seen_sentences:
                    result = self._create_single_blank_cloze(sentence)
                    if result:
                        text_parts, options, correct, explanation = result
                        item_id = f"ac_{lesson_id}_{len(cloze_items) + 1}"
                        cloze_items.append({
                            'id': item_id,
                            'topic_id': topic_id,
                            'lesson_id': lesson_id,
                            'difficulty': 'easy',
                            'text_parts': text_parts,
                            'options': options,
                            'correct': correct,
                            'explanation': explanation
                        })
                        seen_sentences.add(sentence.lower())
        
        return cloze_items
    
    def _filter_quality_sentences(self, sentences: List[Dict]) -> List[Dict]:
        """Filter sentences suitable for cloze exercises"""
        quality = []
        
        for sent in sentences:
            text = sent.get('text', '')
            
            # Length check
            word_count = len(text.split())
            if word_count < 8 or word_count > 30:
                continue
            
            # Has meaningful content
            if any(pattern in text.lower() for pattern in ['should', 'must', 'need to', 'have to']):
                quality.append(sent)
            elif word_count >= 12:
                quality.append(sent)
        
        return quality
    
    def _create_multi_blank_cloze(self, sentence: str, vocabulary: List[Dict]) -> Tuple:
        """Create cloze with 2-3 blanks"""
        words = sentence.split()
        
        # Identify 2-3 key words to blank out
        key_indices = self._identify_key_word_indices(words, vocabulary)
        
        if len(key_indices) < 2:
            return None
        
        # Take top 2-3 key words
        key_indices = sorted(key_indices[:3])
        
        # Build text parts and collect correct answers
        text_parts = []
        correct = []
        current_pos = 0
        
        for idx in key_indices:
            # Add text before blank
            before = ' '.join(words[current_pos:idx])
            text_parts.append(before + ' ' if before else '')
            
            # Add correct answer
            correct.append(words[idx])
            current_pos = idx + 1
        
        # Add remaining text
        remaining = ' '.join(words[current_pos:])
        text_parts.append(' ' + remaining if remaining else '')
        
        # Generate options for each blank
        options = []
        for correct_word in correct:
            word_options = self._generate_distractors(correct_word, sentence)
            options.append(word_options)
        
        # Generate explanation
        explanation = self._generate_explanation(correct, sentence)
        
        return text_parts, options, correct, explanation
    
    def _create_single_blank_cloze(self, sentence: str) -> Tuple:
        """Fallback: create simple single-blank cloze"""
        words = sentence.split()
        
        # Find a good word to blank
        for i, word in enumerate(words):
            clean_word = re.sub(r'[^\w]', '', word).lower()
            if (len(clean_word) > 4 and 
                clean_word not in self.skip_words and
                word[0].isupper() == False):
                
                # Create single blank
                text_parts = [
                    ' '.join(words[:i]) + ' ',
                    ' ' + ' '.join(words[i+1:])
                ]
                
                correct = [clean_word]
                options = [self._generate_distractors(clean_word, sentence)]
                explanation = f"The correct word is '{clean_word}'."
                
                return text_parts, options, correct, explanation
        
        return None
    
    def _identify_key_word_indices(self, words: List[str], vocabulary: List[Dict]) -> List[int]:
        """Identify indices of key words suitable for blanking"""
        key_indices = []
        vocab_words = {v['word'].lower() for v in vocabulary}
        
        for i, word in enumerate(words):
            clean_word = re.sub(r'[^\w]', '', word).lower()
            
            # Skip common words
            if clean_word in self.skip_words or len(clean_word) < 4:
                continue
            
            # Prioritize vocabulary words
            if clean_word in vocab_words:
                key_indices.append(i)
            # Or longer meaningful words
            elif len(clean_word) >= 6 and word[0].isupper() == False:
                key_indices.append(i)
        
        return key_indices
    
    def _generate_distractors(self, correct_word: str, context: str) -> List[str]:
        """Generate 3 distractor options + 1 correct"""
        clean_word = re.sub(r'[^\w]', '', correct_word).lower()
        
        # Common distractor patterns
        distractors = set()
        
        # Similar length words
        if len(clean_word) >= 6:
            # Phonetically similar
            if clean_word.endswith('ing'):
                distractors.add(clean_word[:-3] + 'ed')
                distractors.add(clean_word[:-3] + 'ion')
            elif clean_word.endswith('ed'):
                distractors.add(clean_word[:-2] + 'ing')
            elif clean_word.endswith('tion'):
                distractors.add(clean_word[:-4] + 'te')
        
        # Common confusables
        confusables = {
            'affect': ['effect', 'infect', 'defect'],
            'accept': ['except', 'expect', 'adapt'],
            'advice': ['advise', 'device', 'devise'],
            'complement': ['compliment', 'implement', 'supplement'],
            'principal': ['principle', 'practical', 'essential']
        }
        
        if clean_word in confusables:
            distractors.update(confusables[clean_word][:2])
        
        # Ensure we have 3 distractors
        while len(distractors) < 3:
            # Add generic distractors
            generic = ['complete', 'consider', 'continue', 'develop', 'establish',
                      'maintain', 'provide', 'require', 'support', 'understand']
            for g in generic:
                if g != clean_word and len(g) >= len(clean_word) - 2:
                    distractors.add(g)
                    if len(distractors) >= 3:
                        break
        
        # Build final options list
        options = [clean_word] + list(distractors)[:3]
        random.shuffle(options)
        
        return options
    
    def _assess_difficulty(self, sentence: str, correct_words: List[str]) -> str:
        """Assess difficulty level"""
        word_count = len(sentence.split())
        avg_word_len = sum(len(w) for w in correct_words) / len(correct_words)
        
        if len(correct_words) >= 3 or avg_word_len >= 8:
            return 'hard'
        elif word_count >= 15 or avg_word_len >= 6:
            return 'medium'
        else:
            return 'easy'
    
    def _generate_explanation(self, correct_words: List[str], sentence: str) -> str:
        """Generate explanation for the correct answers"""
        if len(correct_words) == 1:
            return f"The correct word is '{correct_words[0]}'."
        elif len(correct_words) == 2:
            return f"The correct words are '{correct_words[0]}' and '{correct_words[1]}'."
        else:
            words_str = "', '".join(correct_words[:-1]) + f"', and '{correct_words[-1]}'"
            return f"The correct words are '{words_str}'."
