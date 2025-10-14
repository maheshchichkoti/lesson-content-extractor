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

#### Option 1: REST API (Production-Ready)

**1. Install dependencies:**

```bash
pip install -r requirements.txt
```

**2. Start the API server:**

```bash
python api.py
```

Or using uvicorn:

```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

**3. Access the API:**

- **Interactive Docs:** http://localhost:8000/docs
- **API Endpoint:** http://localhost:8000/api/v1/process
- **Health Check:** http://localhost:8000/health

**4. Test with Postman:**

POST to `http://localhost:8000/api/v1/process`

Request body:

```json
{
  "transcript": "Your lesson transcript here...",
  "lesson_number": 1
}
```

#### Option 2: Using Script (Command Line)

```bash
# Unix/Mac/Linux
chmod +x run.sh
./run.sh

# Windows
run.bat
```
