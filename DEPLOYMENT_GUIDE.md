# 🚀 Tulkka Games API - Deployment Guide

## 📋 Pre-Deployment Checklist

### ✅ **Files Verification**
Ensure all these files exist:
- [x] `api.py` - Main FastAPI application
- [x] `requirements.txt` - Python dependencies
- [x] `.env.example` - Environment variables template
- [x] `.gitignore` - Git ignore rules
- [x] `DATABASE_SCHEMA.md` - Database documentation
- [x] `PRODUCTION_CHECKLIST.md` - Production checklist
- [x] `test-games-api.ps1` - Test script
- [x] `src/games/` - All 6 game services
- [x] `src/middleware/` - Auth and rate limiting

---

## 🔧 **Step 1: Environment Setup**

### 1.1 Copy Environment File
```bash
cp .env.example .env
```

### 1.2 Edit `.env` File
Open `.env` and fill in your values:

```env
# REQUIRED - Get from Supabase Dashboard
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# REQUIRED - Generate a strong secret
JWT_SECRET=your-super-secret-key-min-32-characters-long

# OPTIONAL - For pronunciation features
GOOGLE_API_KEY=AIzaSy...
GEMINI_API_KEY=AIzaSy...

# OPTIONAL - For transcription
ASSEMBLYAI_API_KEY=...

# Application
ENVIRONMENT=production
```

**Generate JWT Secret:**
```bash
# Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# PowerShell
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Minimum 0 -Maximum 256 }))
```

---

## 🗄️ **Step 2: Database Setup**

### 2.1 Create Tables in Supabase

Go to Supabase SQL Editor and run:

```sql
-- ============================================================
-- SHARED TABLES (Required for all games)
-- ============================================================

-- Word Lists (for Flashcards & Spelling Bee)
CREATE TABLE IF NOT EXISTS word_lists (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    word_count INTEGER DEFAULT 0,
    is_favorite BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_word_lists_user_favorite ON word_lists(user_id, is_favorite);

-- Words
CREATE TABLE IF NOT EXISTS words (
    id TEXT PRIMARY KEY,
    list_id TEXT REFERENCES word_lists(id) ON DELETE CASCADE,
    word TEXT NOT NULL,
    translation TEXT,
    notes TEXT,
    practice_count INTEGER DEFAULT 0,
    correct_count INTEGER DEFAULT 0,
    accuracy INTEGER DEFAULT 0,
    is_favorite BOOLEAN DEFAULT FALSE,
    last_practiced TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_words_list_favorite ON words(list_id, is_favorite);

-- Game Sessions
CREATE TABLE IF NOT EXISTS game_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    game_type TEXT NOT NULL,
    mode TEXT NOT NULL,
    reference_id TEXT,
    progress_current INTEGER DEFAULT 0,
    progress_total INTEGER DEFAULT 0,
    correct INTEGER DEFAULT 0,
    incorrect INTEGER DEFAULT 0,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX idx_game_sessions_user_game_type ON game_sessions(user_id, game_type);
CREATE INDEX idx_game_sessions_completed ON game_sessions(user_id, completed_at);

-- Game Results
CREATE TABLE IF NOT EXISTS game_results (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    game_type TEXT NOT NULL,
    item_id TEXT NOT NULL,
    is_correct BOOLEAN NOT NULL,
    attempts INTEGER DEFAULT 1,
    time_spent_ms INTEGER DEFAULT 0,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_game_results_session ON game_results(session_id, game_type);

-- User Mistakes
CREATE TABLE IF NOT EXISTS user_mistakes (
    user_id TEXT NOT NULL,
    game_type TEXT NOT NULL,
    item_id TEXT NOT NULL,
    last_error_type TEXT,
    mistake_count INTEGER DEFAULT 1,
    last_attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, game_type, item_id)
);

CREATE INDEX idx_user_mistakes_user_game ON user_mistakes(user_id, game_type);

-- ============================================================
-- ADVANCED CLOZE TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS cloze_topics (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    icon TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cloze_lessons (
    id TEXT PRIMARY KEY,
    topic_id TEXT REFERENCES cloze_topics(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    item_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cloze_items (
    id TEXT PRIMARY KEY,
    topic_id TEXT REFERENCES cloze_topics(id),
    lesson_id TEXT REFERENCES cloze_lessons(id),
    difficulty TEXT CHECK(difficulty IN ('easy', 'medium', 'hard')),
    text_parts JSONB NOT NULL,
    options JSONB NOT NULL,
    correct JSONB NOT NULL,
    explanation TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cloze_items_topic ON cloze_items(topic_id, difficulty);
CREATE INDEX idx_cloze_items_lesson ON cloze_items(lesson_id, difficulty);

-- ============================================================
-- GRAMMAR CHALLENGE TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS grammar_categories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS grammar_lessons (
    id TEXT PRIMARY KEY,
    category_id TEXT REFERENCES grammar_categories(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    question_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS grammar_questions (
    id TEXT PRIMARY KEY,
    category_id TEXT REFERENCES grammar_categories(id),
    lesson_id TEXT REFERENCES grammar_lessons(id),
    difficulty TEXT CHECK(difficulty IN ('easy', 'medium', 'hard')),
    prompt TEXT NOT NULL,
    options JSONB NOT NULL,
    correct_index INTEGER NOT NULL,
    explanation TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_grammar_questions_category ON grammar_questions(category_id, difficulty);
CREATE INDEX idx_grammar_questions_lesson ON grammar_questions(lesson_id, difficulty);

-- ============================================================
-- SENTENCE BUILDER TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS sentence_topics (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sentence_lessons (
    id TEXT PRIMARY KEY,
    topic_id TEXT REFERENCES sentence_topics(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    item_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sentence_items (
    id TEXT PRIMARY KEY,
    topic_id TEXT REFERENCES sentence_topics(id),
    lesson_id TEXT REFERENCES sentence_lessons(id),
    difficulty TEXT CHECK(difficulty IN ('easy', 'medium', 'hard')),
    english TEXT NOT NULL,
    translation TEXT,
    tokens JSONB NOT NULL,
    accepted JSONB NOT NULL,
    distractors JSONB,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sentence_items_topic ON sentence_items(topic_id, difficulty);
CREATE INDEX idx_sentence_items_lesson ON sentence_items(lesson_id, difficulty);
```

