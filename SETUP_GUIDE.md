# Complete Setup Guide - Tulkka Games API

## 🎯 Overview

This guide will help you set up and test all game endpoints in the Tulkka API.

## 📋 Prerequisites

- Python 3.8+
- Access to Supabase project
- API server running on `http://localhost:8000`

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd c:/nvm4w/SAHIONEXT/lesson-content-extractor
pip install -r requirements.txt
```

### 2. Configure Environment

Create or update `.env` file:

```bash
# Supabase (Database)
SUPABASE_URL=https://nlswzwucccjhsebkaczn.supabase.co
SUPABASE_KEY=your_supabase_service_role_key_here

# API Configuration
API_BASE_URL=http://localhost:8000
TEST_USER_ID=test_user_123
```

### 3. Run Database Migrations

**Option A: Supabase Dashboard (Recommended)**

1. Go to [Supabase SQL Editor](https://app.supabase.com/project/nlswzwucccjhsebkaczn/sql)
2. Open each migration file in order:
   - `database/migrations/001_create_advanced_cloze_tables.sql`
   - `database/migrations/002_create_grammar_challenge_tables.sql`
   - `database/migrations/003_create_sentence_builder_tables.sql`
3. Copy/paste content and click **Run** for each

**Option B: Command Line (if you have psql)**

```bash
# Set your database URL
export DATABASE_URL="postgresql://postgres:[PASSWORD]@db.nlswzwucccjhsebkaczn.supabase.co:5432/postgres"

# Run migrations
psql $DATABASE_URL -f database/migrations/001_create_advanced_cloze_tables.sql
psql $DATABASE_URL -f database/migrations/002_create_grammar_challenge_tables.sql
psql $DATABASE_URL -f database/migrations/003_create_sentence_builder_tables.sql
```

### 4. Start API Server

```bash
# Start the API server
python api.py

# Or using uvicorn
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Run Tests

```bash
# Run complete test suite
python tests/test-games.py
```

**Expected Output:**
```
[Health Check]
[Create Word List]
[List Word Lists]
[Add Word]
[Update Word]
[Start Flashcards Session]
[Get Flashcard Session]
[Record Flashcard Result]
[Complete Flashcard Session]
[Flashcard Stats]
[Start Spelling Session]
[Get Spelling Session]
[Get Pronunciation]
[Record Spelling Result]
[Complete Spelling Session]
[Advanced Cloze Catalog]
[Get Advanced Cloze Session]
[Record Advanced Cloze Result]
[Complete Advanced Cloze Session]
[Advanced Cloze Hint & Mistakes]
[Grammar Challenge Catalog]
[Get Grammar Session]
[Record Grammar Result]
[Skip Grammar Question]
[Complete Grammar Session]
[Grammar Hint & Mistakes]
[Sentence Builder Catalog]
[Get Sentence Builder Session]
[Record Sentence Builder Result]
[Complete Sentence Builder Session]
[Sentence Builder Hint & Mistakes]
[Sentence Builder TTS]
[User Aggregate Stats]

==============================================
 All documented game endpoints verified successfully
==============================================

[Cleanup Test Data]
```

## 📊 API Coverage

### ✅ Fully Implemented & Tested

**Word Lists (9 endpoints)**
- ✅ Create, Read, Update, Delete word lists
- ✅ Add, Update, Delete words
- ✅ Toggle favorites (lists & words)

**Flashcards (5 endpoints)**
- ✅ Start, Get, Record results, Complete session
- ✅ Get stats

**Spelling Bee (5 endpoints)**
- ✅ Start, Get, Record results, Complete session
- ✅ Get pronunciation

**Advanced Cloze (9 endpoints)**
- ✅ Topics, Lessons, Items catalog
- ✅ Start, Get, Record, Complete session
- ✅ Hints, Mistakes

**Grammar Challenge (10 endpoints)**
- ✅ Categories, Lessons, Questions catalog
- ✅ Start, Get, Record, Skip, Complete session
- ✅ Hints, Mistakes

**Sentence Builder (10 endpoints)**
- ✅ Topics, Lessons, Items catalog
- ✅ Start, Get, Record, Complete session
- ✅ Hints, TTS, Mistakes

**User Stats (1 endpoint)**
- ✅ Get aggregate user statistics

**Total: 54 endpoints**

## 🧪 Manual Testing with cURL

See `tests/GAME_API_CURL_COMMANDS.md` for complete cURL examples.

### Quick Test

```bash
export BASE_URL="http://localhost:8000"
export USER_ID="test_user_123"

# Health check
curl -X GET "$BASE_URL/health"

# Create word list
curl -X POST "$BASE_URL/v1/word-lists?user_id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test List","description":"Testing"}'

# Get all word lists
curl -X GET "$BASE_URL/v1/word-lists?user_id=$USER_ID&page=1&limit=10"
```

## 🗄️ Database Schema

### Tables Created by Migrations

**Advanced Cloze:**
- `cloze_topics` - 5 sample topics
- `cloze_lessons` - 4 sample lessons
- `cloze_items` - 2 sample exercises
- `cloze_sessions` - User sessions
- `cloze_results` - Per-item results
- `cloze_mistakes` - Mistake tracking

