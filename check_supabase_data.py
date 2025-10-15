"""Script to check what data exists in Supabase zoom_summaries table"""

import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

def check_supabase_data():
    """Check what data exists in the zoom_summaries table"""
    
    # Get credentials from .env
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    
    if not url or not key:
        print("❌ Error: SUPABASE_URL or SUPABASE_KEY not found in .env file")
        return
    
    try:
        # Connect to Supabase
        print("🔌 Connecting to Supabase...")
        client = create_client(url, key)
        print("✅ Connected successfully!\n")
        
        # Check if table exists and has data
        print("📊 Checking zoom_summaries table...\n")
        
        # Get total count
        response = client.table('zoom_summaries').select('id', count='exact').execute()
        total_count = len(response.data)
        
        print(f"📈 Total records in table: {total_count}\n")
        
        if total_count == 0:
            print("⚠️  The table is EMPTY. No Zoom transcripts have been processed yet.")
            print("\n💡 This means:")
            print("   1. The Zoom recording system hasn't run yet, OR")
            print("   2. No meetings have been recorded, OR")
            print("   3. You need to wait for the lead's system to process recordings")
            return
        
        # Get sample records
        print("📋 Sample records from the table:\n")
        response = client.table('zoom_summaries').select(
            'id, user_id, teacher_id, class_id, meeting_date, meeting_topic, teacher_email, transcript_length'
        ).limit(10).execute()
        
        if response.data:
            print(f"Found {len(response.data)} sample records:\n")
            print("-" * 100)
            
            for i, record in enumerate(response.data, 1):
                print(f"\n📝 Record {i}:")
                print(f"   ID: {record.get('id')}")
                print(f"   User ID: {record.get('user_id')}")
                print(f"   Teacher ID: {record.get('teacher_id')}")
                print(f"   Class ID: {record.get('class_id')}")
                print(f"   Meeting Date: {record.get('meeting_date')}")
                print(f"   Meeting Topic: {record.get('meeting_topic')}")
                print(f"   Teacher Email: {record.get('teacher_email')}")
                print(f"   Transcript Length: {record.get('transcript_length')} chars")
            
            print("\n" + "=" * 100)
            print("\n✅ You can use any of these values to test your Zoom endpoint!")
            print("\n📝 Example API call with first record:")
            
            first_record = response.data[0]
            print(f"""
curl --location 'http://localhost:8000/api/v1/process-zoom-lesson' \\
--header 'Content-Type: application/json' \\
--data '{{
  "user_id": "{first_record.get('user_id')}",
  "teacher_id": "{first_record.get('teacher_id')}",
  "class_id": "{first_record.get('class_id')}",
  "date": "{first_record.get('meeting_date')}",
  "lesson_number": 1
}}'
""")
        else:
            print("⚠️  No data returned from query")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Possible issues:")
        print("   1. Invalid Supabase credentials")
        print("   2. Table doesn't exist yet")
        print("   3. Network connection issue")


if __name__ == "__main__":
    print("\n" + "=" * 100)
    print("🔍 SUPABASE DATABASE CHECKER")
    print("=" * 100 + "\n")
    
    check_supabase_data()
    
    print("\n" + "=" * 100)
    print("✅ Check complete!")
    print("=" * 100 + "\n")