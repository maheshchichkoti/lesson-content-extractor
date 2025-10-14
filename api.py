"""Production-ready FastAPI application for lesson content extraction"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import List, Dict
import logging
from datetime import datetime

from src.main import LessonProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Lesson Content Extractor API",
    description="Transform lesson transcripts into structured learning exercises",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize processor
processor = LessonProcessor()


# Request/Response Models
class TranscriptInput(BaseModel):
    """Single transcript input"""
    transcript: str = Field(..., min_length=10, description="Lesson transcript text")
    lesson_number: int = Field(..., ge=1, description="Lesson number (1-based)")
    
    @validator('transcript')
    def validate_transcript(cls, v):
        if not v.strip():
            raise ValueError('Transcript cannot be empty or whitespace only')
        return v


class MultipleTranscriptsInput(BaseModel):
    """Multiple transcripts input"""
    transcripts: List[TranscriptInput] = Field(..., min_items=1, max_items=10)


class LessonExercises(BaseModel):
    """Exercises for a single lesson"""
    lesson_number: int
    fill_in_blank: List[Dict]
    flashcards: List[Dict]
    spelling: List[Dict]
    total_exercises: int
    quality_passed: bool


class ProcessingResponse(BaseModel):
    """Response for processing request"""
    success: bool
    message: str
    lessons: List[LessonExercises]
    processing_time_seconds: float
    timestamp: str


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    version: str


# API Endpoints
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Lesson Content Extractor API",
        "version": "1.0.0",
        "status": "active",
        "documentation": "/docs",
        "endpoints": {
            "health": "/health",
            "process_single": "/api/v1/process",
            "process_multiple": "/api/v1/process/batch"
        }
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version="1.0.0"
    )


@app.post("/api/v1/process", response_model=ProcessingResponse, tags=["Processing"])
async def process_single_lesson(input_data: TranscriptInput):
    """
    Process a single lesson transcript and return structured exercises
    
    **Parameters:**
    - transcript: The lesson transcript text (minimum 10 characters)
    - lesson_number: Lesson identifier (positive integer)
    
    **Returns:**
    - Structured exercises (fill-in-blank, flashcards, spelling)
    - Quality validation results
    - Processing metadata
    """
    try:
        start_time = datetime.utcnow()
        logger.info(f"Processing lesson {input_data.lesson_number}")
        
        # Process the lesson
        result = processor.process_lesson(
            input_data.transcript,
            input_data.lesson_number
        )
        
        # Calculate total exercises
        total = len(result['fill_in_blank']) + len(result['flashcards']) + len(result['spelling'])
        
        # Check quality
        quality_passed = 8 <= total <= 12
        
        # Build response
        lesson_data = LessonExercises(
            lesson_number=input_data.lesson_number,
            fill_in_blank=result['fill_in_blank'],
            flashcards=result['flashcards'],
            spelling=result['spelling'],
            total_exercises=total,
            quality_passed=quality_passed
        )
        
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()
        
        logger.info(f"Lesson {input_data.lesson_number} processed successfully in {processing_time:.2f}s")
        
        return ProcessingResponse(
            success=True,
            message=f"Lesson {input_data.lesson_number} processed successfully",
            lessons=[lesson_data],
            processing_time_seconds=round(processing_time, 2),
            timestamp=end_time.isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error processing lesson {input_data.lesson_number}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing lesson: {str(e)}"
        )


@app.post("/api/v1/process/batch", response_model=ProcessingResponse, tags=["Processing"])
async def process_multiple_lessons(input_data: MultipleTranscriptsInput):
    """
    Process multiple lesson transcripts in batch
    
    **Parameters:**
    - transcripts: List of transcript objects (1-10 lessons)
    
    **Returns:**
    - Structured exercises for all lessons
    - Aggregated processing metadata
    """
    try:
        start_time = datetime.utcnow()
        logger.info(f"Processing batch of {len(input_data.transcripts)} lessons")
        
        lessons_data = []
        
        for transcript_input in input_data.transcripts:
            # Process each lesson
            result = processor.process_lesson(
                transcript_input.transcript,
                transcript_input.lesson_number
            )
            
            total = len(result['fill_in_blank']) + len(result['flashcards']) + len(result['spelling'])
            quality_passed = 8 <= total <= 12
            
            lesson_data = LessonExercises(
                lesson_number=transcript_input.lesson_number,
                fill_in_blank=result['fill_in_blank'],
                flashcards=result['flashcards'],
                spelling=result['spelling'],
                total_exercises=total,
                quality_passed=quality_passed
            )
            lessons_data.append(lesson_data)
        
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()
        
        logger.info(f"Batch processing completed in {processing_time:.2f}s")
        
        return ProcessingResponse(
            success=True,
            message=f"Successfully processed {len(lessons_data)} lessons",
            lessons=lessons_data,
            processing_time_seconds=round(processing_time, 2),
            timestamp=end_time.isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error in batch processing: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in batch processing: {str(e)}"
        )


# Error handlers
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"success": False, "error": str(exc)}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"success": False, "error": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")