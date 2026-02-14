"""Production-ready FastAPI application for lesson content extraction"""

import os
import re
import time
from threading import Thread
from typing import List, Dict, Optional

import assemblyai as aai
import logging
from logging.handlers import RotatingFileHandler
import requests
from datetime import datetime, timedelta

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status, BackgroundTasks, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from supabase import create_client, Client
import json
import uuid
import mysql.connector
from mysql.connector import pooling
from mysql.connector import Error as MySQLError

from src.middleware import limiter, rate_limit_exceeded_handler
from src.main import LessonProcessor
from src.utils.time_utils import utc_now, utc_now_iso

load_dotenv()

# Configure comprehensive logging with rotation
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(
            'api.log',
            maxBytes=10*1024*1024,  # 10MB per file
            backupCount=5  # Keep 5 backup files
        )
    ]
)
logger = logging.getLogger(__name__)

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
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

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
    start_time = utc_now()

    # Log request
    logger.info(f"-> {request.method} {request.url.path} from {request.client.host}")

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration = (utc_now() - start_time).total_seconds()

    # Log response
    logger.info(f"<- {request.method} {request.url.path} - Status: {response.status_code} - Duration: {duration:.3f}s")

    return response

# Initialize processor
processor = LessonProcessor()
logger.info("LessonProcessor initialized")

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

    def fetch_transcript(self, user_id: str, teacher_id: str, class_id: str, date: str,
                        meeting_time: Optional[str] = None, start_time: Optional[str] = None,
                        end_time: Optional[str] = None) -> Optional[Dict]:
        """Fetch transcript from zoom_summaries table with optional time filtering"""
        if not self.client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase client not initialized. Check credentials."
            )

        try:
            logger.info(f"Fetching transcript: user={user_id}, teacher={teacher_id}, class={class_id}, date={date}, time={meeting_time}")

            query = (
                self.client.table('zoom_summaries')
                .select('*')
                .eq('user_id', user_id)
                .eq('teacher_id', teacher_id)
                .eq('class_id', class_id)
                .eq('meeting_date', date)
            )

            # Add time filtering if provided
            if meeting_time:
                query = query.eq('meeting_time', meeting_time)
            elif start_time and end_time:
                query = query.gte('meeting_time', start_time).lte('meeting_time', end_time)

            response = query.order('processing_completed_at', desc=True).limit(1).execute()

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
                'generated_at': utc_now_iso()
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

# ============================================
# MySQL Connection Pool
# ============================================

mysql_config = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER"),
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": os.getenv("MYSQL_DATABASE", "tulkka9"),
    "pool_name": "tulkka_game_pool",
    "pool_size": 10,
    "pool_reset_session": True,
    "autocommit": True,
    "charset": "utf8mb4",
    "collation": "utf8mb4_unicode_ci"
}

mysql_pool = None

try:
    if mysql_config["user"] and mysql_config["password"]:
        mysql_pool = mysql.connector.pooling.MySQLConnectionPool(**mysql_config)
        logger.info(f"✅ MySQL pool created: {mysql_config['host']}:{mysql_config['port']}/{mysql_config['database']}")
    else:
        logger.warning("⚠️ MySQL credentials not provided - game endpoints will not work")
except Exception as e:
    logger.error(f"❌ MySQL pool creation failed: {e}")
    mysql_pool = None


def get_mysql_conn():
    """Get MySQL connection from pool"""
    if not mysql_pool:
        raise HTTPException(
            status_code=503,
            detail="MySQL database not available"
        )
    try:
        return mysql_pool.get_connection()
    except MySQLError as e:
        logger.error(f"Error getting MySQL connection: {e}")
        raise HTTPException(status_code=503, detail="Unable to connect to database")


def execute_query(query: str, params: tuple = None, fetch_one: bool = False, fetch_all: bool = True):
    """Helper to execute MySQL queries"""
    conn = get_mysql_conn()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(query, params or ())

        if fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()
        else:
            # For INSERT/UPDATE/DELETE, commit and return affected rows
            conn.commit()
            result = cursor.rowcount

        cursor.close()
        conn.close()
        return result

    except MySQLError as e:
        conn.rollback()
        cursor.close()
        conn.close()
        logger.error(f"MySQL query error: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# ============================================
# Pydantic Models for Games
# ============================================

class SessionStartInput(BaseModel):
    user_id: str
    game_type: str
    class_id: str
    mode: str = "lesson"
    reference_id: Optional[str] = None
    item_ids: Optional[List[str]] = None


class AnswerResultInput(BaseModel):
    item_id: str
    is_correct: bool
    attempts: int = 1
    time_spent_ms: int
    metadata: Optional[Dict] = None


class SessionCompletionInput(BaseModel):
    final_score: float
    correct_count: int
    incorrect_count: int

# Zoom API Configuration
ZOOM_API_BASE = "https://api.zoom.us/v2"

# Zoom Token Manager (Auto-refresh)
class ZoomTokenManager:
    def __init__(self):
        self.client_id = os.getenv('ZOOM_CLIENT_ID', '')
        self.client_secret = os.getenv('ZOOM_CLIENT_SECRET', '')
        self.access_token = os.getenv('ZOOM_ACCESS_TOKEN', '')
        self.refresh_token = os.getenv('ZOOM_REFRESH_TOKEN', '')
        self.token_expires_at = datetime.now()

    def get_token(self) -> str:
        """Get valid access token, auto-refresh if expired"""
        # If token is still valid, return it
        if self.access_token and datetime.now() < self.token_expires_at:
            return self.access_token

        # Token expired, refresh it
        if not self.refresh_token:
            logger.warning("No refresh token available. Using existing access token.")
            return self.access_token

        try:
            logger.info(" Refreshing Zoom access token...")

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
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)

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
        logger.info(f" Processing recording: {recording['meeting_id']}")

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
                'transcription_completed_at': utc_now_iso()
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
                    'transcription_completed_at': utc_now_iso()
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
                'lesson_number': user_params.get('lesson_number', 1),
                'transcript': result['transcript'],
                'transcript_length': result['transcript_length'],
                'transcript_source': result['transcription_source'],
                'transcription_status': result['transcription_status'],
                'processing_mode': result['processing_mode'],
                'transcription_service': 'Zoom' if result['transcription_source'] == 'zoom_native_transcript' else 'AssemblyAI',
                'transcription_confidence': result.get('transcription_confidence'),
                'audio_duration_seconds': result.get('audio_duration_seconds'),
                'processing_completed_at': utc_now_iso()
            }

            insert_response = supabase_client.client.table('zoom_summaries').insert(supabase_data).execute()
            zoom_summary_id = insert_response.data[0].get('id') if insert_response.data else None
            logger.info(f"Stored in Supabase: {zoom_summary_id if zoom_summary_id else 'unknown'}")

            try:
                pipeline_result = process_lesson_pipeline(
                    transcript_text=result['transcript'],
                    lesson_number=user_params.get('lesson_number', 1),
                    user_id=user_params['user_id'],
                    teacher_id=user_params['teacher_id'],
                    class_id=user_params['class_id'],
                    zoom_summary_id=zoom_summary_id
                )

                lesson_data: LessonExercises = pipeline_result["lesson"]
                logger.info(
                    f"Auto-processed Zoom summary {zoom_summary_id}: "
                    f"{lesson_data.total_exercises} exercises generated"
                )
            except Exception as auto_err:
                logger.error(
                    f"Auto-processing failed for Zoom summary {zoom_summary_id}: {auto_err}"
                )

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
    meeting_time: Optional[str] = Field(None, description="Meeting time in HH:MM format (optional)")
    start_time: Optional[str] = Field(None, description="Start time filter in HH:MM format (optional)")
    end_time: Optional[str] = Field(None, description="End time filter in HH:MM format (optional)")
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


