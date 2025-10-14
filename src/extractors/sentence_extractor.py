"""
Useful sentence extraction for practice exercises
"""

from typing import List, Dict
from src.utils.text_processing import TextProcessor


class SentenceExtractor:
    """Extracts high-quality sentences for practice"""

    def __init__(self):
        self.text_processor = TextProcessor()

    def extract(self, transcript: str) -> List[Dict[str, str]]:
        """Extract useful practice sentences."""
        sentences: List[Dict[str, str]] = []
        seen = set()

        # Priority 1: corrected sentences from mistake-correction pairs
        corrections = self.text_processor.extract_corrections(transcript)
        for _, correct in corrections:
            if correct not in seen:
                sentences.append({
                    "sentence": correct,
                    "source": "correction",
                    "quality_score": 10,
                    "difficulty": "beginner"
                })
                seen.add(correct)

        # Priority 1.5: standalone correction patterns (Teacher corrections without Student lines)
        teacher_lines = self.text_processor.extract_teacher_utterances(transcript)
        for line in teacher_lines:
            # Check for correction patterns
            import re
            patterns = [
                r"[Cc]orrect(?:ion)?[:]?\s*[\"']([^\"']+)[\"']",
                r"[Cc]orrect(?:ion)?:\s*([^.]+)\.?$",
                r"The correct sentence is\s*[\"']([^\"']+)[\"']",
                r"[Bb]etter:\s*[\"']([^\"']+)[\"']"
            ]
            
            for pattern in patterns:
                match = re.search(pattern, line)
                if match:
                    correct = match.group(1).strip()
                    if correct and correct not in seen:
                        sentences.append({
                            "sentence": correct,
                            "source": "correction",
                            "quality_score": 10,
                            "difficulty": "beginner"
                        })
                        seen.add(correct)
                    break

        # Priority 2: uncorrected student sentences
        student_lines = self.text_processor.extract_student_utterances(transcript)
        corrected_lines = [inc for inc, _ in corrections]
        for line in student_lines:
            if line not in corrected_lines and line not in seen:
                sentences.append({
                    "sentence": line,
                    "source": "student_correct",
                    "quality_score": 8,
                    "difficulty": "beginner"
                })
                seen.add(line)

        return sentences