**Grammar Challenge:**
- `grammar_categories` - 10 sample categories
- `grammar_lessons` - 4 sample lessons
- `grammar_questions` - 2 sample questions
- `grammar_sessions` - User sessions
- `grammar_results` - Per-question results
- `grammar_mistakes` - Mistake tracking

**Sentence Builder:**
- `sentence_topics` - 4 sample topics
- `sentence_lessons` - 4 sample lessons
- `sentence_items` - 2 sample exercises
- `sentence_sessions` - User sessions
- `sentence_results` - Per-item results
- `sentence_mistakes` - Mistake tracking

## 🔍 Verification

### Check Tables Were Created

```sql
-- Advanced Cloze
SELECT COUNT(*) as topics FROM cloze_topics;
SELECT COUNT(*) as lessons FROM cloze_lessons;
SELECT COUNT(*) as items FROM cloze_items;

-- Grammar Challenge
SELECT COUNT(*) as categories FROM grammar_categories;
SELECT COUNT(*) as lessons FROM grammar_lessons;
SELECT COUNT(*) as questions FROM grammar_questions;

-- Sentence Builder
SELECT COUNT(*) as topics FROM sentence_topics;
SELECT COUNT(*) as lessons FROM sentence_lessons;
SELECT COUNT(*) as items FROM sentence_items;
```

Expected results:
- Advanced Cloze: 5 topics, 4 lessons, 2 items
- Grammar Challenge: 10 categories, 4 lessons, 2 questions
- Sentence Builder: 4 topics, 4 lessons, 2 items

### Check API Health

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-05T05:30:00.000000+00:00",
  "version": "1.0.0"
}
```

## 🐛 Troubleshooting

### Issue: "Could not find the table 'public.cloze_topics' in the schema cache"

**Solution:** Run database migrations (see Step 3 above)

### Issue: "Connection refused" when running tests

**Solution:** Ensure API server is running:
```bash
python api.py
```

### Issue: "Module not found" errors

**Solution:** Install dependencies:
```bash
pip install -r requirements.txt
```

### Issue: "SUPABASE_URL not set"

**Solution:** Create `.env` file with Supabase credentials (see Step 2)

### Issue: Test shows "Skipped" for games

**Solution:** This is expected if migrations haven't been run. The test gracefully skips missing games.

## 📚 Documentation

- **API Specs:** See `*_API_SPEC.md` files in `tulkka-api/` directory
- **cURL Commands:** `tests/GAME_API_CURL_COMMANDS.md`
- **Database Migrations:** `database/README.md`
- **Test Script:** `tests/test-games.py`

## 🎮 Adding More Content

After migrations, you can add more game content:

### Advanced Cloze
```sql
INSERT INTO cloze_items (id, topic_id, lesson_id, difficulty, text_parts, options, correct, explanation)
VALUES (
    'ac_103',
    'phrasalVerbs',
    'pv_business',
    'hard',
    '["The merger will ", " significant changes in the organization."]'::jsonb,
    '[["bring about", "bring up", "bring down"]]'::jsonb,
    '["bring about"]'::jsonb,
    '"Bring about" means to cause something to happen.'
);
```

### Grammar Challenge
```sql
INSERT INTO grammar_questions (id, category_id, lesson_id, difficulty, prompt, options, correct_index, explanation)
VALUES (
    'gc_q_103',
    'tense',
    'tense_pp_sp',
    'hard',
    'They ____ for three hours when we finally arrived.',
    '["waited", "had waited", "have waited", "were waiting"]'::jsonb,
    1,
    'Use past perfect for an action that was ongoing before another past action.'
);
```

### Sentence Builder
```sql
INSERT INTO sentence_items (id, topic_id, lesson_id, difficulty, english, translation, tokens, accepted)
VALUES (
    'sb_it_103',
    'formal_register',
    'fr_1',
    'hard',
    'The board of directors unanimously approved the proposal.',
    'La junta directiva aprobó unánimemente la propuesta.',
    '["The", "board", "of", "directors", "unanimously", "approved", "the", "proposal", "."]'::jsonb,
    '[["The", "board", "of", "directors", "unanimously", "approved", "the", "proposal", "."]]'::jsonb
);
```

## ✅ Success Criteria

Your setup is complete when:

1. ✅ All migrations run without errors
2. ✅ API server starts successfully
3. ✅ Health check returns `{"status":"healthy"}`
4. ✅ Test script completes with "All documented game endpoints verified successfully"
5. ✅ No "table not found" errors in test output

## 🚀 Next Steps

1. **Add more content** to game tables
2. **Implement authentication** (replace `user_id` param with JWT)
3. **Add rate limiting** per user
4. **Set up monitoring** and logging
5. **Deploy to production** environment

## 📞 Support

For issues or questions:
1. Check `database/README.md` for migration help
2. Review `tests/GAME_API_CURL_COMMANDS.md` for API examples
3. Check API logs for detailed error messages
4. Verify Supabase connection and credentials
