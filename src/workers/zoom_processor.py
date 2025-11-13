"""
Automatic Zoom Recording Processor
Polls Supabase for new zoom_summaries and processes them automatically
"""

import os
import time
import logging
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
from supabase import create_client, Client

from src.main import LessonProcessor

load_dotenv()
logger = logging.getLogger(__name__)

# Initialize Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None


class ZoomAutoProcessor:
    """Automatically processes new Zoom recordings from Supabase"""
    
    def __init__(self, poll_interval: int = 60):
        """
        Initialize auto processor
        
        Args:
            poll_interval: How often to check for new recordings (seconds)
        """
        self.poll_interval = poll_interval
        self.processor = LessonProcessor()
        self.last_check_time = None
        logger.info(f"✅ ZoomAutoProcessor initialized (poll every {poll_interval}s)")
    
    def get_unprocessed_recordings(self):
        """
        Fetch zoom_summaries that haven't been processed yet
        
        Looks for records where:
        - processed = false OR processed is null
        - created_at > last_check_time (if available)
        """
        if not supabase_client:
            logger.error("Supabase client not initialized")
            return []
        
        try:
            # Fetch all recordings from zoom_summaries
            query = supabase_client.table('zoom_summaries').select('*')
            
            # Only fetch new recordings since last check
            if self.last_check_time:
                query = query.gte('created_at', self.last_check_time.isoformat())
            
            response = query.order('created_at', desc=False).execute()
            
            if not response.data:
                return []
            
            # Filter out recordings that already have exercises
            unprocessed = []
            for recording in response.data:
                recording_id = recording.get('id')
                
                # Check if exercises exist for this recording
                exercises_response = supabase_client.table('lesson_exercises')\
                    .select('id')\
                    .eq('zoom_summary_id', recording_id)\
                    .limit(1)\
                    .execute()
                
                if not exercises_response.data:
                    unprocessed.append(recording)
            
            logger.info(f"Found {len(unprocessed)} unprocessed recordings")
            return unprocessed
            
        except Exception as e:
            logger.error(f"Error fetching unprocessed recordings: {e}")
            return []
    
    def process_recording(self, recording: dict) -> bool:
        """
        Process a single Zoom recording
        
        Args:
            recording: zoom_summaries record from Supabase
            
        Returns:
            True if successful, False otherwise
        """
        recording_id = recording.get('id')
        meeting_id = recording.get('meeting_id')
        
        try:
            logger.info(f"Processing recording {recording_id} (meeting: {meeting_id})")
            
            # Extract transcript
            transcript = recording.get('transcript', '')
            if not transcript or len(transcript.strip()) < 10:
                logger.warning(f"Recording {recording_id} has no valid transcript")
                self.mark_as_processed(recording_id, success=False, error="No transcript")
                return False
            
            # Truncate if too long
            if len(transcript) > 5000:
                logger.warning(f"Transcript too long ({len(transcript)} chars), truncating to 3000")
                transcript = transcript[:3000] + "..."
            
            # Process with AI
            lesson_number = recording.get('lesson_number', 1)
            result = self.processor.process_lesson(transcript, lesson_number)
            
            # Calculate quality
            total = (
                len(result.get('fill_in_blank', [])) +
                len(result.get('flashcards', [])) +
                len(result.get('spelling', []))
            )
            quality_passed = 8 <= total <= 12
            
            # Store exercises in Supabase
            exercises_data = {
                'user_id': recording.get('user_id'),
                'teacher_id': recording.get('teacher_id'),
                'class_id': recording.get('class_id'),
                'lesson_number': lesson_number,
                'zoom_summary_id': recording_id,
                'exercises': {
                    'fill_in_blank': result.get('fill_in_blank', []),
                    'flashcards': result.get('flashcards', []),
                    'spelling': result.get('spelling', []),
                    'vocabulary': result.get('vocabulary', []),
                    'mistakes': result.get('mistakes', []),
                    'sentences': result.get('sentences', [])
                },
                'total_exercises': total,
                'quality_score': 100 if quality_passed else 70,
                'generated_at': datetime.utcnow().isoformat(),
                'status': 'pending_review'
            }
            
            stored = supabase_client.store_exercises(exercises_data)
            
            if stored:
                logger.info(f"✅ Exercises stored (ID: {stored.get('id')}, {total} exercises)")
                self.mark_as_processed(recording_id, success=True)
                return True
            else:
                logger.error(f"Failed to store exercises for recording {recording_id}")
                self.mark_as_processed(recording_id, success=False, error="Storage failed")
                return False
                
        except Exception as e:
            logger.error(f"Error processing recording {recording_id}: {e}", exc_info=True)
            self.mark_as_processed(recording_id, success=False, error=str(e))
            return False
    
    def mark_as_processed(self, recording_id: int, success: bool, error: Optional[str] = None):
        """
        Mark a recording as processed
        Note: Processing status is tracked by existence of lesson_exercises record
        This method is kept for logging purposes
        """
        if success:
            logger.info(f"✅ Recording {recording_id} processed successfully")
        else:
            logger.error(f"❌ Recording {recording_id} processing failed: {error}")
    
    def run_once(self):
        """Run one processing cycle"""
        logger.info("🔄 Checking for new Zoom recordings...")
        
        recordings = self.get_unprocessed_recordings()
        
        if not recordings:
            logger.info("No new recordings to process")
            self.last_check_time = datetime.utcnow()
            return
        
        success_count = 0
        fail_count = 0
        
        for recording in recordings:
            if self.process_recording(recording):
                success_count += 1
            else:
                fail_count += 1
            
            # Small delay between recordings
            time.sleep(2)
        
        logger.info(f"✅ Processed {success_count} recordings successfully, {fail_count} failed")
        self.last_check_time = datetime.utcnow()
    
    def run_forever(self):
        """Run continuous processing loop"""
        logger.info(f"🚀 Starting automatic Zoom processor (checking every {self.poll_interval}s)")
        
        while True:
            try:
                self.run_once()
                
                # Wait before next check
                logger.info(f"⏳ Waiting {self.poll_interval}s before next check...")
                time.sleep(self.poll_interval)
                
            except KeyboardInterrupt:
                logger.info("🛑 Stopping Zoom processor...")
                break
            except Exception as e:
                logger.error(f"Error in processing loop: {e}", exc_info=True)
                time.sleep(self.poll_interval)


def start_worker():
    """Start the background worker"""
    poll_interval = int(os.getenv('ZOOM_POLL_INTERVAL', '60'))  # Default: check every 60 seconds
    processor = ZoomAutoProcessor(poll_interval=poll_interval)
    processor.run_forever()


if __name__ == "__main__":
    # Run as standalone script
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    start_worker()
