"""
Game Table Populator - Migrate transcript data to game tables
Production-ready with duplicate prevention and error handling
"""
from typing import Dict, List, Optional
import json
from supabase import create_client, Client
import os

class GamePopulator:
    """Populates game tables from transcript extraction data"""
    
    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        """Initialize with Supabase connection"""
        self.supabase_url = supabase_url or os.getenv('SUPABASE_URL')
        self.supabase_key = supabase_key or os.getenv('SUPABASE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
    
    def populate_word_lists_from_zoom_summary(self, zoom_summary_id: int, 
                                              user_id: str) -> Optional[str]:
        """
        Migrate flashcards and spelling from zoom_summaries to word_lists tables
        
        Args:
            zoom_summary_id: ID of the zoom_summaries record
            user_id: User ID to assign the word list to
            
        Returns:
            Created word list ID or None if failed
        """
        try:
            # Fetch zoom summary
            response = self.supabase.table('zoom_summaries')\
                .select('*')\
                .eq('id', zoom_summary_id)\
                .execute()
            
            if not response.data:
                print(f"[ERROR] Zoom summary {zoom_summary_id} not found")
                return None
            
            summary = response.data[0]
            lesson_number = summary.get('lesson_number', 1)
            
            # Parse flashcards and spelling from JSONB
            flashcards = summary.get('flashcards', [])
            spelling = summary.get('spelling', [])
            
            if isinstance(flashcards, str):
                flashcards = json.loads(flashcards)
            if isinstance(spelling, str):
                spelling = json.loads(spelling)
            
            if not flashcards and not spelling:
                print(f"[WARN] No flashcards or spelling data in summary {zoom_summary_id}")
                return None
            
            # Create word list
            list_name = f"Lesson {lesson_number} Vocabulary"
            list_desc = f"Auto-generated from class on {summary.get('created_at', 'unknown date')}"
            
            # Check if list already exists
            existing = self.supabase.table('word_lists')\
                .select('id')\
                .eq('user_id', user_id)\
                .eq('name', list_name)\
                .execute()
            
            if existing.data:
                list_id = existing.data[0]['id']
                print(f"[INFO] Using existing word list: {list_id}")
            else:
                # Create new list
                list_data = {
                    'user_id': user_id,
                    'name': list_name,
                    'description': list_desc,
                    'is_favorite': False
                }
                
                list_response = self.supabase.table('word_lists')\
                    .insert(list_data)\
                    .execute()
                
                if not list_response.data:
                    print(f"[ERROR] Failed to create word list")
                    return None
                
                list_id = list_response.data[0]['id']
                print(f"[OK] Created word list: {list_id}")
            
            # Add words from flashcards
            words_added = 0
            for card in flashcards:
                word = card.get('word', '').strip()
                translation = card.get('translation', '').strip()
                example = card.get('example_sentence', '')
                
                if not word:
                    continue
                
                # Check for duplicate
                if self._word_exists(list_id, word):
                    print(f"[SKIP] Word '{word}' already exists in list")
                    continue
                
                # Insert word
                word_data = {
                    'list_id': list_id,
                    'word': word,
                    'translation': translation,
                    'notes': example[:500] if example else None,  # Limit notes length
                    'is_favorite': False
                }
                
                try:
                    self.supabase.table('words').insert(word_data).execute()
                    words_added += 1
                except Exception as e:
                    print(f"[ERROR] Failed to insert word '{word}': {e}")
            
            # Add words from spelling (if not already added)
            for spell in spelling:
                word = spell.get('word', '').strip()
                sample = spell.get('sample_sentence', '')
                
                if not word or self._word_exists(list_id, word):
                    continue
                
                word_data = {
                    'list_id': list_id,
                    'word': word,
                    'translation': '',  # Spelling doesn't have translation
                    'notes': sample[:500] if sample else None,
                    'is_favorite': False
                }
                
                try:
                    self.supabase.table('words').insert(word_data).execute()
                    words_added += 1
                except Exception as e:
                    print(f"[ERROR] Failed to insert word '{word}': {e}")
            
            print(f"[OK] Added {words_added} words to list {list_id}")
            return list_id
            
        except Exception as e:
            print(f"[ERROR] Failed to populate word lists: {e}")
            return None
    
    def populate_cloze_items(self, items: List[Dict]) -> int:
        """
        Insert advanced cloze items into database
        
        Args:
            items: List of cloze items from AdvancedClozeGenerator
            
        Returns:
            Number of items inserted
        """
        inserted = 0
        
        for item in items:
            try:
                # Check for duplicate
                existing = self.supabase.table('cloze_items')\
                    .select('id')\
                    .eq('id', item['id'])\
                    .execute()
                
                if existing.data:
                    print(f"[SKIP] Cloze item {item['id']} already exists")
                    continue
                
                # Convert lists to JSONB format
                item_data = {
                    'id': item['id'],
                    'topic_id': item['topic_id'],
                    'lesson_id': item['lesson_id'],
                    'difficulty': item['difficulty'],
                    'text_parts': json.dumps(item['text_parts']),
                    'options': json.dumps(item['options']),
                    'correct': json.dumps(item['correct']),
                    'explanation': item['explanation']
                }
                
                self.supabase.table('cloze_items').insert(item_data).execute()
                inserted += 1
                print(f"[OK] Inserted cloze item: {item['id']}")
                
            except Exception as e:
                print(f"[ERROR] Failed to insert cloze item {item.get('id', 'unknown')}: {e}")
        
        # Update lesson item count
        if inserted > 0 and items:
            self._update_cloze_lesson_count(items[0]['lesson_id'])
        
        return inserted
    
    def populate_grammar_questions(self, questions: List[Dict]) -> int:
        """
        Insert grammar questions into database
        
        Args:
            questions: List of questions from GrammarQuestionGenerator
            
        Returns:
            Number of questions inserted
        """
        inserted = 0
        
        for question in questions:
            try:
                # Check for duplicate
                existing = self.supabase.table('grammar_questions')\
                    .select('id')\
                    .eq('id', question['id'])\
                    .execute()
                
                if existing.data:
                    print(f"[SKIP] Grammar question {question['id']} already exists")
                    continue
                
                # Convert options to JSONB
                question_data = {
                    'id': question['id'],
                    'category_id': question['category_id'],
                    'lesson_id': question['lesson_id'],
                    'difficulty': question['difficulty'],
                    'prompt': question['prompt'],
                    'options': json.dumps(question['options']),
                    'correct_index': question['correct_index'],
                    'explanation': question['explanation']
                }
                
                self.supabase.table('grammar_questions').insert(question_data).execute()
                inserted += 1
                print(f"[OK] Inserted grammar question: {question['id']}")
                
            except Exception as e:
                print(f"[ERROR] Failed to insert grammar question {question.get('id', 'unknown')}: {e}")
        
        # Update lesson question count
        if inserted > 0 and questions:
            self._update_grammar_lesson_count(questions[0]['lesson_id'])
        
        return inserted
    
    def populate_sentence_items(self, items: List[Dict]) -> int:
        """
        Insert sentence builder items into database
        
        Args:
            items: List of items from SentenceBuilderGenerator
            
        Returns:
            Number of items inserted
        """
        inserted = 0
        
        for item in items:
            try:
                # Check for duplicate
                existing = self.supabase.table('sentence_items')\
                    .select('id')\
                    .eq('id', item['id'])\
                    .execute()
                
                if existing.data:
                    print(f"[SKIP] Sentence item {item['id']} already exists")
                    continue
                
                # Convert arrays to JSONB
                item_data = {
                    'id': item['id'],
                    'topic_id': item['topic_id'],
                    'lesson_id': item['lesson_id'],
                    'difficulty': item['difficulty'],
                    'english': item['english'],
                    'translation': item['translation'],
                    'tokens': json.dumps(item['tokens']),
                    'accepted': json.dumps(item['accepted']),
                    'distractors': json.dumps(item['distractors']) if item.get('distractors') else None
                }
                
                self.supabase.table('sentence_items').insert(item_data).execute()
                inserted += 1
                print(f"[OK] Inserted sentence item: {item['id']}")
                
            except Exception as e:
                print(f"[ERROR] Failed to insert sentence item {item.get('id', 'unknown')}: {e}")
        
        # Update lesson item count
        if inserted > 0 and items:
            self._update_sentence_lesson_count(items[0]['lesson_id'])
        
        return inserted
    
    def _word_exists(self, list_id: str, word: str) -> bool:
        """Check if word already exists in list"""
        try:
            response = self.supabase.table('words')\
                .select('id')\
                .eq('list_id', list_id)\
                .eq('word', word)\
                .execute()
            return len(response.data) > 0
        except:
            return False
    
    def _update_cloze_lesson_count(self, lesson_id: str):
        """Update item count for cloze lesson"""
        try:
            # Count items
            count_response = self.supabase.table('cloze_items')\
                .select('id', count='exact')\
                .eq('lesson_id', lesson_id)\
                .execute()
            
            count = count_response.count if hasattr(count_response, 'count') else len(count_response.data)
            
            # Update lesson
            self.supabase.table('cloze_lessons')\
                .update({'item_count': count})\
                .eq('id', lesson_id)\
                .execute()
            
            print(f"[OK] Updated cloze lesson {lesson_id} count: {count}")
        except Exception as e:
            print(f"[WARN] Failed to update cloze lesson count: {e}")
    
    def _update_grammar_lesson_count(self, lesson_id: str):
        """Update question count for grammar lesson"""
        try:
            # Count questions
            count_response = self.supabase.table('grammar_questions')\
                .select('id', count='exact')\
                .eq('lesson_id', lesson_id)\
                .execute()
            
            count = count_response.count if hasattr(count_response, 'count') else len(count_response.data)
            
            # Update lesson
            self.supabase.table('grammar_lessons')\
                .update({'question_count': count})\
                .eq('id', lesson_id)\
                .execute()
            
            print(f"[OK] Updated grammar lesson {lesson_id} count: {count}")
        except Exception as e:
            print(f"[WARN] Failed to update grammar lesson count: {e}")
    
    def _update_sentence_lesson_count(self, lesson_id: str):
        """Update item count for sentence lesson"""
        try:
            # Count items
            count_response = self.supabase.table('sentence_items')\
                .select('id', count='exact')\
                .eq('lesson_id', lesson_id)\
                .execute()
            
            count = count_response.count if hasattr(count_response, 'count') else len(count_response.data)
            
            # Update lesson
            self.supabase.table('sentence_lessons')\
                .update({'item_count': count})\
                .eq('id', lesson_id)\
                .execute()
            
            print(f"[OK] Updated sentence lesson {lesson_id} count: {count}")
        except Exception as e:
            print(f"[WARN] Failed to update sentence lesson count: {e}")
