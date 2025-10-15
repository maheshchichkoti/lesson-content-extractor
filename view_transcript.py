"""Script to view actual Zoom transcript content"""

import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

def view_transcript():
    """View the actual transcript content"""
    
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    
    if not url or not key:
        print("❌ Error: Missing credentials")
        return
    
    try:
        client = create_client(url, key)
        
        # Fetch the first transcript
        response = client.table('zoom_summaries').select(
            'transcript, meeting_topic, teacher_email'
        ).eq('user_id', 'user_124').eq('teacher_id', 'teacher_457').eq('class_id', 'class_789').eq('meeting_date', '2025-06-08').limit(1).execute()
        
        if response.data:
            record = response.data[0]
            transcript = record.get('transcript', '')
            
            print("\n" + "="*100)
            print(f"📝 TRANSCRIPT CONTENT")
            print("="*100)
            print(f"\nMeeting: {record.get('meeting_topic')}")
            print(f"Teacher: {record.get('teacher_email')}")
            print(f"Length: {len(transcript)} characters\n")
            print("-"*100)
            print("\nFirst 2000 characters:\n")
            print(transcript[:2000])
            print("\n" + "-"*100)
            print("\n...\n")
            print("-"*100)
            print("\nLast 500 characters:\n")
            print(transcript[-500:])
            print("\n" + "="*100)
        else:
            print("❌ No data found")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    view_transcript()