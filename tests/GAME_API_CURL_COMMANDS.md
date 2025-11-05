# Tulkka Games API - Complete cURL Reference

## Environment Variables
```bash
export BASE_URL="http://localhost:8000"
export USER_ID="test_user_123"
```

---

## Health & Root

### Health Check
```bash
curl -X GET "$BASE_URL/health"
```

### Root Info
```bash
curl -X GET "$BASE_URL/"
```

---

## Word Lists Management

### Create Word List
```bash
curl -X POST "$BASE_URL/v1/word-lists?user_id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Vocabulary List",
    "description": "Words from lesson 1"
  }'
```

### Get All Word Lists
```bash
curl -X GET "$BASE_URL/v1/word-lists?user_id=$USER_ID&page=1&limit=10"
```

### Get Single Word List
```bash
curl -X GET "$BASE_URL/v1/word-lists/{list_id}?user_id=$USER_ID&include=words"
```

### Update Word List
```bash
curl -X PATCH "$BASE_URL/v1/word-lists/{list_id}?user_id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated List Name",
    "description": "Updated description"
  }'
```

### Delete Word List
```bash
curl -X DELETE "$BASE_URL/v1/word-lists/{list_id}?user_id=$USER_ID"
```

### Toggle List Favorite
```bash
curl -X POST "$BASE_URL/v1/word-lists/{list_id}/favorite?user_id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{"isFavorite": true}'
```

---

## Words Management

### Add Word to List
```bash
curl -X POST "$BASE_URL/v1/word-lists/{list_id}/words?user_id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "word": "hello",
    "translation": "مرحبا",
    "notes": "Common greeting"
  }'
```

### Update Word
```bash
curl -X PATCH "$BASE_URL/v1/word-lists/{list_id}/words/{word_id}?user_id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "translation": "أهلاً",
    "notes": "Updated translation"
  }'
```

### Delete Word
```bash
curl -X DELETE "$BASE_URL/v1/word-lists/{list_id}/words/{word_id}?user_id=$USER_ID"
```

### Toggle Word Favorite
```bash
curl -X POST "$BASE_URL/v1/word-lists/{list_id}/words/{word_id}/favorite?user_id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{"isFavorite": true}'
```

---

## Flashcards Game

### Start Flashcard Session
```bash
curl -X POST "$BASE_URL/v1/flashcards/sessions?user_id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "wordListId": "list_123",
    "selectedWordIds": ["word_1", "word_2"]
  }'
```

### Get Flashcard Session
```bash
curl -X GET "$BASE_URL/v1/flashcards/sessions/{session_id}?user_id=$USER_ID"
```

### Record Flashcard Result
```bash
curl -X POST "$BASE_URL/v1/flashcards/sessions/{session_id}/results?user_id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "wordId": "word_1",
    "isCorrect": true,
    "attempts": 1,
    "timeSpent": 4
  }'
```

### Complete Flashcard Session
```bash
curl -X POST "$BASE_URL/v1/flashcards/sessions/{session_id}/complete?user_id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "progress": {
      "current": 10,
      "total": 10,
      "correct": 8,
      "incorrect": 2
    }
  }'
```

### Get Flashcard Stats
```bash
curl -X GET "$BASE_URL/v1/flashcards/stats/me?user_id=$USER_ID"
```

---

## Spelling Bee Game

### Start Spelling Session
```bash
curl -X POST "$BASE_URL/v1/spelling/sessions?user_id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "wordListId": "list_123",
    "selectedWordIds": ["word_1", "word_2"],
    "shuffle": true
  }'
```

### Get Spelling Session
```bash
curl -X GET "$BASE_URL/v1/spelling/sessions/{session_id}?user_id=$USER_ID"
```

### Record Spelling Result
```bash
curl -X POST "$BASE_URL/v1/spelling/sessions/{session_id}/results?user_id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "wordId": "word_1",
    "userAnswer": "hello",
    "isCorrect": true,
    "attempts": 1,
    "timeSpent": 5
  }'
```

### Complete Spelling Session
```bash
curl -X POST "$BASE_URL/v1/spelling/sessions/{session_id}/complete?user_id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "progress": {
      "current": 10,
      "total": 10,
      "correct": 9,
      "incorrect": 1
    }
  }'
```

### Get Pronunciation
```bash
curl -X GET "$BASE_URL/v1/spelling/pronunciations/{word_id}?user_id=$USER_ID"
```

---

## Advanced Cloze Game

### Get Topics
```bash
curl -X GET "$BASE_URL/v1/advanced-cloze/topics"
```

### Get Lessons
```bash
curl -X GET "$BASE_URL/v1/advanced-cloze/lessons?topicId=phrasalVerbs"
```

### Get Items
```bash
curl -X GET "$BASE_URL/v1/advanced-cloze/items?lessonId=pv_business&include=options&limit=20"
```

### Start Cloze Session
```bash
curl -X POST "$BASE_URL/v1/advanced-cloze/sessions?user_id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "lesson",
    "topicId": "phrasalVerbs",
    "lessonId": "pv_business",
    "difficulty": "medium",
    "limit": 10
  }'
```

