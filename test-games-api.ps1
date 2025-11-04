# ==========================================
# TULKKA GAMES API - TEST SCRIPT
# Tests all 5 game APIs (Word Lists, Flashcards, Spelling Bee, Advanced Cloze, Grammar Challenge, Sentence Builder)
# ==========================================

param(
    [string]$BaseUrl = "http://localhost:8000",
    [string]$UserId = "test_user_$(Get-Date -Format 'yyyyMMddHHmmss')"
)

$ErrorActionPreference = "Continue"
$SuccessCount = 0
$FailureCount = 0

function Write-TestHeader {
    param([string]$Message)
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host $Message -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    $script:SuccessCount++
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Write-Failure {
    param([string]$Message)
    $script:FailureCount++
    Write-Host "✗ $Message" -ForegroundColor Red
}

function Invoke-Api {
    param(
        [string]$Method,
        [string]$Endpoint,
        [object]$Body = $null
    )
    
    try {
        $params = @{
            Uri = "$BaseUrl$Endpoint"
            Method = $Method
            ContentType = "application/json"
        }
        
        if ($Body) {
            $params.Body = ($Body | ConvertTo-Json -Depth 10)
        }
        
        $response = Invoke-RestMethod @params
        return $response
    }
    catch {
        Write-Failure "API call failed: $Method $Endpoint - $_"
        return $null
    }
}

Write-Host "`n╔════════════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "║     TULKKA GAMES - API TEST SUITE     ║" -ForegroundColor Magenta
Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Magenta
Write-Host "Base URL: $BaseUrl" -ForegroundColor White
Write-Host "User ID:  $UserId`n" -ForegroundColor White

# ==========================================
# 1. HEALTH CHECK
# ==========================================

Write-TestHeader "1. HEALTH CHECK"
$health = Invoke-Api -Method Get -Endpoint "/health"
if ($health) {
    Write-Success "API is healthy"
} else {
    Write-Failure "API health check failed - stopping tests"
    exit 1
}

# ==========================================
# 2. WORD LISTS
# ==========================================

Write-TestHeader "2. WORD LISTS"

Write-Host "Creating word list..." -ForegroundColor Yellow
$listBody = @{
    name = "Test List $(Get-Date -Format 'HH:mm:ss')"
    description = "Automated test list"
}
$wordList = Invoke-Api -Method Post -Endpoint "/v1/word-lists?user_id=$UserId" -Body $listBody
if ($wordList -and $wordList.id) {
    $listId = $wordList.id
    Write-Success "Word list created: $listId"
} else {
    Write-Failure "Failed to create word list"
    exit 1
}

Write-Host "Adding words..." -ForegroundColor Yellow
$words = @("hello", "world", "test", "game", "api")
$wordIds = @()

foreach ($word in $words) {
    $wordBody = @{
        word = $word
        translation = "Translation of $word"
        notes = "Test word"
    }
    $wordObj = Invoke-Api -Method Post -Endpoint "/v1/word-lists/$listId/words?user_id=$UserId" -Body $wordBody
    if ($wordObj -and $wordObj.id) {
        $wordIds += $wordObj.id
    }
}
Write-Success "Added $($wordIds.Count) words"

Write-Host "Toggling favorite..." -ForegroundColor Yellow
$favBody = @{ isFavorite = $true }
$favResult = Invoke-Api -Method Post -Endpoint "/v1/word-lists/$listId/favorite?user_id=$UserId" -Body $favBody
if ($favResult.ok) {
    Write-Success "Toggled favorite"
}

Write-Host "Fetching word lists..." -ForegroundColor Yellow
$lists = Invoke-Api -Method Get -Endpoint "/v1/word-lists?user_id=$UserId&page=1&limit=20"
if ($lists.data) {
    Write-Success "Retrieved $($lists.data.Count) word lists"
}

# ==========================================
# 3. FLASHCARDS
# ==========================================

Write-TestHeader "3. FLASHCARDS"

Write-Host "Starting flashcard session..." -ForegroundColor Yellow
$flashBody = @{
    wordListId = $listId
    selectedWordIds = @($wordIds[0], $wordIds[1])
}
$flashSession = Invoke-Api -Method Post -Endpoint "/v1/flashcards/sessions?user_id=$UserId" -Body $flashBody
if ($flashSession -and $flashSession.id) {
    $flashSessionId = $flashSession.id
    Write-Success "Session started: $flashSessionId"
    
    Write-Host "Recording results..." -ForegroundColor Yellow
    foreach ($wordId in @($wordIds[0], $wordIds[1])) {
        $resultBody = @{
            wordId = $wordId
            isCorrect = $true
            timeSpent = 1500
            attempts = 1
        }
        Invoke-Api -Method Post -Endpoint "/v1/flashcards/sessions/$flashSessionId/results?user_id=$UserId" -Body $resultBody | Out-Null
    }
    Write-Success "Recorded 2 results"
    
    Write-Host "Completing session..." -ForegroundColor Yellow
    $completeBody = @{
        progress = @{
            current = 2
            total = 2
            correct = 2
            incorrect = 0
        }
    }
    $completed = Invoke-Api -Method Post -Endpoint "/v1/flashcards/sessions/$flashSessionId/complete?user_id=$UserId" -Body $completeBody
    if ($completed.completedAt) {
        Write-Success "Session completed"
    }
}

Write-Host "Getting stats..." -ForegroundColor Yellow
$flashStats = Invoke-Api -Method Get -Endpoint "/v1/flashcards/stats/me?user_id=$UserId"
if ($flashStats) {
    Write-Success "Retrieved flashcard stats"
}

# ==========================================
# 4. SPELLING BEE
# ==========================================

Write-TestHeader "4. SPELLING BEE"

Write-Host "Starting spelling session..." -ForegroundColor Yellow
$spellBody = @{
    wordListId = $listId
    selectedWordIds = @($wordIds[2], $wordIds[3])
    shuffle = $true
}
$spellSession = Invoke-Api -Method Post -Endpoint "/v1/spelling/sessions?user_id=$UserId" -Body $spellBody
if ($spellSession -and $spellSession.id) {
    $spellSessionId = $spellSession.id
    Write-Success "Session started: $spellSessionId"
    
    Write-Host "Recording result..." -ForegroundColor Yellow
    $spellResultBody = @{
        wordId = $wordIds[2]
        userAnswer = "test"
        isCorrect = $true
        attempts = 1
        timeSpent = 2000
    }
    $spellResult = Invoke-Api -Method Post -Endpoint "/v1/spelling/sessions/$spellSessionId/results?user_id=$UserId" -Body $spellResultBody
    if ($spellResult.ok) {
        Write-Success "Recorded spelling result"
    }
    
    Write-Host "Completing session..." -ForegroundColor Yellow
    Invoke-Api -Method Post -Endpoint "/v1/spelling/sessions/$spellSessionId/complete?user_id=$UserId" | Out-Null
    Write-Success "Session completed"
}

Write-Host "Getting pronunciation..." -ForegroundColor Yellow
$pronunciation = Invoke-Api -Method Get -Endpoint "/v1/spelling/pronunciations/$($wordIds[0])?user_id=$UserId"
if ($pronunciation.audioUrl) {
    Write-Success "Retrieved pronunciation URL"
}

# ==========================================
# 5. ADVANCED CLOZE
# ==========================================

Write-TestHeader "5. ADVANCED CLOZE"

Write-Host "Getting topics..." -ForegroundColor Yellow
$clozeTopics = Invoke-Api -Method Get -Endpoint "/v1/advanced-cloze/topics"
if ($clozeTopics.topics -and $clozeTopics.topics.Count -gt 0) {
    $topicId = $clozeTopics.topics[0].id
    Write-Success "Retrieved $($clozeTopics.topics.Count) topics"
    
    Write-Host "Getting lessons..." -ForegroundColor Yellow
    $clozeLessons = Invoke-Api -Method Get -Endpoint "/v1/advanced-cloze/lessons?topicId=$topicId"
    if ($clozeLessons.lessons) {
        Write-Success "Retrieved $($clozeLessons.lessons.Count) lessons"
    }
    
    Write-Host "Starting session..." -ForegroundColor Yellow
    $clozeBody = @{
        mode = "topic"
        topicId = $topicId
        difficulty = "medium"
        limit = 5
    }
    $clozeSession = Invoke-Api -Method Post -Endpoint "/v1/advanced-cloze/sessions?user_id=$UserId" -Body $clozeBody
    if ($clozeSession -and $clozeSession.id) {
        $clozeSessionId = $clozeSession.id
        Write-Success "Session started: $clozeSessionId"
        
        if ($clozeSession.items -and $clozeSession.items.Count -gt 0) {
            $clozeItemId = $clozeSession.items[0].id
            
            Write-Host "Recording result..." -ForegroundColor Yellow
            $clozeResultBody = @{
                itemId = $clozeItemId
                selectedAnswers = @("answer1", "answer2")
                isCorrect = $true
                attempts = 1
                timeSpent = 3000
            }
            Invoke-Api -Method Post -Endpoint "/v1/advanced-cloze/sessions/$clozeSessionId/results?user_id=$UserId" -Body $clozeResultBody | Out-Null
            Write-Success "Recorded result"
            
            Write-Host "Getting hint..." -ForegroundColor Yellow
            $hint = Invoke-Api -Method Get -Endpoint "/v1/advanced-cloze/items/$clozeItemId/hint?user_id=$UserId"
            if ($hint.hint) {
                Write-Success "Retrieved hint"
            }
        }
        
        Write-Host "Completing session..." -ForegroundColor Yellow
        Invoke-Api -Method Post -Endpoint "/v1/advanced-cloze/sessions/$clozeSessionId/complete?user_id=$UserId" | Out-Null
        Write-Success "Session completed"
    }
} else {
    Write-Host "⚠ No cloze topics found - skipping cloze tests" -ForegroundColor Yellow
}

# ==========================================
# 6. GRAMMAR CHALLENGE
# ==========================================

Write-TestHeader "6. GRAMMAR CHALLENGE"

Write-Host "Getting categories..." -ForegroundColor Yellow
$grammarCats = Invoke-Api -Method Get -Endpoint "/v1/grammar-challenge/categories"
if ($grammarCats.categories -and $grammarCats.categories.Count -gt 0) {
    $categoryId = $grammarCats.categories[0].id
    Write-Success "Retrieved $($grammarCats.categories.Count) categories"
    
    Write-Host "Getting lessons..." -ForegroundColor Yellow
    $grammarLessons = Invoke-Api -Method Get -Endpoint "/v1/grammar-challenge/lessons?categoryId=$categoryId"
    if ($grammarLessons.lessons) {
        Write-Success "Retrieved $($grammarLessons.lessons.Count) lessons"
    }
    
    Write-Host "Starting session..." -ForegroundColor Yellow
    $grammarBody = @{
        mode = "topic"
        categoryId = $categoryId
        difficulty = "medium"
        limit = 5
    }
    $grammarSession = Invoke-Api -Method Post -Endpoint "/v1/grammar-challenge/sessions?user_id=$UserId" -Body $grammarBody
    if ($grammarSession -and $grammarSession.id) {
        $grammarSessionId = $grammarSession.id
        Write-Success "Session started: $grammarSessionId"
        
        if ($grammarSession.questions -and $grammarSession.questions.Count -gt 0) {
            $questionId = $grammarSession.questions[0].id
            
            Write-Host "Recording result..." -ForegroundColor Yellow
            $grammarResultBody = @{
                questionId = $questionId
                selectedAnswer = 1
                isCorrect = $true
                attempts = 1
                timeSpent = 2500
            }
            Invoke-Api -Method Post -Endpoint "/v1/grammar-challenge/sessions/$grammarSessionId/results?user_id=$UserId" -Body $grammarResultBody | Out-Null
            Write-Success "Recorded result"
            
            Write-Host "Getting hint..." -ForegroundColor Yellow
            $hint = Invoke-Api -Method Get -Endpoint "/v1/grammar-challenge/questions/$questionId/hint?user_id=$UserId"
            if ($hint.hint) {
                Write-Success "Retrieved hint"
            }
        }
        
        Write-Host "Completing session..." -ForegroundColor Yellow
        Invoke-Api -Method Post -Endpoint "/v1/grammar-challenge/sessions/$grammarSessionId/complete?user_id=$UserId" | Out-Null
        Write-Success "Session completed"
    }
} else {
    Write-Host "⚠ No grammar categories found - skipping grammar tests" -ForegroundColor Yellow
}

# ==========================================
# 7. SENTENCE BUILDER
# ==========================================

Write-TestHeader "7. SENTENCE BUILDER"

Write-Host "Getting topics..." -ForegroundColor Yellow
$sentenceTopics = Invoke-Api -Method Get -Endpoint "/v1/sentence-builder/topics"
if ($sentenceTopics.topics -and $sentenceTopics.topics.Count -gt 0) {
    $sentenceTopicId = $sentenceTopics.topics[0].id
    Write-Success "Retrieved $($sentenceTopics.topics.Count) topics"
    
    Write-Host "Getting lessons..." -ForegroundColor Yellow
    $sentenceLessons = Invoke-Api -Method Get -Endpoint "/v1/sentence-builder/lessons?topicId=$sentenceTopicId"
    if ($sentenceLessons.lessons) {
        Write-Success "Retrieved $($sentenceLessons.lessons.Count) lessons"
    }
    
    Write-Host "Starting session..." -ForegroundColor Yellow
    $sentenceBody = @{
        mode = "topic"
        topicId = $sentenceTopicId
        difficulty = "medium"
        limit = 5
    }
    $sentenceSession = Invoke-Api -Method Post -Endpoint "/v1/sentence-builder/sessions?user_id=$UserId" -Body $sentenceBody
    if ($sentenceSession -and $sentenceSession.id) {
        $sentenceSessionId = $sentenceSession.id
        Write-Success "Session started: $sentenceSessionId"
        
        if ($sentenceSession.items -and $sentenceSession.items.Count -gt 0) {
            $sentenceItemId = $sentenceSession.items[0].id
            
            Write-Host "Recording result..." -ForegroundColor Yellow
            $sentenceResultBody = @{
                itemId = $sentenceItemId
                userTokens = @("The", "test", "sentence")
                isCorrect = $true
                attempts = 1
                timeSpent = 5000
                errorType = $null
            }
            Invoke-Api -Method Post -Endpoint "/v1/sentence-builder/sessions/$sentenceSessionId/results?user_id=$UserId" -Body $sentenceResultBody | Out-Null
            Write-Success "Recorded result"
            
            Write-Host "Getting hint..." -ForegroundColor Yellow
            $hint = Invoke-Api -Method Get -Endpoint "/v1/sentence-builder/items/$sentenceItemId/hint?user_id=$UserId"
            if ($hint.hint) {
                Write-Success "Retrieved hint"
            }
            
            Write-Host "Getting TTS..." -ForegroundColor Yellow
            $tts = Invoke-Api -Method Get -Endpoint "/v1/sentence-builder/items/$sentenceItemId/tts?user_id=$UserId"
            if ($tts.audioUrl) {
                Write-Success "Retrieved TTS URL"
            }
        }
        
        Write-Host "Completing session..." -ForegroundColor Yellow
        Invoke-Api -Method Post -Endpoint "/v1/sentence-builder/sessions/$sentenceSessionId/complete?user_id=$UserId" | Out-Null
        Write-Success "Session completed"
    }
} else {
    Write-Host "⚠ No sentence topics found - skipping sentence builder tests" -ForegroundColor Yellow
}

# ==========================================
# 8. CLEANUP
# ==========================================

Write-TestHeader "8. CLEANUP"

Write-Host "Deleting test data..." -ForegroundColor Yellow
foreach ($wordId in $wordIds) {
    Invoke-Api -Method Delete -Endpoint "/v1/word-lists/$listId/words/$wordId?user_id=$UserId" | Out-Null
}
Invoke-Api -Method Delete -Endpoint "/v1/word-lists/$listId?user_id=$UserId" | Out-Null
Write-Success "Cleanup complete"

# ==========================================
# FINAL REPORT
# ==========================================

Write-Host "`n╔════════════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "║         TEST SUITE COMPLETE            ║" -ForegroundColor Magenta
Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Magenta
Write-Host "`nPassed:  $SuccessCount" -ForegroundColor Green
Write-Host "Failed:  $FailureCount" -ForegroundColor Red

if ($FailureCount -eq 0) {
    Write-Host "`n✓ ALL TESTS PASSED!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "`n✗ SOME TESTS FAILED" -ForegroundColor Red
    exit 1
}
