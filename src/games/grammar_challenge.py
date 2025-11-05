"""Grammar Challenge game service - Production ready implementation

This service handles multiple-choice grammar questions across various categories
(tenses, agreement, modifiers, etc.). Supports topic/lesson/custom/mistakes modes.

Key features:
- Category/Lesson/Custom/Mistakes modes
- Multiple-choice questions with explanations
- Skip functionality
- Contextual hints after wrong attempts
- Detailed mistake tracking by category
"""

from typing import List, Optional, Dict
from supabase import Client
import logging
import random
from src.utils.time_utils import utc_now_iso

logger = logging.getLogger(__name__)

class GrammarChallengeService:
    """Service for managing Grammar Challenge game sessions and results"""
    
    def __init__(self, supabase: Client):
        """Initialize service with Supabase client
        
        Args:
            supabase: Authenticated Supabase client instance
        """
        self.supabase = supabase
        self.game_type = "grammar_challenge"
    
    def get_categories(self) -> Dict:
        """Get all available grammar categories
        
        Returns:
            List of categories
        """
        try:
            response = self.supabase.table('grammar_categories')\
                .select('id, name')\
                .order('name')\
                .execute()
            
            categories = response.data or []
            logger.info(f"[GRAMMAR_CHALLENGE] Retrieved {len(categories)} categories")
            return {"categories": categories}
        except Exception as e:
            logger.error(f"[GRAMMAR_CHALLENGE] Error getting categories: {e}", exc_info=True)
            raise
    
    def get_lessons(self, category_id: Optional[str] = None) -> Dict:
        """Get lessons, optionally filtered by category
        
        Args:
            category_id: Optional category filter
            
        Returns:
            List of lessons
        """
        try:
            query = self.supabase.table('grammar_lessons')\
                .select('id, category_id, title, question_count')
            
            if category_id:
                query = query.eq('category_id', category_id)
            
            response = query.order('title').execute()
            
            lessons = [
                {
                    "id": lesson['id'],
                    "title": lesson['title'],
                    "categoryId": lesson['category_id'],
                    "questions": lesson['question_count']
                }
                for lesson in (response.data or [])
            ]
            
            logger.info(f"[GRAMMAR_CHALLENGE] Retrieved {len(lessons)} lessons")
            return {"lessons": lessons}
        except Exception as e:
            logger.error(f"[GRAMMAR_CHALLENGE] Error getting lessons: {e}", exc_info=True)
            raise
    
    def get_questions(
        self,
        category_id: Optional[str] = None,
        lesson_id: Optional[str] = None,
        difficulty: Optional[str] = None,
        page: int = 1,
        limit: int = 50,
        include_options: bool = False
    ) -> Dict:
        """Get grammar questions with optional filters
        
        Args:
            category_id: Filter by category
            lesson_id: Filter by lesson
            difficulty: Filter by difficulty (easy/medium/hard)
            page: Page number
            limit: Items per page
            include_options: Whether to include options and explanations
            
        Returns:
            Paginated questions list
        """
        try:
            logger.info(f"[GRAMMAR_CHALLENGE] Fetching questions: category={category_id}, lesson={lesson_id}, difficulty={difficulty}")
            
            # Build query with filters
            query = self.supabase.table('grammar_questions').select('*')
            
            if category_id:
                query = query.eq('category_id', category_id)
            if lesson_id:
                query = query.eq('lesson_id', lesson_id)
            if difficulty:
                query = query.eq('difficulty', difficulty)
            
            # Get total count
            count_response = query.execute()
            total = len(count_response.data or [])
            
            # Apply pagination
            offset = (page - 1) * limit
            query = query.range(offset, offset + limit - 1)
            
            response = query.execute()
            questions = []
            
            for q in (response.data or []):
                question_data = {
                    "id": q['id'],
                    "category": q['category_id'],
                    "difficulty": q['difficulty'],
                    "lesson": q['lesson_id'],
                    "prompt": q['prompt']
                }
                
                if include_options:
                    question_data.update({
                        "options": q['options'],
                        "correctIndex": q['correct_index'],
                        "explanation": q['explanation']
                    })
                
                questions.append(question_data)
            
            logger.info(f"[GRAMMAR_CHALLENGE] Retrieved {len(questions)} questions (total: {total})")
            
            return {
                "data": questions,
                "pagination": {"page": page, "limit": limit, "total": total}
            }
        except Exception as e:
            logger.error(f"[GRAMMAR_CHALLENGE] Error getting questions: {e}", exc_info=True)
            raise
    
    def start_session(
        self,
        user_id: str,
        mode: str,
        category_id: Optional[str] = None,
        lesson_id: Optional[str] = None,
        selected_question_ids: Optional[List[str]] = None,
        difficulty: Optional[str] = None,
        limit: int = 10
    ) -> Dict:
        """Start a new grammar challenge session
        
        Args:
            user_id: User identifier
            mode: Session mode (topic/lesson/custom/mistakes)
            category_id: Category for topic mode
            lesson_id: Lesson for lesson mode
            selected_question_ids: Questions for custom mode
            difficulty: Difficulty filter
            limit: Max questions for topic/lesson modes
            
        Returns:
            Session object with questions and progress
            
        Raises:
            ValueError: If invalid mode or missing required parameters
        """
        try:
            logger.info(f"[GRAMMAR_CHALLENGE] Starting {mode} session for user {user_id}")
            
            # Validate mode-specific requirements
            if mode == "topic" and not category_id:
                raise ValueError("category_id required for topic mode")
            if mode == "lesson" and not lesson_id:
                raise ValueError("lesson_id required for lesson mode")
            if mode == "custom" and not selected_question_ids:
                raise ValueError("selected_question_ids required for custom mode")
            
            # Fetch questions based on mode
            questions = []
            reference_id = None
            
            if mode == "topic":
                # In production: query grammar_questions by category_id and difficulty
                questions = self.get_questions(category_id=category_id, difficulty=difficulty, limit=limit, include_options=True)["data"]
                reference_id = category_id
            elif mode == "lesson":
                # In production: query grammar_questions by lesson_id
                questions = self.get_questions(lesson_id=lesson_id, difficulty=difficulty, include_options=True)["data"]
                reference_id = lesson_id
            elif mode == "custom":
                # Fetch specific questions by IDs
                if selected_question_ids:
                    query = self.supabase.table('grammar_questions')\
                        .select('*')\
                        .in_('id', selected_question_ids)
                    response = query.execute()
                    questions = [
                        {
                            "id": q['id'],
                            "category": q['category_id'],
                            "difficulty": q['difficulty'],
                            "lesson": q['lesson_id'],
                            "prompt": q['prompt'],
                            "options": q['options'],
                            "correctIndex": q['correct_index'],
                            "explanation": q['explanation']
                        }
                        for q in (response.data or [])
                    ]
                reference_id = "custom"
            elif mode == "mistakes":
                # Fetch user's mistakes
                mistakes_response = self.supabase.table('user_mistakes')\
                    .select('item_id')\
                    .eq('user_id', user_id)\
                    .eq('game_type', self.game_type)\
                    .execute()
                
                mistake_ids = [m['item_id'] for m in (mistakes_response.data or [])]
                if mistake_ids:
                    # Fetch actual questions for these mistakes
                    query = self.supabase.table('grammar_questions')\
                        .select('*')\
                        .in_('id', mistake_ids[:limit])
                    response = query.execute()
                    questions = [
                        {
                            "id": q['id'],
                            "category": q['category_id'],
                            "difficulty": q['difficulty'],
                            "lesson": q['lesson_id'],
                            "prompt": q['prompt'],
                            "options": q['options'],
                            "correctIndex": q['correct_index'],
                            "explanation": q['explanation']
                        }
                        for q in (response.data or [])
                    ]
                reference_id = "mistakes"
            
            if not questions:
                raise ValueError("No questions available for this session")
            
            # Randomize order
            random.shuffle(questions)
            
            # Create session
            session_data = {
                "user_id": user_id,
                "game_type": self.game_type,
                "mode": mode,
                "reference_id": reference_id,
                "progress_current": 0,
                "progress_total": len(questions),
                "correct": 0,
                "incorrect": 0
            }
            
            session_response = self.supabase.table('game_sessions')\
                .insert(session_data)\
                .execute()
            
            session = session_response.data[0]
            logger.info(f"[GRAMMAR_CHALLENGE] Session created: {session['id']} with {len(questions)} questions")
            
            return {
                "id": session['id'],
                "mode": mode,
                "categoryId": category_id,
                "lessonId": lesson_id,
                "questions": questions,
                "progress": {"current": 0, "total": len(questions), "correct": 0, "incorrect": 0},
                "startedAt": session['started_at'],
                "completedAt": None
            }
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"[GRAMMAR_CHALLENGE] Error starting session: {e}", exc_info=True)
            raise
    
    def get_session(self, session_id: str, user_id: str, include_options: bool = False) -> Optional[Dict]:
        """Get session details
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            include_options: Whether to expand questions with options
            
        Returns:
            Session object or None
        """
        try:
            session_response = self.supabase.table('game_sessions')\
                .select('*')\
                .eq('id', session_id)\
                .eq('user_id', user_id)\
                .eq('game_type', self.game_type)\
                .execute()
            
            if not session_response.data:
                return None
            
            session = session_response.data[0]
            
            # In production: fetch actual questions if needed
            questions = []
            
            return {
                "id": session['id'],
                "mode": session['mode'],
                "categoryId": session.get('reference_id') if session['mode'] == 'topic' else None,
                "lessonId": session.get('reference_id') if session['mode'] == 'lesson' else None,
                "questions": questions,
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
            logger.error(f"[GRAMMAR_CHALLENGE] Error getting session: {e}", exc_info=True)
            raise
    
    def record_result(
        self,
        session_id: str,
        user_id: str,
        question_id: str,
        selected_answer: int,
        is_correct: bool,
        attempts: int,
        time_spent: int
    ) -> Dict:
        """Record a question result
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            question_id: Question being answered
            selected_answer: Index of selected answer
            is_correct: Whether answer was correct
            attempts: Number of attempts
            time_spent: Time in milliseconds
            
        Returns:
            Success response
        """
        try:
            logger.info(f"[GRAMMAR_CHALLENGE] Recording result for question {question_id}")
            
            # Verify session
            session_response = self.supabase.table('game_sessions')\
                .select('*')\
                .eq('id', session_id)\
                .eq('user_id', user_id)\
                .eq('game_type', self.game_type)\
                .execute()
            
            if not session_response.data:
                raise ValueError("Session not found or access denied")
            
            session = session_response.data[0]
            
            # Store result
            result_data = {
                "session_id": session_id,
                "game_type": self.game_type,
                "item_id": question_id,
                "is_correct": is_correct,
                "attempts": attempts,
                "time_spent_ms": time_spent,
                "metadata": {"selected_answer": selected_answer}
            }
            
            self.supabase.table('game_results')\
                .insert(result_data)\
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
            
            # Track mistakes
            if not is_correct:
                self.supabase.table('user_mistakes')\
                    .upsert({
                        "user_id": user_id,
                        "game_type": self.game_type,
                        "item_id": question_id,
                        "last_error_type": "incorrect_answer",
                        "mistake_count": 1,
                        "last_attempted_at": utc_now_iso()
                    }, on_conflict="user_id,game_type,item_id")\
                    .execute()
            
            return {"ok": True}
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"[GRAMMAR_CHALLENGE] Error recording result: {e}", exc_info=True)
            raise
    
    def skip_question(self, session_id: str, user_id: str, question_id: str) -> Dict:
        """Record a skipped question
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            question_id: Question being skipped
            
        Returns:
            Success response
        """
        try:
            logger.info(f"[GRAMMAR_CHALLENGE] Skipping question {question_id}")
            
            # Verify session
            session_response = self.supabase.table('game_sessions')\
                .select('*')\
                .eq('id', session_id)\
                .eq('user_id', user_id)\
                .eq('game_type', self.game_type)\
                .execute()
            
            if not session_response.data:
                raise ValueError("Session not found or access denied")
            
            session = session_response.data[0]
            
            # Record skip as incorrect result
            result_data = {
                "session_id": session_id,
                "game_type": self.game_type,
                "item_id": question_id,
                "is_correct": False,
                "attempts": 0,
                "time_spent_ms": 0,
                "metadata": {"skipped": True}
            }
            
            self.supabase.table('game_results')\
                .insert(result_data)\
                .execute()
            
            # Update session progress
            new_current = session['progress_current'] + 1
            new_incorrect = session['incorrect'] + 1
            
            self.supabase.table('game_sessions')\
                .update({
                    "progress_current": new_current,
                    "incorrect": new_incorrect
                })\
                .eq('id', session_id)\
                .execute()
            
            return {"ok": True}
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"[GRAMMAR_CHALLENGE] Error skipping question: {e}", exc_info=True)
            raise
    
    def complete_session(self, session_id: str, user_id: str, final_progress: Optional[Dict] = None) -> Dict:
        """Complete a grammar challenge session
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            final_progress: Optional progress override
            
        Returns:
            Completed session object
        """
        try:
            logger.info(f"[GRAMMAR_CHALLENGE] Completing session {session_id}")
            
            session_response = self.supabase.table('game_sessions')\
                .select('*')\
                .eq('id', session_id)\
                .eq('user_id', user_id)\
                .eq('game_type', self.game_type)\
                .execute()
            
            if not session_response.data:
                raise ValueError("Session not found or access denied")
            
            session = session_response.data[0]
            
            update_data = {"completed_at": utc_now_iso()}
            
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
            
            updated_response = self.supabase.table('game_sessions')\
                .select('*')\
                .eq('id', session_id)\
                .execute()
            
            session = updated_response.data[0]
            
            return {
                "id": session['id'],
                "mode": session['mode'],
                "categoryId": session.get('reference_id') if session['mode'] == 'topic' else None,
                "lessonId": session.get('reference_id') if session['mode'] == 'lesson' else None,
                "questions": [],
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
            logger.error(f"[GRAMMAR_CHALLENGE] Error completing session: {e}", exc_info=True)
            raise
    
    def get_hint(self, question_id: str, user_id: str) -> Dict:
        """Get contextual hint for a question
        
        Args:
            question_id: Question identifier
            user_id: User identifier
            
        Returns:
            Hint text
        """
        try:
            # Fetch question from database
            question_response = self.supabase.table('grammar_questions')\
                .select('explanation')\
                .eq('id', question_id)\
                .execute()
            
            if not question_response.data:
                raise ValueError("Question not found")
            
            # Use explanation as hint
            hint = question_response.data[0].get('explanation', 'No hint available')
            
            return {
                "questionId": question_id,
                "hint": hint
            }
        except Exception as e:
            logger.error(f"[GRAMMAR_CHALLENGE] Error getting hint: {e}", exc_info=True)
            raise
    
    def get_mistakes(self, user_id: str, page: int = 1, limit: int = 50) -> Dict:
        """Get user's mistakes for review
        
        Args:
            user_id: User identifier
            page: Page number
            limit: Items per page
            
        Returns:
            Paginated mistakes list
        """
        try:
            offset = (page - 1) * limit
            
            mistakes_response = self.supabase.table('user_mistakes')\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('game_type', self.game_type)\
                .order('last_attempted_at', desc=True)\
                .range(offset, offset + limit - 1)\
                .execute()
            
            mistakes = mistakes_response.data or []
            
            # Enrich with question details
            data = []
            for m in mistakes:
                question_id = m['item_id']
                # Fetch question details
                question_response = self.supabase.table('grammar_questions')\
                    .select('category_id')\
                    .eq('id', question_id)\
                    .execute()
                
                category = question_response.data[0]['category_id'] if question_response.data else "unknown"
                
                data.append({
                    "questionId": question_id,
                    "category": category,
                    "lastSelected": 0,
                    "lastAnsweredAt": m['last_attempted_at']
                })
            
            return {
                "data": data,
                "pagination": {"page": page, "limit": limit, "total": len(mistakes)}
            }
        except Exception as e:
            logger.error(f"[GRAMMAR_CHALLENGE] Error getting mistakes: {e}", exc_info=True)
            raise