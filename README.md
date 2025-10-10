# Lesson Content Extractor & Exercise Generator

Automatically transforms raw lesson transcripts into structured learning exercises for language learning applications.

## 🎯 Features

- **Smart Content Extraction**: Identifies vocabulary, mistakes, and practice sentences
- **Multi-Type Exercise Generation**:
  - Fill-in-the-blank with realistic distractors
  - Flashcards with translations and examples
  - Spelling exercises with sample sentences
- **Production-Ready**: Hybrid approach with AI enhancement and rule-based fallback
- **Quality Assured**: Automated validation ensures zero typos and consistent structure

## 📊 Output

Generates **3 CSV files per lesson**:
1. `lesson_N_fill_in_blank.csv` - Multiple choice exercises
2. `lesson_N_flashcards.csv` - Vocabulary cards with translations
3. `lesson_N_spelling.csv` - Spelling practice with context

Additionally generates:
- Combined Excel file with all exercises
- Detailed methodology report

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip (Python package manager)

### Installation & Running

#### Option 1: Using Script (Recommended)
```bash
# Unix/Mac/Linux
chmod +x run.sh
./run.sh

# Windows
run.bat