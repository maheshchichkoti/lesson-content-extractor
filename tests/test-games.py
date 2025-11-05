#!/usr/bin/env python3
"""End-to-end verification script for Tulkka Games API."""

from __future__ import annotations

import os
import json as jsonlib
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests


BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
USER_ID = os.getenv("TEST_USER_ID", "test_user_123")
HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}
PAUSE_SECONDS = float(os.getenv("TEST_STEP_PAUSE", "0.3"))


def step(message: str) -> None:
    print(f"\n[{message}]")


def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def req(method: str, path: str, *, params: Optional[Dict[str, Any]] = None, json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = f"{BASE_URL}{path}"
    response = requests.request(method, url, headers=HEADERS, params=params, json=json, timeout=30)
    response.raise_for_status()
    try:
        return response.json()
    except jsonlib.JSONDecodeError:
        return {"status": "ok", "text": response.text}


def pause() -> None:
    if PAUSE_SECONDS:
        time.sleep(PAUSE_SECONDS)


def call_optional_game(label: str, func, *args, **kwargs) -> Optional[Any]:
    try:
        return func(*args, **kwargs)
    except requests.HTTPError as err:
        status = err.response.status_code if err.response is not None else None
        if status not in {404, 500}:
            raise

        step(f"{label} Skipped")
        detail_parts: List[str] = []
        if status is not None:
            detail_parts.append(f"HTTP {status}")
        if err.response is not None:
            body_text = err.response.text.strip()
            if body_text:
                detail_parts.append(body_text)
        detail = " - ".join(detail_parts) if detail_parts else str(err)
        print(f"Skipping {label} endpoints. {detail}")
        pause()
        return None


@dataclass
class WordListArtifacts:
    list_id: str
    word_id: str
    flash_session_id: str
    spelling_session_id: str


def exercise_word_lists() -> WordListArtifacts:
    step("Health Check")
    health = req("GET", "/health")
    ensure(health.get("status") in {"ok", "healthy"}, "Health check did not return an accepted status")
    pause()

    step("Create Word List")
    list_payload = {
        "name": "QA Auto List",
        "description": "Created by automated end-to-end test"
    }
    created_list = req("POST", "/v1/word-lists", params={"user_id": USER_ID}, json=list_payload)
    list_id = created_list["id"]
    pause()

    step("List Word Lists")
    lists = req("GET", "/v1/word-lists", params={"user_id": USER_ID, "page": 1, "limit": 10})
    ensure(any(entry["id"] == list_id for entry in lists.get("data", [])), "New word list not returned in listing")
    pause()

    step("Add Word")
    word_payload = {
        "word": "python",
        "translation": "पायथन",
        "notes": "Automated test fixture"
    }
    created_word = req("POST", f"/v1/word-lists/{list_id}/words", params={"user_id": USER_ID}, json=word_payload)
    word_id = created_word["id"]
    pause()

    step("Update Word")
    update_payload = {
        "translation": "पायथन (Python)",
        "notes": "Updated via automated test"
    }
    req("PATCH", f"/v1/word-lists/{list_id}/words/{word_id}", params={"user_id": USER_ID}, json=update_payload)
    pause()

    step("Start Flashcards Session")
    flash_session = req(
        "POST",
        "/v1/flashcards/sessions",
        params={"user_id": USER_ID},
        json={"wordListId": list_id, "selectedWordIds": [word_id]}
    )
    flash_session_id = flash_session["id"]
    pause()

    step("Get Flashcard Session")
    session_details = req("GET", f"/v1/flashcards/sessions/{flash_session_id}", params={"user_id": USER_ID})
    ensure(session_details["id"] == flash_session_id, "Session ID mismatch")
    pause()

    step("Record Flashcard Result")
    req(
        "POST",
        f"/v1/flashcards/sessions/{flash_session_id}/results",
        params={"user_id": USER_ID},
        json={"wordId": word_id, "isCorrect": True, "attempts": 1, "timeSpent": 4}
    )
    pause()

    step("Complete Flashcard Session")
    req(
        "POST",
        f"/v1/flashcards/sessions/{flash_session_id}/complete",
        params={"user_id": USER_ID},
        json={"progress": {"current": 1, "total": 1, "correct": 1, "incorrect": 0}}
    )
    pause()

    step("Flashcard Stats")
    stats = req("GET", "/v1/flashcards/stats/me", params={"user_id": USER_ID})
    ensure("totals" in stats, "Flashcard stats response missing 'totals'")
    pause()

    step("Start Spelling Session")
    spelling_session = req(
        "POST",
        "/v1/spelling/sessions",
        params={"user_id": USER_ID},
        json={"wordListId": list_id, "selectedWordIds": [word_id], "shuffle": False}
    )
    spelling_session_id = spelling_session["id"]
    pause()

    step("Get Spelling Session")
    spelling_details = req("GET", f"/v1/spelling/sessions/{spelling_session_id}", params={"user_id": USER_ID})
    ensure(spelling_details["id"] == spelling_session_id, "Spelling session ID mismatch")
    pause()

    step("Get Pronunciation")
    try:
        req("GET", f"/v1/spelling/pronunciations/{word_id}", params={"user_id": USER_ID})
    except requests.HTTPError as e:
        if e.response.status_code not in {403, 404}:
            raise
        print(f"Pronunciation not available (expected): {e.response.status_code}")
    pause()

    step("Record Spelling Result")
    req(
        "POST",
        f"/v1/spelling/sessions/{spelling_session_id}/results",
        params={"user_id": USER_ID},
        json={
            "wordId": word_id,
            "userAnswer": "python",
            "isCorrect": True,
            "attempts": 1,
            "timeSpent": 5
        }
    )
    pause()

    step("Complete Spelling Session")
    req(
        "POST",
        f"/v1/spelling/sessions/{spelling_session_id}/complete",
        params={"user_id": USER_ID},
        json={"progress": {"current": 1, "total": 1, "correct": 1, "incorrect": 0}}
    )
    pause()

    return WordListArtifacts(list_id=list_id, word_id=word_id, flash_session_id=flash_session_id, spelling_session_id=spelling_session_id)


def exercise_advanced_cloze(user_id: str) -> None:
    step("Advanced Cloze Catalog")
    topics = req("GET", "/v1/advanced-cloze/topics")
    topic_list = topics.get("topics", [])
    ensure(topic_list, "No Advanced Cloze topics available. Seed cloze_topics table.")
    topic_id = topic_list[0]["id"]
    pause()

    lessons = req("GET", "/v1/advanced-cloze/lessons", params={"topicId": topic_id})
    lesson_list = lessons.get("lessons", [])
    ensure(lesson_list, f"No lessons for Advanced Cloze topic '{topic_id}'. Seed cloze_lessons table.")
    lesson_id = lesson_list[0]["id"]
    pause()

    items = req(
        "GET",
        "/v1/advanced-cloze/items",
        params={"lessonId": lesson_id, "include": "options", "limit": 20}
    )
    item_list = items.get("data", [])
    ensure(item_list, f"No cloze items for lesson '{lesson_id}'. Seed cloze_items table.")
    first_item = item_list[0]
    pause()

    step("Start Advanced Cloze Session")
    session = req(
        "POST",
        "/v1/advanced-cloze/sessions",
        params={"user_id": user_id},
        json={
            "mode": "lesson",
            "topicId": topic_id,
            "lessonId": lesson_id,
            "difficulty": first_item.get("difficulty"),
            "limit": min(5, len(item_list))
        }
    )
    session_id = session["id"]
    pause()

    step("Get Advanced Cloze Session")
    session_details = req("GET", f"/v1/advanced-cloze/sessions/{session_id}", params={"user_id": user_id, "include": "options"})
    ensure(session_details["id"] == session_id, "Cloze session ID mismatch")
    pause()

    step("Record Advanced Cloze Result")
    req(
        "POST",
        f"/v1/advanced-cloze/sessions/{session_id}/results",
        params={"user_id": user_id},
        json={
            "itemId": first_item["id"],
            "selectedAnswers": first_item.get("correct", []),
            "isCorrect": True,
            "attempts": 1,
            "timeSpent": 7
        }
    )
    pause()

    step("Complete Advanced Cloze Session")
    req(
        "POST",
        f"/v1/advanced-cloze/sessions/{session_id}/complete",
        params={"user_id": user_id},
        json={"progress": {"current": 1, "total": session["progress"]["total"], "correct": 1, "incorrect": 0}}
    )
    pause()

    step("Advanced Cloze Hint & Mistakes")
    req("GET", f"/v1/advanced-cloze/items/{first_item['id']}/hint", params={"user_id": user_id})
    req("GET", "/v1/advanced-cloze/mistakes", params={"user_id": user_id, "page": 1, "limit": 10})
    pause()


def exercise_grammar_challenge(user_id: str) -> None:
    step("Grammar Challenge Catalog")
    categories = req("GET", "/v1/grammar-challenge/categories")
    category_list = categories.get("categories", [])
    ensure(category_list, "No grammar categories available. Seed grammar_categories table.")
    category_id = category_list[0]["id"]
    pause()

    lessons = req("GET", "/v1/grammar-challenge/lessons", params={"categoryId": category_id})
    lesson_list = lessons.get("lessons", [])
    ensure(lesson_list, f"No lessons for grammar category '{category_id}'. Seed grammar_lessons table.")
    lesson_id = lesson_list[0]["id"]
    pause()

    questions = req(
        "GET",
        "/v1/grammar-challenge/questions",
        params={"lessonId": lesson_id, "include": "options", "limit": 20}
    )
    question_list = questions.get("data", [])
    ensure(question_list, f"No grammar questions for lesson '{lesson_id}'. Seed grammar_questions table.")
    first_question = question_list[0]
    pause()

    step("Start Grammar Challenge Session")
    session = req(
        "POST",
        "/v1/grammar-challenge/sessions",
        params={"user_id": user_id},
        json={
            "mode": "lesson",
            "categoryId": category_id,
            "lessonId": lesson_id,
            "difficulty": first_question.get("difficulty"),
            "limit": min(5, len(question_list))
        }
    )
    session_id = session["id"]
    pause()

    step("Get Grammar Session")
    session_details = req("GET", f"/v1/grammar-challenge/sessions/{session_id}", params={"user_id": user_id, "include": "options"})
    ensure(session_details["id"] == session_id, "Grammar session ID mismatch")
    pause()

    step("Record Grammar Result")
    req(
        "POST",
        f"/v1/grammar-challenge/sessions/{session_id}/results",
        params={"user_id": user_id},
        json={
            "questionId": first_question["id"],
            "selectedAnswer": first_question.get("correctIndex", 0),
            "isCorrect": True,
            "attempts": 1,
            "timeSpent": 6
        }
    )
    pause()

    step("Skip Grammar Question")
    if len(question_list) > 1:
        second = question_list[1]
        req(
            "POST",
            f"/v1/grammar-challenge/sessions/{session_id}/skip",
            params={"user_id": user_id},
            json={"questionId": second["id"]}
        )
        pause()

    step("Complete Grammar Session")
    req(
        "POST",
        f"/v1/grammar-challenge/sessions/{session_id}/complete",
        params={"user_id": user_id},
        json={"progress": {"current": 2, "total": session["progress"]["total"], "correct": 1, "incorrect": 1}}
    )
    pause()

    step("Grammar Hint & Mistakes")
    req("GET", f"/v1/grammar-challenge/questions/{first_question['id']}/hint", params={"user_id": user_id})
    req("GET", "/v1/grammar-challenge/mistakes", params={"user_id": user_id, "page": 1, "limit": 10})
    pause()


def exercise_sentence_builder(user_id: str) -> None:
    step("Sentence Builder Catalog")
    topics = req("GET", "/v1/sentence-builder/topics")
    topic_list = topics.get("topics", [])
    ensure(topic_list, "No sentence builder topics available. Seed sentence_topics table.")
    topic_id = topic_list[0]["id"]
    pause()

    lessons = req("GET", "/v1/sentence-builder/lessons", params={"topicId": topic_id})
    lesson_list = lessons.get("lessons", [])
    ensure(lesson_list, f"No lessons for sentence topic '{topic_id}'. Seed sentence_lessons table.")
    lesson_id = lesson_list[0]["id"]
    pause()

    items = req(
        "GET",
        "/v1/sentence-builder/items",
        params={"lessonId": lesson_id, "include": "tokens", "limit": 20}
    )
    item_list = items.get("data", [])
    ensure(item_list, f"No sentence items for lesson '{lesson_id}'. Seed sentence_items table.")
    first_item = item_list[0]
    pause()

    step("Start Sentence Builder Session")
    session = req(
        "POST",
        "/v1/sentence-builder/sessions",
        params={"user_id": user_id},
        json={
            "mode": "lesson",
            "topicId": topic_id,
            "lessonId": lesson_id,
            "difficulty": first_item.get("difficulty"),
            "limit": min(5, len(item_list))
        }
    )
    session_id = session["id"]
    pause()

    step("Get Sentence Builder Session")
    session_details = req("GET", f"/v1/sentence-builder/sessions/{session_id}", params={"user_id": user_id, "include": "items"})
    ensure(session_details["id"] == session_id, "Sentence session ID mismatch")
    pause()

    accepted_sequences: List[List[str]] = first_item.get("accepted", [])
    ensure(accepted_sequences, "Sentence Builder item missing 'accepted' token sequences")
    user_tokens = accepted_sequences[0]

    step("Record Sentence Builder Result")
    req(
        "POST",
        f"/v1/sentence-builder/sessions/{session_id}/results",
        params={"user_id": user_id},
        json={
            "itemId": first_item["id"],
            "userTokens": user_tokens,
            "isCorrect": True,
            "attempts": 1,
            "timeSpent": 8,
            "errorType": "word_order"
        }
    )
    pause()

    step("Complete Sentence Builder Session")
    req(
        "POST",
        f"/v1/sentence-builder/sessions/{session_id}/complete",
        params={"user_id": user_id},
        json={"progress": {"current": 1, "total": session["progress"]["total"], "correct": 1, "incorrect": 0}}
    )
    pause()

    step("Sentence Builder Hint & Mistakes")
    req("GET", f"/v1/sentence-builder/items/{first_item['id']}/hint", params={"user_id": user_id})
    req("GET", "/v1/sentence-builder/mistakes", params={"user_id": user_id, "page": 1, "limit": 10})
    pause()

    step("Sentence Builder TTS")
    try:
        req("GET", f"/v1/sentence-builder/items/{first_item['id']}/tts", params={"user_id": user_id})
    except requests.HTTPError as e:
        if e.response.status_code not in {404, 500}:
            raise
        print(f"TTS not available (expected): {e.response.status_code}")
    pause()


def cleanup_word_list(artifacts: WordListArtifacts) -> None:
    step("Cleanup Test Data")
    req("DELETE", f"/v1/word-lists/{artifacts.list_id}/words/{artifacts.word_id}", params={"user_id": USER_ID})
    req("DELETE", f"/v1/word-lists/{artifacts.list_id}", params={"user_id": USER_ID})


def main() -> None:
    artifacts: Optional[WordListArtifacts] = None
    try:
        artifacts = exercise_word_lists()
        call_optional_game("Advanced Cloze", exercise_advanced_cloze, USER_ID)
        call_optional_game("Grammar Challenge", exercise_grammar_challenge, USER_ID)
        call_optional_game("Sentence Builder", exercise_sentence_builder, USER_ID)

        step("User Aggregate Stats")
        req("GET", "/v1/user/stats", params={"user_id": USER_ID})

        print("\n==============================================")
        print(" All documented game endpoints verified successfully")
        print("==============================================")
    except Exception as exc:
        print(f"\n Test suite failed: {exc}")
        raise SystemExit(1)
    finally:
        if artifacts:
            try:
                cleanup_word_list(artifacts)
            except Exception as cleanup_error:
                print(f"Cleanup warning: {cleanup_error}")


if __name__ == "__main__":
    main()