#!/usr/bin/env python3
"""
End-to-end test suite for Flashcards/Word Lists API
"""

import os
import json
import time
import requests
from typing import Dict, Any

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
USER_ID = os.getenv("TEST_USER_ID", "test_user_123")
HEADERS = {"Content-Type": "application/json"}

def step(msg: str):
    print(f"\n[{msg}]")

def req(method: str, path: str, **kwargs) -> Dict[str, Any]:
    url = f"{BASE_URL}{path}"
    r = requests.request(method, url, headers=HEADERS, **kwargs)
    r.raise_for_status()
    try:
        return r.json()
    except json.JSONDecodeError:
        return {"status": "ok", "text": r.text}

def main():
    try:
        step("Health Check")
        print(req("GET", "/health"))
        time.sleep(1)

        # Create list
        step("Create Word List")
        list_body = {"name": "Python QA List", "description": "Automated test run"}
        lst = req("POST", f"/v1/word-lists?user_id={USER_ID}", json=list_body)
        print(lst)
        list_id = lst["id"]
        time.sleep(1)

        # Get lists
        step("Get All Word Lists")
        print(req("GET", f"/v1/word-lists?user_id={USER_ID}&page=1&limit=20"))
        time.sleep(1)

        # Add word
        step("Add Word to List")
        word_body = {"word": "python", "translation": "पायथन", "notes": "Programming language"}
        word = req("POST", f"/v1/word-lists/{list_id}/words?user_id={USER_ID}", json=word_body)
        print(word)
        word_id = word["id"]
        time.sleep(1)

        # Update word
        step("Update Word")
        upd = {"translation": "पायथन (python)", "notes": "Updated: Programming language"}
        print(req("PATCH", f"/v1/word-lists/{list_id}/words/{word_id}?user_id={USER_ID}", json=upd))
        time.sleep(1)

        # Start flashcard session
        step("Start Flashcard Session")
        sess_body = {"wordListId": list_id, "selectedWordIds": [word_id]}
        sess = req("POST", f"/v1/flashcards/sessions?user_id={USER_ID}", json=sess_body)
        print(sess)
        session_id = sess["id"]
        time.sleep(1)

        # Record result
        step("Record Practice Result")
        result_body = {"wordId": word_id, "isCorrect": True, "attempts": 1, "timeSpent": 5}
        print(req("POST", f"/v1/flashcards/sessions/{session_id}/results?user_id={USER_ID}", json=result_body))
        time.sleep(1)

        # Complete session
        step("Complete Flashcard Session")
        comp_body = {"progress": {"correct": 1, "incorrect": 0}}
        print(req("POST", f"/v1/flashcards/sessions/{session_id}/complete?user_id={USER_ID}", json=comp_body))
        time.sleep(1)

        # Stats
        step("User Word-List Stats")
        print(req("GET", f"/v1/user/stats?user_id={USER_ID}"))
        time.sleep(1)

        step("Flashcard Stats")
        print(req("GET", f"/v1/flashcards/stats/me?user_id={USER_ID}"))
        time.sleep(1)

        # Cleanup
        step("Cleanup")
        req("DELETE", f"/v1/word-lists/{list_id}/words/{word_id}?user_id={USER_ID}")
        req("DELETE", f"/v1/word-lists/{list_id}?user_id={USER_ID}")

        print("\n===============================")
        print("All game endpoints tested!")
        print("===============================")
    except Exception as e:
        print(f"\nTest suite failed: {e}")
        raise SystemExit(1)

if __name__ == "__main__":
    main()