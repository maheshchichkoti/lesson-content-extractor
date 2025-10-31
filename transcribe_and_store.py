"""
Audio Transcription and Storage Script
Uses AssemblyAI to transcribe audio files and stores in Supabase
"""

import os
import sys
import time
import requests
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
ASSEMBLYAI_API_KEY = os.getenv('ASSEMBLYAI_API_KEY')
ASSEMBLYAI_BASE_URL = os.getenv('ASSEMBLYAI_BASE_URL', 'https://api.assemblyai.com/v2')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Initialize Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def transcribe_audio(audio_file_path: str) -> dict:
    """
    Transcribe audio file using AssemblyAI
    
    Args:
        audio_file_path: Path to audio file (MP3, MP4, M4A, WAV, etc.)
    
    Returns:
        dict with transcript text and metadata
    """
    
    if not os.path.exists(audio_file_path):
        raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
    
    print(f"\n{'='*60}")
    print(f"🎤 Transcribing: {os.path.basename(audio_file_path)}")
    print(f"{'='*60}\n")
    
    headers = {
        "authorization": ASSEMBLYAI_API_KEY,
        "content-type": "application/json"
    }
    
    # Step 1: Upload audio file
    print("📤 Step 1: Uploading audio file...")
    upload_url = f"{ASSEMBLYAI_BASE_URL}/upload"
    
    with open(audio_file_path, 'rb') as f:
        upload_response = requests.post(
            upload_url,
            headers={"authorization": ASSEMBLYAI_API_KEY},
            data=f
        )
    
    if upload_response.status_code != 200:
        raise Exception(f"Upload failed: {upload_response.text}")
    
    audio_url = upload_response.json()['upload_url']
    print(f"   ✓ Audio uploaded successfully")
    
    # Step 2: Request transcription
    print("\n🔄 Step 2: Requesting transcription...")
    transcript_url = f"{ASSEMBLYAI_BASE_URL}/transcript"
    
    transcript_request = {
        "audio_url": audio_url,
        "language_code": "en"  # Change if needed
    }
    
    transcript_response = requests.post(
        transcript_url,
        headers=headers,
        json=transcript_request
    )
    
    if transcript_response.status_code != 200:
        raise Exception(f"Transcription request failed: {transcript_response.text}")
    
    transcript_id = transcript_response.json()['id']
    print(f"   ✓ Transcription started (ID: {transcript_id})")
    
    # Step 3: Poll for completion
    print("\n⏳ Step 3: Waiting for transcription to complete...")
    polling_url = f"{ASSEMBLYAI_BASE_URL}/transcript/{transcript_id}"
    
    while True:
        polling_response = requests.get(polling_url, headers=headers)
        result = polling_response.json()
        
        status = result['status']
        
        if status == 'completed':
            transcript_text = result['text']
            print(f"\n   ✅ Transcription completed!")
            print(f"   📝 Length: {len(transcript_text)} characters")
            print(f"   ⏱️  Duration: {result.get('audio_duration', 0)} seconds")
            
            return {
                'transcript': transcript_text,
                'transcript_length': len(transcript_text),
                'audio_duration': result.get('audio_duration', 0),
                'confidence': result.get('confidence', 0),
                'words_count': len(transcript_text.split())
            }
        
        elif status == 'error':
            error_msg = result.get('error', 'Unknown error')
            raise Exception(f"Transcription failed: {error_msg}")
        
        else:
            print(f"   Status: {status}... (checking again in 3 seconds)")
            time.sleep(3)


def store_in_supabase(
    transcript_data: dict,
    user_id: str,
    teacher_id: str,
    class_id: str,
    meeting_date: str,
    meeting_topic: str = "Manual Upload"
) -> dict:
    """
    Store transcript in Supabase zoom_summaries table
    
    Args:
        transcript_data: Dict from transcribe_audio()
        user_id: Student user ID
        teacher_id: Teacher ID
        class_id: Class ID
        meeting_date: Date in YYYY-MM-DD format
        meeting_topic: Optional meeting topic
    
    Returns:
        Stored record from Supabase
    """
    
    print(f"\n{'='*60}")
    print("💾 Storing in Supabase...")
    print(f"{'='*60}\n")
    
    data = {
        'user_id': user_id,
        'teacher_id': teacher_id,
        'class_id': class_id,
        'meeting_date': meeting_date,
        'meeting_topic': meeting_topic,
        'transcript': transcript_data['transcript'],
        'transcript_length': transcript_data['transcript_length'],
        'transcript_source': 'manual_upload',
        'transcription_service': 'AssemblyAI',
        'transcription_status': 'completed',
        'processing_mode': 'audio_transcription',
        'processing_completed_at': datetime.utcnow().isoformat()
    }
    
    try:
        response = supabase.table('zoom_summaries').insert(data).execute()
        
        if response.data:
            record = response.data[0]
            print(f"   ✅ Stored successfully!")
            print(f"   🆔 Record ID: {record['id']}")
            print(f"   👤 User: {user_id}")
            print(f"   📅 Date: {meeting_date}")
            print(f"   📊 Length: {transcript_data['transcript_length']} chars")
            return record
        else:
            raise Exception("No data returned from Supabase")
    
    except Exception as e:
        print(f"   ❌ Error storing in Supabase: {e}")
        raise


def main():
    """Main function - Edit the parameters below"""
    
    print("\n" + "="*60)
    print("🎯 Audio Transcription & Storage Tool")
    print("="*60)
    
    # ========================================
    # EDIT THESE PARAMETERS
    # ========================================
    
    # Path to your audio file
    audio_file = "path/to/your/audio.mp4"  # CHANGE THIS
    
    # Metadata
    user_id = "student_123"          # CHANGE THIS
    teacher_id = "teacher_456"       # CHANGE THIS
    class_id = "class_789"           # CHANGE THIS
    meeting_date = "2025-10-30"      # CHANGE THIS (YYYY-MM-DD)
    meeting_topic = "English Lesson" # CHANGE THIS
    
    # ========================================
    
    # Validate inputs
    if not os.path.exists(audio_file):
        print(f"\n❌ Error: Audio file not found: {audio_file}")
        print("\n💡 Please edit the 'audio_file' variable in this script")
        sys.exit(1)
    
    if not ASSEMBLYAI_API_KEY:
        print("\n❌ Error: ASSEMBLYAI_API_KEY not found in .env file")
        sys.exit(1)
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("\n❌ Error: Supabase credentials not found in .env file")
        sys.exit(1)
    
    try:
        # Step 1: Transcribe audio
        transcript_data = transcribe_audio(audio_file)
        
        # Step 2: Store in Supabase
        record = store_in_supabase(
            transcript_data=transcript_data,
            user_id=user_id,
            teacher_id=teacher_id,
            class_id=class_id,
            meeting_date=meeting_date,
            meeting_topic=meeting_topic
        )
        
        # Success!
        print(f"\n{'='*60}")
        print("✅ SUCCESS! Transcript stored in Supabase")
        print(f"{'='*60}\n")
        
        print("📋 Next Steps:")
        print("   1. Verify in Supabase dashboard")
        print("   2. Call your API to process:")
        print(f"\n   POST /api/v1/process-zoom-lesson")
        print(f"   {{")
        print(f'     "user_id": "{user_id}",')
        print(f'     "teacher_id": "{teacher_id}",')
        print(f'     "class_id": "{class_id}",')
        print(f'     "date": "{meeting_date}",')
        print(f'     "lesson_number": 1')
        print(f"   }}\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()