-- Seed data for game tables
-- Run this after creating the schema

USE tulkka9;

-- ============================================
-- ADVANCED CLOZE SEED DATA
-- ============================================

-- Cloze Topics
INSERT INTO cloze_topics (id, name, icon, description) VALUES
('cloze-topic-1', 'Daily Conversations', '💬', 'Common phrases and expressions for everyday situations'),
('cloze-topic-2', 'Grammar Basics', '📚', 'Essential grammar patterns and structures'),
('cloze-topic-3', 'Vocabulary Building', '📖', 'Expand your word knowledge with context'),
('cloze-topic-4', 'Reading Comprehension', '📰', 'Practice understanding written text');

-- Cloze Lessons
INSERT INTO cloze_lessons (id, topic_id, title, description, difficulty, item_count) VALUES
('cloze-lesson-1', 'cloze-topic-1', 'Greetings and Introductions', 'Learn how to greet people', 'easy', 3),
('cloze-lesson-2', 'cloze-topic-2', 'Present Tense', 'Master present tense usage', 'easy', 3),
('cloze-lesson-3', 'cloze-topic-3', 'Common Verbs', 'Essential action words', 'medium', 3),
('cloze-lesson-4', 'cloze-topic-4', 'Short Stories', 'Read and understand stories', 'medium', 3);

-- Cloze Items
INSERT INTO cloze_items (id, topic_id, lesson_id, difficulty, text_parts, options, correct_answers, hint, explanation) VALUES
('cloze-item-1', 'cloze-topic-1', 'cloze-lesson-1', 'easy', 
 '["Hello, my", "__", "is John."]', 
 '["name","age","job"]', 
 '["name"]', 
 'What do you say when introducing yourself?', 
 'We use "name" when introducing ourselves.'),

('cloze-item-2', 'cloze-topic-1', 'cloze-lesson-1', 'easy', 
 '["Nice to", "__", "you!"]', 
 '["meet","see","know"]', 
 '["meet"]', 
 'Common greeting phrase', 
 '"Nice to meet you" is a standard greeting.'),

('cloze-item-3', 'cloze-topic-2', 'cloze-lesson-2', 'easy', 
 '["She", "__", "to school every day."]', 
 '["go","goes","going"]', 
 '["goes"]', 
 'Third person singular present tense', 
 'Use "goes" for he/she/it in present tense.'),

('cloze-item-4', 'cloze-topic-3', 'cloze-lesson-3', 'medium', 
 '["I", "__", "breakfast at 8 AM."]', 
 '["eat","eats","eating"]', 
 '["eat"]', 
 'First person present tense', 
 'Use "eat" for I/you/we/they.');

-- ============================================
-- GRAMMAR CHALLENGE SEED DATA
-- ============================================

-- Grammar Categories
INSERT INTO grammar_categories (id, name, icon, description) VALUES
('grammar-cat-1', 'Verb Tenses', '⏰', 'Master past, present, and future tenses'),
('grammar-cat-2', 'Articles', '📝', 'Learn when to use a, an, and the'),
('grammar-cat-3', 'Prepositions', '🎯', 'Practice in, on, at, and more'),
('grammar-cat-4', 'Question Formation', '❓', 'Ask questions correctly');

-- Grammar Lessons
INSERT INTO grammar_lessons (id, category_id, title, description, difficulty, question_count) VALUES
('grammar-lesson-1', 'grammar-cat-1', 'Simple Present', 'Basic present tense', 'easy', 3),
('grammar-lesson-2', 'grammar-cat-2', 'A vs An', 'Choose the right article', 'easy', 3),
('grammar-lesson-3', 'grammar-cat-3', 'Time Prepositions', 'In, on, at for time', 'medium', 3),
('grammar-lesson-4', 'grammar-cat-4', 'Wh-Questions', 'Who, what, where, when', 'medium', 3);

