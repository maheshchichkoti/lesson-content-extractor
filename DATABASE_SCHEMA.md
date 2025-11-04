# Tulkka Games - Database Schema

## Overview
This document describes the database schema for all Tulkka language learning games.

## Shared Tables (Used by all games)

### `word_lists`
Stores user-created word lists for flashcards and spelling bee.

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | Primary key (UUID) |
| user_id | TEXT | User who created the list |
| name | TEXT | List name |
| description | TEXT | Optional description |
| word_count | INTEGER | Number of words in list |
| is_favorite | BOOLEAN | Favorite flag |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |

**Indexes:**
- `idx_word_lists_user_favorite` on (user_id, is_favorite)

---

### `words`
Individual words within word lists.

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | Primary key (UUID) |
| list_id | TEXT | Foreign key to word_lists |
| word | TEXT | The word itself |
| translation | TEXT | Translation |
| notes | TEXT | Optional notes |
| practice_count | INTEGER | Times practiced |
| correct_count | INTEGER | Times answered correctly |
| accuracy | INTEGER | Accuracy percentage |
| is_favorite | BOOLEAN | Favorite flag |
| last_practiced | TIMESTAMP | Last practice time |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |

**Indexes:**
- `idx_words_list_favorite` on (list_id, is_favorite)

---

### `game_sessions`
Tracks active and completed game sessions across all game types.

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | Primary key (UUID) |
| user_id | TEXT | User playing the game |
| game_type | TEXT | Game type (flashcards, spelling, cloze, grammar, sentence) |
| mode | TEXT | Game mode (practice, topic, lesson, custom, mistakes) |
| reference_id | TEXT | ID of related content (word_list_id, topic_id, etc.) |
| progress_current | INTEGER | Current progress |
| progress_total | INTEGER | Total items |
| correct | INTEGER | Correct answers |
| incorrect | INTEGER | Incorrect answers |
| started_at | TIMESTAMP | Session start time |
| completed_at | TIMESTAMP | Session completion time (NULL if active) |

**Indexes:**
- `idx_game_sessions_user_game_type` on (user_id, game_type)
- `idx_game_sessions_completed` on (user_id, completed_at)

---

### `game_results`
Individual results for each item within a session.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| session_id | TEXT | Foreign key to game_sessions |
| game_type | TEXT | Game type |
| item_id | TEXT | ID of the item (word_id, question_id, etc.) |
| is_correct | BOOLEAN | Whether answer was correct |
| attempts | INTEGER | Number of attempts |
| time_spent_ms | INTEGER | Time spent in milliseconds |
| metadata | JSONB | Additional game-specific data |
| created_at | TIMESTAMP | Result timestamp |

**Indexes:**
- `idx_game_results_session` on (session_id, game_type)

---

### `user_mistakes`
Tracks user mistakes for review/practice.

| Column | Type | Description |
|--------|------|-------------|
| user_id | TEXT | User ID |
| game_type | TEXT | Game type |
| item_id | TEXT | ID of the item |
| last_error_type | TEXT | Type of error |
| mistake_count | INTEGER | Number of mistakes |
| last_attempted_at | TIMESTAMP | Last attempt timestamp |

**Primary Key:** (user_id, game_type, item_id)

**Indexes:**
- `idx_user_mistakes_user_game` on (user_id, game_type)

---

## Advanced Cloze Tables

### `cloze_topics`
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | Primary key (UUID) |
| name | TEXT | Topic name |
| icon | TEXT | Icon identifier |
| description | TEXT | Topic description |
| created_at | TIMESTAMP | Creation timestamp |

---

### `cloze_lessons`
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | Primary key (UUID) |
| topic_id | TEXT | Foreign key to cloze_topics |
| title | TEXT | Lesson title |
| item_count | INTEGER | Number of items |
| created_at | TIMESTAMP | Creation timestamp |

---

### `cloze_items`
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | Primary key (UUID) |
| topic_id | TEXT | Foreign key to cloze_topics |
| lesson_id | TEXT | Foreign key to cloze_lessons |
| difficulty | TEXT | easy/medium/hard |
| text_parts | JSONB | Array of text segments |
| options | JSONB | Array of option arrays |
| correct | JSONB | Array of correct answers |
| explanation | TEXT | Explanation text |
| metadata | JSONB | Additional metadata |
| created_at | TIMESTAMP | Creation timestamp |

