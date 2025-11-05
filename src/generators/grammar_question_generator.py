"""
Grammar Question generator - Convert mistakes to multiple-choice questions
Production-ready with comprehensive error type handling
"""
from typing import List, Dict, Tuple
import random
import re

class GrammarQuestionGenerator:
    """Generates grammar questions from student mistakes"""
    
    def __init__(self):
        self.min_questions = 2
        self.max_questions = 4
        
        # Grammar category mapping
        self.category_map = {
            'grammar_past_tense': 'tense',
            'grammar_verb_tense': 'tense',
            'grammar_subject_verb': 'agreement',
            'grammar_article': 'articles',
            'grammar_preposition': 'prepositions',
            'grammar_pronoun': 'pronouns',
            'grammar_word_order': 'word_order',
            'grammar_plural': 'number',
            'vocabulary': 'vocabulary',
            'spelling': 'spelling'
        }
    
    def generate(self, mistakes: List[Dict], category_id: str, lesson_id: str) -> List[Dict]:
        """
        Generate grammar questions from mistakes
        
        Args:
            mistakes: List of student mistakes with corrections
            category_id: Grammar category identifier
            lesson_id: Lesson identifier
            
        Returns:
            List of grammar questions ready for database insertion
        """
        questions = []
        seen_prompts = set()
        
        # Filter grammar mistakes only
        grammar_mistakes = [m for m in mistakes if 'grammar' in m.get('error_type', '')]
        
        for mistake in grammar_mistakes:
            if len(questions) >= self.max_questions:
                break
            
            # Create question from mistake
            result = self._create_question_from_mistake(mistake)
            
            if result:
                prompt, options, correct_idx, explanation = result
                
                # Avoid duplicate prompts
                if prompt.lower() in seen_prompts:
                    continue
                
                # Create unique ID
                question_id = f"gc_{lesson_id}_q{len(questions) + 1}"
                
                questions.append({
                    'id': question_id,
                    'category_id': category_id,
                    'lesson_id': lesson_id,
                    'difficulty': self._assess_difficulty(mistake),
                    'prompt': prompt,
                    'options': options,
                    'correct_index': correct_idx,
                    'explanation': explanation
                })
                
                seen_prompts.add(prompt.lower())
        
        # If not enough grammar mistakes, create from patterns
        if len(questions) < self.min_questions:
            pattern_questions = self._generate_pattern_questions(category_id, lesson_id)
            questions.extend(pattern_questions[:self.min_questions - len(questions)])
        
        return questions
    
    def _create_question_from_mistake(self, mistake: Dict) -> Tuple:
        """Convert a mistake into a multiple-choice question"""
        incorrect = mistake.get('incorrect', '')
        correct = mistake.get('correct', '')
        error_type = mistake.get('error_type', '')
        
        if not incorrect or not correct:
            return None
        
        # Create prompt with blank
        prompt = self._create_prompt_with_blank(correct, mistake.get('focus_word', ''))
        
        if not prompt:
            return None
        
        # Generate 4 options (1 correct + 3 distractors)
        options, correct_idx = self._generate_options_from_mistake(
            incorrect, correct, error_type
        )
        
        # Generate explanation
        explanation = self._generate_explanation(
            correct, incorrect, error_type
        )
        
        return prompt, options, correct_idx, explanation
    
    def _create_prompt_with_blank(self, correct_sentence: str, focus_word: str) -> str:
        """Create a prompt with a blank for the focus word"""
        words = correct_sentence.split()
        
        # Find focus word or a key verb/word
        blank_word = None
        blank_idx = -1
        
        if focus_word:
            # Try to find focus word
            for i, word in enumerate(words):
                if focus_word.lower() in word.lower():
                    blank_word = word
                    blank_idx = i
                    break
        
        # If no focus word, find a verb or important word
        if blank_idx == -1:
            for i, word in enumerate(words):
                clean = re.sub(r'[^\w]', '', word).lower()
                # Look for verbs (common patterns)
                if (clean.endswith('ed') or clean.endswith('ing') or 
                    clean in ['is', 'are', 'was', 'were', 'have', 'has', 'had']):
                    blank_word = word
                    blank_idx = i
                    break
        
        if blank_idx == -1:
            return None
        
        # Create prompt with blank
        prompt_words = words.copy()
        prompt_words[blank_idx] = '____'
        prompt = ' '.join(prompt_words)
        
        return prompt
    
    def _generate_options_from_mistake(self, incorrect: str, correct: str, 
                                      error_type: str) -> Tuple[List[str], int]:
        """Generate 4 options based on the mistake type"""
        
        # Extract the key words
        inc_words = incorrect.split()
        cor_words = correct.split()
        
        # Find the differing word
        correct_word = None
        incorrect_word = None
        
        for i, (inc_w, cor_w) in enumerate(zip(inc_words, cor_words)):
            if inc_w.lower() != cor_w.lower():
                correct_word = cor_w
                incorrect_word = inc_w
                break
        
        if not correct_word:
            # Try to find from focus word
            for cor_w in cor_words:
                if cor_w.lower() not in [w.lower() for w in inc_words]:
                    correct_word = cor_w
                    break
        
        if not correct_word:
            correct_word = cor_words[0] if cor_words else 'correct'
        
        # Generate distractors based on error type
        distractors = self._generate_distractors_by_type(
            correct_word, incorrect_word, error_type
        )
        
        # Build options list
        options = [correct_word] + distractors[:3]
        
        # Ensure we have 4 options
        while len(options) < 4:
            options.append(correct_word + 's')  # Generic distractor
        
        # Shuffle and track correct index
        correct_idx = 0
        random.shuffle(options)
        correct_idx = options.index(correct_word)
        
        return options, correct_idx
    
    def _generate_distractors_by_type(self, correct: str, incorrect: str, 
                                     error_type: str) -> List[str]:
        """Generate distractors based on grammar error type"""
        distractors = []
        clean_correct = re.sub(r'[^\w]', '', correct).lower()
        
        if 'past_tense' in error_type:
            # Past tense errors
            if clean_correct.endswith('ed'):
                base = clean_correct[:-2] if clean_correct.endswith('ed') else clean_correct
                distractors = [base, base + 'ing', base + 's']
            else:
                # Irregular verbs
                irregular = {
                    'went': ['go', 'goes', 'going'],
                    'bought': ['buy', 'buys', 'buying'],
                    'ate': ['eat', 'eats', 'eating'],
                    'wrote': ['write', 'writes', 'writing'],
                    'spoke': ['speak', 'speaks', 'speaking']
                }
                if clean_correct in irregular:
                    distractors = irregular[clean_correct]
                else:
                    distractors = [clean_correct + 's', clean_correct + 'ing', 'have ' + clean_correct]
        
        elif 'verb_tense' in error_type:
            # General tense errors
            if clean_correct.endswith('ing'):
                base = clean_correct[:-3]
                distractors = [base, base + 'ed', base + 's']
            elif clean_correct.endswith('ed'):
                base = clean_correct[:-2]
                distractors = [base, base + 'ing', base + 's']
            else:
                distractors = [clean_correct + 'ed', clean_correct + 'ing', clean_correct + 's']
        
        elif 'subject_verb' in error_type or 'agreement' in error_type:
            # Subject-verb agreement
            if clean_correct in ['is', 'are', 'was', 'were']:
                distractors = ['is', 'are', 'was', 'were']
                distractors.remove(clean_correct)
            elif clean_correct.endswith('s'):
                base = clean_correct[:-1]
                distractors = [base, base + 'es', base + 'ed']
            else:
                distractors = [clean_correct + 's', clean_correct + 'es', clean_correct + 'ed']
        
        elif 'article' in error_type:
            # Article errors
            distractors = ['a', 'an', 'the', '']
            if clean_correct in distractors:
                distractors.remove(clean_correct)
        
        elif 'preposition' in error_type:
            # Preposition errors
            common_preps = ['in', 'on', 'at', 'to', 'for', 'with', 'by', 'from']
            distractors = [p for p in common_preps if p != clean_correct][:3]
        
        else:
            # Generic distractors
            if incorrect:
                distractors.append(re.sub(r'[^\w]', '', incorrect).lower())
            distractors.extend([clean_correct + 's', clean_correct + 'ed', clean_correct + 'ing'])
        
        # Remove duplicates and limit to 3
        distractors = list(dict.fromkeys(distractors))[:3]
        
        return distractors
    
    def _generate_explanation(self, correct: str, incorrect: str, error_type: str) -> str:
        """Generate explanation for the correct answer"""
        
        explanations = {
            'grammar_past_tense': f"Use past tense when describing completed actions. '{correct}' is the correct past tense form.",
            'grammar_verb_tense': f"The verb tense should match the time reference. '{correct}' is the appropriate tense here.",
            'grammar_subject_verb': f"The verb must agree with the subject. '{correct}' is the correct form for subject-verb agreement.",
            'grammar_article': f"The correct article usage is '{correct}' in this context.",
            'grammar_preposition': f"The correct preposition is '{correct}' when used with this verb/noun.",
            'grammar_pronoun': f"'{correct}' is the appropriate pronoun in this context.",
            'grammar_word_order': f"The correct word order is '{correct}'.",
            'grammar_plural': f"'{correct}' is the correct singular/plural form."
        }
        
        return explanations.get(error_type, f"The correct form is '{correct}'.")
    
    def _assess_difficulty(self, mistake: Dict) -> str:
        """Assess question difficulty"""
        error_type = mistake.get('error_type', '')
        severity = mistake.get('severity', 'medium')
        
        if 'past_tense' in error_type or 'article' in error_type:
            return 'easy'
        elif 'subject_verb' in error_type or 'preposition' in error_type:
            return 'medium'
        else:
            return 'hard' if severity == 'high' else 'medium'
    
    def _generate_pattern_questions(self, category_id: str, lesson_id: str) -> List[Dict]:
        """Generate questions from common grammar patterns when not enough mistakes"""
        pattern_questions = []
        
        # Common grammar patterns by category
        patterns = {
            'tense': [
                {
                    'prompt': 'Yesterday, I ____ to the store.',
                    'options': ['go', 'went', 'going', 'gone'],
                    'correct_index': 1,
                    'explanation': 'Use past tense "went" with time marker "yesterday".',
                    'difficulty': 'easy'
                },
                {
                    'prompt': 'She ____ working here for five years.',
                    'options': ['is', 'has been', 'was', 'will be'],
                    'correct_index': 1,
                    'explanation': 'Use present perfect continuous for actions continuing from past to present.',
                    'difficulty': 'medium'
                }
            ],
            'agreement': [
                {
                    'prompt': 'The team ____ ready for the match.',
                    'options': ['is', 'are', 'were', 'be'],
                    'correct_index': 0,
                    'explanation': 'Collective nouns like "team" take singular verbs.',
                    'difficulty': 'medium'
                }
            ],
            'articles': [
                {
                    'prompt': 'I need ____ umbrella because it is raining.',
                    'options': ['a', 'an', 'the', ''],
                    'correct_index': 1,
                    'explanation': 'Use "an" before words starting with vowel sounds.',
                    'difficulty': 'easy'
                }
            ]
        }
        
        category_patterns = patterns.get(category_id, patterns.get('tense', []))
        
        for i, pattern in enumerate(category_patterns[:2]):
            question_id = f"gc_{lesson_id}_pattern{i + 1}"
            pattern_questions.append({
                'id': question_id,
                'category_id': category_id,
                'lesson_id': lesson_id,
                **pattern
            })
        
        return pattern_questions
