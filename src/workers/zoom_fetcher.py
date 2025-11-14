"""
Automatic Zoom Recording Fetcher & Transcriber
Fetches new Zoom recordings, transcribes them, and stores in Supabase
"""

import os
import time
import logging
import requests
import base64
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dotenv import load_dotenv
import assemblyai as aai
from supabase import create_client, Client

load_dotenv()
logger = logging.getLogger(__name__)

# Initialize Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None


class ZoomTokenManager:
    """Manages Zoom OAuth tokens with auto-refresh"""
    
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
            logger.info("🔄 Refreshing Zoom access token...")
            
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
                
                logger.info(f"✅ Zoom token refreshed successfully (expires in {expires_in}s)")
                return self.access_token
            else:
                logger.error(f"❌ Failed to refresh token: {response.status_code} - {response.text}")
                return self.access_token
                
        except Exception as e:
            logger.error(f"❌ Error refreshing Zoom token: {e}")
            return self.access_token


class ZoomRecordingFetcher:
    """Automatically fetches and transcribes Zoom recordings"""
    
    def __init__(self, poll_interval: int = 300):
        """
        Initialize Zoom fetcher
        
        Args:
            poll_interval: How often to check for new recordings (seconds, default 5 minutes)
        """
        self.poll_interval = poll_interval
        self.token_manager = ZoomTokenManager()
        self.assemblyai_key = os.getenv('ASSEMBLYAI_API_KEY')
        
        if not self.token_manager.access_token:
            logger.error("ZOOM_ACCESS_TOKEN not set!")
        
        if not self.assemblyai_key:
            logger.error("ASSEMBLYAI_API_KEY not set!")
        else:
            aai.settings.api_key = self.assemblyai_key
        
        self.last_check_time = None
        logger.info(f"✅ ZoomRecordingFetcher initialized (poll every {poll_interval}s)")
    
    def get_zoom_recordings(self, from_date: Optional[str] = None) -> List[Dict]:
        """
        Fetch recordings from Zoom API
        
        Args:
            from_date: Start date in YYYY-MM-DD format (default: yesterday)
            
        Returns:
            List of recording objects
        """
        # Get fresh token (auto-refreshes if expired)
        access_token = self.token_manager.get_token()
        
        if not access_token:
            logger.error("Cannot fetch recordings: No valid Zoom access token")
            return []
        
        # Default: fetch recordings from last 24 hours
        if not from_date:
            yesterday = datetime.now() - timedelta(days=1)
            from_date = yesterday.strftime('%Y-%m-%d')
        
        to_date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            # Get list of users (teachers)
            users_url = "https://api.zoom.us/v2/users"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            users_response = requests.get(users_url, headers=headers)
            users_response.raise_for_status()
            users = users_response.json().get('users', [])
            
            logger.info(f"Found {len(users)} Zoom users")
            
            all_recordings = []
            
            # Fetch recordings for each user
            for user in users:
                user_id = user.get('id')
                user_email = user.get('email')
                
                recordings_url = f"https://api.zoom.us/v2/users/{user_id}/recordings"
                params = {
                    'from': from_date,
                    'to': to_date,
                    'page_size': 100
                }
                
                recordings_response = requests.get(recordings_url, headers=headers, params=params)
                
                if recordings_response.status_code == 200:
                    meetings = recordings_response.json().get('meetings', [])
                    logger.info(f"User {user_email}: {len(meetings)} recordings")
                    
                    for meeting in meetings:
                        meeting['teacher_email'] = user_email
                        all_recordings.append(meeting)
                else:
                    logger.warning(f"Failed to fetch recordings for {user_email}: {recordings_response.status_code}")
            
            logger.info(f"Total recordings fetched: {len(all_recordings)}")
            return all_recordings
            
        except Exception as e:
            logger.error(f"Error fetching Zoom recordings: {e}", exc_info=True)
            return []
    
    def check_if_already_processed(self, meeting_id: str) -> bool:
        """Check if recording already exists in Supabase"""
        try:
            if not supabase_client:
                logger.error("Cannot query Supabase: Supabase client not initialized")
                return False

            response = supabase_client.table('zoom_summaries')\
                .select('id')\
                .eq('meeting_id', meeting_id)\
                .limit(1)\
                .execute()
            
            return len(response.data) > 0
            
        except Exception as e:
            logger.error(f"Error checking if recording exists: {e}")
            return False
    
    def download_transcript_file(self, download_url: str, access_token: str) -> Optional[str]:
        """
        Download transcript file (VTT/TXT) from Zoom
        
        Args:
            download_url: URL to download transcript
            access_token: Zoom access token
            
        Returns:
            Transcript content as string or None
        """
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(download_url, headers=headers)
            response.raise_for_status()
            
            logger.info(f"✅ Downloaded transcript file")
            return response.text
            
        except Exception as e:
            logger.error(f"Error downloading transcript: {e}")
            return None
    
    def clean_vtt_transcript(self, vtt_content: str) -> str:
        """
        Clean VTT transcript format to plain text
        
        Args:
            vtt_content: Raw VTT content
            
        Returns:
            Cleaned transcript text
        """
        lines = []
        for line in vtt_content.split('\n'):
            line = line.strip()
            # Skip VTT headers, timestamps, and empty lines
            if (line and 
                not line.startswith('WEBVTT') and
                not line.startswith('NOTE') and
                not '-->' in line and
                not line.isdigit()):
                lines.append(line)
        
        return '\n'.join(lines)
    
    def download_recording(self, download_url: str, access_token: str) -> Optional[str]:
        """
        Download recording file from Zoom
        
        Args:
            download_url: URL to download recording
            access_token: Zoom access token
            
        Returns:
            Path to downloaded file or None
        """
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(download_url, headers=headers, stream=True)
            response.raise_for_status()
            
            # Save to temp file
            filename = f"temp_recording_{int(time.time())}.mp4"
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Downloaded recording to {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Error downloading recording: {e}")
            return None
    
    def transcribe_audio(self, audio_file: str) -> Optional[str]:
        """
        Transcribe audio file using AssemblyAI
        
        Args:
            audio_file: Path to audio file
            
        Returns:
            Transcript text or None
        """
        if not self.assemblyai_key:
            logger.error("Cannot transcribe: ASSEMBLYAI_API_KEY not set")
            return None
        
        try:
            logger.info(f"Transcribing {audio_file}...")
            
            transcriber = aai.Transcriber()
            transcript = transcriber.transcribe(audio_file)
            
            if transcript.status == aai.TranscriptStatus.error:
                logger.error(f"Transcription failed: {transcript.error}")
                return None
            
            logger.info(f"✅ Transcription complete ({len(transcript.text)} chars)")
            return transcript.text
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}", exc_info=True)
            return None
    
    def store_transcript(self, meeting_data: Dict, transcript: str, 
                        transcription_source: str = 'zoom_native_transcript',
                        transcription_service: str = 'Zoom') -> bool:
        """
        Store transcript in Supabase
        
        Args:
            meeting_data: Zoom meeting metadata
            transcript: Transcribed text
            transcription_source: Source of transcription
            transcription_service: Service used for transcription
            
        Returns:
            True if successful
        """
        if not supabase_client:
            logger.error("Cannot store transcript: Supabase client not initialized")
            return False

        try:
            # Extract metadata
            meeting_id = meeting_data.get('id')
            topic = meeting_data.get('topic', 'Unknown')
            start_time = meeting_data.get('start_time', '')
            teacher_email = meeting_data.get('teacher_email', '')
            
            # Parse date and time
            if start_time:
                dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                meeting_date = dt.strftime('%Y-%m-%d')
                meeting_time = dt.strftime('%H:%M:%S')
            else:
                meeting_date = datetime.now().strftime('%Y-%m-%d')
                meeting_time = datetime.now().strftime('%H:%M:%S')
            
            # TODO: Extract user_id, teacher_id, class_id from meeting topic or metadata
            # For now, use placeholders - you'll need to implement your own logic
            user_id = self.extract_user_id(topic, teacher_email)
            teacher_id = self.extract_teacher_id(teacher_email)
            class_id = self.extract_class_id(topic)
            
            data = {
                'user_id': user_id,
                'teacher_id': teacher_id,
                'class_id': class_id,
                'meeting_id': str(meeting_id),
                'meeting_topic': topic,
                'meeting_date': meeting_date,
                'meeting_time': meeting_time,
                'teacher_email': teacher_email,
                'transcript': transcript,
                'transcript_length': len(transcript),
                'transcript_source': transcription_source,
                'transcription_service': transcription_service,
                'processing_mode': 'auto_fetch',
                'transcription_status': 'completed',
                'transcription_completed_at': datetime.utcnow().isoformat(),
                'created_at': datetime.utcnow().isoformat()
            }
            
            response = supabase_client.table('zoom_summaries').insert(data).execute()
            
            if response.data:
                logger.info(f"✅ Transcript stored in Supabase (ID: {response.data[0].get('id')})")
                return True
            else:
                logger.error("Failed to store transcript")
                return False
                
        except Exception as e:
            logger.error(f"Error storing transcript: {e}", exc_info=True)
            return False
    
    def extract_user_id(self, topic: str, teacher_email: str) -> str:
        """
        Extract user_id from meeting topic or email
        
        TODO: Implement your own logic based on your naming convention
        Example: "English Lesson - Student John" → extract "john"
        """
        # Placeholder - implement your logic
        return "student_placeholder"
    
    def extract_teacher_id(self, teacher_email: str) -> str:
        """
        Extract teacher_id from email
        
        TODO: Implement your own logic
        Example: "teacher@example.com" → "teacher_123"
        """
        # Placeholder - implement your logic
        return teacher_email.split('@')[0]
    
    def extract_class_id(self, topic: str) -> str:
        """
        Extract class_id from meeting topic
        
        TODO: Implement your own logic
        Example: "English Lesson - Class 5A" → "class_5a"
        """
        # Placeholder - implement your logic
        return "class_placeholder"
    
    def process_recording(self, meeting: Dict) -> bool:
        """
        Process a single Zoom recording
        
        Args:
            meeting: Zoom meeting object
            
        Returns:
            True if successful
        """
        meeting_id = meeting.get('id')
        topic = meeting.get('topic', 'Unknown')
        
        try:
            logger.info(f"Processing recording: {meeting_id} - {topic}")
            
            # Check if already processed
            if self.check_if_already_processed(str(meeting_id)):
                logger.info(f"Recording {meeting_id} already processed, skipping")
                return True
            
            # Get recording files
            recording_files = meeting.get('recording_files', [])
            
            if not recording_files:
                logger.warning(f"No recording files found for meeting {meeting_id}")
                return False
            
            # PRIORITY 1: Check for Zoom native transcript (VTT/TXT) - FASTEST & FREE
            transcript_file = None
            for file in recording_files:
                rec_type = (file.get('recording_type') or '').lower()
                file_type = (file.get('file_type') or '').lower()
                
                if 'audio_transcript' in rec_type or 'transcript' in rec_type:
                    transcript_file = file
                    break
                if file_type in ['vtt', 'txt']:
                    transcript_file = file
                    break
            
            # If transcript exists, download it directly (no transcription needed!)
            if transcript_file:
                logger.info(f"✅ Found Zoom native transcript for {meeting_id}")
                download_url = transcript_file.get('download_url')
                if download_url:
                    access_token = self.token_manager.get_token()
                    transcript_content = self.download_transcript_file(download_url, access_token)
                    if transcript_content:
                        transcript = self.clean_vtt_transcript(transcript_content)
                        transcription_source = 'zoom_native_transcript'
                        transcription_service = 'Zoom'
                    else:
                        logger.warning(f"Failed to download transcript for {meeting_id}")
                        return False
                else:
                    logger.warning(f"No download URL for transcript {meeting_id}")
                    return False
            else:
                # PRIORITY 2: No transcript - find audio file for AssemblyAI transcription
                logger.info(f"⚠️ No native transcript, will transcribe audio for {meeting_id}")
                audio_file = None
                for file in recording_files:
                    rec_type = file.get('recording_type', '')
                    file_type = (file.get('file_type') or '').lower()
                    
                    # Prefer audio_only, then m4a/mp3 (NOT mp4 video!)
                    if rec_type == 'audio_only':
                        audio_file = file
                        break
                    if file_type in ['m4a', 'mp3', 'wav', 'aac']:
                        audio_file = file
                        break
                
                if not audio_file:
                    logger.warning(f"No audio file found for meeting {meeting_id}")
                    return False
                
                download_url = audio_file.get('download_url')
                if not download_url:
                    logger.warning(f"No download URL for meeting {meeting_id}")
                    return False
                
                # Download audio (get fresh token)
                access_token = self.token_manager.get_token()
                local_file = self.download_recording(download_url, access_token)
                if not local_file:
                    return False
                
                # Transcribe with AssemblyAI
                transcript = self.transcribe_audio(local_file)
                transcription_source = 'assemblyai'
                transcription_service = 'AssemblyAI'
                
                # Clean up downloaded file
                try:
                    os.remove(local_file)
                    logger.info(f"Cleaned up {local_file}")
                except:
                    pass
                
                if not transcript:
                    return False
            
            # Store in Supabase
            success = self.store_transcript(meeting, transcript, transcription_source, transcription_service)
            
            if success:
                logger.info(f"✅ Successfully processed recording {meeting_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error processing recording {meeting_id}: {e}", exc_info=True)
            return False
    
    def run_once(self):
        """Run one fetch cycle"""
        logger.info("🔄 Checking for new Zoom recordings...")
        
        recordings = self.get_zoom_recordings()
        
        if not recordings:
            logger.info("No new recordings found")
            return
        
        success_count = 0
        fail_count = 0
        skip_count = 0
        
        for recording in recordings:
            meeting_id = recording.get('id')
            
            # Check if already processed
            if self.check_if_already_processed(str(meeting_id)):
                skip_count += 1
                continue
            
            if self.process_recording(recording):
                success_count += 1
            else:
                fail_count += 1
            
            # Delay between recordings to avoid rate limits
            time.sleep(5)
        
        logger.info(
            f"✅ Fetch complete: {success_count} processed, "
            f"{skip_count} skipped, {fail_count} failed"
        )
    
    def run_forever(self):
        """Run continuous fetch loop"""
        logger.info(f"🚀 Starting Zoom recording fetcher (checking every {self.poll_interval}s)")
        
        while True:
            try:
                self.run_once()
                
                # Wait before next check
                logger.info(f"⏳ Waiting {self.poll_interval}s before next check...")
                time.sleep(self.poll_interval)
                
            except KeyboardInterrupt:
                logger.info("🛑 Stopping Zoom fetcher...")
                break
            except Exception as e:
                logger.error(f"Error in fetch loop: {e}", exc_info=True)
                time.sleep(self.poll_interval)


def start_fetcher():
    """Start the Zoom fetcher"""
    poll_interval = int(os.getenv('ZOOM_FETCH_INTERVAL', '300'))  # Default: 5 minutes
    fetcher = ZoomRecordingFetcher(poll_interval=poll_interval)
    fetcher.run_forever()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    start_fetcher()
