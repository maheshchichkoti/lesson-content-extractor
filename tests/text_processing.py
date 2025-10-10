"""
Text processing utilities
Production-ready text parsing and analysis
"""

import re
from typing import List, Tuple, Dict

class TextProcessor:
    """Handles all text parsing and pattern matching"""
    
    @staticmethod
    def extract_corrections(transcript: str) -> List[Tuple[str, str]]:
        """Extract student mistakes and corrections from transcript."""
        corrections = []
        lines = transcript.strip().split('\n')

        for i in range(len(lines)):
            if 'Teacher:' in lines[i]:
                teacher_line = lines[i].replace('Teacher:', '').strip()

                patterns = [
                    r'[Cc]orrect(?:ion)?:\s*["\'“”]?([^"“”]+)["\'“”]?',
                    r'[Cc]orrect(?:\s+form)?:\s*["\'“”]?([^"“”]+)["\'“”]?',
                    r'(?:It\s+)?should\s+be:\s*["\'“”]?([^"“”]+)["\'“”]?',
                    r'[Bb]etter:\s*["\'“”]?([^"“”]+)["\'“”]?',
                    r'The correct sentence is\s*["\'“”]?([^"“”]+)["\'“”]?'
                ]
                for pattern in patterns:
                    match = re.search(pattern, teacher_line)
                    if match:
                        correct = match.group(1).strip()
                        # NO punctuation strip here – retain '.', '?', etc.
                        correct = correct.strip(' "')

                        # previous line = student error
                        if i > 0 and 'Student:' in lines[i-1]:
                            incorrect = lines[i-1].replace('Student:', '').strip()
                            incorrect = incorrect.strip(' "')
                            if incorrect and correct:
                                corrections.append((incorrect, correct))
                        break
        return corrections

    @staticmethod
    def extract_student_utterances(transcript: str) -> List[str]:
        return [
            line.replace('Student:', '').strip()
            for line in transcript.split('\n') if line.startswith('Student:')
        ]

    @staticmethod
    def extract_teacher_utterances(transcript: str) -> List[str]:
        return [
            line.replace('Teacher:', '').strip()
            for line in transcript.split('\n') if line.startswith('Teacher:')
        ]

    @staticmethod
    def identify_lesson_topic(transcript: str) -> str:
        teacher_lines = TextProcessor.extract_teacher_utterances(transcript)
        if not teacher_lines:
            return 'general'
        first = teacher_lines[0].lower()
        topics = {
            'daily_routines': ['routine', 'wake up', 'morning', 'breakfast', 'teeth'],
            'hobbies': ['hobbies', 'free time', 'football', 'music'],
            'family': ['family', 'father', 'mother'],
            'past_tense': ['yesterday', 'did you', 'describe yesterday'],
            'travel': ['travel', 'city', 'hotel', 'stayed', 'visited']
        }
        scores = {t: sum(k in first for k in kws) for t, kws in topics.items()}
        return max(scores, key=scores.get) if any(scores.values()) else 'general'

    @staticmethod
    def extract_key_vocabulary(sentence: str) -> List[str]:
        stop_words = {
            'i','you','he','she','it','we','they',
            'am','is','are','was','were','be','been','being',
            'have','has','had','a','an','the',
            'and','or','but','if','because','as','until','while',
            'to','in','on','at','for','with','by','from','of','about',
            'my','your','his','her','its','our','their',
            'what','when','where','why','how','which','who','whom',
            'this','that','these','those','also','very','then',
            'nice','good','try','well','can','will','should','may','might'
        }

        words = re.findall(r'\b[a-zA-Z]+\b', sentence.lower())
        vocab = [w for w in words if w not in stop_words and len(w) > 2]

        # add phrases
        phrases = {
            'wake up': r'\bwake\s+up\b',
            'brush teeth': r'\bbrush(?:ing)?\s+(?:my\s+)?teeth\b'
        }
        for phrase, pat in phrases.items():
            if re.search(pat, sentence.lower()):
                vocab.append(phrase)

        # Deduplicate
        seen, unique_vocab = set(), []
        for w in vocab:
            if w not in seen:
                unique_vocab.append(w)
                seen.add(w)

        # Normalize phrasal verbs “wake up” → “wake”
        normalized = []
        for w in unique_vocab:
            normalized.append(w.split()[0] if " " in w else w)
        unique_vocab = list(dict.fromkeys(normalized))
        return unique_vocab[:5]