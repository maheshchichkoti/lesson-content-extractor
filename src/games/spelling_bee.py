"""Spelling Bee game service - Production ready implementation

This service handles spelling practice sessions where users type words
they hear. It reuses the word_lists infrastructure and tracks detailed
statistics for each word.

Key features:
- Session management with shuffle support
- Per-word result tracking with user answers
- Word statistics updates (practice count, accuracy)
- Mistake tracking for review mode
- Optional pronunciation audio URLs
"""

from typing import List, Optional, Dict
from supabase import Client
import logging
from datetime import datetime
import random

logger = logging.getLogger(__name__)

class SpellingBeeService:
    """Service for managing Spelling Bee game sessions and results"""
    
    def __init__(self, supabase: Client):
        """Initialize service with Supabase client
        
        Args:
            supabase: Authenticated Supabase client instance
        """
        self.supabase = supabase
        self.game_type = "spelling_bee"
    
    def start_session(
        self,
        user_id: str,
        word_list_id: str,
        selected_word_ids: Optional[List[str]] = None,
        shuffle: bool = True
    ) -> Dict:
        """Start a new spelling bee practice session
        
        Args:
            user_id: User identifier
            word_list_id: Word list to practice from
            selected_word_ids: Optional subset of words to practice
            shuffle: Whether to randomize word order
            
        Returns:
            Session object with id, words, and progress
            
        Raises:
            ValueError: If word list not found or no words available
        """
        try:
            logger.info(f"[SPELLING_BEE] Starting session for user {user_id}, list {word_list_id}")
            
            # Verify word list ownership
            list_response = self.supabase.table('word_lists')\
                .select('*')\
                .eq('id', word_list_id)\
                .eq('user_id', user_id)\
                .execute()
            
            if not list_response.data:
                logger.warning(f"[SPELLING_BEE] Word list {word_list_id} not found for user {user_id}")
                raise ValueError("Word list not found or access denied")
            
            # Fetch words (selected subset or all)
            if selected_word_ids:
                logger.info(f"[SPELLING_BEE] Using {len(selected_word_ids)} selected words")
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
                logger.warning(f"[SPELLING_BEE] No words found in list {word_list_id}")
                raise ValueError("No words found in this list")
            
            # Shuffle for variety if requested
            if shuffle:
                random.shuffle(words)
                logger.info(f"[SPELLING_BEE] Shuffled {len(words)} words")
            
            # Create game session
            session_data = {
                "user_id": user_id,
                "game_type": self.game_type,
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
            logger.info(f"[SPELLING_BEE] Session created: {session['id']}")
            
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
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"[SPELLING_BEE] Error starting session: {e}", exc_info=True)
            raise
    
    def get_session(self, session_id: str, user_id: str) -> Optional[Dict]:
        """Retrieve session details
        
        Args:
            session_id: Session identifier
            user_id: User identifier for ownership verification
            
        Returns:
            Session object or None if not found
        """
        try:
            session_response = self.supabase.table('game_sessions')\
                .select('*')\
                .eq('id', session_id)\
                .eq('user_id', user_id)\
                .eq('game_type', self.game_type)\
                .execute()
            
            if not session_response.data:
                logger.warning(f"[SPELLING_BEE] Session {session_id} not found for user {user_id}")
                return None
            
            session = session_response.data[0]
            
            # Include words only for active sessions (performance optimization)
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
            logger.error(f"[SPELLING_BEE] Error getting session: {e}", exc_info=True)
            raise
    
    def record_result(
        self,
        session_id: str,
        user_id: str,
        word_id: str,
        user_answer: str,
        is_correct: bool,
        attempts: int,
        time_spent: int
    ) -> Dict:
        """Record a spelling attempt result
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            word_id: Word being practiced
            user_answer: User's typed answer
            is_correct: Whether answer was correct
            attempts: Number of attempts made
            time_spent: Time in milliseconds
            
        Returns:
            Success response
            
        Raises:
            ValueError: If session not found or word not in list
        """
        try:
            logger.info(f"[SPELLING_BEE] Recording result for word {word_id} in session {session_id}")
            
            # Verify session ownership
            session_response = self.supabase.table('game_sessions')\
                .select('*')\
                .eq('id', session_id)\
                .eq('user_id', user_id)\
                .eq('game_type', self.game_type)\
                .execute()
            
            if not session_response.data:
                logger.warning(f"[SPELLING_BEE] Session {session_id} not found")
                raise ValueError("Session not found or access denied")
            
            session = session_response.data[0]
            
            # Store result with metadata
            result_data = {
                "session_id": session_id,
                "game_type": self.game_type,
                "item_id": word_id,
                "is_correct": is_correct,
                "attempts": attempts,
                "time_spent_ms": time_spent,
                "metadata": {
                    "user_answer": user_answer,
                    "mode": "spelling"
                }
            }
            
            self.supabase.table('game_results')\
                .insert(result_data)\
                .execute()
            
            # Update word-level statistics
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
                
                logger.info(f"[SPELLING_BEE] Updated word stats: {new_practice_count} practices, {new_accuracy}% accuracy")
            
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
            
            # Track mistakes for targeted review
            if not is_correct:
                self.supabase.table('user_mistakes')\
                    .upsert({
                        "user_id": user_id,
                        "game_type": self.game_type,
                        "item_id": word_id,
                        "last_error_type": "spelling_error",
                        "mistake_count": 1,
                        "last_attempted_at": datetime.utcnow().isoformat()
                    }, on_conflict="user_id,game_type,item_id")\
                    .execute()
                logger.info(f"[SPELLING_BEE] Tracked mistake for word {word_id}")
            
            return {"ok": True}
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"[SPELLING_BEE] Error recording result: {e}", exc_info=True)
            raise
    
    def complete_session(
        self,
        session_id: str,
        user_id: str,
        final_progress: Optional[Dict] = None
    ) -> Dict:
        """Mark session as complete and return final summary
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            final_progress: Optional final progress override from client
            
        Returns:
            Completed session object
            
        Raises:
            ValueError: If session not found
        """
        try:
            logger.info(f"[SPELLING_BEE] Completing session {session_id}")
            
            # Verify session ownership
            session_response = self.supabase.table('game_sessions')\
                .select('*')\
                .eq('id', session_id)\
                .eq('user_id', user_id)\
                .eq('game_type', self.game_type)\
                .execute()
            
            if not session_response.data:
                logger.warning(f"[SPELLING_BEE] Session {session_id} not found")
                raise ValueError("Session not found or access denied")
            
            session = session_response.data[0]
            
            # Prepare update data
            update_data = {
                "completed_at": datetime.utcnow().isoformat()
            }
            
            # Allow client to override final progress (reconciliation)
            if final_progress:
                update_data.update({
                    "progress_current": final_progress.get('current', session['progress_current']),
                    "correct": final_progress.get('correct', session['correct']),
                    "incorrect": final_progress.get('incorrect', session['incorrect'])
                })
            
            self.supabase.table('game_sessions')\
                .update(update_data)\
                .eq('id', session_id)\
                .execute()
            
            # Fetch updated session
            updated_response = self.supabase.table('game_sessions')\
                .select('*')\
                .eq('id', session_id)\
                .execute()
            
            session = updated_response.data[0]
            logger.info(f"[SPELLING_BEE] Session completed: {session['correct']}/{session['progress_total']} correct")
            
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
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"[SPELLING_BEE] Error completing session: {e}", exc_info=True)
            raise
    
    def get_pronunciation(self, word_id: str, user_id: str) -> Dict:
        """Get pronunciation audio URL for a word (optional feature)
        
        This is a placeholder for future TTS/audio integration.
        In production, this would:
        1. Check if pre-generated audio exists in CDN
        2. Generate on-demand using TTS service if needed
        3. Return signed CDN URL with expiration
        
        Args:
            word_id: Word identifier
            user_id: User identifier for access verification
            
        Returns:
            Audio metadata with URL
            
        Raises:
            ValueError: If word not found or access denied
        """
        try:
            # Verify word access through word list ownership
            word_response = self.supabase.table('words')\
                .select('*, word_lists!inner(user_id)')\
                .eq('id', word_id)\
                .execute()
            
            if not word_response.data:
                raise ValueError("Word not found")
            
            word = word_response.data[0]
            
            # Verify ownership
            if word.get('word_lists', {}).get('user_id') != user_id:
                raise ValueError("Access denied")
            
            # In production: return actual CDN URL
            # For now: return placeholder structure
            return {
                "wordId": word_id,
                "audioUrl": f"https://cdn.tulkka.com/audio/spelling/{word_id}_en_us.mp3",
                "language": "en-US"
            }
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"[SPELLING_BEE] Error getting pronunciation: {e}", exc_info=True)
            raise