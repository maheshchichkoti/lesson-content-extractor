"""Flashcards game service"""

from typing import List, Optional
from supabase import Client
import logging
from datetime import datetime
import random

logger = logging.getLogger(__name__)

class FlashcardsService:
    def __init__(self, supabase: Client):
        self.supabase = supabase
    
    def start_session(self, user_id: str, word_list_id: str, selected_word_ids: Optional[List[str]] = None):
        """Start a new flashcard practice session"""
        try:
            # Get word list
            list_response = self.supabase.table('word_lists')\
                .select('*')\
                .eq('id', word_list_id)\
                .eq('user_id', user_id)\
                .execute()
            
            if not list_response.data:
                raise ValueError("Word list not found or access denied")
            
            # Get words
            if selected_word_ids:
                words_response = self.supabase.table('words')\
                    .select('*')\
                    .eq('list_id', word_list_id)\
                    .in_('id', selected_word_ids)\
                    .execute()
            else:
                words_response = self.supabase.table('words')\
                    .select('*')\
                    .eq('list_id', word_list_id)\
                    .execute()
            
            words = words_response.data
            
            if not words:
                raise ValueError("No words found in this list")
            
            # Shuffle words for practice
            random.shuffle(words)
            
            # Create session
            session_data = {
                "user_id": user_id,
                "game_type": "flashcards",
                "mode": "practice",
                "reference_id": word_list_id,
                "progress_current": 0,
                "progress_total": len(words),
                "correct": 0,
                "incorrect": 0
            }
            
            session_response = self.supabase.table('game_sessions')\
                .insert(session_data)\
                .execute()
            
            session = session_response.data[0]
            
            return {
                "id": session['id'],
                "wordListId": word_list_id,
                "words": words,
                "progress": {
                    "current": 0,
                    "total": len(words),
                    "correct": 0,
                    "incorrect": 0
                },
                "startedAt": session['started_at'],
                "completedAt": None
            }
        except Exception as e:
            logger.error(f"Error starting flashcard session: {e}")
            raise
    
    def get_session(self, session_id: str, user_id: str):
        """Get session details"""
        try:
            session_response = self.supabase.table('game_sessions')\
                .select('*')\
                .eq('id', session_id)\
                .eq('user_id', user_id)\
                .execute()
            
            if not session_response.data:
                return None
            
            session = session_response.data[0]
            
            # Get words if session is active
            words = []
            if not session['completed_at']:
                words_response = self.supabase.table('words')\
                    .select('*')\
                    .eq('list_id', session['reference_id'])\
                    .execute()
                words = words_response.data
            
            return {
                "id": session['id'],
                "wordListId": session['reference_id'],
                "words": words,
                "progress": {
                    "current": session['progress_current'],
                    "total": session['progress_total'],
                    "correct": session['correct'],
                    "incorrect": session['incorrect']
                },
                "startedAt": session['started_at'],
                "completedAt": session['completed_at']
            }
        except Exception as e:
            logger.error(f"Error getting session: {e}")
            raise
    
    def record_result(self, session_id: str, user_id: str, word_id: str, is_correct: bool, attempts: int, time_spent: int):
        """Record a practice result for a word"""
        try:
            # Verify session ownership
            session_response = self.supabase.table('game_sessions')\
                .select('*')\
                .eq('id', session_id)\
                .eq('user_id', user_id)\
                .execute()
            
            if not session_response.data:
                raise ValueError("Session not found or access denied")
            
            session = session_response.data[0]
            
            # Record result
            result_data = {
                "session_id": session_id,
                "game_type": "flashcards",
                "item_id": word_id,
                "is_correct": is_correct,
                "attempts": attempts,
                "time_spent_ms": time_spent,
                "metadata": {}
            }
            
            self.supabase.table('game_results')\
                .insert(result_data)\
                .execute()
            
            # Update word statistics
            word_response = self.supabase.table('words')\
                .select('*')\
                .eq('id', word_id)\
                .execute()
            
            if word_response.data:
                word = word_response.data[0]
                new_practice_count = word['practice_count'] + 1
                new_correct_count = word['correct_count'] + (1 if is_correct else 0)
                new_accuracy = round(100 * new_correct_count / new_practice_count) if new_practice_count > 0 else 0
                
                self.supabase.table('words')\
                    .update({
                        "practice_count": new_practice_count,
                        "correct_count": new_correct_count,
                        "accuracy": new_accuracy,
                        "last_practiced": datetime.utcnow().isoformat(),
                        "updated_at": datetime.utcnow().isoformat()
                    })\
                    .eq('id', word_id)\
                    .execute()
            
            # Update session progress
            new_current = session['progress_current'] + 1
            new_correct = session['correct'] + (1 if is_correct else 0)
            new_incorrect = session['incorrect'] + (0 if is_correct else 1)
            
            self.supabase.table('game_sessions')\
                .update({
                    "progress_current": new_current,
                    "correct": new_correct,
                    "incorrect": new_incorrect
                })\
                .eq('id', session_id)\
                .execute()
            
            # Track mistakes for review
            if not is_correct:
                self.supabase.table('user_mistakes')\
                    .upsert({
                        "user_id": user_id,
                        "game_type": "flashcards",
                        "item_id": word_id,
                        "last_error_type": "incorrect",
                        "mistake_count": 1,
                        "last_attempted_at": datetime.utcnow().isoformat()
                    }, on_conflict="user_id,game_type,item_id")\
                    .execute()
            
            return {"ok": True}
        except Exception as e:
            logger.error(f"Error recording result: {e}")
            raise
    
    def complete_session(self, session_id: str, user_id: str, final_progress: Optional[dict] = None):
        """Mark session as complete"""
        try:
            # Verify session ownership
            session_response = self.supabase.table('game_sessions')\
                .select('*')\
                .eq('id', session_id)\
                .eq('user_id', user_id)\
                .execute()
            
            if not session_response.data:
                raise ValueError("Session not found or access denied")
            
            # Update session
            update_data = {
                "completed_at": datetime.utcnow().isoformat()
            }
            
            if final_progress:
                update_data.update({
                    "progress_current": final_progress.get('current', session_response.data[0]['progress_current']),
                    "correct": final_progress.get('correct', session_response.data[0]['correct']),
                    "incorrect": final_progress.get('incorrect', session_response.data[0]['incorrect'])
                })
            
            self.supabase.table('game_sessions')\
                .update(update_data)\
                .eq('id', session_id)\
                .execute()
            
            # Get updated session
            updated_response = self.supabase.table('game_sessions')\
                .select('*')\
                .eq('id', session_id)\
                .execute()
            
            session = updated_response.data[0]
            
            return {
                "id": session['id'],
                "wordListId": session['reference_id'],
                "words": [],
                "progress": {
                    "current": session['progress_current'],
                    "total": session['progress_total'],
                    "correct": session['correct'],
                    "incorrect": session['incorrect']
                },
                "startedAt": session['started_at'],
                "completedAt": session['completed_at']
            }
        except Exception as e:
            logger.error(f"Error completing session: {e}")
            raise
    
    def get_user_stats(self, user_id: str):
        """Get user statistics for analytics"""
        try:
            # Get total sessions
            sessions_response = self.supabase.table('game_sessions')\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('game_type', 'flashcard')\
                .execute()
            
            total_sessions = len(sessions_response.data)
            completed_sessions = len([s for s in sessions_response.data if s.get('completed_at')])
            
            # Get total words practiced
            results_response = self.supabase.table('game_results')\
                .select('*')\
                .in_('session_id', [s['id'] for s in sessions_response.data])\
                .execute()
            
            total_words = len(results_response.data)
            correct_words = len([r for r in results_response.data if r.get('is_correct')])
            
            overall_accuracy = round((correct_words / total_words * 100), 1) if total_words > 0 else 0
            
            return {
                "totals": {
                    "sessions": total_sessions,
                    "completedSessions": completed_sessions,
                    "wordsStudied": total_words
                },
                "accuracy": {
                    "overall": overall_accuracy,
                    "correct": correct_words,
                    "incorrect": total_words - correct_words
                }
            }
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            raise