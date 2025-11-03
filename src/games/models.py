"""Pydantic models for games API"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# Word List Models
class WordListCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = ""

class WordListUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    description: Optional[str] = None
    is_favorite: Optional[bool] = None

class Word(BaseModel):
    id: str
    list_id: str
    word: str
    translation: str
    notes: Optional[str] = ""
    is_favorite: bool = False
    practice_count: int = 0
    correct_count: int = 0
    accuracy: int = 0
    last_practiced: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

class WordList(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str] = ""
    word_count: int = 0
    is_favorite: bool = False
    created_at: datetime
    updated_at: datetime
    words: Optional[List[Word]] = None

# Word Models
class WordCreate(BaseModel):
    word: str = Field(..., min_length=1, max_length=120)
    translation: str = Field(..., min_length=1, max_length=240)
    notes: Optional[str] = ""

class WordUpdate(BaseModel):
    word: Optional[str] = Field(None, min_length=1, max_length=120)
    translation: Optional[str] = Field(None, min_length=1, max_length=240)
    notes: Optional[str] = None
    is_favorite: Optional[bool] = None

# Session Models
class SessionStart(BaseModel):
    wordListId: str
    selectedWordIds: Optional[List[str]] = None

class Progress(BaseModel):
    current: int = 0
    total: int = 0
    correct: int = 0
    incorrect: int = 0

class GameSession(BaseModel):
    id: str
    wordListId: str
    words: List[Word]
    progress: Progress
    startedAt: datetime
    completedAt: Optional[datetime] = None

# Result Models
class PracticeResult(BaseModel):
    wordId: str
    isCorrect: bool
    timeSpent: int = Field(..., ge=0)
    attempts: int = Field(1, ge=1)

class SessionComplete(BaseModel):
    progress: Optional[Progress] = None

# Response Models
class PaginationInfo(BaseModel):
    page: int
    limit: int
    total: int

class WordListsResponse(BaseModel):
    data: List[WordList]
    pagination: PaginationInfo

class SuccessResponse(BaseModel):
    ok: bool = True

class FavoriteToggle(BaseModel):
    isFavorite: bool