
"""Production-ready FastAPI application for lesson content extraction"""

import os
import re
import time
from threading import Thread
from fastapi import FastAPI, HTTPException, status, BackgroundTasks, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional
import logging
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv
import requests
import assemblyai as aai
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.main import LessonProcessor

load_dotenv()

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('api.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Log startup
logger.info("="*50)
logger.info("Starting Lesson Content Extractor API")
logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
logger.info("="*50)

# Initialize FastAPI app
app = FastAPI(
    title="Lesson Content Extractor API",
    description="Transform lesson transcripts into structured learning exercises",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests"""
    start_time = datetime.utcnow()
    
    # Log request
    logger.info(f"-> {request.method} {request.url.path} from {request.client.host}")
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = (datetime.utcnow() - start_time).total_seconds()
    
    # Log response
    logger.info(f"<- {request.method} {request.url.path} - Status: {response.status_code} - Duration: {duration:.3f}s")
    
    return response

# Initialize processor
processor = LessonProcessor()

# Supabase Client
class SupabaseClient:
    """Client for fetching Zoom transcripts from Supabase"""
    
    def __init__(self):
        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_KEY')
        
        if not self.url or not self.key:
            logger.warning("Supabase credentials not found. Zoom integration disabled.")
            self.client = None
        else:
            try:
                self.client: Client = create_client(self.url, self.key)
                logger.info("Supabase client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase: {e}")
                self.client = None
    
    def fetch_transcript(self, user_id: str, teacher_id: str, class_id: str, date: str) -> Optional[Dict]:
        """Fetch transcript from zoom_summaries table"""
        if not self.client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase client not initialized. Check credentials."
            )
        
        try:
            logger.info(f"Fetching transcript: user={user_id}, teacher={teacher_id}, class={class_id}, date={date}")
            
            response = (
                self.client.table('zoom_summaries')
                .select('*')
                .eq('user_id', user_id)
                .eq('teacher_id', teacher_id)
                .eq('class_id', class_id)
                .eq('meeting_date', date)
                .order('processing_completed_at', desc=True)
                .limit(1)
                .execute()
            )
            
            if not response.data:
                return None
            
            transcript_data = response.data[0]
            logger.info(f"Transcript found (ID: {transcript_data.get('id')}, length: {transcript_data.get('transcript_length', 0)})")
            return transcript_data
            
        except Exception as e:
            logger.error(f"Error fetching transcript: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}"
            )
    
    def store_exercises(self, user_id: str, teacher_id: str, class_id: str, 
                       lesson_number: int, exercises: Dict, zoom_summary_id: Optional[int] = None) -> Dict:
        """Store generated exercises in lesson_exercises table"""
        if not self.client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase client not initialized. Check credentials."
            )
        
        try:
            # Calculate quality score
            total_exercises = (
                len(exercises.get('fill_in_blank', [])) + 
                len(exercises.get('flashcards', [])) + 
                len(exercises.get('spelling', []))
            )
            
            exercise_data = {
                'zoom_summary_id': zoom_summary_id,
                'user_id': user_id,
                'teacher_id': teacher_id,
                'class_id': class_id,
                'lesson_number': lesson_number,
                'fill_in_blank': exercises.get('fill_in_blank', []),
                'flashcards': exercises.get('flashcards', []),
                'spelling': exercises.get('spelling', []),
                'quality_score': total_exercises,
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
            
            response = self.client.table('lesson_exercises').insert(exercise_data).execute()
            
            if response.data:
                logger.info(f"Exercises stored successfully (ID: {response.data[0].get('id')})")
                return response.data[0]
            else:
                raise Exception("No data returned from insert")
                
        except Exception as e:
            logger.error(f"Error storing exercises: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to store exercises: {str(e)}"
            )
    
    def get_exercises(self, class_id: str, user_id: Optional[str] = None) -> List[Dict]:
        """Retrieve exercises for a class"""
        if not self.client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase client not initialized. Check credentials."
            )
        
        try:
            query = self.client.table('lesson_exercises').select('*').eq('class_id', class_id)
            
            if user_id:
                query = query.eq('user_id', user_id)
            
            response = query.order('generated_at', desc=True).execute()
            
            logger.info(f"Retrieved {len(response.data)} exercise sets for class {class_id}")
            return response.data
            
        except Exception as e:
            logger.error(f"Error retrieving exercises: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve exercises: {str(e)}"
            )
    
    def health_check(self) -> bool:
        """Check Supabase connection"""
        if not self.client:
            return False
        try:
            self.client.table('zoom_summaries').select('id').limit(1).execute()
            return True
        except:
            return False


# Initialize Supabase client
supabase_client = SupabaseClient()

# Zoom API Configuration
ZOOM_API_BASE = "https://api.zoom.us/v2"

# Zoom Token Manager (Auto-refresh)
class ZoomTokenManager:
    def __init__(self):
        self.client_id = os.getenv('ZOOM_CLIENT_ID', '')
        self.client_secret = os.getenv('ZOOM_CLIENT_SECRET', '')
        self.access_token = os.getenv('ZOOM_ACCESS_TOKEN', '')
        self.refresh_token = os.getenv('ZOOM_REFRESH_TOKEN', '')
        self.token_expires_at = datetime.now(timezone.utc)
    
    def get_token(self) -> str:
        """Get valid access token, auto-refresh if expired"""
        # If token is still valid, return it
        if self.access_token and datetime.now(timezone.utc) < self.token_expires_at:
            return self.access_token
        
        # Token expired, refresh it
        if not self.refresh_token:
            logger.warning("No refresh token available. Using existing access token.")
            return self.access_token
        
        try:
            logger.info("🔄 Refreshing Zoom access token...")
            
            import base64
            credentials = f"{self.client_id}:{self.client_secret}"
            encoded = base64.b64encode(credentials.encode()).decode()
            
            response = requests.post(
                "https://zoom.us/oauth/token",
                headers={
                    "Authorization": f"Basic {encoded}",
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token
                }
            )
            
            if response.status_code == 200:
                tokens = response.json()
                self.access_token = tokens['access_token']
                self.refresh_token = tokens.get('refresh_token', self.refresh_token)
                # Set expiry 5 minutes before actual expiry for safety
                expires_in = tokens.get('expires_in', 3600)
                self.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in - 300)
                
                logger.info(f"[OK] Zoom token refreshed successfully (expires in {expires_in}s)")
                return self.access_token
            else:
                logger.error(f"Failed to refresh token: {response.status_code} - {response.text}")
                return self.access_token
                
        except Exception as e:
            logger.error(f"Error refreshing Zoom token: {e}")
            return self.access_token

# Initialize Zoom token manager
zoom_token_manager = ZoomTokenManager()

def get_zoom_token() -> str:
    """Get current valid Zoom access token"""
    return zoom_token_manager.get_token()

# AssemblyAI Configuration
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY", "")
ASSEMBLYAI_BASE_URL = os.getenv("ASSEMBLYAI_BASE_URL", "https://api.assemblyai.com/v2")

if ASSEMBLYAI_API_KEY:
    aai.settings.api_key = ASSEMBLYAI_API_KEY
    logger.info("[OK] AssemblyAI initialized successfully")
else:
    logger.warning("[WARNING] ASSEMBLYAI_API_KEY not found. Audio transcription will be disabled.")
    
# Zoom Helper Functions
def validate_time(time_str: str) -> Optional[str]:
    """Validate and format time string to HH:MM format."""
    if not time_str:
        return None
    match = re.match(r'^([01]?[0-9]|2[0-3]):([0-5][0-9])$', time_str)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        return f"{hours:02d}:{minutes:02d}"
    raise ValueError(f"Invalid time format: {time_str}. Use HH:MM format.")


def get_utc_time_from_iso(iso_string: str) -> Optional[str]:
    """Extract UTC time from ISO string."""
    try:
        dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        return f"{dt.hour:02d}:{dt.minute:02d}"
    except Exception as e:
        logger.error(f"Time parsing error: {e}")
        return None


def time_to_minutes(time_str: str) -> Optional[int]:
    """Convert HH:MM to total minutes."""
    if not time_str:
        return None
    hours, minutes = map(int, time_str.split(':'))
    return hours * 60 + minutes


def is_time_in_range(meeting_time: str, start_time: Optional[str], end_time: Optional[str]) -> bool:
    """Check if meeting time falls within the specified range."""
    if not start_time or not end_time:
        return True
    
    meeting_time_str = get_utc_time_from_iso(meeting_time)
    if not meeting_time_str:
        return False
    
    meeting_minutes = time_to_minutes(meeting_time_str)
    start_minutes = time_to_minutes(start_time)
    end_minutes = time_to_minutes(end_time)
    
    if None in (meeting_minutes, start_minutes, end_minutes):
        return False
    
    if end_minutes < start_minutes:
        return meeting_minutes >= start_minutes or meeting_minutes < end_minutes
    else:
        return start_minutes <= meeting_minutes < end_minutes


def has_audio_transcript(recording_files: List[Dict]) -> Optional[Dict]:
    """Check for audio transcript files."""
    if not recording_files:
        return None
    
    for file in recording_files:
        rec_type = (file.get('recording_type') or '').lower()
        file_type = (file.get('file_type') or '').lower()
        
        if 'audio_transcript' in rec_type or 'transcript' in rec_type:
            return file
        if file_type in ['vtt', 'txt']:
            return file
    return None


def has_audio_files(recording_files: List[Dict]) -> Optional[Dict]:
    """Check for audio files."""
    if not recording_files:
        return None
    
    for file in recording_files:
        rec_type = file.get('recording_type', '')
        file_type = (file.get('file_type') or '').lower()
        file_size = file.get('file_size', 0)
        
        if rec_type == 'audio_only':
            return file
        if file_type in ['m4a', 'mp3', 'wav', 'aac', 'ogg']:
            return file
        if rec_type in ['audio_interpretation', 'shared_screen_with_speaker_view']:
            if file_size < 100 * 1024 * 1024:
                return file
    return None


def clean_vtt_transcript(content: str) -> str:
    """Clean VTT transcript format."""
    if 'WEBVTT' not in content and '-->' not in content:
        return content
    
    lines = content.split('\n')
    text_lines = []
    
    for line in lines:
        trimmed = line.strip()
        if (trimmed and 
            not trimmed.startswith('WEBVTT') and 
            '-->' not in trimmed and 
            not trimmed.isdigit() and
            not trimmed.startswith('NOTE') and
            not trimmed.startswith('Kind:') and
            not trimmed.startswith('Language:')):
            text_lines.append(trimmed)
    
    return ' '.join(text_lines).strip()


def fetch_zoom_recordings(teacher_email: str, date: str) -> Dict:
    """Fetch Zoom recordings for a specific teacher and date."""
    token = get_zoom_token()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ZOOM_ACCESS_TOKEN not configured. Please set it in .env file."
        )
    
    url = f"{ZOOM_API_BASE}/users/{teacher_email}/recordings"
    params = {'from': date, 'to': date}
    headers = {'Authorization': f'Bearer {token}'}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Zoom API error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch Zoom recordings: {str(e)}"
        )


def download_zoom_file(download_url: str, response_format: str = 'text'):
    """Download file from Zoom."""
    token = get_zoom_token()
    if not token:
        raise ValueError("ZOOM_ACCESS_TOKEN not configured")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'User-Agent': 'lesson-content-extractor/1.0'
    }
    
    response = requests.get(download_url, headers=headers, timeout=300)
    response.raise_for_status()
    
    return response.text if response_format == 'text' else response.content

def transcribe_audio_with_assemblyai(audio_url: str) -> Dict:
    """Transcribe audio file using AssemblyAI."""
    if not ASSEMBLYAI_API_KEY:
        raise ValueError("ASSEMBLYAI_API_KEY not configured")
    
    try:
        logger.info("Starting AssemblyAI transcription...")
        
        # Configure transcription settings
        config = aai.TranscriptionConfig(
            language_code="en",  # Change if needed
            punctuate=True,
            format_text=True,
            speaker_labels=True  # Enable speaker diarization for Teacher/Student labels
        )
        
        transcriber = aai.Transcriber(config=config)
        
        # Transcribe from URL (AssemblyAI will download the file)
        transcript = transcriber.transcribe(audio_url)
        
        # Wait for transcription to complete
        if transcript.status == aai.TranscriptStatus.error:
            raise Exception(f"Transcription failed: {transcript.error}")
        
        logger.info(f"Transcription completed ({len(transcript.text)} characters)")
        
        return {
            'text': transcript.text,
            'status': 'completed',
            'duration': transcript.audio_duration,  # in seconds
            'confidence': getattr(transcript, 'confidence', None),
            'words_count': len(transcript.words) if transcript.words else 0
        }
        
    except Exception as e:
        logger.error(f"AssemblyAI transcription error: {e}")
        raise Exception(f"Transcription failed: {str(e)}")

        
def process_recording_background(recording: Dict, user_params: Dict):
    """Background task to process a single recording."""
    try:
        logger.info(f"📄 Processing recording: {recording['meeting_id']}")
        
        # Download transcript from Zoom
        if recording['processing_type'] == 'TRANSCRIPT_DOWNLOAD':
            transcript_content = download_zoom_file(
                recording['target_file']['download_url'], 
                response_format='text'
            )
            clean_transcript = clean_vtt_transcript(transcript_content)
            
            if len(clean_transcript) < 10:
                clean_transcript = f"Error: Transcript appears empty.\n\nRaw: {transcript_content}"
            
            meeting_date = datetime.fromisoformat(
                recording['start_time'].replace('Z', '+00:00')
            ).strftime('%Y-%m-%d')
            
            result = {
                **recording,
                **user_params,
                'meeting_date': meeting_date,
                'transcript': clean_transcript,
                'transcript_length': len(clean_transcript),
                'transcription_source': 'zoom_native_transcript',
                'processing_mode': 'transcript_download',
                'transcription_status': 'completed',
                'transcription_completed_at': datetime.now(timezone.utc).isoformat()
            }
        
        # Audio transcription with AssemblyAI
        elif recording['processing_type'] == 'AUDIO_TRANSCRIPTION':
            if not ASSEMBLYAI_API_KEY:
                logger.error("AssemblyAI API key not configured")
                return
            
            logger.info(f"Starting audio transcription for meeting {recording['meeting_id']}")
            
            # Get audio file download URL (with Zoom token)
            audio_url = recording['target_file']['download_url']
            
            # Download audio file first (AssemblyAI needs accessible URL or file upload)
            audio_content = download_zoom_file(audio_url, response_format='binary')
            
            # Save temporarily
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.m4a') as tmp_file:
                tmp_file.write(audio_content)
                tmp_audio_path = tmp_file.name
            
            try:
                # Transcribe with AssemblyAI
                transcription_result = transcribe_audio_with_assemblyai(tmp_audio_path)
                
                meeting_date = datetime.fromisoformat(
                    recording['start_time'].replace('Z', '+00:00')
                ).strftime('%Y-%m-%d')
                
                result = {
                    **recording,
                    **user_params,
                    'meeting_date': meeting_date,
                    'transcript': transcription_result['text'],
                    'transcript_length': len(transcription_result['text']),
                    'transcription_source': 'assemblyai',
                    'processing_mode': 'audio_transcription',
                    'transcription_status': transcription_result['status'],
                    'transcription_confidence': transcription_result.get('confidence'),
                    'audio_duration_seconds': transcription_result.get('duration'),
                    'transcription_completed_at': datetime.now(timezone.utc).isoformat()
                }
                
                logger.info(f"Audio transcribed successfully ({len(transcription_result['text'])} chars)")
                
            finally:
                # Clean up temp file
                import os
                if os.path.exists(tmp_audio_path):
                    os.remove(tmp_audio_path)
        
        else:
            logger.warning(f"Unknown processing type: {recording.get('processing_type')}")
            return
        
        # Store in Supabase
        if supabase_client.client:
            supabase_data = {
                'user_id': result.get('user_id'),
                'teacher_id': result.get('teacher_id'),
                'class_id': result.get('class_id'),
                'teacher_email': result.get('teacher_email'),
                'meeting_id': result['meeting_id'],
                'meeting_topic': result.get('topic'),
                'meeting_date': result['meeting_date'],
                'meeting_time': result.get('meeting_time'),
                'transcript': result['transcript'],
                'transcript_length': result['transcript_length'],
                'transcript_source': result['transcription_source'],
                'transcription_status': result['transcription_status'],
                'processing_mode': result['processing_mode'],
                'transcription_service': 'Zoom' if result['transcription_source'] == 'zoom_native_transcript' else 'AssemblyAI',
                'transcription_confidence': result.get('transcription_confidence'),
                'audio_duration_seconds': result.get('audio_duration_seconds'),
                'processing_completed_at': datetime.now(timezone.utc).isoformat()
            }
            
            response = supabase_client.client.table('zoom_summaries').insert(supabase_data).execute()
            logger.info(f"Stored in Supabase: {response.data[0].get('id') if response.data else 'unknown'}")
        
    except Exception as e:
        logger.error(f"Error processing recording {recording.get('meeting_id')}: {e}")

# Request/Response Models
class TranscriptInput(BaseModel):
    """Single transcript input"""
    transcript: str = Field(..., min_length=10, description="Lesson transcript text")
    lesson_number: int = Field(..., ge=1, description="Lesson number (1-based)")
    
    @field_validator('transcript')
    @classmethod
    def validate_transcript(cls, v):
        if not v.strip():
            raise ValueError('Transcript cannot be empty or whitespace only')
        return v


class MultipleTranscriptsInput(BaseModel):
    """Multiple transcripts input"""
    transcripts: List[TranscriptInput] = Field(..., min_items=1, max_items=10)


class ZoomTranscriptInput(BaseModel):
    """Input for fetching and processing Zoom transcript"""
    user_id: str = Field(..., description="User identifier")
    teacher_id: str = Field(..., description="Teacher identifier")
    class_id: str = Field(..., description="Class identifier")
    date: str = Field(..., description="Date in YYYY-MM-DD format", pattern=r'^\d{4}-\d{2}-\d{2}$')
    lesson_number: Optional[int] = Field(1, ge=1, description="Lesson number (defaults to 1)")
    
    @field_validator('date')
    @classmethod
    def validate_date(cls, v):
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')


class LessonExercises(BaseModel):
    """Exercises for a single lesson"""
    lesson_number: int
    fill_in_blank: List[Dict]
    flashcards: List[Dict]
    spelling: List[Dict]
    total_exercises: int
    quality_passed: bool


class ProcessingResponse(BaseModel):
    """Response for processing request"""
    success: bool
    message: str
    lessons: List[LessonExercises]
    processing_time_seconds: float
    timestamp: str


class ZoomProcessingResponse(BaseModel):
    """Response for Zoom transcript processing"""
    success: bool
    message: str
    lesson: Optional[LessonExercises]
    zoom_metadata: Optional[Dict]
    processing_time_seconds: float
    timestamp: str


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    version: str


# API Endpoints
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Lesson Content Extractor API",
        "version": "1.0.0",
        "status": "active",
        "documentation": "/docs",
        "endpoints": {
            "health": "/health",
            "process_single": "/api/v1/process",
            "process_multiple": "/api/v1/process/batch",
            "process_zoom": "/api/v1/process-zoom-lesson"
        },
        "zoom_integration": {
            "enabled": supabase_client.client is not None,
            "status": "active" if supabase_client.client else "disabled"
        }
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version="1.0.0"
    )


@app.post("/api/v1/process", response_model=ProcessingResponse, tags=["Processing"])
async def process_single_lesson(input_data: TranscriptInput):
    """
    Process a single lesson transcript and return structured exercises
    
    **Parameters:**
    - transcript: The lesson transcript text (minimum 10 characters)
    - lesson_number: Lesson identifier (positive integer)
    
    **Returns:**
    - Structured exercises (fill-in-blank, flashcards, spelling)
    - Quality validation results
    - Processing metadata
    """
    try:
        start_time = datetime.utcnow()
        logger.info(f"Processing lesson {input_data.lesson_number}")
        
        # Process the lesson
        result = processor.process_lesson(
            input_data.transcript,
            input_data.lesson_number
        )
        
        # Calculate total exercises
        total = len(result['fill_in_blank']) + len(result['flashcards']) + len(result['spelling'])
        
        # Check quality
        quality_passed = 8 <= total <= 12
        
        # Build response
        lesson_data = LessonExercises(
            lesson_number=input_data.lesson_number,
            fill_in_blank=result['fill_in_blank'],
            flashcards=result['flashcards'],
            spelling=result['spelling'],
            total_exercises=total,
            quality_passed=quality_passed
        )
        
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()
        
        logger.info(f"Lesson {input_data.lesson_number} processed successfully in {processing_time:.2f}s")
        
        return ProcessingResponse(
            success=True,
            message=f"Lesson {input_data.lesson_number} processed successfully",
            lessons=[lesson_data],
            processing_time_seconds=round(processing_time, 2),
            timestamp=end_time.isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error processing lesson {input_data.lesson_number}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing lesson: {str(e)}"
        )


@app.post("/api/v1/process-zoom-lesson", response_model=ZoomProcessingResponse, tags=["Zoom Integration"])
async def process_zoom_lesson(input_data: ZoomTranscriptInput):
    """
    Fetch Zoom transcript from Supabase and process into exercises
    
    **Parameters:**
    - user_id: User identifier
    - teacher_id: Teacher identifier  
    - class_id: Class identifier
    - date: Meeting date in YYYY-MM-DD format
    - lesson_number: Optional lesson number (defaults to 1)
    
    **Returns:**
    - Structured exercises (fill-in-blank, flashcards, spelling)
    - Zoom meeting metadata
    - Processing metadata
    """
    try:
        start_time = datetime.utcnow()
        logger.info(
            f"Processing Zoom lesson: user={input_data.user_id}, "
            f"teacher={input_data.teacher_id}, class={input_data.class_id}, date={input_data.date}"
        )
        
        # Fetch transcript from Supabase
        transcript_data = supabase_client.fetch_transcript(
            user_id=input_data.user_id,
            teacher_id=input_data.teacher_id,
            class_id=input_data.class_id,
            date=input_data.date
        )
        
        if not transcript_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No transcript found for the specified parameters. "
                       f"Please ensure the Zoom meeting was recorded and processed."
            )
        
        # Extract transcript text
        transcript_text = transcript_data.get('transcript', '')
        
        if not transcript_text or len(transcript_text.strip()) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transcript is empty or too short to process"
            )
        
        logger.info(f"Transcript fetched successfully (length: {len(transcript_text)} chars)")
        
        # Truncate very long transcripts to prevent timeout
        if len(transcript_text) > 5000:
            logger.warning(f"Transcript too long ({len(transcript_text)} chars), truncating to 3000 chars")
            transcript_text = transcript_text[:3000] + "..."
        
        # Process the transcript
        result = processor.process_lesson(
            transcript_text,
            input_data.lesson_number
        )
        
        # Calculate total exercises
        total = len(result['fill_in_blank']) + len(result['flashcards']) + len(result['spelling'])
        quality_passed = 8 <= total <= 12
        
        # Store exercises in Supabase
        stored_result = supabase_client.store_exercises(
            user_id=input_data.user_id,
            teacher_id=input_data.teacher_id,
            class_id=input_data.class_id,
            lesson_number=input_data.lesson_number,
            exercises=result,
            zoom_summary_id=transcript_data.get('id')
        )
        
        logger.info(f"Exercises stored in Supabase (ID: {stored_result.get('id')})")
        
        # Build lesson exercises
        lesson_data = LessonExercises(
            lesson_number=input_data.lesson_number,
            fill_in_blank=result['fill_in_blank'],
            flashcards=result['flashcards'],
            spelling=result['spelling'],
            total_exercises=total,
            quality_passed=quality_passed
        )
        
        # Build Zoom metadata
        zoom_metadata = {
            "meeting_id": transcript_data.get('meeting_id'),
            "meeting_topic": transcript_data.get('meeting_topic'),
            "meeting_date": transcript_data.get('meeting_date'),
            "meeting_time": transcript_data.get('meeting_time'),
            "teacher_email": transcript_data.get('teacher_email'),
            "transcript_source": transcript_data.get('transcript_source'),
            "transcript_length": transcript_data.get('transcript_length'),
            "transcription_service": transcript_data.get('transcription_service')
        }
        
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()
        
        logger.info(
            f"Zoom lesson processed successfully in {processing_time:.2f}s "
            f"({total} exercises generated)"
        )
        
        return ZoomProcessingResponse(
            success=True,
            message=f"Zoom lesson processed successfully. Generated {total} exercises.",
            lesson=lesson_data,
            zoom_metadata=zoom_metadata,
            processing_time_seconds=round(processing_time, 2),
            timestamp=end_time.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing Zoom lesson: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing Zoom lesson: {str(e)}"
        )


@app.get("/api/v1/get-transcript", tags=["Zoom Integration"])
async def get_transcript(
    user_id: str,
    teacher_id: str,
    class_id: str,
    date: str
):
    """
    Get raw transcript from Supabase without processing
    
    **Parameters:**
    - user_id: User identifier
    - teacher_id: Teacher identifier
    - class_id: Class identifier
    - date: Meeting date in YYYY-MM-DD format
    
    **Returns:**
    - Raw transcript data from Supabase
    """
    try:
        logger.info(f"Fetching transcript: user={user_id}, teacher={teacher_id}, class={class_id}, date={date}")
        
        transcript_data = supabase_client.fetch_transcript(
            user_id=user_id,
            teacher_id=teacher_id,
            class_id=class_id,
            date=date
        )
        
        if not transcript_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No transcript found for the specified parameters."
            )
        
        return {
            "success": True,
            "data": transcript_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching transcript: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching transcript: {str(e)}"
        )


class ZoomRecordingInput(BaseModel):
    """Input for fetching Zoom recordings"""
    teacher_email: str = Field(..., description="Teacher's Zoom email")
    user_id: str = Field(..., description="User identifier")
    teacher_id: str = Field(..., description="Teacher identifier")
    class_id: str = Field(..., description="Class identifier")
    date: str = Field(..., description="Date in YYYY-MM-DD format", pattern=r'^\d{4}-\d{2}-\d{2}$')
    start_time: Optional[str] = Field(None, description="Start time in HH:MM format")
    end_time: Optional[str] = Field(None, description="End time in HH:MM format")


@app.post("/api/v1/fetch-zoom-recordings", tags=["Zoom Integration"])
async def fetch_zoom_recordings_endpoint(input_data: ZoomRecordingInput, background_tasks: BackgroundTasks):
    """
    Fetch Zoom recordings and process them in background
    
    **Parameters:**
    - teacher_email: Teacher's Zoom email
    - user_id: User identifier
    - teacher_id: Teacher identifier
    - class_id: Class identifier
    - date: Meeting date in YYYY-MM-DD format
    - start_time: Optional start time filter (HH:MM)
    - end_time: Optional end time filter (HH:MM)
    
    **Returns:**
    - Status of recording fetch and processing
    """
    try:
        logger.info(f"Fetching Zoom recordings for {input_data.teacher_email} on {input_data.date}")
        
        # Validate time format
        formatted_start_time = validate_time(input_data.start_time) if input_data.start_time else None
        formatted_end_time = validate_time(input_data.end_time) if input_data.end_time else None
        
        # Fetch Zoom recordings
        zoom_data = fetch_zoom_recordings(input_data.teacher_email, input_data.date)
        meetings = zoom_data.get('meetings', [])
        
        logger.info(f"Found {len(meetings)} total meetings")
        
        if not meetings:
            return {
                "success": False,
                "message": "No Zoom recordings found for the specified date",
                "details": {
                    "teacher_email": input_data.teacher_email,
                    "date": input_data.date,
                    "total_meetings": 0
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Filter recordings
        filtered_recordings = []
        for meeting in meetings:
            if not meeting.get('recording_files'):
                continue
            
            meeting_date = datetime.fromisoformat(
                meeting['start_time'].replace('Z', '+00:00')
            ).strftime('%Y-%m-%d')
            
            if input_data.date and meeting_date != input_data.date:
                continue
            
            if not is_time_in_range(meeting['start_time'], formatted_start_time, formatted_end_time):
                continue
            
            transcript_file = has_audio_transcript(meeting['recording_files'])
            audio_file = has_audio_files(meeting['recording_files'])
            
            if transcript_file or audio_file:
                meeting_time = get_utc_time_from_iso(meeting['start_time'])
                filtered_recordings.append({
                    'meeting_id': meeting['id'],
                    'topic': meeting.get('topic', 'Untitled Meeting'),
                    'start_time': meeting['start_time'],
                    'meeting_time': meeting_time,
                    'processing_type': 'TRANSCRIPT_DOWNLOAD' if transcript_file else 'AUDIO_TRANSCRIPTION',
                    'target_file': transcript_file or audio_file,
                    'files': meeting['recording_files']
                })
        
        logger.info(f"Filtered to {len(filtered_recordings)} matching recordings")
        
        if not filtered_recordings:
            return {
                "success": False,
                "message": "No audio recordings found for the specified criteria",
                "details": {
                    "teacher_email": input_data.teacher_email,
                    "date": input_data.date,
                    "time_range": f"{formatted_start_time} - {formatted_end_time}" if formatted_start_time else "No time filter",
                    "total_meetings": len(meetings),
                    "filtered_recordings": 0
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Process recordings in background
        user_params = {
            'teacher_email': input_data.teacher_email,
            'user_id': input_data.user_id,
            'teacher_id': input_data.teacher_id,
            'class_id': input_data.class_id,
            'formatted_date': input_data.date,
            'start_time': formatted_start_time,
            'end_time': formatted_end_time
        }
        
        for recording in filtered_recordings:
            background_tasks.add_task(process_recording_background, recording, user_params)
        
        return {
            "success": True,
            "message": "Zoom recordings found, processing started in background",
            "status": "processing_started",
            "data": {
                "recordings_count": len(filtered_recordings),
                "user_id": input_data.user_id,
                "teacher_id": input_data.teacher_id,
                "class_id": input_data.class_id,
                "teacher_email": input_data.teacher_email,
                "date": input_data.date,
                "time_range": f"{formatted_start_time} - {formatted_end_time}" if formatted_start_time else "No time filter",
                "estimated_processing_time": "2-3 minutes",
                "recordings": [
                    {
                        "meeting_id": r['meeting_id'],
                        "topic": r['topic'],
                        "meeting_time": r['meeting_time'],
                        "processing_type": r['processing_type']
                    }
                    for r in filtered_recordings
                ]
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching Zoom recordings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching Zoom recordings: {str(e)}"
        )


@app.get("/api/v1/exercises", tags=["Integration"])
async def get_exercises(
    class_id: str,
    user_id: Optional[str] = None
):
    """
    Get exercises for a class (for backend team to import)
    
    **Parameters:**
    - class_id: Class identifier (required)
    - user_id: User identifier (optional filter)
    
    **Returns:**
    - List of exercise sets with flashcards, fill-in-blank, and spelling
    """
    try:
        logger.info(f"Retrieving exercises: class={class_id}, user={user_id}")
        
        exercises = supabase_client.get_exercises(class_id=class_id, user_id=user_id)
        
        if not exercises:
            return {
                "success": True,
                "message": "No exercises found for the specified class",
                "data": [],
                "count": 0,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        return {
            "success": True,
            "message": f"Retrieved {len(exercises)} exercise set(s)",
            "data": exercises,
            "count": len(exercises),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving exercises: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving exercises: {str(e)}"
        )


@app.post("/api/v1/process/batch", response_model=ProcessingResponse, tags=["Processing"])
async def process_multiple_lessons(input_data: MultipleTranscriptsInput):
    """
    Process multiple lesson transcripts in batch
    
    **Parameters:**
    - transcripts: List of transcript objects (1-10 lessons)
    
    **Returns:**
    - Structured exercises for all lessons
    - Aggregated processing metadata
    """
    try:
        start_time = datetime.utcnow()
        logger.info(f"Processing batch of {len(input_data.transcripts)} lessons")
        
        lessons_data = []
        
        for transcript_input in input_data.transcripts:
            # Process each lesson
            result = processor.process_lesson(
                transcript_input.transcript,
                transcript_input.lesson_number
            )
            
            total = len(result['fill_in_blank']) + len(result['flashcards']) + len(result['spelling'])
            quality_passed = 8 <= total <= 12
            
            lesson_data = LessonExercises(
                lesson_number=transcript_input.lesson_number,
                fill_in_blank=result['fill_in_blank'],
                flashcards=result['flashcards'],
                spelling=result['spelling'],
                total_exercises=total,
                quality_passed=quality_passed
            )
            lessons_data.append(lesson_data)
        
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()
        
        logger.info(f"Batch processing completed in {processing_time:.2f}s")
        
        return ProcessingResponse(
            success=True,
            message=f"Successfully processed {len(lessons_data)} lessons",
            lessons=lessons_data,
            processing_time_seconds=round(processing_time, 2),
            timestamp=end_time.isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error in batch processing: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in batch processing: {str(e)}"
        )


# Error handlers
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"success": False, "error": str(exc)}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"success": False, "error": "Internal server error"}
    )

# ============================================================
# GAMES API ENDPOINTS
# ============================================================

from src.games.word_lists import WordListsService
from src.games.flashcards import FlashcardsService
from src.games.models import (
    WordListCreate, WordListUpdate, WordCreate, WordUpdate,
    SessionStart, PracticeResult, SessionComplete, FavoriteToggle
)

# Initialize games services
word_lists_service = WordListsService(supabase_client.client)
flashcards_service = FlashcardsService(supabase_client.client)

# Word Lists Endpoints
@app.get("/v1/word-lists", tags=["Word Lists"])
@limiter.limit("60/minute")
async def get_word_lists(
    request: Request,
    user_id: str,
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    favorite: Optional[bool] = None,
    sort: str = "created_at"
):
    """Get all word lists for a user"""
    try:
        logger.info(f"[FETCH] Fetching word lists for user: {user_id}")
        result = word_lists_service.get_word_lists(user_id, page, limit, search, favorite, sort)
        logger.info(f"[OK] Returned {len(result['data'])} word lists")
        return result
    except Exception as e:
        logger.error(f"[ERROR] Error getting word lists: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/word-lists", tags=["Word Lists"], status_code=201)
@limiter.limit("30/minute")
async def create_word_list(request: Request, data: WordListCreate, user_id: str):
    """Create a new word list"""
    try:
        logger.info(f"[CREATE] Creating word list '{data.name}' for user: {user_id}")
        result = word_lists_service.create_word_list(user_id, data.name, data.description)
        logger.info(f"[OK] Word list created: {result['id']}")
        return result
    except Exception as e:
        logger.error(f"[ERROR] Error creating word list: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/word-lists/{list_id}", tags=["Word Lists"])
@limiter.limit("60/minute")
async def get_word_list(request: Request, list_id: str, user_id: str, include: Optional[str] = None):
    """Get a single word list"""
    try:
        logger.info(f"[FETCH] Fetching word list {list_id} for user: {user_id}")
        include_words = include == "words"
        result = word_lists_service.get_word_list(list_id, user_id, include_words)
        if not result:
            logger.warning(f"[WARNING] Word list {list_id} not found")
            raise HTTPException(status_code=404, detail="Word list not found")
        logger.info(f"[OK] Word list retrieved: {list_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Error getting word list: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/v1/word-lists/{list_id}", tags=["Word Lists"])
@limiter.limit("30/minute")
async def update_word_list(request: Request, list_id: str, user_id: str, data: WordListUpdate):
    """Update a word list"""
    try:
        logger.info(f"[UPDATE] Updating word list {list_id} for user: {user_id}")
        updates = data.dict(exclude_unset=True)
        result = word_lists_service.update_word_list(list_id, user_id, updates)
        if not result:
            raise HTTPException(status_code=404, detail="Word list not found")
        logger.info(f"[OK] Word list updated: {list_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Error updating word list: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/v1/word-lists/{list_id}", tags=["Word Lists"], status_code=204)
@limiter.limit("30/minute")
async def delete_word_list(request: Request, list_id: str, user_id: str):
    """Delete a word list"""
    try:
        logger.info(f"[DELETE] Deleting word list {list_id} for user: {user_id}")
        word_lists_service.delete_word_list(list_id, user_id)
        logger.info(f"[OK] Word list deleted: {list_id}")
        return None
    except Exception as e:
        logger.error(f"[ERROR] Error deleting word list: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/word-lists/{list_id}/words", tags=["Words"], status_code=201)
@limiter.limit("60/minute")
async def add_word(request: Request, list_id: str, user_id: str, data: WordCreate):
    """Add a word to a list"""
    try:
        logger.info(f"[ADD] Adding word '{data.word}' to list {list_id}")
        result = word_lists_service.add_word(list_id, user_id, data.word, data.translation, data.notes)
        logger.info(f"[OK] Word added: {result['id']}")
        return result
    except ValueError as e:
        logger.warning(f"[WARNING] Access denied: {e}")
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"[ERROR] Error adding word: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/v1/word-lists/{list_id}/words/{word_id}", tags=["Words"])
@limiter.limit("60/minute")
async def update_word(request: Request, list_id: str, word_id: str, user_id: str, data: WordUpdate):
    """Update a word"""
    try:
        logger.info(f"[UPDATE] Updating word {word_id} in list {list_id}")
        updates = data.dict(exclude_unset=True)
        result = word_lists_service.update_word(list_id, word_id, user_id, updates)
        if not result:
            raise HTTPException(status_code=404, detail="Word not found")
        logger.info(f"[OK] Word updated: {word_id}")
        return result
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Error updating word: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/v1/word-lists/{list_id}/words/{word_id}", tags=["Words"], status_code=204)
@limiter.limit("60/minute")
async def delete_word(request: Request, list_id: str, word_id: str, user_id: str):
    """Delete a word"""
    try:
        logger.info(f"[DELETE] Deleting word {word_id} from list {list_id}")
        word_lists_service.delete_word(list_id, word_id, user_id)
        logger.info(f"[OK] Word deleted: {word_id}")
        return None
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"[ERROR] Error deleting word: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/word-lists/{list_id}/favorite", tags=["Word Lists"])
@limiter.limit("60/minute")
async def toggle_list_favorite(request: Request, list_id: str, user_id: str, data: FavoriteToggle):
    """Toggle favorite status for a word list"""
    try:
        logger.info(f"[FAVORITE] Toggling list {list_id} favorite to {data.isFavorite}")
        result = word_lists_service.toggle_list_favorite(list_id, user_id, data.isFavorite)
        logger.info(f"[OK] List favorite toggled: {list_id}")
        return result
    except ValueError as e:
        logger.warning(f"[WARNING] Access denied: {e}")
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"[ERROR] Error toggling list favorite: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/word-lists/{list_id}/words/{word_id}/favorite", tags=["Words"])
@limiter.limit("60/minute")
async def toggle_word_favorite(request: Request, list_id: str, word_id: str, user_id: str, data: FavoriteToggle):
    """Toggle favorite status for a word"""
    try:
        logger.info(f"[FAVORITE] Toggling word {word_id} favorite to {data.isFavorite}")
        result = word_lists_service.toggle_word_favorite(list_id, word_id, user_id, data.isFavorite)
        logger.info(f"[OK] Word favorite toggled: {word_id}")
        return result
    except ValueError as e:
        logger.warning(f"[WARNING] Access denied: {e}")
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"[ERROR] Error toggling word favorite: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/user/stats", tags=["User Stats"])
@limiter.limit("60/minute")
async def get_user_stats(request: Request, user_id: str):
    """Get user stats"""
    try:
        logger.info(f"[FETCH] Fetching user stats for user: {user_id}")
        result = word_lists_service.get_user_stats(user_id)
        logger.info(f"[OK] User stats retrieved: {user_id}")
        return result
    except Exception as e:
        logger.error(f"[ERROR] Error getting user stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/flashcards/stats/me", tags=["Analytics"])
@limiter.limit("60/minute")
async def get_flashcard_stats(request: Request, user_id: str):
    """Get flashcard analytics for the current user"""
    try:
        logger.info(f"[FETCH] Fetching flashcard stats for user: {user_id}")
        result = flashcards_service.get_user_stats(user_id)
        logger.info(f"[OK] Flashcard stats retrieved: {user_id}")
        return result
    except Exception as e:
        logger.error(f"[ERROR] Error getting flashcard stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# FLASHCARDS GAME ENDPOINTS
# ============================================================

@app.post("/v1/flashcards/sessions", tags=["Flashcards"], status_code=201)
@limiter.limit("30/minute")
async def start_flashcard_session(request: Request, data: SessionStart, user_id: str):
    """Start a new flashcard practice session"""
    try:
        logger.info(f"[START] Starting flashcard session for user: {user_id}, list: {data.wordListId}")
        result = flashcards_service.start_session(user_id, data.wordListId, data.selectedWordIds)
        logger.info(f"[OK] Flashcard session started: {result['id']}")
        return result
    except ValueError as e:
        logger.warning(f"[WARNING] Invalid request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[ERROR] Error starting flashcard session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/flashcards/sessions/{session_id}", tags=["Flashcards"])
@limiter.limit("60/minute")
async def get_flashcard_session(request: Request, session_id: str, user_id: str):
    """Get flashcard session details"""
    try:
        logger.info(f"[FETCH] Fetching flashcard session: {session_id}")
        result = flashcards_service.get_session(session_id, user_id)
        if not result:
            logger.warning(f"[WARNING] Session {session_id} not found")
            raise HTTPException(status_code=404, detail="Session not found")
        logger.info(f"[OK] Session retrieved: {session_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Error getting flashcard session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/flashcards/sessions/{session_id}/results", tags=["Flashcards"])
@limiter.limit("120/minute")
async def record_flashcard_result(request: Request, session_id: str, user_id: str, data: PracticeResult):
    """Record a practice result for a flashcard"""
    try:
        logger.info(f"[RECORD] Recording result for session: {session_id}, word: {data.wordId}, correct: {data.isCorrect}")
        result = flashcards_service.record_result(
            session_id, user_id, data.wordId, data.isCorrect, data.attempts, data.timeSpent
        )
        logger.info(f"[OK] Result recorded for word: {data.wordId}")
        return result
    except ValueError as e:
        logger.warning(f"[WARNING] Invalid result: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[ERROR] Error recording flashcard result: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/flashcards/sessions/{session_id}/complete", tags=["Flashcards"])
@limiter.limit("30/minute")
async def complete_flashcard_session(request: Request, session_id: str, user_id: str, data: Optional[SessionComplete] = None):
    """Complete a flashcard session"""
    try:
        logger.info(f"[COMPLETE] Completing flashcard session: {session_id}")
        final_progress = data.progress.dict() if data and data.progress else None
        result = flashcards_service.complete_session(session_id, user_id, final_progress)
        logger.info(f"[OK] Session completed: {session_id}")
        return result
    except ValueError as e:
        logger.warning(f"[WARNING] Invalid completion: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[ERROR] Error completing flashcard session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")