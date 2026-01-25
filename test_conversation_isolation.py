#!/usr/bin/env python3
"""Tests that conversation context is isolated per (user_identifier, conversation_id).

This mirrors the requirement:
 - user_identifier comes from PHP session
 - conversation_id comes from PHP session
 - history must not mix between different user+conversation combinations
"""

import os
import sys
import time
import json
import subprocess
import requests


def _api_base_url() -> str:
    host = os.getenv("HOST", "localhost")
    port = os.getenv("PORT", "8001")
    return f"http://{host}:{port}"


def start_server():
    """Start the API server in a separate process."""
    process = subprocess.Popen(
        [sys.executable, "api.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "PYTHONPATH": "."},
    )
    time.sleep(5)
    return process


def _post_chat(base_url: str, *, user_identifier: str, conversation_id: str, message: str):
    payload = {
        "message": message,
        "headers": {
            "x-user-id": user_identifier,
            "x-username": user_identifier,
            "x-user-groups": "api_users",
            "x-conversation-id": conversation_id,
        },
        "metadata": {"test": "conversation_isolation"},
    }
    return requests.post(f"{base_url}/api/vanna/v2/chat_poll", json=payload, timeout=60)


def _get_history(base_url: str, *, user_identifier: str, conversation_id: str):
    return requests.get(
        f"{base_url}/api/v1/conversation/history",
        params={"user_identifier": user_identifier, "conversation_id": conversation_id, "limit": 50},
        timeout=20,
    )


def main() -> int:
    base_url = _api_base_url()
    proc = start_server()
    try:
        # Clear everything first.
        requests.delete(f"{base_url}/api/v1/conversation/clear", timeout=20)

        # Same user, two conversations
        r1 = _post_chat(base_url, user_identifier="userA", conversation_id="sales", message="Question about sales")
        r2 = _post_chat(base_url, user_identifier="userA", conversation_id="inventory", message="Question about inventory")
        assert r1.status_code == 200, r1.text
        assert r2.status_code == 200, r2.text

        h_sales = _get_history(base_url, user_identifier="userA", conversation_id="sales")
        h_inv = _get_history(base_url, user_identifier="userA", conversation_id="inventory")
        assert h_sales.status_code == 200, h_sales.text
        assert h_inv.status_code == 200, h_inv.text

        sales_data = h_sales.json()
        inv_data = h_inv.json()

        sales_text = json.dumps(sales_data.get("conversations", []))
        inv_text = json.dumps(inv_data.get("conversations", []))

        if "inventory" in sales_text.lower():
            raise AssertionError("inventory leaked into sales conversation")
        if "sales" in inv_text.lower():
            raise AssertionError("sales leaked into inventory conversation")

        # Different users, same conversation_id
        r3 = _post_chat(base_url, user_identifier="userB", conversation_id="sales", message="UserB sales question")
        assert r3.status_code == 200, r3.text

        h_userA_sales = _get_history(base_url, user_identifier="userA", conversation_id="sales")
        h_userB_sales = _get_history(base_url, user_identifier="userB", conversation_id="sales")
        assert h_userA_sales.status_code == 200, h_userA_sales.text
        assert h_userB_sales.status_code == 200, h_userB_sales.text

        a_text = json.dumps(h_userA_sales.json().get("conversations", []))
        b_text = json.dumps(h_userB_sales.json().get("conversations", []))

        if "userb" in a_text.lower():
            raise AssertionError("UserB content leaked into UserA sales conversation")
        if "usera" in b_text.lower():
            raise AssertionError("UserA content leaked into UserB sales conversation")

        print("✅ Conversation isolation test passed")
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
