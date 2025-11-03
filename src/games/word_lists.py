"""Word Lists service for Flashcards and Spelling games"""

from typing import List, Optional, Dict

from supabase import Client
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class WordListsService:
    def __init__(self, supabase: Client):
        self.supabase = supabase
    
    def get_word_lists(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 20,
        search: Optional[str] = None,
        favorite: Optional[bool] = None,
        sort: str = "created_at"
    ):
        """Get all word lists for a user"""
        try:
            query = self.supabase.table('word_lists').select('*').eq('user_id', user_id)
            
            # Apply filters
            if search:
                query = query.ilike('name', f'%{search}%')
            if favorite is not None:
                query = query.eq('is_favorite', favorite)
            
            # Apply sorting
            query = query.order(sort, desc=True)
            
            # Get total count
            count_response = query.execute()
            total = len(count_response.data)
            
            # Apply pagination
            offset = (page - 1) * limit
            query = query.range(offset, offset + limit - 1)
            
            response = query.execute()
            
            return {
                "data": response.data,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total
                }
            }
        except Exception as e:
            logger.error(f"Error getting word lists: {e}")
            raise
    
    def create_word_list(self, user_id: str, name: str, description: str = ""):
        """Create a new word list"""
        try:
            data = {
                "user_id": user_id,
                "name": name,
                "description": description,
                "word_count": 0,
                "is_favorite": False
            }
            
            response = self.supabase.table('word_lists').insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating word list: {e}")
            raise
    
    def get_word_list(self, list_id: str, user_id: str, include_words: bool = False):
        """Get a single word list"""
        try:
            query = self.supabase.table('word_lists').select('*').eq('id', list_id).eq('user_id', user_id)
            response = query.execute()
            
            if not response.data:
                return None
            
            word_list = response.data[0]
            
            if include_words:
                words_response = self.supabase.table('words').select('*').eq('list_id', list_id).execute()
                word_list['words'] = words_response.data
            
            return word_list
        except Exception as e:
            logger.error(f"Error getting word list: {e}")
            raise
    
    def update_word_list(self, list_id: str, user_id: str, updates: dict):
        """Update a word list"""
        try:
            updates['updated_at'] = datetime.utcnow().isoformat()
            
            response = self.supabase.table('word_lists')\
                .update(updates)\
                .eq('id', list_id)\
                .eq('user_id', user_id)\
                .execute()
            
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error updating word list: {e}")
            raise
    
    def delete_word_list(self, list_id: str, user_id: str):
        """Delete a word list"""
        try:
            self.supabase.table('word_lists')\
                .delete()\
                .eq('id', list_id)\
                .eq('user_id', user_id)\
                .execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting word list: {e}")
            raise
    
    def add_word(self, list_id: str, user_id: str, word: str, translation: str, notes: str = ""):
        """Add a word to a list"""
        try:
            # Verify list ownership
            list_check = self.get_word_list(list_id, user_id)
            if not list_check:
                raise ValueError("Word list not found or access denied")
            
            # Insert word
            data = {
                "list_id": list_id,
                "word": word,
                "translation": translation,
                "notes": notes
            }
            
            response = self.supabase.table('words').insert(data).execute()
            
            # Update word count
            self.supabase.table('word_lists')\
                .update({"word_count": list_check['word_count'] + 1, "updated_at": datetime.utcnow().isoformat()})\
                .eq('id', list_id)\
                .execute()
            
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error adding word: {e}")
            raise
    
    def update_word(self, list_id: str, word_id: str, user_id: str, updates: dict):
        """Update a word"""
        try:
            # Verify list ownership
            list_check = self.get_word_list(list_id, user_id)
            if not list_check:
                raise ValueError("Word list not found or access denied")
            
            updates['updated_at'] = datetime.utcnow().isoformat()
            
            response = self.supabase.table('words')\
                .update(updates)\
                .eq('id', word_id)\
                .eq('list_id', list_id)\
                .execute()
            
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error updating word: {e}")
            raise
    
    def delete_word(self, list_id: str, word_id: str, user_id: str):
        """Delete a word"""
        try:
            # Verify list ownership
            list_check = self.get_word_list(list_id, user_id)
            if not list_check:
                raise ValueError("Word list not found or access denied")
            
            self.supabase.table('words')\
                .delete()\
                .eq('id', word_id)\
                .eq('list_id', list_id)\
                .execute()
            
            # Update word count
            self.supabase.table('word_lists')\
                .update({"word_count": max(0, list_check['word_count'] - 1), "updated_at": datetime.utcnow().isoformat()})\
                .eq('id', list_id)\
                .execute()
            
            return True
        except Exception as e:
            logger.error(f"Error deleting word: {e}")
            raise
    
    def toggle_list_favorite(self, list_id: str, user_id: str, is_favorite: bool):
        """Toggle favorite status for a word list"""
        try:
            response = self.supabase.table('word_lists')\
                .update({"is_favorite": is_favorite, "updated_at": datetime.utcnow().isoformat()})\
                .eq('id', list_id)\
                .eq('user_id', user_id)\
                .execute()
            
            if not response.data:
                raise ValueError("Word list not found or access denied")
            
            return {"ok": True, "is_favorite": is_favorite}
        except Exception as e:
            logger.error(f"Error toggling list favorite: {e}")
            raise
    
    def toggle_word_favorite(self, list_id: str, word_id: str, user_id: str, is_favorite: bool):
        """Toggle favorite status for a word"""
        try:
            # Verify list ownership
            list_check = self.get_word_list(list_id, user_id)
            if not list_check:
                raise ValueError("Word list not found or access denied")
            
            response = self.supabase.table('words')\
                .update({"is_favorite": is_favorite, "updated_at": datetime.utcnow().isoformat()})\
                .eq('id', word_id)\
                .eq('list_id', list_id)\
                .execute()
            
            if not response.data:
                raise ValueError("Word not found")
            
            return {"ok": True, "is_favorite": is_favorite}
        except Exception as e:
            logger.error(f"Error toggling word favorite: {e}")
            raise
    
    def get_user_stats(self, user_id: str) -> dict:
        """Aggregate high-level stats for a user's word lists"""
        try:
            lists_response = self.supabase.table('word_lists')\
                .select('id, is_favorite, word_count')\
                .eq('user_id', user_id)\
                .execute()
            
            lists = lists_response.data or []
            total_lists = len(lists)
            favorite_lists = len([lst for lst in lists if lst.get('is_favorite')])
            total_words = sum(lst.get('word_count') or 0 for lst in lists)
            
            favorite_words = 0
            if lists:
                list_ids = [lst['id'] for lst in lists if lst.get('id')]
                if list_ids:
                    words_response = self.supabase.table('words')\
                        .select('is_favorite')\
                        .in_('list_id', list_ids)\
                        .execute()
                    favorite_words = len([word for word in (words_response.data or []) if word.get('is_favorite')])
            
            return {
                "totals": {
                    "lists": total_lists,
                    "favoriteLists": favorite_lists,
                    "words": total_words,
                    "favoriteWords": favorite_words
                }
            }
        except Exception as e:
            logger.error(f"Error calculating user stats: {e}")
            raise