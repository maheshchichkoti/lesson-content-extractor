"""
Text processing utilities
Production-ready text parsing and analysis
"""

import re
from typing import List, Tuple, Dict


class TextProcessor:
    """Handles all text parsing and pattern matching."""

    # ------------------------------------------------------------------
    @staticmethod
    def extract_corrections(transcript: str) -> List[Tuple[str, str]]:
        """
        Extract student mistakes and teacher corrections – tolerant to punctuation,
        quotes, and trailing periods.
        """
        corrections: List[Tuple[str, str]] = []
        
        # Handle both newline-separated and inline transcripts
        if '\n' in transcript:
            lines = transcript.strip().split("\n")
        else:
            # Split on Teacher:/Student: markers for inline transcripts
            lines = re.split(r'(?=(?:Teacher|Student):)', transcript.strip())
            lines = [l.strip() for l in lines if l.strip()]

        for i, line in enumerate(lines):
            if "Teacher:" not in line:
                continue
            teacher_line = line.replace("Teacher:", "").strip()

            # patterns – covers quoted and unquoted corrections
            patterns = [
                # "Correction: I bought..." -> "I bought..."
                r"[Cc]orrect(?:ion)?[:]?\s+([A-Z][^.!?]+)",
                # "The correct sentence is: Yesterday I went..." -> "Yesterday I went..."
                r"The correct sentence is[:\s]+([A-Z][^.!?]+)",
                # "should be: I am..." -> "I am..."
                r"(?:It\s+)?should\s+be[:\s]+([A-Z][^.!?]+)",
                # "Better: My father..." -> "My father..."
                r"[Bb]etter[:\s]+([A-Z][^.!?]+)",
                # "Correct: My father is an engineer" -> "My father is an engineer"
                r"[Cc]orrect[:\s]+([A-Z][^.!?]+)"
            ]

            for pat in patterns:
                match = re.search(pat, teacher_line)
                if not match:
                    continue
                correct = match.group(1).strip().strip('\"“”\' ')
                if i > 0 and "Student:" in lines[i - 1]:
                    incorrect = lines[i - 1].replace("Student:", "").strip().strip('\"“”\' ')
                    if incorrect and correct:
                        corrections.append((incorrect, correct))
                break
        return corrections

    # ------------------------------------------------------------------
    @staticmethod
    def extract_student_utterances(transcript: str) -> List[str]:
        """Extract all student utterances."""
        return [
            l.replace("Student:", "").strip()
            for l in transcript.split("\n")
            if l.startswith("Student:")
        ]

    @staticmethod
    def extract_teacher_utterances(transcript: str) -> List[str]:
        """Extract all teacher utterances."""
        return [
            l.replace("Teacher:", "").strip()
            for l in transcript.split("\n")
            if l.startswith("Teacher:")
        ]

    # ------------------------------------------------------------------
    @staticmethod
    def identify_lesson_topic(transcript: str) -> str:
        """Identify the lesson topic from teacher's introduction."""
        teachers = TextProcessor.extract_teacher_utterances(transcript)
        if not teachers:
            return "general"
        first = teachers[0].lower()
        topics = {
            "daily_routines": ["routine", "wake up", "morning", "breakfast", "teeth"],
            "hobbies": ["hobbies", "free time", "football", "music"],
            "family": ["family", "father", "mother"],
            "past_tense": ["yesterday", "did you", "describe yesterday", "what did"],
            "travel": ["travel", "city", "hotel", "stayed", "visited"],
        }
        scores = {t: sum(k in first for k in kws) for t, kws in topics.items()}
        return max(scores, key=scores.get) if any(scores.values()) else "general"

    # ------------------------------------------------------------------
    @staticmethod
    def extract_key_vocabulary(sentence: str) -> List[str]:
        """Extract meaningful vocabulary and normalize phrasal verbs."""
        stop_words = {
            'i','you','he','she','it','we','they','am','is','are','was','were','be','been',
            'being','have','has','had','a','an','the','and','or','but','if','because','as',
            'until','while','to','in','on','at','for','with','by','from','of','about','my',
            'your','his','her','its','our','their','what','when','where','why','how','which',
            'who','whom','this','that','these','those','also','very','then','nice','good',
            'try','well','can','could','will','would','should','may','might','must'
        }

        # Break to words
        words = re.findall(r"\b[a-zA-Z]+\b", sentence.lower())
        vocab = [w for w in words if w not in stop_words and len(w) > 2]

        # detect key phrases
        phrases = {
            "wake up": r"\bwake\s+up\b",
            "brush teeth": r"\bbrush(?:ing)?\s+(?:my\s+)?teeth\b",
            "free time": r"\bfree\s+time\b",
            "last year": r"\blast\s+year\b",
        }
        for phrase, pat in phrases.items():
            if re.search(pat, sentence.lower()):
                vocab.append(phrase)

        # normalize phrasal verbs before deduplication
        normalized = [w.split()[0] if " " in w else w for w in vocab]

        # deduplicate preserving order
        seen, unique = set(), []
        for w in normalized:
            if w not in seen:
                unique.append(w)
                seen.add(w)
        return unique[:5]