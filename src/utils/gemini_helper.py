# src/utils/gemini_helper.py
"""Google Gemini AI integration for content extraction
Production-ready with optimized prompts and comprehensive error handling"""

import os
from typing import List, Dict, Optional, Tuple
import logging
import json
import re

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

logger = logging.getLogger(__name__)

class GeminiHelper:
    """Production-ready Gemini AI wrapper with optimized prompts"""
    
    def __init__(self, prompt_style: str = 'detailed'):
        """
        Initialize Gemini AI helper
        
        Args:
            prompt_style: 'detailed', 'simple', or 'role' for A/B testing
        """
        self.api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
        self.prompt_style = prompt_style
        
        if self.api_key and GENAI_AVAILABLE:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-pro')
                self.enabled = True
                print(f"Google Gemini AI initialized (prompt style: {prompt_style})")
                logger.info(f"Gemini AI enabled with {prompt_style} prompts")
            except Exception as e:
                print(f"Gemini AI initialization failed: {e}. Using fallback.")
                logger.warning(f"Gemini init failed: {e}")
                self.enabled = False
                self.model = None
        else:
            if not GENAI_AVAILABLE:
                print("google-generativeai package not installed. Using rule-based fallback.")
            else:
                print("GOOGLE_API_KEY not found. Using rule-based fallback.")
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
    
    def translate_phrase(self, phrase: str, target_lang: str = 'Hebrew') -> str:
        """Translate phrase for flashcards"""
        
        # Simple translation dictionary (expandable)
        translations = {
            'wake up': 'להתעורר (lehitorer)',
            'breakfast': 'ארוחת בוקר (aruchat boker)',
            'bread': 'לחם (lechem)',
            'eggs': 'ביצים (beitzim)',
            'teeth': 'שיניים (shinayim)',
            'football': 'כדורגל (kaduregel)',
            'music': 'מוזיקה (muzika)',
            'books': 'ספרים (sefarim)',
            'family': 'משפחה (mishpacha)',
            'father': 'אבא (aba)',
            'mother': 'אמא (ima)',
            'engineer': 'מהנדס (mihandes)',
            'teacher': 'מורה (mora)',
            'market': 'שוק (shuk)',
            'vegetables': 'ירקות (yerakot)',
            'fruits': 'פירות (priyot)',
            'yesterday': 'אתמול (etmol)',
            'hotel': 'מלון (malon)',
            'comfortable': 'נוח (noach)',
            'sometimes': 'לפעמים (lepaamim)'
        }
        
        phrase_lower = phrase.lower()
        return translations.get(phrase_lower, f"[{phrase}]")
    
    def extract_vocabulary_with_ai(self, transcript: str, max_words: int = 15) -> List[Dict[str, str]]:
        """Extract vocabulary using optimized AI prompts"""
        
        if not self.enabled or not self.model:
            logger.warning("Gemini AI not available, using fallback")
            return self._fallback_vocabulary_extraction(transcript, max_words)
        
        try:
            # Select prompt based on style
            if self.prompt_style == 'detailed':
                prompt = self._get_detailed_vocab_prompt(transcript, max_words)
            elif self.prompt_style == 'simple':
                prompt = self._get_simple_vocab_prompt(transcript, max_words)
            else:  # role-based
                prompt = self._get_role_vocab_prompt(transcript, max_words)
            
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Parse JSON response
            vocab_list = self._parse_json_response(result_text)
            
            if vocab_list:
                # Validate quality
                validated = self._validate_vocabulary(vocab_list, transcript)
                logger.info(f"[OK] Gemini AI extracted {len(validated)} vocabulary words")
                return validated[:max_words]
            else:
                logger.warning("Could not parse Gemini response, using fallback")
                return self._fallback_vocabulary_extraction(transcript, max_words)
                
        except Exception as e:
            logger.error(f"Gemini AI vocabulary extraction failed: {e}")
            return self._fallback_vocabulary_extraction(transcript, max_words)
    
    def _get_detailed_vocab_prompt(self, transcript: str, max_words: int) -> str:
        """Detailed prompt with explicit formatting guidance"""
        return f"""Analyze this conversation transcript and extract the most important English vocabulary words that would help an intermediate learner.

Instructions:
1. Identify {max_words} useful English words or phrases (prioritize mistakes, key topics, and practical expressions).
2. For each item include:
   - "word": the vocabulary word or phrase
   - "context": a simple example sentence from the transcript (or create a natural sentence if needed)
   - "difficulty": "beginner", "intermediate", or "advanced"

Transcript:
{transcript[:2500]}

Format your response EXACTLY as a JSON array. Example:
[
  {{"word": "breakfast", "context": "I eat breakfast at 8 AM.", "difficulty": "beginner"}},
  {{"word": "comfortable", "context": "The hotel was very comfortable.", "difficulty": "intermediate"}}
]

Return ONLY the JSON array with no extra commentary."""
    
    def _get_simple_vocab_prompt(self, transcript: str, max_words: int) -> str:
        """Concise prompt variant"""
        return f"""From the following transcript, list {max_words} important English words that students should practice.
For each entry include the word, a clear example sentence, and the difficulty level.

Transcript:
{transcript[:2000]}

Output JSON only in this shape:
[{{"word": "...", "context": "...", "difficulty": "beginner/intermediate/advanced"}}]

Do not include any extra prose—return just the JSON array."""
    
    def _get_role_vocab_prompt(self, transcript: str, max_words: int) -> str:
        """Role-based prompt aimed at teaching context"""
        return f"""You are preparing feedback for your ESL class. Review this transcript and choose {max_words} vocabulary words your students must study.
Focus on real-world usefulness, mistakes the students made, and the lesson's main theme.

For each item report:
- "word": the vocabulary item
- "context": a short example sentence (prefer the transcript; otherwise craft a natural example)
- "difficulty": beginner / intermediate / advanced

Transcript:
{transcript[:2500]}

Return ONLY a JSON array like:
[{{"word": "...", "context": "...", "difficulty": "..."}}]"""
    
    def generate_lesson_feedback(self, transcript: str) -> Dict[str, any]:
        """Generate comprehensive lesson feedback using AI"""
        
        if not self.enabled or not self.model:
            logger.warning("Gemini AI not available for feedback generation")
            return self._fallback_feedback(transcript)
        
        try:
            prompt = f"""Analyze this English lesson transcript and provide constructive feedback for the student.

Transcript:
{transcript[:3000]}

Provide detailed feedback in these categories:

1. STRENGTHS: What did the student do well? (2-3 specific points)
2. AREAS FOR IMPROVEMENT: What mistakes were made? (2-3 specific issues)
3. VOCABULARY LEARNED: Key words/phrases from this lesson (5-8 words)
4. GRAMMAR POINTS: Grammar concepts covered or needing practice
5. NEXT STEPS: Specific recommendations for practice

Format as JSON:
{{
  "strengths": ["Good use of past tense in most sentences", "Clear pronunciation of difficult words"],
  "improvements": ["Practice using articles (a, an, the)", "Work on subject-verb agreement"],
  "vocabulary_learned": ["breakfast", "comfortable", "yesterday", "market"],
  "grammar_points": ["Past simple tense", "Daily routine expressions"],
  "next_steps": ["Practice daily routine vocabulary", "Review past tense irregular verbs"],
  "overall_level": "intermediate",
  "progress_notes": "Student is making good progress with conversational English"
}}

Return only the JSON object."""
            
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Parse JSON
            feedback = self._parse_json_response(result_text, expect_array=False)
            
            if feedback:
                logger.info("[OK] Generated lesson feedback successfully")
                return feedback
            else:
                return self._fallback_feedback(transcript)
                
        except Exception as e:
            logger.error(f"Feedback generation failed: {e}")
            return self._fallback_feedback(transcript)
    
    def generate_fill_blank_exercises(self, transcript: str, count: int = 8) -> List[Dict[str, any]]:
        """Generate fill-in-blank exercises using AI"""
        
        if not self.enabled or not self.model:
            logger.warning("Gemini AI not available for fill-in-blank generation")
            return []
        
        try:
            prompt = f"""Create {count} fill-in-blank exercises from this lesson transcript.

Transcript:
{transcript[:2500]}

Instructions:
1. Select {count} sentences from the transcript (or create similar ones)
2. For each sentence, remove ONE key word (verb, noun, adjective, or adverb)
3. Provide 4 options: 1 correct answer + 3 plausible distractors
4. Distractors should be grammatically similar but contextually wrong
5. Mark which option is correct

Few-shot example:
Original: "I wake up at 7 AM every morning."
Exercise: "I ___ up at 7 AM every morning."
Options: ["wake", "woke", "waking", "woken"]
Correct: "wake"

Format as JSON array:
[
  {{
    "sentence": "I ___ up at 7 AM every morning.",
    "blank_word": "wake",
    "options": ["wake", "woke", "waking", "woken"],
    "correct_answer": "wake",
    "difficulty": "beginner",
    "explanation": "Present simple tense for daily routines"
  }}
]

Return only the JSON array with {count} exercises."""
            
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            exercises = self._parse_json_response(result_text)
            
            if exercises:
                logger.info(f"[OK] Generated {len(exercises)} fill-in-blank exercises")
                return exercises[:count]
            else:
                logger.warning("Could not parse fill-in-blank response")
                return []
                
        except Exception as e:
            logger.error(f"Fill-in-blank generation failed: {e}")
            return []
    
    def generate_spelling_exercises(self, transcript: str, count: int = 10) -> List[Dict[str, str]]:
        """Generate spelling exercises using AI"""
        
        if not self.enabled or not self.model:
            logger.warning("Gemini AI not available for spelling generation")
            return []
        
        try:
            prompt = f"""Generate {count} spelling practice words from this lesson transcript.

Transcript:
{transcript[:2500]}

Select {count} words that:
1. Are important for students to spell correctly
2. Are at appropriate difficulty (not too easy, not too hard)
3. Appear in the lesson or are topic-relevant
4. Range from 4-12 letters

For each word provide:
- The word to spell
- A clear example sentence
- Difficulty level
- Optional hint about the word

Format as JSON array:
[
  {{
    "word": "breakfast",
    "sample_sentence": "I eat breakfast at 8 o'clock every morning",
    "difficulty": "intermediate",
    "hint": "First meal of the day",
    "word_type": "noun"
  }}
]

Return only the JSON array with {count} words."""
            
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            spelling_words = self._parse_json_response(result_text)
            
            if spelling_words:
                logger.info(f"[OK] Generated {len(spelling_words)} spelling exercises")
                return spelling_words[:count]
            else:
                logger.warning("Could not parse spelling response")
                return []
                
        except Exception as e:
            logger.error(f"Spelling generation failed: {e}")
            return []
    
    def _parse_json_response(self, text: str, expect_array: bool = True) -> Optional[any]:
        """Parse JSON from AI response with error handling"""
        try:
            # Remove markdown code blocks if present
            text = re.sub(r'```json\s*', '', text)
            text = re.sub(r'```\s*', '', text)
            
            # Try to find JSON in response
            if expect_array:
                json_match = re.search(r'\[.*\]', text, re.DOTALL)
            else:
                json_match = re.search(r'\{.*\}', text, re.DOTALL)
            
            if json_match:
                return json.loads(json_match.group())
            else:
                # Try parsing entire text
                return json.loads(text)
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Response parsing error: {e}")
            return None
    
    def _validate_vocabulary(self, vocab_list: List[Dict], transcript: str) -> List[Dict]:
        """Validate and filter vocabulary results"""
        validated = []
        seen_words = set()
        
        # Common words to exclude
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 
                     'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                     'i', 'you', 'he', 'she', 'it', 'we', 'they', 'this', 'that'}
        
        for item in vocab_list:
            word = item.get('word', '').lower().strip()
            
            # Validation checks
            if not word:
                continue
            if word in stop_words:
                continue
            if word in seen_words:
                continue
            if len(word) < 2 or len(word) > 30:
                continue
            
            # Ensure required fields
            if 'context' not in item:
                item['context'] = f"Example with {word}"
            if 'difficulty' not in item:
                item['difficulty'] = 'intermediate'
            
            validated.append(item)
            seen_words.add(word)
        
        return validated
    
    def _fallback_feedback(self, transcript: str) -> Dict[str, any]:
        """Fallback feedback when AI is unavailable"""
        return {
            "strengths": ["Completed the lesson", "Engaged in conversation"],
            "improvements": ["Continue practicing", "Review vocabulary"],
            "vocabulary_learned": [],
            "grammar_points": ["General practice"],
            "next_steps": ["Practice daily", "Review lesson content"],
            "overall_level": "intermediate",
            "progress_notes": "Keep up the good work!"
        }
    
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
        
        logger.info(f"[OK] Fallback extracted {len(vocabulary)} vocabulary words")
        return vocabulary
