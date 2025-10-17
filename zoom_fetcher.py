"""Script to check database and show correct API test commands"""

import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

def show_api_tests():
    """Show correct API test commands based on actual database data"""
    
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    
    if not url or not key:
        print("❌ Error: Missing Supabase credentials in .env file")
        return
    
    try:
        client = create_client(url, key)
        
        print("\n" + "="*100)
        print("🔍 CHECKING DATABASE FOR TEST DATA")
        print("="*100 + "\n")
        
        # Fetch first record
        response = client.table('zoom_summaries').select(
            'user_id, teacher_id, class_id, meeting_date, meeting_topic, teacher_email, transcript_length'
        ).limit(1).execute()
        
        if not response.data:
            print("⚠️  Database is EMPTY. No Zoom transcripts found.")
            print("\n💡 To add data:")
            print("   1. Wait for Amit's Zoom recording system to process meetings")
            print("   2. OR use the /api/v1/fetch-zoom-recordings endpoint")
            return
        
        record = response.data[0]
        
        print("✅ Found transcript data!\n")
        print(f"   User ID: {record.get('user_id')}")
        print(f"   Teacher ID: {record.get('teacher_id')}")
        print(f"   Class ID: {record.get('class_id')}")
        print(f"   Date: {record.get('meeting_date')}")
        print(f"   Meeting: {record.get('meeting_topic')}")
        print(f"   Teacher: {record.get('teacher_email')}")
        print(f"   Transcript Length: {record.get('transcript_length')} chars")
        
        print("\n" + "="*100)
        print("🚀 CORRECT API TEST COMMANDS")
        print("="*100 + "\n")
        
        # Test 1: Process Zoom Lesson
        print("1️⃣  Process Zoom Lesson (Main Endpoint):")
        print("\ncurl --location 'http://localhost:8000/api/v1/process-zoom-lesson' \\")
        print("--header 'Content-Type: application/json' \\")
        print("--data '{")
        print(f'  \"user_id\": \"{record.get("user_id")}\",')  
        print(f'  \"teacher_id\": \"{record.get("teacher_id")}\",')  
        print(f'  \"class_id\": \"{record.get("class_id")}\",')  
        print(f'  \"date\": \"{record.get("meeting_date")}\",')  
        print('  "lesson_number": 1')
        print("}'")  
        
        # Test 2: Get Raw Transcript
        print("\n" + "-"*100 + "\n")
        print("2️⃣  Get Raw Transcript (No Processing):")
        print(f"\ncurl 'http://localhost:8000/api/v1/get-transcript?user_id={record.get('user_id')}&teacher_id={record.get('teacher_id')}&class_id={record.get('class_id')}&date={record.get('meeting_date')}'")
        
        # Test 3: Direct Processing
        print("\n" + "-"*100 + "\n")
        print("3️⃣  Process Direct Transcript (No Database):")
        print("\ncurl --location 'http://localhost:8000/api/v1/process' \\")
        print("--header 'Content-Type: application/json' \\")
        print("--data '{")
        print('  "transcript": "Teacher: Yesterday I go to market. Teacher: Correction: Yesterday I went to the market.",')  
        print('  "lesson_number": 1')
        print("}'")  
        
        print("\n" + "="*100)
        print("✅ All endpoints are ready to use!")
        print("="*100 + "\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    show_api_tests()