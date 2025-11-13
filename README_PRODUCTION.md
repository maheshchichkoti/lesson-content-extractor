# 🎓 Tulkka AI Backend - Production Ready

**Transform lesson transcripts into structured learning exercises and interactive games.**

[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.11-blue)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green)]()
[![MySQL](https://img.shields.io/badge/MySQL-8.0-orange)]()

---

## 🎯 What This Does

This AI-powered backend:
1. **Processes Zoom lesson transcripts** via AssemblyAI
2. **Generates educational content** using Google Gemini AI
3. **Stores exercises** in Supabase (temporary approval queue)
4. **Serves game content** from MySQL (production database)
5. **Tracks student progress** and mistakes

### Supported Game Types
- 📚 **Flashcards** - Vocabulary learning
- ✍️ **Spelling Bee** - Word spelling practice
- 🧩 **Advanced Cloze** - Fill-in-the-blank exercises
- 📖 **Grammar Challenge** - Grammar questions
- 🗣️ **Sentence Builder** - Word order practice

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    SUPABASE (Temporary)                 │
│  • zoom_summaries (transcripts)                         │
│  • lesson_exercises (pending approval)                  │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│                  FastAPI Backend (This Repo)            │
│  • Transcript processing                                │
│  • AI content generation                                │
│  • Game content API                                     │
│  • Progress tracking                                    │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│                    MySQL (Production)                   │
│  • word_lists, words                                    │
│  • cloze_topics, cloze_lessons, cloze_items            │
│  • grammar_categories, grammar_lessons, questions       │
│  • sentence_topics, sentence_lessons, sentence_items    │
│  • game_sessions, game_results, user_mistakes          │
└─────────────────────────────────────────────────────────┘
```

---

## ⚡ Quick Start

### Using Docker (Recommended)

```bash
# 1. Clone repository
git clone <your-repo-url>
cd lesson-content-extractor

# 2. Configure environment
cp .env.example .env
nano .env  # Add your credentials

# 3. Start everything
docker-compose up -d

# 4. Verify
curl http://localhost:8000/health

# 5. Run tests
python tests/test-games.py
```

### Manual Setup

```bash
# 1. Install Python 3.11+
python --version

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up MySQL
mysql -u root -p < sql/mysql_schema.sql
mysql -u root -p < sql/seed_game_data.sql

# 4. Configure .env
cp .env.example .env
# Edit .env with your credentials

# 5. Run server
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

---

## 📝 Environment Variables

### Required

```env
# Supabase (for transcript storage)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key

# MySQL (for game content)
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=tulkka_user
MYSQL_PASSWORD=your-password
MYSQL_DATABASE=tulkka9

# AI Services
GOOGLE_API_KEY=your-google-key
GEMINI_API_KEY=your-gemini-key
```

### Optional

```env
# AssemblyAI (for transcription)
ASSEMBLYAI_API_KEY=your-assemblyai-key

# App Configuration
ENVIRONMENT=production
POPULATE_GAMES_ON_API=true
LOG_LEVEL=INFO
```

---

## 🧪 Testing

### Run Full Test Suite

```bash
python tests/test-games.py
```

**Expected Output:**
```
[Health Check]
[Create Word List]
[List Word Lists]
...
==============================================
 All documented game endpoints verified successfully
==============================================
Exit code: 0
```

### Test Individual Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Get word lists
curl "http://localhost:8000/api/v1/word-lists?user_id=test&class_id=test&limit=10"

# Get cloze topics
curl http://localhost:8000/api/v1/cloze/topics

# API documentation
open http://localhost:8000/docs
```

---

## 📚 API Endpoints

### Health & Status
- `GET /health` - System health check

### Content Processing
- `POST /api/v1/process` - Process single transcript
- `POST /api/v1/process-zoom-lesson` - Process Zoom lesson
- `GET /api/v1/exercises` - Get generated exercises

### Flashcards & Spelling
- `GET /api/v1/word-lists` - List word lists
- `POST /api/v1/word-lists` - Create word list
- `POST /api/v1/words` - Add word to list
- `PUT /api/v1/words/{id}` - Update word

### Advanced Cloze
- `GET /api/v1/cloze/topics` - Get topics
- `GET /api/v1/cloze/lessons` - Get lessons
- `GET /api/v1/cloze/items` - Get cloze items

### Grammar Challenge
- `GET /api/v1/grammar/categories` - Get categories
- `GET /api/v1/grammar/lessons` - Get lessons
- `GET /api/v1/grammar/questions` - Get questions

### Sentence Builder
- `GET /api/v1/sentence/topics` - Get topics
- `GET /api/v1/sentence/lessons` - Get lessons
- `GET /api/v1/sentence/items` - Get sentence items

### Progress Tracking
- `POST /api/v1/sessions/start` - Start game session
- `POST /api/v1/sessions/{id}/result` - Record result
- `POST /api/v1/sessions/{id}/complete` - Complete session
- `GET /api/v1/progress/{user_id}` - Get user progress
- `GET /api/v1/mistakes/{user_id}` - Get user mistakes

**Full API documentation:** http://localhost:8000/docs

---

## 🗄️ Database Schema

### Supabase Tables (Temporary)
- `zoom_summaries` - Zoom meeting transcripts
- `lesson_exercises` - Generated exercises awaiting approval

### MySQL Tables (Production)

**Game Content:**
- `word_lists`, `words` - Flashcard content
- `cloze_topics`, `cloze_lessons`, `cloze_items` - Cloze exercises
- `grammar_categories`, `grammar_lessons`, `grammar_questions` - Grammar content
- `sentence_topics`, `sentence_lessons`, `sentence_items` - Sentence building

**Progress Tracking:**
- `game_sessions` - Active game sessions
- `game_results` - Completed game results
- `user_mistakes` - Student mistakes for review

See `mysql_schema.sql` for complete schema.

---

## 🚀 Deployment

### Docker Deployment

```bash
# Build and run
docker-compose up -d

# View logs
docker logs tulkka_api -f

# Stop services
docker-compose down
```

### Cloud Platforms

**Render.com:**
1. Connect GitHub repo
2. Set build: `pip install -r requirements.txt`
3. Set start: `uvicorn api:app --host 0.0.0.0 --port $PORT`
4. Add environment variables

**AWS EC2:**
```bash
ssh -i key.pem ubuntu@ec2-ip
sudo apt-get install docker.io docker-compose
git clone <repo>
docker-compose up -d
```

**Fly.io:**
```bash
flyctl launch
flyctl secrets set SUPABASE_URL=... MYSQL_HOST=...
flyctl deploy
```

See `PRODUCTION_DEPLOYMENT.md` for detailed instructions.

---

## 🔧 Configuration

### Rate Limiting
Default: 60 requests/minute per IP
Configure in `api.py`:
```python
@limiter.limit("60/minute")
```

### Logging
- Console output + rotating file (`api.log`)
- Max 10MB per file, 5 backup files
- Configurable via `LOG_LEVEL` env var

### CORS
Default: Allow all origins (development)
Production: Set `ALLOWED_ORIGINS` in `.env`

---

## 🐛 Troubleshooting

### Tests Fail with 404

**Problem:** No seed data in database

**Solution:**
```bash
mysql -u root -p tulkka9 < sql/seed_game_data.sql
```

### MySQL Connection Error

**Problem:** Can't connect to MySQL

**Solutions:**
- Check MySQL is running: `docker ps | grep mysql`
- Verify credentials in `.env`
- Check MySQL logs: `docker logs tulkka_mysql`

### Supabase 503 Error

**Problem:** Supabase not configured

**Solutions:**
- Add `SUPABASE_URL` and `SUPABASE_KEY` to `.env`
- Verify Supabase project is active
- Check tables exist: `zoom_summaries`, `lesson_exercises`

### API Returns 500 with trace_id

**Problem:** Internal server error

**Solutions:**
- Check logs: `tail -f api.log`
- Search for trace_id in logs
- Verify all environment variables are set

---

## 📊 Monitoring

### Health Checks

```bash
# Application health
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "databases": {
    "supabase": "connected",
    "mysql": "connected"
  }
}
```

### Logs

```bash
# Application logs
tail -f api.log

# Docker logs
docker logs tulkka_api -f
```

### Metrics
- Request duration logged for each endpoint
- Exception traces with unique IDs
- Database connection status

---

## 🔒 Security

- ✅ Rate limiting enabled (slowapi)
- ✅ Parameterized SQL queries (no injection)
- ✅ Environment-based secrets
- ✅ CORS configuration
- ✅ Exception handling with trace IDs
- ⚠️ Add JWT authentication for production
- ⚠️ Enable HTTPS/TLS
- ⚠️ Restrict CORS origins

---

## 📦 Project Structure

```
lesson-content-extractor/
├── api.py                      # Main FastAPI application
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container definition
├── docker-compose.yml          # Multi-container setup
├── .env.example                # Environment template
├── sql/
│   ├── mysql_schema.sql        # Database schema
│   └── seed_game_data.sql      # Sample data
├── tests/
│   └── test-games.py           # Integration tests
├── src/
│   ├── main.py                 # LessonProcessor
│   ├── middleware.py           # Rate limiting
│   ├── utils/                  # Utilities
│   ├── extractors/             # Content extractors
│   └── generators/             # Game generators
└── docs/
    ├── README_PRODUCTION.md    # This file
    └── PRODUCTION_DEPLOYMENT.md # Deployment guide
```

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing`
3. Make changes and test: `python tests/test-games.py`
4. Commit: `git commit -m 'Add amazing feature'`
5. Push: `git push origin feature/amazing`
6. Open Pull Request

---

## 📄 License

[Your License Here]

---

## 🆘 Support

- **Documentation:** See `/docs` folder
- **API Docs:** http://localhost:8000/docs
- **Issues:** [GitHub Issues]
- **Email:** [Your Email]

---

## ✅ Production Checklist

Before deploying to production:

- [ ] All environment variables configured
- [ ] MySQL schema loaded
- [ ] Seed data populated
- [ ] Tests passing (exit code 0)
- [ ] Health endpoint returns "healthy"
- [ ] Logs configured and rotating
- [ ] Rate limiting enabled
- [ ] CORS restricted to frontend domain
- [ ] HTTPS/SSL enabled
- [ ] Automated backups configured
- [ ] Monitoring/alerting set up
- [ ] Security review completed

**Your system is production-ready! 🎉**
