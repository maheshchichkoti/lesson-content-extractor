-- Tulkka Games MySQL Database Schema
-- Database: tulkka9

-- ============================================
-- SHARED TABLES (All Games)
-- ============================================

-- Game Sessions (tracks active game sessions)
CREATE TABLE IF NOT EXISTS game_sessions (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    game_type VARCHAR(50) NOT NULL,
    class_id VARCHAR(255),
    mode VARCHAR(50),
    reference_id VARCHAR(255),
    progress_current INT DEFAULT 0,
    progress_total INT DEFAULT 0,
    correct_count INT DEFAULT 0,
    incorrect_count INT DEFAULT 0,
    final_score DECIMAL(5,2) DEFAULT 0.00,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    metadata JSON,
    INDEX idx_user_game (user_id, game_type),
    INDEX idx_class (class_id),
    INDEX idx_started (started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Game Results (completed game records)
CREATE TABLE IF NOT EXISTS game_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    game_type VARCHAR(50) NOT NULL,
    class_id VARCHAR(255),
    reference_id VARCHAR(255),
    correct_count INT DEFAULT 0,
    incorrect_count INT DEFAULT 0,
    final_score DECIMAL(5,2) DEFAULT 0.00,
    time_spent INT,
    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON,
    INDEX idx_user_game (user_id, game_type),
    INDEX idx_session (session_id),
    INDEX idx_completed (completed_at),
    FOREIGN KEY (session_id) REFERENCES game_sessions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- User Mistakes (tracks errors for review)
CREATE TABLE IF NOT EXISTS user_mistakes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    game_type VARCHAR(50) NOT NULL,
    item_id VARCHAR(255),
    question TEXT,
    user_answer TEXT,
    correct_answer TEXT,
    mistake_count INT DEFAULT 1,
    last_mistake_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved BOOLEAN DEFAULT FALSE,
    INDEX idx_user_game (user_id, game_type),
    INDEX idx_resolved (resolved),
    INDEX idx_last_mistake (last_mistake_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- FLASHCARDS & SPELLING
-- ============================================

-- Word Lists
CREATE TABLE IF NOT EXISTS word_lists (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    class_id VARCHAR(255),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    word_count INT DEFAULT 0,
    is_favorite BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_class (user_id, class_id),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Words
CREATE TABLE IF NOT EXISTS words (
    id VARCHAR(36) PRIMARY KEY,
    list_id VARCHAR(36) NOT NULL,
    word VARCHAR(255) NOT NULL,
    definition TEXT,
    example_sentence TEXT,
    pronunciation VARCHAR(255),
    difficulty VARCHAR(20),
    mastery_level INT DEFAULT 0,
    times_practiced INT DEFAULT 0,
    times_correct INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_list (list_id),
    INDEX idx_difficulty (difficulty),
    FOREIGN KEY (list_id) REFERENCES word_lists(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- ADVANCED CLOZE
-- ============================================

-- Cloze Topics
CREATE TABLE IF NOT EXISTS cloze_topics (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    icon VARCHAR(50),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Cloze Lessons
CREATE TABLE IF NOT EXISTS cloze_lessons (
    id VARCHAR(50) PRIMARY KEY,
    topic_id VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    difficulty VARCHAR(20),
    item_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_topic (topic_id),
    INDEX idx_difficulty (difficulty),
    FOREIGN KEY (topic_id) REFERENCES cloze_topics(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Cloze Items
CREATE TABLE IF NOT EXISTS cloze_items (
    id VARCHAR(50) PRIMARY KEY,
    topic_id VARCHAR(50) NOT NULL,
    lesson_id VARCHAR(50) NOT NULL,
    difficulty VARCHAR(20),
    text_parts JSON NOT NULL,
    options JSON NOT NULL,
    correct_answers JSON NOT NULL,
    hint TEXT,
    explanation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_topic (topic_id),
    INDEX idx_lesson (lesson_id),
    INDEX idx_difficulty (difficulty),
    FOREIGN KEY (topic_id) REFERENCES cloze_topics(id) ON DELETE CASCADE,
    FOREIGN KEY (lesson_id) REFERENCES cloze_lessons(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- GRAMMAR CHALLENGE
-- ============================================

-- Grammar Categories
CREATE TABLE IF NOT EXISTS grammar_categories (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    icon VARCHAR(50),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Grammar Lessons
CREATE TABLE IF NOT EXISTS grammar_lessons (
    id VARCHAR(50) PRIMARY KEY,
    category_id VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    difficulty VARCHAR(20),
    question_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_category (category_id),
    INDEX idx_difficulty (difficulty),
    FOREIGN KEY (category_id) REFERENCES grammar_categories(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Grammar Questions
CREATE TABLE IF NOT EXISTS grammar_questions (
    id VARCHAR(50) PRIMARY KEY,
    category_id VARCHAR(50) NOT NULL,
    lesson_id VARCHAR(50) NOT NULL,
    difficulty VARCHAR(20),
    question TEXT NOT NULL,
    options JSON NOT NULL,
    correct_answer VARCHAR(255) NOT NULL,
    hint TEXT,
    explanation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_category (category_id),
    INDEX idx_lesson (lesson_id),
    INDEX idx_difficulty (difficulty),
    FOREIGN KEY (category_id) REFERENCES grammar_categories(id) ON DELETE CASCADE,
    FOREIGN KEY (lesson_id) REFERENCES grammar_lessons(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- SENTENCE BUILDER
-- ============================================

-- Sentence Topics
CREATE TABLE IF NOT EXISTS sentence_topics (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    icon VARCHAR(50),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Sentence Lessons
CREATE TABLE IF NOT EXISTS sentence_lessons (
    id VARCHAR(50) PRIMARY KEY,
    topic_id VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    difficulty VARCHAR(20),
    item_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_topic (topic_id),
    INDEX idx_difficulty (difficulty),
    FOREIGN KEY (topic_id) REFERENCES sentence_topics(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Sentence Items
CREATE TABLE IF NOT EXISTS sentence_items (
    id VARCHAR(50) PRIMARY KEY,
    topic_id VARCHAR(50) NOT NULL,
    lesson_id VARCHAR(50) NOT NULL,
    difficulty VARCHAR(20),
    english_sentence TEXT NOT NULL,
    translation TEXT,
    sentence_tokens JSON NOT NULL,
    accepted_sequences JSON NOT NULL,
    distractors JSON,
    hint TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_topic (topic_id),
    INDEX idx_lesson (lesson_id),
    INDEX idx_difficulty (difficulty),
    FOREIGN KEY (topic_id) REFERENCES sentence_topics(id) ON DELETE CASCADE,
    FOREIGN KEY (lesson_id) REFERENCES sentence_lessons(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