-- Grammar Questions
INSERT INTO grammar_questions (id, category_id, lesson_id, difficulty, question, options, correct_answer, hint, explanation) VALUES
('grammar-q-1', 'grammar-cat-1', 'grammar-lesson-1', 'easy', 
 'She ___ to school every day.', 
 '["go","goes","going"]', 
 'goes', 
 'Third person singular', 
 'Use "goes" for she/he/it in present tense.'),

('grammar-q-2', 'grammar-cat-1', 'grammar-lesson-1', 'easy', 
 'They ___ football on weekends.', 
 '["play","plays","playing"]', 
 'play', 
 'Plural subject', 
 'Use "play" for they/we/you in present tense.'),

('grammar-q-3', 'grammar-cat-2', 'grammar-lesson-2', 'easy', 
 'I have ___ apple.', 
 '["a","an","the"]', 
 'an', 
 'Vowel sound', 
 'Use "an" before vowel sounds.'),

('grammar-q-4', 'grammar-cat-3', 'grammar-lesson-3', 'medium', 
 'The meeting is ___ 3 PM.', 
 '["in","on","at"]', 
 'at', 
 'Specific time', 
 'Use "at" for specific times.');

-- ============================================
-- SENTENCE BUILDER SEED DATA
-- ============================================

-- Sentence Topics
INSERT INTO sentence_topics (id, name, icon, description) VALUES
('sentence-topic-1', 'Basic Sentences', '✍️', 'Simple sentence construction'),
('sentence-topic-2', 'Daily Activities', '🏃', 'Describe what you do every day'),
('sentence-topic-3', 'Likes and Dislikes', '❤️', 'Express preferences'),
('sentence-topic-4', 'Questions', '❓', 'Form questions correctly');

-- Sentence Lessons
INSERT INTO sentence_lessons (id, topic_id, title, description, difficulty, item_count) VALUES
('sentence-lesson-1', 'sentence-topic-1', 'Subject-Verb-Object', 'Basic word order', 'easy', 3),
('sentence-lesson-2', 'sentence-topic-2', 'Morning Routine', 'Talk about your morning', 'easy', 3),
('sentence-lesson-3', 'sentence-topic-3', 'Food Preferences', 'What do you like to eat?', 'medium', 3),
('sentence-lesson-4', 'sentence-topic-4', 'Yes/No Questions', 'Ask simple questions', 'medium', 3);

-- Sentence Items
INSERT INTO sentence_items (id, topic_id, lesson_id, difficulty, english_sentence, translation, sentence_tokens, accepted_sequences, distractors, hint) VALUES
('sentence-item-1', 'sentence-topic-1', 'sentence-lesson-1', 'easy', 
 'I like pizza.', 
 'मुझे पिज़्ज़ा पसंद है।', 
 '["I","like","pizza","."]', 
 '[["I","like","pizza","."]]', 
 '["hate","love","enjoy"]', 
 'Subject + verb + object'),

('sentence-item-2', 'sentence-topic-1', 'sentence-lesson-1', 'easy', 
 'She reads books.', 
 'वह किताबें पढ़ती है।', 
 '["She","reads","books","."]', 
 '[["She","reads","books","."]]', 
 '["writes","buys","sells"]', 
 'Third person singular'),

('sentence-item-3', 'sentence-topic-2', 'sentence-lesson-2', 'easy', 
 'I wake up early.', 
 'मैं जल्दी उठता हूं।', 
 '["I","wake","up","early","."]', 
 '[["I","wake","up","early","."]]', 
 '["late","now","soon"]', 
 'Phrasal verb: wake up'),

('sentence-item-4', 'sentence-topic-3', 'sentence-lesson-3', 'medium', 
 'Do you like coffee?', 
 'क्या आपको कॉफी पसंद है?', 
 '["Do","you","like","coffee","?"]', 
 '[["Do","you","like","coffee","?"]]', 
 '["tea","milk","water"]', 
 'Yes/No question format');