### Get Cloze Session
```bash
curl -X GET "$BASE_URL/v1/advanced-cloze/sessions/{session_id}?user_id=$USER_ID&include=options"
```

### Record Cloze Result
```bash
curl -X POST "$BASE_URL/v1/advanced-cloze/sessions/{session_id}/results?user_id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "itemId": "ac_101",
    "selectedAnswers": ["phase out", "bring in"],
    "isCorrect": true,
    "attempts": 1,
    "timeSpent": 7
  }'
```

### Complete Cloze Session
```bash
curl -X POST "$BASE_URL/v1/advanced-cloze/sessions/{session_id}/complete?user_id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "progress": {
      "current": 10,
      "total": 10,
      "correct": 7,
      "incorrect": 3
    }
  }'
```

### Get Cloze Hint
```bash
curl -X GET "$BASE_URL/v1/advanced-cloze/items/{item_id}/hint?user_id=$USER_ID"
```

### Get Cloze Mistakes
```bash
curl -X GET "$BASE_URL/v1/advanced-cloze/mistakes?user_id=$USER_ID&page=1&limit=50"
```

---

## Grammar Challenge Game

### Get Categories
```bash
curl -X GET "$BASE_URL/v1/grammar-challenge/categories"
```

### Get Lessons
```bash
curl -X GET "$BASE_URL/v1/grammar-challenge/lessons?categoryId=tense"
```

### Get Questions
```bash
curl -X GET "$BASE_URL/v1/grammar-challenge/questions?lessonId=tense_pp_sp&include=options&limit=20"
```

### Start Grammar Session
```bash
curl -X POST "$BASE_URL/v1/grammar-challenge/sessions?user_id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "lesson",
    "categoryId": "tense",
    "lessonId": "tense_pp_sp",
    "difficulty": "medium",
    "limit": 10
  }'
```

### Get Grammar Session
```bash
curl -X GET "$BASE_URL/v1/grammar-challenge/sessions/{session_id}?user_id=$USER_ID&include=options"
```

### Record Grammar Result
```bash
curl -X POST "$BASE_URL/v1/grammar-challenge/sessions/{session_id}/results?user_id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "questionId": "gc_q_101",
    "selectedAnswer": 1,
    "isCorrect": true,
    "attempts": 1,
    "timeSpent": 6
  }'
```

### Skip Grammar Question
```bash
curl -X POST "$BASE_URL/v1/grammar-challenge/sessions/{session_id}/skip?user_id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "questionId": "gc_q_205"
  }'
```

### Complete Grammar Session
```bash
curl -X POST "$BASE_URL/v1/grammar-challenge/sessions/{session_id}/complete?user_id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "progress": {
      "current": 10,
      "total": 10,
      "correct": 7,
      "incorrect": 3
    }
  }'
```

### Get Grammar Hint
```bash
curl -X GET "$BASE_URL/v1/grammar-challenge/questions/{question_id}/hint?user_id=$USER_ID"
```

### Get Grammar Mistakes
```bash
curl -X GET "$BASE_URL/v1/grammar-challenge/mistakes?user_id=$USER_ID&page=1&limit=50"
```

---

## Sentence Builder Game

### Get Topics
```bash
curl -X GET "$BASE_URL/v1/sentence-builder/topics"
```

### Get Lessons
```bash
curl -X GET "$BASE_URL/v1/sentence-builder/lessons?topicId=formal_register"
```

### Get Items
```bash
curl -X GET "$BASE_URL/v1/sentence-builder/items?lessonId=fr_1&include=tokens&limit=20"
```

### Start Sentence Builder Session
```bash
curl -X POST "$BASE_URL/v1/sentence-builder/sessions?user_id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "lesson",
    "topicId": "formal_register",
    "lessonId": "fr_1",
    "difficulty": "medium",
    "limit": 10
  }'
```

### Get Sentence Builder Session
```bash
curl -X GET "$BASE_URL/v1/sentence-builder/sessions/{session_id}?user_id=$USER_ID&include=items"
```

### Record Sentence Builder Result
```bash
curl -X POST "$BASE_URL/v1/sentence-builder/sessions/{session_id}/results?user_id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "itemId": "sb_it_101",
    "userTokens": ["The", "CEO", "announced", "that", "the", "company", "would", "mitigate", "its", "impact", "."],
    "isCorrect": true,
    "attempts": 1,
    "timeSpent": 8,
    "errorType": "word_order"
  }'
```

### Complete Sentence Builder Session
```bash
curl -X POST "$BASE_URL/v1/sentence-builder/sessions/{session_id}/complete?user_id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "progress": {
      "current": 10,
      "total": 10,
      "correct": 7,
      "incorrect": 3
    }
  }'
```

### Get Sentence Builder Hint
```bash
curl -X GET "$BASE_URL/v1/sentence-builder/items/{item_id}/hint?user_id=$USER_ID"
```