**Indexes:**
- `idx_cloze_items_topic` on (topic_id, difficulty)
- `idx_cloze_items_lesson` on (lesson_id, difficulty)

---

## Grammar Challenge Tables

### `grammar_categories`
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | Primary key (UUID) |
| name | TEXT | Category name |
| created_at | TIMESTAMP | Creation timestamp |

---

### `grammar_lessons`
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | Primary key (UUID) |
| category_id | TEXT | Foreign key to grammar_categories |
| title | TEXT | Lesson title |
| question_count | INTEGER | Number of questions |
| created_at | TIMESTAMP | Creation timestamp |

---

### `grammar_questions`
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | Primary key (UUID) |
| category_id | TEXT | Foreign key to grammar_categories |
| lesson_id | TEXT | Foreign key to grammar_lessons |
| difficulty | TEXT | easy/medium/hard |
| prompt | TEXT | Question prompt |
| options | JSONB | Array of answer options |
| correct_index | INTEGER | Index of correct answer |
| explanation | TEXT | Explanation text |
| metadata | JSONB | Additional metadata |
| created_at | TIMESTAMP | Creation timestamp |

**Indexes:**
- `idx_grammar_questions_category` on (category_id, difficulty)
- `idx_grammar_questions_lesson` on (lesson_id, difficulty)

---

## Sentence Builder Tables

### `sentence_topics`
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | Primary key (UUID) |
| name | TEXT | Topic name |
| created_at | TIMESTAMP | Creation timestamp |

---

### `sentence_lessons`
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | Primary key (UUID) |
| topic_id | TEXT | Foreign key to sentence_topics |
| title | TEXT | Lesson title |
| item_count | INTEGER | Number of items |
| created_at | TIMESTAMP | Creation timestamp |

---

### `sentence_items`
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | Primary key (UUID) |
| topic_id | TEXT | Foreign key to sentence_topics |
| lesson_id | TEXT | Foreign key to sentence_lessons |
| difficulty | TEXT | easy/medium/hard |
| english | TEXT | English sentence |
| translation | TEXT | Translation |
| tokens | JSONB | Array of tokens |
| accepted | JSONB | Array of acceptable token sequences |
| distractors | JSONB | Optional extra tokens |
| metadata | JSONB | Additional metadata |
| created_at | TIMESTAMP | Creation timestamp |

**Indexes:**
- `idx_sentence_items_topic` on (topic_id, difficulty)
- `idx_sentence_items_lesson` on (lesson_id, difficulty)

---

## Game Types Reference

| Game Type | Value | Description |
|-----------|-------|-------------|
| Flashcards | `flashcards` | Vocabulary flashcard practice |
| Spelling Bee | `spelling` | Spelling practice with audio |
| Advanced Cloze | `cloze` | Fill-in-the-blank exercises |
| Grammar Challenge | `grammar` | Multiple choice grammar questions |
| Sentence Builder | `sentence` | Build sentences from tokens |

---

## Difficulty Levels

All games support three difficulty levels:
- `easy` - Beginner level
- `medium` - Intermediate level
- `hard` - Advanced level

---

## Session Modes

| Mode | Description | Available In |
|------|-------------|--------------|
| `practice` | Practice from word list | Flashcards, Spelling Bee |
| `topic` | Practice by topic | Cloze, Grammar, Sentence Builder |
| `lesson` | Practice specific lesson | Cloze, Grammar, Sentence Builder |
| `custom` | Custom selection of items | Cloze, Grammar, Sentence Builder |
| `mistakes` | Review past mistakes | Cloze, Grammar, Sentence Builder |

---

## Notes for Future Scaling

### Performance Optimization
- All foreign key relationships should have indexes
- Consider partitioning `game_results` by `created_at` when data grows
- Add composite indexes on frequently queried combinations

### Caching Strategy (Future)
- Cache topics/lessons/categories (they rarely change)
- Cache user stats with TTL of 5 minutes
- Invalidate cache on session completion

### Analytics (Future)
Consider adding:
- `game_analytics` table for detailed metrics
- Materialized views for user statistics
- Time-series data for progress tracking
