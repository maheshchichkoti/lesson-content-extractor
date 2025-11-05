"""
Populate Game Tables from Existing Zoom Summaries
Production-ready script to migrate transcript data to game tables
"""
import os
import sys
from dotenv import load_dotenv
from supabase import create_client
from src.main import LessonProcessor

# Load environment
load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

def main():
    """Populate game tables from existing zoom_summaries"""
    
    print("\n" + "="*70)
    print("🎮 GAME TABLE POPULATOR - Migrate Transcripts to Games")
    print("="*70)
    
    # Validate environment
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("\n❌ Error: SUPABASE_URL and SUPABASE_KEY must be set in .env")
        sys.exit(1)
    
    # Initialize
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    processor = LessonProcessor(populate_games=True)
    
    if not processor.populate_games:
        print("\n❌ Error: Game populator initialization failed")
        print("Check your Supabase credentials and connection")
        sys.exit(1)
    
    print("\n✅ Connected to Supabase")
    print("✅ Game populator initialized\n")
    
    # Fetch all zoom_summaries
    print("📊 Fetching zoom_summaries from database...")
    try:
        response = supabase.table('zoom_summaries')\
            .select('id, user_id, lesson_number, transcript, flashcards, spelling')\
            .order('lesson_number')\
            .execute()
        
        summaries = response.data
        
        if not summaries:
            print("\n⚠️  No zoom_summaries found in database")
            print("Please run transcription first to generate content")
            sys.exit(0)
        
        print(f"✅ Found {len(summaries)} zoom_summaries\n")
        
    except Exception as e:
        print(f"\n❌ Error fetching summaries: {e}")
        sys.exit(1)
    
    # Process each summary
    total_stats = {
        'word_lists': 0,
        'cloze_items': 0,
        'grammar_questions': 0,
        'sentence_items': 0
    }
    
    for i, summary in enumerate(summaries, 1):
        zoom_id = summary['id']
        user_id = summary['user_id']
        lesson_num = summary.get('lesson_number', i)
        transcript = summary.get('transcript', '')
        
        print(f"\n{'='*70}")
        print(f"Processing Summary {i}/{len(summaries)}")
        print(f"  ID: {zoom_id}")
        print(f"  Lesson: {lesson_num}")
        print(f"  User: {user_id}")
        print(f"{'='*70}")
        
        if not transcript:
            print("⚠️  No transcript found, skipping...")
            continue
        
        try:
            # Process transcript to extract content
            print("\n[STEP 1] Extracting content from transcript...")
            exercises = processor.process_lesson(transcript, lesson_num)
            
            # Populate game tables
            print("\n[STEP 2] Populating game tables...")
            results = processor.populate_game_tables(
                exercises=exercises,
                lesson_number=lesson_num,
                user_id=user_id,
                zoom_summary_id=zoom_id
            )
            
            # Update totals
            for key in total_stats:
                total_stats[key] += results.get(key, 0)
            
            print(f"\n✅ Completed summary {zoom_id}")
            
        except Exception as e:
            print(f"\n❌ Error processing summary {zoom_id}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Final summary
    print("\n" + "="*70)
    print("🎉 MIGRATION COMPLETE")
    print("="*70)
    print(f"\n📊 Total Items Created:")
    print(f"   • Word Lists: {total_stats['word_lists']}")
    print(f"   • Advanced Cloze Items: {total_stats['cloze_items']}")
    print(f"   • Grammar Questions: {total_stats['grammar_questions']}")
    print(f"   • Sentence Builder Items: {total_stats['sentence_items']}")
    print(f"\n   TOTAL: {sum(total_stats.values())} items across all games")
    print("="*70)
    
    print("\n✅ All game tables populated successfully!")
    print("\n📋 Next Steps:")
    print("   1. Verify data in Supabase dashboard")
    print("   2. Run game API tests: python tests/test-games.py")
    print("   3. Test frontend with populated data\n")

if __name__ == "__main__":
    main()