### Get Sentence Builder TTS
```bash
curl -X GET "$BASE_URL/v1/sentence-builder/items/{item_id}/tts?user_id=$USER_ID"
```

### Get Sentence Builder Mistakes
```bash
curl -X GET "$BASE_URL/v1/sentence-builder/mistakes?user_id=$USER_ID&page=1&limit=50"
```

---

## User Stats & Analytics

### Get User Stats
```bash
curl -X GET "$BASE_URL/v1/user/stats?user_id=$USER_ID"
```

---

## Quick Test Commands

### Test All Working Endpoints (Word Lists + Flashcards + Spelling)
```bash
# 1. Health check
curl -X GET "$BASE_URL/health"

# 2. Create word list
LIST_RESPONSE=$(curl -s -X POST "$BASE_URL/v1/word-lists?user_id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test List","description":"Automated test"}')
LIST_ID=$(echo $LIST_RESPONSE | jq -r '.id')

# 3. Add word
WORD_RESPONSE=$(curl -s -X POST "$BASE_URL/v1/word-lists/$LIST_ID/words?user_id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{"word":"hello","translation":"مرحبا","notes":"greeting"}')
WORD_ID=$(echo $WORD_RESPONSE | jq -r '.id')

# 4. Start flashcard session
SESSION_RESPONSE=$(curl -s -X POST "$BASE_URL/v1/flashcards/sessions?user_id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d "{\"wordListId\":\"$LIST_ID\",\"selectedWordIds\":[\"$WORD_ID\"]}")
SESSION_ID=$(echo $SESSION_RESPONSE | jq -r '.id')

# 5. Record result
curl -X POST "$BASE_URL/v1/flashcards/sessions/$SESSION_ID/results?user_id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d "{\"wordId\":\"$WORD_ID\",\"isCorrect\":true,\"attempts\":1,\"timeSpent\":3000}"

# 6. Complete session
curl -X POST "$BASE_URL/v1/flashcards/sessions/$SESSION_ID/complete?user_id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{"progress":{"current":1,"total":1,"correct":1,"incorrect":0}}'

# 7. Cleanup
curl -X DELETE "$BASE_URL/v1/word-lists/$LIST_ID/words/$WORD_ID?user_id=$USER_ID"
curl -X DELETE "$BASE_URL/v1/word-lists/$LIST_ID?user_id=$USER_ID"
```

### Test Advanced Cloze (After Running Migrations)
```bash
# 1. Get topics
curl -X GET "$BASE_URL/v1/advanced-cloze/topics"

# 2. Get lessons for a topic
curl -X GET "$BASE_URL/v1/advanced-cloze/lessons?topicId=phrasalVerbs"

# 3. Get items
curl -X GET "$BASE_URL/v1/advanced-cloze/items?lessonId=pv_business&include=options"

# 4. Start session
CLOZE_SESSION=$(curl -s -X POST "$BASE_URL/v1/advanced-cloze/sessions?user_id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{"mode":"lesson","topicId":"phrasalVerbs","lessonId":"pv_business","difficulty":"medium","limit":5}')
CLOZE_SESSION_ID=$(echo $CLOZE_SESSION | jq -r '.id')

# 5. Record result
curl -X POST "$BASE_URL/v1/advanced-cloze/sessions/$CLOZE_SESSION_ID/results?user_id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{"itemId":"ac_101","selectedAnswers":["phase out","bring in"],"isCorrect":true,"attempts":1,"timeSpent":5000}'

# 6. Complete
curl -X POST "$BASE_URL/v1/advanced-cloze/sessions/$CLOZE_SESSION_ID/complete?user_id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{"progress":{"current":1,"total":1,"correct":1,"incorrect":0}}'
```

## Database Setup

**IMPORTANT**: Before testing Advanced Cloze, Grammar Challenge, or Sentence Builder, run the database migrations:

```bash
# Navigate to project root
cd c:/nvm4w/SAHIONEXT/lesson-content-extractor

# Run migrations (see database/README.md for detailed instructions)
# Option 1: Via Supabase Dashboard SQL Editor
# Option 2: Via psql command line
# Option 3: Via Python script
```

See `database/README.md` for complete migration instructions.

## Notes

1. **Database Tables**: Run migrations in `database/migrations/` to create:
   - Advanced Cloze: `cloze_topics`, `cloze_lessons`, `cloze_items`
   - Grammar Challenge: `grammar_categories`, `grammar_lessons`, `grammar_questions`
   - Sentence Builder: `sentence_topics`, `sentence_lessons`, `sentence_items`

2. **Replace Placeholders**: 
   - `{list_id}` - Word list UUID
   - `{word_id}` - Word UUID
   - `{session_id}` - Session UUID
   - `{item_id}` - Item/Question UUID

3. **Rate Limits**: All endpoints have rate limiting (30-180 requests/minute per user)

4. **Authentication**: Current implementation uses `user_id` query parameter. Production should use JWT Bearer tokens.

5. **Testing**: Run `python tests/test-games.py` to verify all endpoints
