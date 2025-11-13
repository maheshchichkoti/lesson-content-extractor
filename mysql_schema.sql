-- Tulkka Games MySQL Database Schema
-- Database: tulkka9

-- ============================================
-- SHARED TABLES (All Games)
-- ============================================

CREATE TABLE IF NOT EXISTS word_lists (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    class_id VARCHAR(255) DEFAULT 'default',
    name VARCHAR(255) NOT NULL,
    description TEXT,
    word_count INT DEFAULT 0,
    is_favorite BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_word_lists_user (user_id),
    INDEX idx_word_lists_user_favorite (user_id, is_favorite)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS words (
    id VARCHAR(36) PRIMARY KEY,
    word_list_id VARCHAR(36) NOT NULL,
    word VARCHAR(255) NOT NULL,
    translation VARCHAR(255),
    notes TEXT,
    difficulty VARCHAR(20),
    example_sentence TEXT,
    pronunciation_audio_url TEXT,
    practice_count INT DEFAULT 0,
    correct_count INT DEFAULT 0,
    accuracy INT DEFAULT 0,
    is_favorite BOOLEAN DEFAULT FALSE,
    last_practiced TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (word_list_id) REFERENCES word_lists(id) ON DELETE CASCADE,
    INDEX idx_words_list (word_list_id),
    INDEX idx_words_list_favorite (word_list_id, is_favorite)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS game_sessions (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    game_type VARCHAR(50) NOT NULL,
    class_id VARCHAR(255) DEFAULT 'default',
    mode VARCHAR(50),
    reference_id VARCHAR(36),
    item_ids JSON,
    status VARCHAR(20) DEFAULT 'active',
    progress_current INT DEFAULT 0,
    progress_total INT DEFAULT 0,
    correct_count INT DEFAULT 0,
    incorrect_count INT DEFAULT 0,
    final_score DECIMAL(5,2),
    metadata JSON,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    INDEX idx_game_sessions_user (user_id),
    INDEX idx_game_sessions_user_game (user_id, game_type),
    INDEX idx_game_sessions_completed (user_id, completed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS game_results (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL,
    game_type VARCHAR(50) NOT NULL,
    item_id VARCHAR(36) NOT NULL,
    is_correct BOOLEAN NOT NULL,
    attempts INT DEFAULT 1,
    time_spent_ms INT DEFAULT 0,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES game_sessions(id) ON DELETE CASCADE,
    INDEX idx_game_results_session (session_id),
    INDEX idx_game_results_item (item_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS user_mistakes (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    game_type VARCHAR(50) NOT NULL,
    item_type VARCHAR(50) NOT NULL,
    item_id VARCHAR(36) NOT NULL,
    user_answer TEXT,
    correct_answer TEXT,
    mistake_type VARCHAR(50),
    mistake_count INT DEFAULT 1,
    last_attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_mistakes_user (user_id),
    INDEX idx_user_mistakes_user_game (user_id, game_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- ADVANCED CLOZE TABLES
-- ============================================

CREATE TABLE IF NOT EXISTS cloze_topics (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    icon VARCHAR(100),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS cloze_lessons (
    id VARCHAR(36) PRIMARY KEY,
    topic_id VARCHAR(36) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    difficulty VARCHAR(20),
    item_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (topic_id) REFERENCES cloze_topics(id) ON DELETE CASCADE,
    INDEX idx_cloze_lessons_topic (topic_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS cloze_items (
    id VARCHAR(36) PRIMARY KEY,
    topic_id VARCHAR(36) NOT NULL,
    lesson_id VARCHAR(36),
    difficulty VARCHAR(20),
    text_parts JSON NOT NULL,
    options JSON,
    correct_answers JSON NOT NULL,
    hint TEXT,
    explanation TEXT,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (topic_id) REFERENCES cloze_topics(id) ON DELETE CASCADE,
    FOREIGN KEY (lesson_id) REFERENCES cloze_lessons(id) ON DELETE CASCADE,
    INDEX idx_cloze_items_topic (topic_id, difficulty),
    INDEX idx_cloze_items_lesson (lesson_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- GRAMMAR CHALLENGE TABLES
-- ============================================

CREATE TABLE IF NOT EXISTS grammar_categories (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    icon VARCHAR(100),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS grammar_lessons (
    id VARCHAR(36) PRIMARY KEY,
    category_id VARCHAR(36) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    difficulty VARCHAR(20),
    question_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES grammar_categories(id) ON DELETE CASCADE,
    INDEX idx_grammar_lessons_category (category_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS grammar_questions (
    id VARCHAR(36) PRIMARY KEY,
    category_id VARCHAR(36) NOT NULL,
    lesson_id VARCHAR(36),
    difficulty VARCHAR(20),
    question TEXT NOT NULL,
    options JSON NOT NULL,
    correct_answer VARCHAR(255) NOT NULL,
    hint TEXT,
    explanation TEXT,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES grammar_categories(id) ON DELETE CASCADE,
    FOREIGN KEY (lesson_id) REFERENCES grammar_lessons(id) ON DELETE CASCADE,
    INDEX idx_grammar_questions_category (category_id, difficulty),
    INDEX idx_grammar_questions_lesson (lesson_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- SENTENCE BUILDER TABLES
-- ============================================

CREATE TABLE IF NOT EXISTS sentence_topics (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    icon VARCHAR(100),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS sentence_lessons (
    id VARCHAR(36) PRIMARY KEY,
    topic_id VARCHAR(36) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    difficulty VARCHAR(20),
    item_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (topic_id) REFERENCES sentence_topics(id) ON DELETE CASCADE,
    INDEX idx_sentence_lessons_topic (topic_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS sentence_items (
    id VARCHAR(36) PRIMARY KEY,
    topic_id VARCHAR(36) NOT NULL,
    lesson_id VARCHAR(36),
    difficulty VARCHAR(20),
    english_sentence TEXT NOT NULL,
    translation TEXT,
    sentence_tokens JSON NOT NULL,
    accepted_sequences JSON NOT NULL,
    distractors JSON,
    hint TEXT,
    tts_audio_url TEXT,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (topic_id) REFERENCES sentence_topics(id) ON DELETE CASCADE,
    FOREIGN KEY (lesson_id) REFERENCES sentence_lessons(id) ON DELETE CASCADE,
    INDEX idx_sentence_items_topic (topic_id, difficulty),
    INDEX idx_sentence_items_lesson (lesson_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
