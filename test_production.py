"""Test script to verify production readiness"""

import json
from src.main import LessonProcessor

# Sample transcript
transcript = """Teacher: Good morning! Today we'll practice past tense verbs.

Student: Yesterday I go to the market.

Teacher: Good try! But we need past tense. The correct sentence is: 'Yesterday I went to the market.' Remember, 'go' becomes 'went' in past tense.

Student: Oh, I see. Yesterday I went to the market.

Teacher: Perfect! Now tell me, what did you buy?

Student: I buy some vegetables and eggs.

Teacher: Almost! Correction: 'I bought some vegetables and eggs.' The past tense of 'buy' is 'bought'.

Student: I bought some vegetables and eggs.

Teacher: Excellent! Let's practice more. Important vocabulary: yesterday, market, bought, vegetables, comfortable, necessary.

Student: My father is engineer.

Teacher: Good sentence, but we need an article. Correct: 'My father is an engineer.'

Student: My father is an engineer.

Teacher: Very good! Now you're using articles correctly."""

print("="*70)
print("PRODUCTION READINESS TEST")
print("="*70)

processor = LessonProcessor()
result = processor.process_lesson(transcript, 1)

print("\n" + "="*70)
print("RESULTS")
print("="*70)

print(f"\n✓ Fill-in-blank: {len(result['fill_in_blank'])} exercises")
for i, ex in enumerate(result['fill_in_blank'][:2], 1):
    print(f"  {i}. {ex['sentence'][:80]}...")
    print(f"     Answer: {ex['correct_word']}")

print(f"\n✓ Flashcards: {len(result['flashcards'])} cards")
for i, card in enumerate(result['flashcards'][:2], 1):
    print(f"  {i}. {card['word']} = {card['translation']}")
    print(f"     Example: {card['example_sentence'][:80]}...")

print(f"\n✓ Spelling: {len(result['spelling'])} words")
for i, spell in enumerate(result['spelling'][:2], 1):
    print(f"  {i}. {spell['word']}")
    print(f"     Sentence: {spell['sample_sentence'][:80]}...")

total = len(result['fill_in_blank']) + len(result['flashcards']) + len(result['spelling'])
quality_passed = 8 <= total <= 12

print(f"\n" + "="*70)
print(f"TOTAL EXERCISES: {total}")
print(f"QUALITY CHECK: {'✅ PASSED' if quality_passed else '❌ FAILED'}")
print(f"TARGET RANGE: 8-12 exercises")
print("="*70)

# Check example sentence lengths
print("\n" + "="*70)
print("EXAMPLE SENTENCE LENGTH CHECK")
print("="*70)

for card in result['flashcards']:
    length = len(card['example_sentence'])
    status = "✅" if length < 200 else "❌"
    print(f"{status} {card['word']}: {length} chars")

for spell in result['spelling']:
    length = len(spell['sample_sentence'])
    status = "✅" if length < 200 else "❌"
    print(f"{status} {spell['word']}: {length} chars")

print("\n" + "="*70)
if quality_passed and all(len(c['example_sentence']) < 200 for c in result['flashcards']):
    print("🎉 PRODUCTION READY!")
else:
    print("⚠️  NEEDS FIXES")
print("="*70)