def process_lesson_pipeline(
    transcript_text: str,
    lesson_number: int,
    user_id: str,
    teacher_id: str,
    class_id: str,
    zoom_summary_id: Optional[int] = None
) -> Dict[str, Optional[object]]:
    """Run full processing pipeline and persist outputs"""
    result = processor.process_lesson(transcript_text, lesson_number)

    total = (
        len(result.get('fill_in_blank', [])) +
        len(result.get('flashcards', [])) +
        len(result.get('spelling', []))
    )
    quality_passed = 8 <= total <= 12

    lesson_data = LessonExercises(
        lesson_number=lesson_number,
        fill_in_blank=result.get('fill_in_blank', []),
        flashcards=result.get('flashcards', []),
        spelling=result.get('spelling', []),
        total_exercises=total,
        quality_passed=quality_passed
    )

    stored_record = supabase_client.store_exercises(
        user_id=user_id,
        teacher_id=teacher_id,
        class_id=class_id,
        lesson_number=lesson_number,
        exercises=result,
        zoom_summary_id=zoom_summary_id
    )

    return {
        "lesson": lesson_data,
        "stored_record": stored_record
    }


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


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    mysql_status = "disconnected"
    if mysql_pool:
        try:
            conn = mysql_pool.get_connection()
            conn.close()
            mysql_status = "connected"
        except:
            mysql_status = "error"

    supabase_status = supabase_client.health_check()

    return {
        "status": "healthy",
        "timestamp": utc_now_iso(),
        "version": "1.0.0",
        "databases": {
            "supabase": "connected" if supabase_status else "disconnected",
            "mysql": mysql_status
        }
    }


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
        start_time = utc_now()
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

        end_time = utc_now()
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
        start_time = utc_now()
        logger.info(
            f"Processing Zoom lesson: user={input_data.user_id}, "
            f"teacher={input_data.teacher_id}, class={input_data.class_id}, date={input_data.date}"
        )

        # Fetch transcript from Supabase
        transcript_data = supabase_client.fetch_transcript(
            user_id=input_data.user_id,
            teacher_id=input_data.teacher_id,
            class_id=input_data.class_id,
            date=input_data.date,
            meeting_time=input_data.meeting_time,
            start_time=input_data.start_time,
            end_time=input_data.end_time
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

        pipeline_result = process_lesson_pipeline(
            transcript_text=transcript_text,
            lesson_number=input_data.lesson_number,
            user_id=input_data.user_id,
            teacher_id=input_data.teacher_id,
            class_id=input_data.class_id,
            zoom_summary_id=transcript_data.get('id')
        )

        lesson_data: LessonExercises = pipeline_result["lesson"]
        stored_record = pipeline_result["stored_record"]

        if stored_record:
            logger.info(f"Exercises stored in Supabase (ID: {stored_record.get('id')})")

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

        end_time = utc_now()
        processing_time = (end_time - start_time).total_seconds()

        logger.info(
            f"Zoom lesson processed successfully in {processing_time:.2f}s "
            f"({lesson_data.total_exercises} exercises generated)"
        )

        return ZoomProcessingResponse(
            success=True,
            message=(
                "Zoom lesson processed successfully. Generated "
                f"{lesson_data.total_exercises} exercises."
            ),
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
            'timestamp': utc_now_iso()
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
                "timestamp": utc_now_iso()
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
                "timestamp": utc_now_iso()
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
            "timestamp": utc_now_iso()
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
                "timestamp": utc_now_iso()
            }

        return {
            "success": True,
            "message": f"Retrieved {len(exercises)} exercise set(s)",
            "data": exercises,
            "count": len(exercises),
            "timestamp": utc_now_iso()
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
        start_time = utc_now()
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

        end_time = utc_now()
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
    trace_id = str(uuid.uuid4())
    logger.error(f"[{trace_id}] Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Internal server error",
            "trace_id": trace_id
        }
    )

# ============================================================
# GAME CONTENT ENDPOINTS - MySQL
# ============================================================

# FLASHCARDS & SPELLING

@app.post("/api/v1/word-lists", tags=["Games - Flashcards"])
@limiter.limit("60/minute")
async def create_word_list(request: Request, user_id: str, data: dict):
    """Create a new word list"""
    try:
        query = """
            INSERT INTO word_lists (id, user_id, class_id, name, description, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        list_id = str(uuid.uuid4())
        params = [
            list_id, user_id, data.get('class_id', 'default'),
            data.get('name'), data.get('description'), utc_now_iso()
        ]

        execute_query(query, params, fetch_all=False)
        logger.info(f"[WORD_LISTS] Created list {list_id} for user {user_id}")
        return {"id": list_id, "message": "Word list created successfully"}

    except Exception as e:
        logger.error(f"Error creating word list: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/word-lists/{list_id}", tags=["Games - Flashcards"])
@limiter.limit("60/minute")
async def get_word_list(request: Request, list_id: str, user_id: str):
    """Get a specific word list"""
    try:
        query = """
            SELECT id, user_id, class_id, name, description, created_at, updated_at
            FROM word_lists
            WHERE id = %s AND user_id = %s
        """
        word_list = execute_query(query, (list_id, user_id), fetch_one=True)

        if not word_list:
            raise HTTPException(status_code=404, detail="Word list not found")

        return word_list

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting word list: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/v1/word-lists/{list_id}", tags=["Games - Flashcards"])
@limiter.limit("60/minute")
async def update_word_list(request: Request, list_id: str, user_id: str, data: dict):
    """Update a word list"""
    try:
        # Check if list exists and belongs to user
        check_query = "SELECT id FROM word_lists WHERE id = %s AND user_id = %s"
        existing = execute_query(check_query, (list_id, user_id), fetch_one=True)

        if not existing:
            raise HTTPException(status_code=404, detail="Word list not found")

        # Update the list
        update_fields = []
        params = []

        if 'name' in data:
            update_fields.append("name = %s")
            params.append(data['name'])
        if 'description' in data:
            update_fields.append("description = %s")
            params.append(data['description'])

        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        update_fields.append("updated_at = %s")
        params.append(utc_now_iso())
        params.append(list_id)
        params.append(user_id)

        query = f"""
            UPDATE word_lists
            SET {', '.join(update_fields)}
            WHERE id = %s AND user_id = %s
        """

        execute_query(query, tuple(params), fetch_all=False)
        logger.info(f"[WORD_LISTS] Updated list {list_id} for user {user_id}")
        return {"message": "Word list updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating word list: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/word-lists/{list_id}", tags=["Games - Flashcards"])
@limiter.limit("60/minute")
async def delete_word_list(request: Request, list_id: str, user_id: str):
    """Delete a word list"""
    try:
        # Delete words first (foreign key constraint)
        delete_words_query = "DELETE FROM words WHERE word_list_id = %s"
        execute_query(delete_words_query, (list_id,), fetch_all=False)

        # Delete the list
        delete_list_query = "DELETE FROM word_lists WHERE id = %s AND user_id = %s"
        result = execute_query(delete_list_query, (list_id, user_id), fetch_all=False)

        if result == 0:
            raise HTTPException(status_code=404, detail="Word list not found")

        logger.info(f"[WORD_LISTS] Deleted list {list_id} for user {user_id}")
        return {"message": "Word list deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting word list: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/word-lists/{list_id}/favorite", tags=["Games - Flashcards"])
@limiter.limit("60/minute")
async def toggle_favorite(request: Request, list_id: str, user_id: str):
    """Toggle favorite status of a word list"""
    try:
        # Check if list exists
        check_query = "SELECT id FROM word_lists WHERE id = %s AND user_id = %s"
        existing = execute_query(check_query, (list_id, user_id), fetch_one=True)

        if not existing:
            raise HTTPException(status_code=404, detail="Word list not found")

        # Toggle favorite
        toggle_query = """
            UPDATE word_lists
            SET is_favorite = NOT is_favorite, updated_at = %s
            WHERE id = %s AND user_id = %s
        """
        execute_query(toggle_query, (utc_now_iso(), list_id, user_id), fetch_all=False)

        # Get updated status
        status_query = "SELECT is_favorite FROM word_lists WHERE id = %s"
        status = execute_query(status_query, (list_id,), fetch_one=True)

        logger.info(f"[WORD_LISTS] Toggled favorite for list {list_id}")
        return {"is_favorite": status['is_favorite']}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling favorite: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/word-lists/{list_id}/words", tags=["Games - Flashcards"])
@limiter.limit("60/minute")
async def add_word_to_list(request: Request, list_id: str, user_id: str, data: dict):
    """Add a word to a word list"""
    try:
        # Check if list exists
        check_query = "SELECT id FROM word_lists WHERE id = %s AND user_id = %s"
        existing = execute_query(check_query, (list_id, user_id), fetch_one=True)

        if not existing:
            raise HTTPException(status_code=404, detail="Word list not found")

        # Add word
        query = """
            INSERT INTO words (id, word_list_id, word, translation, notes, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        word_id = str(uuid.uuid4())
        params = [
            word_id, list_id, data.get('word'),
            data.get('translation'), data.get('notes'), utc_now_iso()
        ]

        execute_query(query, params, fetch_all=False)
        logger.info(f"[WORD_LISTS] Added word {word_id} to list {list_id}")
        return {"id": word_id, "message": "Word added successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding word: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/v1/word-lists/{list_id}/words/{word_id}", tags=["Games - Flashcards"])
@limiter.limit("60/minute")
async def update_word_in_list(request: Request, list_id: str, word_id: str, user_id: str, data: dict):
    """Update a word in a word list"""
    try:
        # Check if word exists and belongs to user's list
        check_query = """
            SELECT w.id FROM words w
            JOIN word_lists wl ON w.word_list_id = wl.id
            WHERE w.id = %s AND w.word_list_id = %s AND wl.user_id = %s
        """
        existing = execute_query(check_query, (word_id, list_id, user_id), fetch_one=True)

        if not existing:
            raise HTTPException(status_code=404, detail="Word not found")

        # Update the word
        update_fields = []
        params = []

        if 'word' in data:
            update_fields.append("word = %s")
            params.append(data['word'])
        if 'translation' in data:
            update_fields.append("translation = %s")
            params.append(data['translation'])
        if 'notes' in data:
            update_fields.append("notes = %s")
            params.append(data['notes'])

        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        update_fields.append("updated_at = %s")
        params.append(utc_now_iso())
        params.append(word_id)

        query = f"""
            UPDATE words
            SET {', '.join(update_fields)}
            WHERE id = %s
        """

        execute_query(query, tuple(params), fetch_all=False)
        logger.info(f"[WORD_LISTS] Updated word {word_id}")
        return {"message": "Word updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating word: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/word-lists/{list_id}/words/{word_id}", tags=["Games - Flashcards"])
@limiter.limit("60/minute")
async def delete_word_from_list(request: Request, list_id: str, word_id: str, user_id: str):
    """Delete a word from a word list"""
    try:
        # Check if word exists and belongs to user's list
        check_query = """
            SELECT w.id FROM words w
            JOIN word_lists wl ON w.word_list_id = wl.id
            WHERE w.id = %s AND w.word_list_id = %s AND wl.user_id = %s
        """
        existing = execute_query(check_query, (word_id, list_id, user_id), fetch_one=True)

        if not existing:
            raise HTTPException(status_code=404, detail="Word not found")

        # Delete the word
        delete_query = "DELETE FROM words WHERE id = %s"
        result = execute_query(delete_query, (word_id,), fetch_all=False)

        if result == 0:
            raise HTTPException(status_code=404, detail="Word not found")

        logger.info(f"[WORD_LISTS] Deleted word {word_id} from list {list_id}")
        return {"message": "Word deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting word: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/word-lists/{list_id}/words", tags=["Games - Flashcards"])
@limiter.limit("60/minute")
async def get_words_from_list(
    request: Request,
    list_id: str,
    user_id: str,
    page: int = 1,
    limit: int = 50
):
    """Get words from a specific word list from MySQL"""
    try:
        # Check if list exists and belongs to user
        check_query = "SELECT id FROM word_lists WHERE id = %s AND user_id = %s"
        existing = execute_query(check_query, (list_id, user_id), fetch_one=True)

        if not existing:
            raise HTTPException(status_code=404, detail="Word list not found")

        query = """
            SELECT id, word, translation, notes, difficulty,
                   pronunciation_audio_url, created_at, updated_at
            FROM words
            WHERE word_list_id = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        offset = (page - 1) * limit
        words = execute_query(query, (list_id, limit, offset))

        logger.info(f"[WORD_LISTS] Retrieved {len(words)} words for list {list_id}")
        return {"words": words}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching words: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/word-lists", tags=["Games - Flashcards"])
@limiter.limit("60/minute")
async def get_word_lists(
    request: Request,
    user_id: str,
    class_id: str,
    limit: int = 20
):
    """Get flashcard lists from MySQL"""
    try:
        query = """
            SELECT id, user_id, class_id, name, description,
                   word_count, is_favorite, created_at, updated_at
            FROM word_lists
            WHERE user_id = %s AND class_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """
        lists = execute_query(query, (user_id, class_id, limit))

        for lst in lists:
            if lst.get('created_at'):
                lst['created_at'] = lst['created_at'].isoformat()
            if lst.get('updated_at'):
                lst['updated_at'] = lst['updated_at'].isoformat()

        return {"success": True, "count": len(lists), "data": lists}

    except Exception as e:
        logger.error(f"Error fetching word lists: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/word-lists/{list_id}/words", tags=["Games - Flashcards"])
@limiter.limit("60/minute")
async def get_words(request: Request, list_id: int):
    """Get words for a list"""
    try:
        query = """
            SELECT id, list_id, word, translation, example_sentence,
                   difficulty, is_favorite, created_at
            FROM words
            WHERE list_id = %s
            ORDER BY id
        """
        words = execute_query(query, (list_id,))

        for word in words:
            if word.get('created_at'):
                word['created_at'] = word['created_at'].isoformat()
            word['is_favorite'] = bool(word.get('is_favorite', False))

        return {"success": True, "count": len(words), "words": words}

    except Exception as e:
        logger.error(f"Error fetching words: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/flashcards/sessions/{session_id}", tags=["Games - Flashcards"])
@limiter.limit("60/minute")
async def get_flashcard_session(request: Request, session_id: str, user_id: str):
    """Get flashcard session details"""
    try:
        query = """
            SELECT id, user_id, game_type, class_id, item_ids, status,
                   started_at, completed_at, metadata
            FROM game_sessions
            WHERE id = %s AND user_id = %s AND game_type = 'flashcards'
        """
        session = execute_query(query, (session_id, user_id), fetch_one=True)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        return session

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting flashcard session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/flashcards/stats/me", tags=["Games - Flashcards"])
@limiter.limit("60/minute")
async def get_flashcard_stats(request: Request, user_id: str):
    """Get user flashcard statistics"""
    try:
        # Get overall stats
        stats_query = """
            SELECT
                COUNT(*) as total_sessions,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_sessions,
                AVG(final_score) as avg_score,
                SUM(correct_count) as total_correct,
                SUM(incorrect_count) as total_incorrect
            FROM game_sessions
            WHERE user_id = %s AND game_type = 'flashcards'
        """
        stats = execute_query(stats_query, (user_id,), fetch_one=True)

        return {
            "totals": stats or {
                "total_sessions": 0,
                "completed_sessions": 0,
                "avg_score": 0,
                "total_correct": 0,
                "total_incorrect": 0
            }
        }

    except Exception as e:
        logger.error(f"Error getting flashcard stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/spelling/sessions/{session_id}", tags=["Games - Spelling"])
@limiter.limit("60/minute")
async def get_spelling_session(request: Request, session_id: str, user_id: str):
    """Get spelling session details"""
    try:
        query = """
            SELECT id, user_id, game_type, class_id, item_ids, status,
                   started_at, completed_at, metadata
            FROM game_sessions
            WHERE id = %s AND user_id = %s AND game_type = 'spelling_bee'
        """
        session = execute_query(query, (session_id, user_id), fetch_one=True)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        return session

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting spelling session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/spelling/pronunciations/{word_id}", tags=["Games - Spelling"])
@limiter.limit("60/minute")
async def get_pronunciation(request: Request, word_id: str, user_id: str):
    """Get pronunciation for a word"""
    try:
        query = """
            SELECT word, pronunciation_audio_url
            FROM words
            WHERE id = %s
        """
        word = execute_query(query, (word_id,), fetch_one=True)

        if not word:
            raise HTTPException(status_code=404, detail="Word not found")

        return {
            "word": word['word'],
            "pronunciation_url": word.get('pronunciation_audio_url'),
            "message": "Pronunciation feature not yet implemented"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pronunciation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/api/v1/spelling/words", tags=["Games - Spelling"])
@limiter.limit("60/minute")
async def get_spelling_words(
    request: Request,
    user_id: str,
    class_id: str,
    difficulty: Optional[str] = None,
    limit: int = 20
):
    """Get spelling words from MySQL"""
    try:
        query = """
            SELECT w.id, w.word, w.translation, w.example_sentence,
                   w.difficulty, wl.name as list_name
            FROM words w
            JOIN word_lists wl ON w.word_list_id = wl.id
            WHERE wl.user_id = %s AND wl.class_id = %s
        """
        params = [user_id, class_id]

        if difficulty:
            query += " AND w.difficulty = %s"
            params.append(difficulty)

        query += " ORDER BY RAND() LIMIT %s"
        params.append(limit)

        words = execute_query(query, tuple(params))

        return {"success": True, "count": len(words), "words": words}

    except Exception as e:
        logger.error(f"Error fetching spelling words: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# ADVANCED CLOZE
# ============================================

@app.get("/api/v1/cloze/lessons", tags=["Games - Cloze"])
@limiter.limit("60/minute")
async def get_cloze_lessons(
    request: Request,
    topic_id: str,
    difficulty: Optional[str] = None,
    limit: int = 20
):
    """Get cloze lessons for a topic"""
    try:
        query = """
            SELECT id, topic_id, title, description, difficulty,
                   item_count, created_at
            FROM cloze_lessons
            WHERE topic_id = %s
        """
        params = [topic_id]

        if difficulty:
            query += " AND difficulty = %s"
            params.append(difficulty)

        query += " ORDER BY title LIMIT %s"
        params.append(limit)

        lessons = execute_query(query, tuple(params))
        logger.info(f"[CLOZE] Retrieved {len(lessons)} lessons for topic {topic_id}")
        return {"lessons": lessons}

    except Exception as e:
        logger.error(f"Error fetching cloze lessons: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/cloze/sessions/{session_id}", tags=["Games - Cloze"])
@limiter.limit("60/minute")
async def get_cloze_session(request: Request, session_id: str, user_id: str):
    """Get cloze session details"""
    try:
        query = """
            SELECT id, user_id, game_type, class_id, item_ids, status,
                   started_at, completed_at, metadata
            FROM game_sessions
            WHERE id = %s AND user_id = %s AND game_type = 'advanced_cloze'
        """
        session = execute_query(query, (session_id, user_id), fetch_one=True)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        return session

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cloze session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/cloze/sessions", tags=["Games - Cloze"])
@limiter.limit("60/minute")
async def start_cloze_session(request: Request, data: SessionStartInput):
    """Start a cloze session"""
    try:
        query = """
            INSERT INTO game_sessions (id, user_id, game_type, class_id, mode,
                                      reference_id, item_ids, status, started_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        session_id = str(uuid.uuid4())
        params = [
            session_id, data.user_id, data.game_type, data.class_id,
            data.mode, data.reference_id, data.item_ids, 'active', utc_now_iso()
        ]

        execute_query(query, params, fetch_all=False)
        logger.info(f"[CLOZE] Started session {session_id} for user {data.user_id}")
        return {"id": session_id, "status": "active"}

    except Exception as e:
        logger.error(f"Error starting cloze session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/cloze/sessions/{session_id}/results", tags=["Games - Cloze"])
@limiter.limit("60/minute")
async def record_cloze_result(request: Request, session_id: str, user_id: str, data: dict):
    """Record cloze result"""
    try:
        query = """
            INSERT INTO game_results (id, session_id, game_type, item_id, is_correct,
                                     attempts, time_spent_ms, metadata, created_at)
            VALUES (%s, %s, 'cloze', %s, %s, %s, %s, %s, %s)
        """
        result_id = str(uuid.uuid4())
        params = [
            result_id, session_id, data['item_id'], data['is_correct'],
            data.get('attempts', 1), data.get('time_spent_ms', 0),
            json.dumps(data.get('metadata')) if data.get('metadata') else None, utc_now_iso()
        ]

        execute_query(query, params, fetch_all=False)
        logger.info(f"[CLOZE] Recorded result for session {session_id}")
        return {"id": result_id, "message": "Result recorded"}

    except Exception as e:
        logger.error(f"Error recording cloze result: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/cloze/sessions/{session_id}/complete", tags=["Games - Cloze"])
@limiter.limit("60/minute")
async def complete_cloze_session(request: Request, session_id: str, user_id: str, data: SessionCompletionInput):
    """Complete cloze session"""
    try:
        query = """
            UPDATE game_sessions
            SET status = 'completed', completed_at = %s,
                final_score = %s, correct_count = %s, incorrect_count = %s
            WHERE id = %s AND user_id = %s
        """
        params = [
            utc_now_iso(), data.final_score, data.correct_count,
            data.incorrect_count, session_id, user_id
        ]

        result = execute_query(query, tuple(params), fetch_all=False)
        if result == 0:
            raise HTTPException(status_code=404, detail="Session not found")

        logger.info(f"[CLOZE] Completed session {session_id}")
        return {"message": "Session completed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing cloze session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/cloze/items/{item_id}/hint", tags=["Games - Cloze"])
@limiter.limit("60/minute")
async def get_cloze_hint(request: Request, item_id: str, user_id: str):
    """Get hint for cloze item"""
    try:
        query = """
            SELECT id, text_parts, correct_answers, hint
            FROM cloze_items
            WHERE id = %s
        """
        item = execute_query(query, (item_id,), fetch_one=True)

        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        return {
            "item_id": item_id,
            "hint": item.get('hint', 'No hint available'),
            "message": "Use this hint to help with the answer"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cloze hint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/cloze/mistakes", tags=["Games - Cloze"])
@limiter.limit("60/minute")
async def get_cloze_mistakes(
    request: Request,
    user_id: str,
    page: int = 1,
    limit: int = 10
):
    """Get user cloze mistakes"""
    try:
        offset = (page - 1) * limit
        query = """
            SELECT um.id, um.item_id, um.item_type, um.user_answer,
                   um.correct_answer, um.mistake_type, um.created_at,
                   ci.text_parts, ci.correct_answers
            FROM user_mistakes um
            JOIN cloze_items ci ON um.item_id = ci.id
            WHERE um.user_id = %s AND um.item_type = 'advanced_cloze'
            ORDER BY um.created_at DESC
            LIMIT %s OFFSET %s
        """
        mistakes = execute_query(query, (user_id, limit, offset))

        for m in mistakes:
            if m['created_at']:
                m['created_at'] = m['created_at'].isoformat()

        return {"success": True, "mistakes": mistakes}

    except Exception as e:
        logger.error(f"Error fetching cloze mistakes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/grammar/lessons", tags=["Games - Grammar"])
@limiter.limit("60/minute")
async def get_grammar_lessons(
    request: Request,
    category_id: str,
    difficulty: Optional[str] = None,
    limit: int = 20
):
    """Get grammar lessons for a category"""
    try:
        query = """
            SELECT id, category_id, title, description, difficulty,
                   question_count, created_at
            FROM grammar_lessons
            WHERE category_id = %s
        """
        params = [category_id]

        if difficulty:
            query += " AND difficulty = %s"
            params.append(difficulty)

        query += " ORDER BY title LIMIT %s"
        params.append(limit)

        lessons = execute_query(query, tuple(params))
        logger.info(f"[GRAMMAR] Retrieved {len(lessons)} lessons for category {category_id}")
        return {"lessons": lessons}

    except Exception as e:
        logger.error(f"Error fetching grammar lessons: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/grammar/sessions/{session_id}", tags=["Games - Grammar"])
@limiter.limit("60/minute")
async def get_grammar_session(request: Request, session_id: str, user_id: str):
    """Get grammar session details"""
    try:
        query = """
            SELECT id, user_id, game_type, class_id, item_ids, status,
                   started_at, completed_at, metadata
            FROM game_sessions
            WHERE id = %s AND user_id = %s AND game_type = 'grammar_challenge'
        """
        session = execute_query(query, (session_id, user_id), fetch_one=True)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        return session

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting grammar session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/grammar/sessions", tags=["Games - Grammar"])
@limiter.limit("60/minute")
async def start_grammar_session(request: Request, data: SessionStartInput):
    """Start a grammar session"""
    try:
        query = """
            INSERT INTO game_sessions (id, user_id, game_type, class_id, mode,
                                      reference_id, item_ids, status, started_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        session_id = str(uuid.uuid4())
        params = [
            session_id, data.user_id, data.game_type, data.class_id,
            data.mode, data.reference_id, data.item_ids, 'active', utc_now_iso()
        ]

        execute_query(query, params, fetch_all=False)
        logger.info(f"[GRAMMAR] Started session {session_id} for user {data.user_id}")
        return {"id": session_id, "status": "active"}

    except Exception as e:
        logger.error(f"Error starting grammar session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/grammar/sessions/{session_id}/results", tags=["Games - Grammar"])
@limiter.limit("60/minute")
async def record_grammar_result(request: Request, session_id: str, user_id: str, data: dict):
    """Record grammar result"""
    try:
        query = """
            INSERT INTO game_results (id, session_id, game_type, item_id, is_correct,
                                     attempts, time_spent_ms, metadata, created_at)
            VALUES (%s, %s, 'grammar', %s, %s, %s, %s, %s, %s)
        """
        result_id = str(uuid.uuid4())
        params = [
            result_id, session_id, data['item_id'], data['is_correct'],
            data.get('attempts', 1), data.get('time_spent_ms', 0),
            json.dumps(data.get('metadata')) if data.get('metadata') else None, utc_now_iso()
        ]

        execute_query(query, params, fetch_all=False)
        logger.info(f"[GRAMMAR] Recorded result for session {session_id}")
        return {"id": result_id, "message": "Result recorded"}

    except Exception as e:
        logger.error(f"Error recording grammar result: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/grammar/sessions/{session_id}/skip", tags=["Games - Grammar"])
@limiter.limit("60/minute")
async def skip_grammar_question(request: Request, session_id: str, user_id: str, data: dict):
    """Skip a grammar question"""
    try:
        # Record as incorrect result
        query = """
            INSERT INTO game_results (id, session_id, game_type, item_id, is_correct,
                                     attempts, time_spent_ms, metadata, created_at)
            VALUES (%s, %s, 'grammar', %s, %s, %s, %s, %s, %s)
        """
        result_id = str(uuid.uuid4())
        params = [
            result_id, session_id, data.get('question_id', data.get('item_id')), False,
            0, 0, json.dumps({"skipped": True}), utc_now_iso()
        ]

        execute_query(query, params, fetch_all=False)
        logger.info(f"[GRAMMAR] Skipped question for session {session_id}")
        return {"id": result_id, "message": "Question skipped"}

    except Exception as e:
        logger.error(f"Error skipping grammar question: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/grammar/sessions/{session_id}/complete", tags=["Games - Grammar"])
@limiter.limit("60/minute")
async def complete_grammar_session(request: Request, session_id: str, user_id: str, data: SessionCompletionInput):
    """Complete grammar session"""
    try:
        query = """
            UPDATE game_sessions
            SET status = 'completed', completed_at = %s,
                final_score = %s, correct_count = %s, incorrect_count = %s
            WHERE id = %s AND user_id = %s
        """
        params = [
            utc_now_iso(), data.final_score, data.correct_count,
            data.incorrect_count, session_id, user_id
        ]

        result = execute_query(query, tuple(params), fetch_all=False)
        if result == 0:
            raise HTTPException(status_code=404, detail="Session not found")

        logger.info(f"[GRAMMAR] Completed session {session_id}")
        return {"message": "Session completed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing grammar session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/grammar/questions/{question_id}/hint", tags=["Games - Grammar"])
@limiter.limit("60/minute")
async def get_grammar_hint(request: Request, question_id: str, user_id: str):
    """Get hint for grammar question"""
    try:
        query = """
            SELECT id, question, options, correct_answer, hint, explanation
            FROM grammar_questions
            WHERE id = %s
        """
        question = execute_query(query, (question_id,), fetch_one=True)

        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        return {
            "question_id": question_id,
            "hint": question.get('hint', 'No hint available'),
            "explanation": question.get('explanation', 'No explanation available')
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting grammar hint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/grammar/mistakes", tags=["Games - Grammar"])
@limiter.limit("60/minute")
async def get_grammar_mistakes(
    request: Request,
    user_id: str,
    page: int = 1,
    limit: int = 10
):
    """Get user grammar mistakes"""
    try:
        offset = (page - 1) * limit
        query = """
            SELECT um.id, um.item_id, um.item_type, um.user_answer,
                   um.correct_answer, um.mistake_type, um.created_at,
                   gq.question, gq.options, gq.correct_answer
            FROM user_mistakes um
            JOIN grammar_questions gq ON um.item_id = gq.id
            WHERE um.user_id = %s AND um.item_type = 'grammar_challenge'
            ORDER BY um.created_at DESC
            LIMIT %s OFFSET %s
        """
        mistakes = execute_query(query, (user_id, limit, offset))

        for m in mistakes:
            if m['created_at']:
                m['created_at'] = m['created_at'].isoformat()

        return {"success": True, "mistakes": mistakes}

    except Exception as e:
        logger.error(f"Error fetching grammar mistakes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/sentence/lessons", tags=["Games - Sentence"])
@limiter.limit("60/minute")
async def get_sentence_lessons(
    request: Request,
    topic_id: str,
    difficulty: Optional[str] = None,
    limit: int = 20
):
    """Get sentence lessons for a topic"""
    try:
        query = """
            SELECT id, topic_id, title, description, difficulty,
                   item_count, created_at
            FROM sentence_lessons
            WHERE topic_id = %s
        """
        params = [topic_id]

        if difficulty:
            query += " AND difficulty = %s"
            params.append(difficulty)

        query += " ORDER BY title LIMIT %s"
        params.append(limit)

        lessons = execute_query(query, tuple(params))
        logger.info(f"[SENTENCE] Retrieved {len(lessons)} lessons for topic {topic_id}")
        return {"lessons": lessons}

    except Exception as e:
        logger.error(f"Error fetching sentence lessons: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/sentence/sessions/{session_id}", tags=["Games - Sentence"])
@limiter.limit("60/minute")
async def get_sentence_session(request: Request, session_id: str, user_id: str):
    """Get sentence session details"""
    try:
        query = """
            SELECT id, user_id, game_type, class_id, item_ids, status,
                   started_at, completed_at, metadata
            FROM game_sessions
            WHERE id = %s AND user_id = %s AND game_type = 'sentence_builder'
        """
        session = execute_query(query, (session_id, user_id), fetch_one=True)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        return session

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting sentence session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/sentence/sessions", tags=["Games - Sentence"])
@limiter.limit("60/minute")
async def start_sentence_session(request: Request, data: SessionStartInput):
    """Start a sentence session"""
    try:
        query = """
            INSERT INTO game_sessions (id, user_id, game_type, class_id, mode,
                                      reference_id, item_ids, status, started_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        session_id = str(uuid.uuid4())
        params = [
            session_id, data.user_id, data.game_type, data.class_id,
            data.mode, data.reference_id, data.item_ids, 'active', utc_now_iso()
        ]

        execute_query(query, params, fetch_all=False)
        logger.info(f"[SENTENCE] Started session {session_id} for user {data.user_id}")
        return {"id": session_id, "status": "active"}

    except Exception as e:
        logger.error(f"Error starting sentence session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/sentence/sessions/{session_id}/results", tags=["Games - Sentence"])
@limiter.limit("60/minute")
async def record_sentence_result(request: Request, session_id: str, user_id: str, data: dict):
    """Record sentence result"""
    try:
        query = """
            INSERT INTO game_results (id, session_id, game_type, item_id, is_correct,
                                     attempts, time_spent_ms, metadata, created_at)
            VALUES (%s, %s, 'sentence', %s, %s, %s, %s, %s, %s)
        """
        result_id = str(uuid.uuid4())
        params = [
            result_id, session_id, data['item_id'], data['is_correct'],
            data.get('attempts', 1), data.get('time_spent_ms', 0),
            json.dumps(data.get('metadata')) if data.get('metadata') else None, utc_now_iso()
        ]

        execute_query(query, params, fetch_all=False)
        logger.info(f"[SENTENCE] Recorded result for session {session_id}")
        return {"id": result_id, "message": "Result recorded"}

    except Exception as e:
        logger.error(f"Error recording sentence result: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/sentence/sessions/{session_id}/complete", tags=["Games - Sentence"])
@limiter.limit("60/minute")
async def complete_sentence_session(request: Request, session_id: str, user_id: str, data: SessionCompletionInput):
    """Complete sentence session"""
    try:
        query = """
            UPDATE game_sessions
            SET status = 'completed', completed_at = %s,
                final_score = %s, correct_count = %s, incorrect_count = %s
            WHERE id = %s AND user_id = %s
        """
        params = [
            utc_now_iso(), data.final_score, data.correct_count,
            data.incorrect_count, session_id, user_id
        ]

        result = execute_query(query, tuple(params), fetch_all=False)
        if result == 0:
            raise HTTPException(status_code=404, detail="Session not found")

        logger.info(f"[SENTENCE] Completed session {session_id}")
        return {"message": "Session completed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing sentence session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/sentence/items/{item_id}/hint", tags=["Games - Sentence"])
@limiter.limit("60/minute")
async def get_sentence_hint(request: Request, item_id: str, user_id: str):
    """Get hint for sentence item"""
    try:
        query = """
            SELECT id, sentence_tokens, accepted_sequences, hint
            FROM sentence_items
            WHERE id = %s
        """
        item = execute_query(query, (item_id,), fetch_one=True)

        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        return {
            "item_id": item_id,
            "hint": item.get('hint', 'No hint available'),
            "accepted_sequences": item.get('accepted_sequences', [])
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting sentence hint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/sentence/items/{item_id}/tts", tags=["Games - Sentence"])
@limiter.limit("60/minute")
async def get_sentence_tts(request: Request, item_id: str, user_id: str):
    """Get TTS audio for sentence item"""
    try:
        query = """
            SELECT id, sentence_tokens, tts_audio_url
            FROM sentence_items
            WHERE id = %s
        """
        item = execute_query(query, (item_id,), fetch_one=True)

        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        # Convert tokens back to sentence
        tokens = item.get('sentence_tokens', [])
        sentence = ' '.join(tokens)

        return {
            "item_id": item_id,
            "sentence": sentence,
            "tts_url": item.get('tts_audio_url'),
            "message": "TTS feature not yet implemented"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting sentence TTS: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/sentence/mistakes", tags=["Games - Sentence"])
@limiter.limit("60/minute")
async def get_sentence_mistakes(
    request: Request,
    user_id: str,
    page: int = 1,
    limit: int = 10
):
    """Get user sentence mistakes"""
    try:
        offset = (page - 1) * limit
        query = """
            SELECT um.id, um.item_id, um.item_type, um.user_answer,
                   um.correct_answer, um.mistake_type, um.created_at,
                   si.sentence_tokens, si.accepted_sequences
            FROM user_mistakes um
            JOIN sentence_items si ON um.item_id = si.id
            WHERE um.user_id = %s AND um.item_type = 'sentence_builder'
            ORDER BY um.created_at DESC
            LIMIT %s OFFSET %s
        """
        mistakes = execute_query(query, (user_id, limit, offset))

        for m in mistakes:
            if m['created_at']:
                m['created_at'] = m['created_at'].isoformat()

        return {"success": True, "mistakes": mistakes}

    except Exception as e:
        logger.error(f"Error fetching sentence mistakes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/stats/me", tags=["User Stats"])
@limiter.limit("60/minute")
async def get_user_stats(request: Request, user_id: str):
    """Get aggregate user statistics across all games"""
    try:
        # Get overall stats
        stats_query = """
            SELECT
                game_type,
                COUNT(*) as total_sessions,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_sessions,
                AVG(final_score) as avg_score,
                SUM(correct_count) as total_correct,
                SUM(incorrect_count) as total_incorrect,
                MAX(started_at) as last_played
            FROM game_sessions
            WHERE user_id = %s
            GROUP BY game_type
        """
        game_stats = execute_query(stats_query, (user_id,))

        # Get total mistakes
        mistakes_query = """
            SELECT COUNT(*) as total_mistakes
            FROM user_mistakes
            WHERE user_id = %s
        """
        mistakes_stats = execute_query(mistakes_query, (user_id,), fetch_one=True)

        return {
            "user_id": user_id,
            "game_stats": game_stats or [],
            "total_mistakes": mistakes_stats['total_mistakes'] if mistakes_stats else 0,
            "generated_at": utc_now_iso()
        }

    except Exception as e:
        logger.error(f"Error getting user stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/sessions/{session_id}", tags=["Universal Session Management"])
@limiter.limit("60/minute")
async def get_session(request: Request, session_id: str, user_id: str):
    """Get any session details (universal endpoint)"""
    try:
        query = """
            SELECT id, user_id, game_type, class_id, item_ids, status,
                   started_at, completed_at, final_score, correct_count,
                   incorrect_count, metadata
            FROM game_sessions
            WHERE id = %s AND user_id = %s
        """
        session = execute_query(query, (session_id, user_id), fetch_one=True)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        return session

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/word-lists/{list_id}/words/{word_id}", tags=["Games - Flashcards"])
@limiter.limit("60/minute")
async def get_word_from_list(request: Request, list_id: str, word_id: str, user_id: str):
    """Get a specific word from a word list"""
    try:
        query = """
            SELECT w.id, w.word, w.translation, w.notes, w.created_at, w.updated_at
            FROM words w
            JOIN word_lists wl ON w.word_list_id = wl.id
            WHERE w.id = %s AND w.word_list_id = %s AND wl.user_id = %s
        """
        word = execute_query(query, (word_id, list_id, user_id), fetch_one=True)

        if not word:
            raise HTTPException(status_code=404, detail="Word not found")

        return word

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting word: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/api/v1/cloze/items", tags=["Games - Cloze"])
@limiter.limit("60/minute")
async def get_cloze_items(
    request: Request,
    topic_id: Optional[str] = None,
    lesson_id: Optional[str] = None,
    difficulty: Optional[str] = None,
    limit: int = 10
):
    """Get cloze items from MySQL"""
    try:
        query = """
            SELECT id, topic_id, lesson_id, difficulty,
                   text_parts, options, correct_answers, hint, explanation, created_at
            FROM cloze_items
            WHERE 1=1
        """
        params = []

        if topic_id:
            query += " AND topic_id = %s"
            params.append(topic_id)

        if lesson_id:
            query += " AND lesson_id = %s"
            params.append(lesson_id)

        if difficulty:
            query += " AND difficulty = %s"
            params.append(difficulty)

        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)

        items = execute_query(query, tuple(params))

        for item in items:
            item['text_parts'] = json.loads(item['text_parts']) if isinstance(item['text_parts'], str) else item['text_parts']
            item['options'] = json.loads(item['options']) if isinstance(item['options'], str) else item['options']
            item['correct_answers'] = json.loads(item['correct_answers']) if isinstance(item['correct_answers'], str) else item['correct_answers']
            if item.get('created_at'):
                item['created_at'] = item['created_at'].isoformat()

        return {"success": True, "count": len(items), "items": items}

    except Exception as e:
        logger.error(f"Error fetching cloze items: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/cloze/topics", tags=["Games - Cloze"])
@limiter.limit("30/minute")
async def get_cloze_topics(request: Request):
    """Get cloze topics"""
    try:
        query = """
            SELECT id, name, icon, description
            FROM cloze_topics
            ORDER BY name
        """
        topics = execute_query(query)
        return {"success": True, "topics": topics}

    except Exception as e:
        logger.error(f"Error fetching topics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# GRAMMAR CHALLENGE
# ============================================

@app.get("/api/v1/grammar/questions", tags=["Games - Grammar"])
@limiter.limit("60/minute")
async def get_grammar_questions(
    request: Request,
    category_id: Optional[str] = None,
    lesson_id: Optional[str] = None,
    difficulty: Optional[str] = None,
    limit: int = 10
):
    """Get grammar questions from MySQL"""
    try:
        query = """
            SELECT id, category_id, lesson_id, difficulty, question,
                   options, correct_answer, hint, explanation, created_at
            FROM grammar_questions
            WHERE 1=1
        """
        params: List[Any] = []

        if category_id:
            query += " AND category_id = %s"
            params.append(category_id)

        if lesson_id:
            query += " AND lesson_id = %s"
            params.append(lesson_id)

        if difficulty:
            query += " AND difficulty = %s"
            params.append(difficulty)

        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)

        questions = execute_query(query, tuple(params))

        for q in questions:
            q['options'] = json.loads(q['options']) if isinstance(q['options'], str) else q['options']
            if q.get('created_at'):
                q['created_at'] = q['created_at'].isoformat()

        return {"success": True, "count": len(questions), "questions": questions}

    except Exception as e:
        logger.error(f"Error fetching grammar questions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/grammar/categories", tags=["Games - Grammar"])
@limiter.limit("30/minute")
async def get_grammar_categories(request: Request):
    """Get grammar categories"""
    try:
        query = """
            SELECT id, name, icon, description
            FROM grammar_categories
            ORDER BY name
        """
        categories = execute_query(query)
        return {"success": True, "categories": categories}

    except Exception as e:
        logger.error(f"Error fetching categories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# SENTENCE BUILDER
# ============================================

@app.get("/api/v1/sentence/items", tags=["Games - Sentence"])
@limiter.limit("60/minute")
async def get_sentence_items(
    request: Request,
    topic_id: Optional[str] = None,
    lesson_id: Optional[str] = None,
    difficulty: Optional[str] = None,
    limit: int = 10
):
    """Get sentence items from MySQL"""
    try:
        query = """
            SELECT id, topic_id, lesson_id, difficulty, english_sentence, translation,
                   sentence_tokens, accepted_sequences, distractors, hint, created_at
            FROM sentence_items
            WHERE 1=1
        """
        params = []

        if topic_id:
            query += " AND topic_id = %s"
            params.append(topic_id)

        if lesson_id:
            query += " AND lesson_id = %s"
            params.append(lesson_id)

        if difficulty:
            query += " AND difficulty = %s"
            params.append(difficulty)

        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)

        items = execute_query(query, tuple(params))

        for item in items:
            item['sentence_tokens'] = json.loads(item['sentence_tokens']) if isinstance(item['sentence_tokens'], str) else item['sentence_tokens']

            accepted = item.get('accepted_sequences')
            if isinstance(accepted, str):
                accepted = json.loads(accepted)
            if accepted is None:
                accepted = []
            item['accepted_sequences'] = accepted
            # Provide legacy key expected by clients/tests
            item['accepted'] = accepted

            distractors = item.get('distractors')
            if isinstance(distractors, str):
                distractors = json.loads(distractors)
            item['distractors'] = distractors

            if item.get('created_at'):
                item['created_at'] = item['created_at'].isoformat()

        return {"success": True, "count": len(items), "items": items}

    except Exception as e:
        logger.error(f"Error fetching sentence items: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/sentence/topics", tags=["Games - Sentence"])
@limiter.limit("30/minute")
async def get_sentence_topics(request: Request):
    """Get sentence topics"""
    try:
        query = """
            SELECT id, name, icon, description
            FROM sentence_topics
            ORDER BY name
        """
        topics = execute_query(query)
        return {"success": True, "topics": topics}

    except Exception as e:
        logger.error(f"Error fetching topics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# PROGRESS TRACKING - MySQL
# ============================================

@app.post("/api/v1/sessions/start", tags=["Progress Tracking"])
@limiter.limit("60/minute")
async def start_session(session_data: SessionStartInput, request: Request):
    """Start a game session"""
    try:
        session_id = str(uuid.uuid4())

        query = """
            INSERT INTO game_sessions
            (id, user_id, game_type, class_id, mode, reference_id,
             progress_total, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        metadata = json.dumps({"item_ids": session_data.item_ids})
        total = len(session_data.item_ids) if session_data.item_ids else 0

        execute_query(query, (
            session_id,
            session_data.user_id,
            session_data.game_type,
            session_data.class_id,
            session_data.mode,
            session_data.reference_id,
            total,
            metadata
        ), fetch_all=False)

        return {
            "id": session_id,
            "user_id": session_data.user_id,
            "game_type": session_data.game_type,
            "total_items": total,
            "status": "active"
        }

    except Exception as e:
        logger.error(f"Error starting session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/sessions/{session_id}/result", tags=["Progress Tracking"])
@limiter.limit("120/minute")
async def record_result(
    session_id: str,
    result_data: AnswerResultInput,
    request: Request
):
    """Record an answer"""
    try:
        result_id = str(uuid.uuid4())

        query1 = """
            INSERT INTO game_results
            (id, session_id, game_type, item_id, is_correct, attempts, time_spent_ms, metadata)
            SELECT %s, %s, game_type, %s, %s, %s, %s, %s
            FROM game_sessions WHERE id = %s
        """

        metadata = json.dumps(result_data.metadata) if result_data.metadata else None

        execute_query(query1, (
            result_id,
            session_id,
            result_data.item_id,
            result_data.is_correct,
            result_data.attempts,
            result_data.time_spent_ms,
            metadata,
            session_id
        ), fetch_all=False)

        query2 = """
            UPDATE game_sessions
            SET progress_current = progress_current + 1,
                correct_count = correct_count + %s,
                incorrect_count = incorrect_count + %s
            WHERE id = %s
        """

        execute_query(query2, (
            1 if result_data.is_correct else 0,
            0 if result_data.is_correct else 1,
            session_id
        ), fetch_all=False)

        if not result_data.is_correct:
            session_info = execute_query(
                "SELECT user_id, game_type FROM game_sessions WHERE id = %s",
                (session_id,),
                fetch_one=True
            )

            if session_info:
                mistake_id = str(uuid.uuid4())
                query3 = """
                    INSERT INTO user_mistakes (
                        id, user_id, game_type, item_type, item_id,
                        user_answer, correct_answer, mistake_type
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """

                execute_query(query3, (
                    mistake_id,
                    session_info['user_id'],
                    session_info['game_type'],
                    session_info['game_type'],
                    result_data.item_id,
                    metadata,
                    None,
                    "incorrect"
                ), fetch_all=False)

        return {"success": True, "recorded": True}

    except Exception as e:
        logger.error(f"Error recording result: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/sessions/{session_id}/complete", tags=["Progress Tracking"])
@limiter.limit("60/minute")
async def complete_session(
    session_id: str,
    completion_data: SessionCompletionInput,
    request: Request
):
    """Complete a session"""
    try:
        query = """
            UPDATE game_sessions
            SET completed_at = CURRENT_TIMESTAMP,
                final_score = %s,
                correct_count = %s,
                incorrect_count = %s
            WHERE id = %s
        """

        execute_query(query, (
            completion_data.final_score,
            completion_data.correct_count,
            completion_data.incorrect_count,
            session_id
        ), fetch_all=False)

        return {
            "success": True,
            "session": {
                "id": session_id,
                "score": completion_data.final_score,
                "correct": completion_data.correct_count,
                "incorrect": completion_data.incorrect_count
            }
        }

    except Exception as e:
        logger.error(f"Error completing session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/progress/{user_id}", tags=["Progress Tracking"])
@limiter.limit("30/minute")
async def get_progress(
    user_id: str,
    request: Request,
    game_type: Optional[str] = None,
    limit: int = 10
):
    """Get user progress"""
    try:
        query = """
            SELECT id, game_type, class_id, mode, final_score, correct_count, incorrect_count,
                   started_at, completed_at
            FROM game_sessions
            WHERE user_id = %s AND completed_at IS NOT NULL
        """
        params = [user_id]

        if game_type:
            query += " AND game_type = %s"
            params.append(game_type)

        query += " ORDER BY completed_at DESC LIMIT %s"
        params.append(limit)

        sessions = execute_query(query, tuple(params))

        for s in sessions:
            if s.get('started_at'):
                s['started_at'] = s['started_at'].isoformat()
            if s.get('completed_at'):
                s['completed_at'] = s['completed_at'].isoformat()

        total_sessions = len(sessions)
        total_correct = sum(s.get('correct_count', 0) for s in sessions)
        total_incorrect = sum(s.get('incorrect_count', 0) for s in sessions)
        avg_score = sum(s.get('final_score', 0) for s in sessions) / total_sessions if total_sessions > 0 else 0

        return {
            "success": True,
            "totals": {
                "sessions": total_sessions,
                "correct": total_correct,
                "incorrect": total_incorrect,
                "average_score": round(avg_score, 2)
            },
            "sessions": sessions
        }

    except Exception as e:
        logger.error(f"Error fetching progress: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/mistakes/{user_id}", tags=["Progress Tracking"])
@limiter.limit("30/minute")
async def get_mistakes(
    user_id: str,
    request: Request,
    game_type: Optional[str] = None,
    limit: int = 20
):
    """Get user mistakes"""
    try:
        query = """
            SELECT user_id, game_type, item_id, item_type,
                   user_answer, correct_answer, mistake_type,
                   mistake_count, last_attempted_at
            FROM user_mistakes
            WHERE user_id = %s
        """
        params = [user_id]

        if game_type:
            query += " AND game_type = %s"
            params.append(game_type)

        query += " ORDER BY mistake_count DESC LIMIT %s"
        params.append(limit)

        mistakes = execute_query(query, tuple(params))

        for m in mistakes:
            if m.get('last_attempted_at'):
                m['last_attempted_at'] = m['last_attempted_at'].isoformat()

        return {"success": True, "mistakes": mistakes}

    except Exception as e:
        logger.error(f"Error fetching mistakes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