### 2.2 Seed Sample Data (Optional)

```sql
-- Sample Cloze Topic
INSERT INTO cloze_topics (id, name, icon, description) VALUES
('topic_business', 'Business English', '💼', 'Professional communication and business vocabulary');

-- Sample Grammar Category
INSERT INTO grammar_categories (id, name) VALUES
('cat_tenses', 'Verb Tenses');

-- Sample Sentence Topic
INSERT INTO sentence_topics (id, name) VALUES
('topic_daily', 'Daily Conversations');
```

---

## 📦 **Step 3: Install Dependencies**

### 3.1 Create Virtual Environment
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
```

### 3.2 Install Requirements
```bash
pip install -r requirements.txt
```

### 3.3 Verify Installation
```bash
pip list | grep -E "fastapi|supabase|pydantic|slowapi"
```

---

## 🧪 **Step 4: Test the API**

### 4.1 Start the API (Development)
```bash
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

### 4.2 Run Test Script
```powershell
# In a new terminal
.\test-games-api.ps1
```

### 4.3 Manual Test
Open browser: `http://localhost:8000/docs`

Test health endpoint:
```bash
curl http://localhost:8000/health
```

---

## 🌐 **Step 5: Production Deployment**

### Option A: Deploy to Render/Railway/Fly.io

#### 5.1 Create `Procfile`
```
web: uvicorn api:app --host 0.0.0.0 --port $PORT --workers 4
```

#### 5.2 Set Environment Variables
In your hosting platform dashboard, add all variables from `.env`

#### 5.3 Deploy
```bash
git push origin main
```

### Option B: Deploy to VPS (Ubuntu)

#### 5.1 Install Dependencies
```bash
sudo apt update
sudo apt install python3-pip python3-venv nginx
```

#### 5.2 Clone Repository
```bash
git clone <your-repo-url>
cd lesson-content-extractor
```

#### 5.3 Setup Application
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### 5.4 Create Systemd Service
```bash
sudo nano /etc/systemd/system/tulkka-api.service
```

```ini
[Unit]
Description=Tulkka Games API
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/lesson-content-extractor
Environment="PATH=/path/to/lesson-content-extractor/.venv/bin"
ExecStart=/path/to/lesson-content-extractor/.venv/bin/uvicorn api:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

#### 5.5 Start Service
```bash
sudo systemctl daemon-reload
sudo systemctl start tulkka-api
sudo systemctl enable tulkka-api
sudo systemctl status tulkka-api
```

#### 5.6 Configure Nginx
```bash
sudo nano /etc/nginx/sites-available/tulkka-api
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/tulkka-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 📊 **Step 6: Monitoring**

### 6.1 Check Logs
```bash
# Application logs
tail -f api.log

# System logs (if using systemd)
sudo journalctl -u tulkka-api -f
```

### 6.2 Monitor Performance
```bash
# Check API health
curl https://your-domain.com/health

# Check response time
curl -w "@-" -o /dev/null -s https://your-domain.com/health <<'EOF'
    time_namelookup:  %{time_namelookup}\n
       time_connect:  %{time_connect}\n
    time_appconnect:  %{time_appconnect}\n
      time_redirect:  %{time_redirect}\n
   time_pretransfer:  %{time_pretransfer}\n
 time_starttransfer:  %{time_starttransfer}\n
                    ----------\n
         time_total:  %{time_total}\n
EOF
```

---

## 🔒 **Security Checklist**

- [ ] `.env` file is in `.gitignore`
- [ ] JWT_SECRET is strong (32+ characters)
- [ ] CORS origins are restricted in production
- [ ] Rate limiting is enabled
- [ ] HTTPS is configured (use Let's Encrypt)
- [ ] Database credentials are secure
- [ ] API keys are not hardcoded

---

## 🆘 **Troubleshooting**

### Issue: "Supabase client not initialized"
**Solution:** Check `SUPABASE_URL` and `SUPABASE_KEY` in `.env`

### Issue: "Rate limit exceeded"
**Solution:** Wait 1 minute or adjust rate limits in `api.py`

### Issue: "Module not found"
**Solution:** Ensure virtual environment is activated and dependencies installed

### Issue: "Port already in use"
**Solution:** 
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux
lsof -ti:8000 | xargs kill -9
```

---

## 📞 **Support**

For issues or questions:
1. Check logs: `tail -f api.log`
2. Review `PRODUCTION_CHECKLIST.md`
3. Run test script: `.\test-games-api.ps1`
4. Check database schema: `DATABASE_SCHEMA.md`

---

## ✅ **Post-Deployment Verification**

1. [ ] API is accessible at your domain
2. [ ] Health endpoint returns 200 OK
3. [ ] Test script passes all tests
4. [ ] Logs show no errors
5. [ ] Database connections are working
6. [ ] Rate limiting is functioning
7. [ ] CORS is properly configured

**Your API is now LIVE! 🎉**
