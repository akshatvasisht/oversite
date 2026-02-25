#!/usr/bin/env python3
import requests
import time
import json
import os
import sys
import logging

# Setup logging
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "demo_output.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000/api/v1"

def print_step(step_name: str):
    """
    Renders a highlighted progression step to the console output.

    Args:
        step_name: Description of the current simulation stage.
    """
    logger.info(f"=== {step_name} ===")

def print_result(res: requests.Response):
    """
    Evaluates the response status and renders a success or failure summary.

    Args:
        res: The response object from a requests call.
    """
    if res.status_code // 100 == 2:
        logger.info(f"Success ({res.status_code}): {json.dumps(res.json(), indent=2)[:300]}...")
    else:
        logger.error(f"Failed ({res.status_code}): {res.text}")
        exit(1)

def run_demo():
    """
    Executes a comprehensive end-to-end simulation of the OverSite platform.

    Emulates a full candidate journey: login, session initialization, 
    interactive coding with AI, execution, and session submission.
    Follows with an admin journey to verify scoring and narrative generation.
    """
    print_step("1. Candidate logs in")
    res = requests.post(f"{BASE_URL}/auth/login", json={"username": "candidate"})
    print_result(res)
    candidate_token = res.json()["token"]
    
    # We pass session_id in X-Session-ID, but for starting, we just need the username (the backend uses the token or username in body?)
    # Let's check test_session_endpoints.py. /session/start expects {"username": "candidate", "project_name": "demo"}
    print_step("2. Candidate starts a session")
    res = requests.post(f"{BASE_URL}/session/start", json={"username": "candidate", "project_name": "tic-tac-toe"}, headers={"Authorization": f"Bearer {candidate_token}"})
    print_result(res)
    session_id = res.json()["session_id"]
    headers = {
        "X-Session-ID": session_id,
        "Authorization": f"Bearer {candidate_token}"
    }

    print_step("3. Candidate opens a file")
    res = requests.post(f"{BASE_URL}/files", headers=headers, json={"filename": "main.py", "initial_content": "def main():\n    pass"})
    print_result(res)
    file_id = res.json()["file_id"]

    print_step("4. Candidate focuses Chat Panel")
    res = requests.post(f"{BASE_URL}/events/panel", headers=headers, json={"panel": "chat"})
    print_result(res)

    print_step("5. Candidate sends a prompt")
    res = requests.post(f"{BASE_URL}/ai/chat", headers=headers, json={
        "prompt": "Can you help me write a tic-tac-toe game? I need a minimax AI.",
        "file_id": file_id
    })
    
    if res.status_code == 200 or res.status_code == 201:
        print_result(res)
        interaction_id = res.json()["interaction_id"]

        print_step("6. Application renders suggestion (simulate diff resolution)")
        res = requests.post(f"{BASE_URL}/suggestions", headers=headers, json={
            "interaction_id": interaction_id,
            "file_id": file_id,
            "original_content": "def main():\n    pass",
            "proposed_content": "def main():\n    print('Tic Tac Toe')# Minimax placeholder"
        })
        print_result(res)
        suggestion_id = res.json()["suggestion_id"]

        print_step("7. Candidate deliberates for 5 seconds and modifies the chunk")
        time.sleep(1) # Sleep to generate some deliberation time
        res = requests.post(f"{BASE_URL}/suggestions/{suggestion_id}/chunks/0/decide", headers=headers, json={
            "decision": "modified",
            "final_code": "def main():\n    print('Super Tic Tac Toe!')",
            "time_on_chunk_ms": 5000
        })
        print_result(res)
    else:
        print(f"\033[93mSkipped steps 6-7 because /ai/chat responded with {res.status_code}. (Testing Fallback mode)\033[0m")

    print_step("8. Candidate executes the code")
    res = requests.post(f"{BASE_URL}/events/execute", headers=headers, json={
        "command": "python main.py",
        "exit_code": 0,
        "stdout": "Super Tic Tac Toe!\n",
        "stderr": ""
    })
    print_result(res)

    print_step("9. Candidate ends session")
    res = requests.post(f"{BASE_URL}/session/end", headers=headers)
    print_result(res)

    print_step("10. Admin logs in")
    res = requests.post(f"{BASE_URL}/auth/login", json={"username": "admin"})
    print_result(res)
    admin_token = res.json()["token"]
    admin_headers = {
        "Authorization": f"Bearer {admin_token}"
    }

    print_step("11. Admin views overview")
    res = requests.get(f"{BASE_URL}/analytics/overview?completed_only=true", headers=admin_headers)
    print_result(res)
    
    print_step("12. Wait for async LLM Judge to populate narrative (Poll up to 15s)")
    for i in range(15):
        res = requests.get(f"{BASE_URL}/analytics/session/{session_id}", headers=admin_headers)
        if res.status_code == 200:
            data = res.json()
            if data.get("llm_narrative"):
                logger.info(f"Narrative Generated!\n{data['llm_narrative']}")
                break
        print(".", end="", flush=True)
        time.sleep(1)
    else:
        print("\n\033[91mTimed out waiting for narrative.\033[0m")
        exit(1)

    logger.info(json.dumps(res.json(), indent=2))
    logger.info("Demo simulation completed flawlessly.")

if __name__ == "__main__":
    try:
        run_demo()
    except requests.exceptions.ConnectionError:
        logger.error("Connection Error: Is the backend server running on localhost:8000?")
        exit(1)
