# 🚀 Quick Start Guide - Tulkka Games API

## ⚡ Get Started in 5 Minutes

### 1️⃣ **Setup Environment** (2 minutes)
```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your Supabase credentials
# SUPABASE_URL=https://xxxxx.supabase.co
# SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
# JWT_SECRET=your-secret-key-min-32-chars
```

### 2️⃣ **Install Dependencies** (1 minute)
```bash
# Create virtual environment
python -m venv .venv

# Activate it
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install packages
pip install -r requirements.txt
```

### 3️⃣ **Setup Database** (1 minute)
Go to Supabase SQL Editor and run the SQL from `DEPLOYMENT_GUIDE.md` (Step 2.1)

### 4️⃣ **Start API** (30 seconds)
```bash
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

### 5️⃣ **Test It** (30 seconds)
```powershell
# Run test script
.\test-games-api.ps1

# Or open browser
# http://localhost:8000/docs
```

---

## 📚 **What You Get**

### 🎮 **6 Game APIs**
1. **Word Lists** - Manage vocabulary lists
2. **Flashcards** - Practice with flashcards
3. **Spelling Bee** - Spelling practice with audio
4. **Advanced Cloze** - Fill-in-the-blank exercises
5. **Grammar Challenge** - Multiple choice grammar
6. **Sentence Builder** - Build sentences from tokens

### 🔌 **42 API Endpoints**
- 9 Word Lists endpoints
- 5 Flashcards endpoints
- 5 Spelling Bee endpoints
- 8 Advanced Cloze endpoints
- 9 Grammar Challenge endpoints
- 9 Sentence Builder endpoints
- Plus health check and docs

### 🛡️ **Production Features**
- ✅ Rate limiting (30-120 req/min)
- ✅ Error handling
- ✅ Request logging
- ✅ Input validation
- ✅ JWT auth ready (optional)
- ✅ CORS configured

---

## 📖 **Documentation**

| Document | Purpose |
|----------|---------|
| `QUICK_START.md` | This file - get started fast |
| `DEPLOYMENT_GUIDE.md` | Complete deployment instructions |
| `DATABASE_SCHEMA.md` | Database tables and structure |
| `PRODUCTION_CHECKLIST.md` | Pre-deployment checklist |
| `FINAL_AUDIT_REPORT.md` | Complete audit report |
| `test-games-api.ps1` | Automated test script |

---

## 🔗 **Useful Links**

- **API Docs:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Health Check:** http://localhost:8000/health

---

## 🆘 **Common Issues**

**"Supabase client not initialized"**
→ Check `.env` file has correct `SUPABASE_URL` and `SUPABASE_KEY`

**"Port 8000 already in use"**
→ Change port: `uvicorn api:app --port 8001`

**"Module not found"**
→ Activate virtual environment: `.venv\Scripts\activate`

**"No tests passing"**
→ Make sure API is running and database tables are created

---

## ✅ **You're Ready!**

Your API is now running at: **http://localhost:8000**

**Next Steps:**
1. Open http://localhost:8000/docs to see all endpoints
2. Run `.\test-games-api.ps1` to verify everything works
3. Read `DEPLOYMENT_GUIDE.md` for production deployment
4. Check `FINAL_AUDIT_REPORT.md` for complete details

**Happy coding! 🎉**
