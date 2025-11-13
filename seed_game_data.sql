-- Seed data for game tables
-- Run this after creating the schema

USE tulkka9;

-- ============================================
-- CLOZE TOPICS & CONTENT
-- ============================================

INSERT INTO cloze_topics (id, name, icon, description) VALUES
('cloze-topic-1', 'Daily Conversations', '💬', 'Common phrases for everyday situations'),
('cloze-topic-2', 'Travel & Tourism', '✈️', 'Useful expressions for travelers'),
('cloze-topic-3', 'Business English', '💼', 'Professional communication skills');

INSERT INTO cloze_lessons (id, topic_id, title, description, difficulty, item_count) VALUES
('cloze-lesson-1', 'cloze-topic-1', 'Greetings & Introductions', 'Learn basic greetings', 'easy', 3),
('cloze-lesson-2', 'cloze-topic-1', 'Making Plans', 'Arrange meetings and activities', 'medium', 3),
('cloze-lesson-3', 'cloze-topic-2', 'At the Airport', 'Navigate airport situations', 'medium', 3);

INSERT INTO cloze_items (id, topic_id, lesson_id, difficulty, text_parts, options, correct_answers, hint, explanation) VALUES
('cloze-item-1', 'cloze-topic-1', 'cloze-lesson-1', 'easy', 
 '["Hello, my ", " is John. Nice to ", " you."]',
 '[["name", "age", "job"], ["meet", "see", "know"]]',
 '["name", "meet"]',
 'Think about introducing yourself',
 'We use "name" when introducing ourselves and "meet" when greeting someone new.'),
 
('cloze-item-2', 'cloze-topic-1', 'cloze-lesson-1', 'easy',
 '["Good ", ", how are you ", "?"]',
 '[["morning", "night", "afternoon"], ["today", "yesterday", "tomorrow"]]',
 '["morning", "today"]',
 'Common greeting phrase',
 'This is a standard morning greeting asking about someone\'s current state.'),
 
('cloze-item-3', 'cloze-topic-2', 'cloze-lesson-3', 'medium',
 '["Where is the ", " counter? I need to ", " in."]',
 '[["check-in", "ticket", "baggage"], ["check", "sign", "go"]]',
 '["check-in", "check"]',
 'Airport procedures',
 'At airports, you go to the check-in counter to check in for your flight.');

-- ============================================
-- GRAMMAR CATEGORIES & CONTENT
-- ============================================

INSERT INTO grammar_categories (id, name, icon, description) VALUES
('grammar-cat-1', 'Verb Tenses', '⏰', 'Past, present, and future tenses'),
('grammar-cat-2', 'Articles', '📝', 'Using a, an, and the correctly'),
('grammar-cat-3', 'Prepositions', '📍', 'In, on, at, and other prepositions');

INSERT INTO grammar_lessons (id, category_id, title, description, difficulty, question_count) VALUES
('grammar-lesson-1', 'grammar-cat-1', 'Present Simple', 'Basic present tense usage', 'easy', 3),
('grammar-lesson-2', 'grammar-cat-1', 'Past Simple', 'Regular and irregular past forms', 'medium', 3),
('grammar-lesson-3', 'grammar-cat-2', 'Definite Articles', 'When to use "the"', 'easy', 3);

INSERT INTO grammar_questions (id, category_id, lesson_id, difficulty, question, options, correct_answer, hint, explanation) VALUES
('grammar-q-1', 'grammar-cat-1', 'grammar-lesson-1', 'easy',
 'She ___ to school every day.',
 '["go", "goes", "going", "gone"]',
 'goes',
 'Third person singular',
 'With "she/he/it" in present simple, we add -s or -es to the verb.'),
 
('grammar-q-2', 'grammar-cat-1', 'grammar-lesson-1', 'easy',
 'They ___ English at school.',
 '["learn", "learns", "learning", "learned"]',
 'learn',
 'Plural subject',
 'With plural subjects (they, we, you), we use the base form of the verb.'),
 
('grammar-q-3', 'grammar-cat-2', 'grammar-lesson-3', 'easy',
 'I saw ___ cat in the garden.',
 '["a", "an", "the", "no article"]',
 'a',
 'Indefinite article',
 'Use "a" before consonant sounds when mentioning something for the first time.');

-- ============================================
-- SENTENCE BUILDER TOPICS & CONTENT
-- ============================================

INSERT INTO sentence_topics (id, name, icon, description) VALUES
('sentence-topic-1', 'Basic Sentences', '📖', 'Simple sentence construction'),
('sentence-topic-2', 'Questions', '❓', 'Forming questions correctly'),
('sentence-topic-3', 'Descriptions', '🎨', 'Describing people and things');

INSERT INTO sentence_lessons (id, topic_id, title, description, difficulty, item_count) VALUES
('sentence-lesson-1', 'sentence-topic-1', 'Subject-Verb-Object', 'Basic sentence structure', 'easy', 3),
('sentence-lesson-2', 'sentence-topic-2', 'Yes/No Questions', 'Simple questions', 'easy', 3),
('sentence-lesson-3', 'sentence-topic-3', 'Adjectives', 'Using descriptive words', 'medium', 3);

INSERT INTO sentence_items (id, topic_id, lesson_id, difficulty, english_sentence, translation, sentence_tokens, accepted_sequences, distractors, hint) VALUES
('sentence-item-1', 'sentence-topic-1', 'sentence-lesson-1', 'easy',
 'I like pizza.',
 'मुझे पिज्जा पसंद है।',
 '["I", "like", "pizza", "."]',
 '[["I", "like", "pizza", "."], ["I", "love", "pizza", "."]]',
 '["hate", "enjoy"]',
 'Subject + verb + object'),
 
('sentence-item-2', 'sentence-topic-1', 'sentence-lesson-1', 'easy',
 'She reads books.',
 'वह किताबें पढ़ती है।',
 '["She", "reads", "books", "."]',
 '[["She", "reads", "books", "."], ["She", "loves", "books", "."]]',
 '["writes", "buys"]',
 'Remember the -s for third person'),
 
('sentence-item-3', 'sentence-topic-2', 'sentence-lesson-2', 'easy',
 'Do you like coffee?',
 'क्या आपको कॉफी पसंद है?',
 '["Do", "you", "like", "coffee", "?"]',
 '[["Do", "you", "like", "coffee", "?"], ["Do", "you", "love", "coffee", "?"]]',
 '["tea", "milk"]',
 'Questions start with Do/Does');

-- Verify data
SELECT 'Cloze Topics:' as Info, COUNT(*) as Count FROM cloze_topics
UNION ALL
SELECT 'Cloze Lessons:', COUNT(*) FROM cloze_lessons
UNION ALL
SELECT 'Cloze Items:', COUNT(*) FROM cloze_items
UNION ALL
SELECT 'Grammar Categories:', COUNT(*) FROM grammar_categories
UNION ALL
SELECT 'Grammar Lessons:', COUNT(*) FROM grammar_lessons
UNION ALL
SELECT 'Grammar Questions:', COUNT(*) FROM grammar_questions
UNION ALL
SELECT 'Sentence Topics:', COUNT(*) FROM sentence_topics
UNION ALL
SELECT 'Sentence Lessons:', COUNT(*) FROM sentence_lessons
UNION ALL
SELECT 'Sentence Items:', COUNT(*) FROM sentence_items;
