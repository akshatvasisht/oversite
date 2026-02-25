import os
import sys
import sqlite3
import requests
from dotenv import load_dotenv

def print_status(check_name: str, status: bool, details: str = ""):
    """
    Renders the clinical status of a health system check to the console.

    Args:
        check_name: Human-readable identifier for the check.
        status: Boolean indicating success or failure.
        details: Optional supplementary information (e.g., file paths, masked keys).
    """
    color = "\033[92m[OK]\033[0m" if status else "\033[91m[FAIL]\033[0m"
    print(f"{color} {check_name:<30} {details}")

def run_healthcheck():
    """
    Coordinates a comprehensive verification of the backend environment.

    Validates environment variables, database connectivity/schema, and 
    the availability of pre-trained model artifacts.
    """
    print("\n=== OverSite Platform Health Verification ===\n")
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(base_dir, ".env")
    
    # 1. Check .env file
    has_env = os.path.exists(env_path)
    print_status(".env file exists", has_env, env_path)
    if not has_env:
        sys.exit(1)
        
    load_dotenv(env_path)
    
    # 2. Check essential env vars
    vars_to_check = ['GEMINI_API_KEY', 'FLASK_SECRET_KEY', 'DATABASE_URL']
    all_vars = True
    for v in vars_to_check:
        val = os.environ.get(v)
        has_v = bool(val)
        masked = f"{val[:5]}...{val[-4:]}" if val and len(val) > 10 else "***"
        print_status(f"Env var: {v}", has_v, masked if has_v else "Missing")
        all_vars = all_vars and has_v
    
    if not all_vars:
        sys.exit(1)
        
    # 3. Check Database
    db_path = os.getenv("DATABASE_URL", "sqlite:///oversite.db").replace("sqlite:///", "")
    if db_path.startswith('/'): # Absolute path
        db_full_path = db_path
    else:
        db_full_path = os.path.join(base_dir, db_path)
        
    has_db = os.path.exists(db_full_path)
    print_status("Database file exists", has_db, db_full_path)
    if has_db:
        try:
            conn = sqlite3.connect(db_full_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [r[0] for r in cursor.fetchall()]
            required_tables = ['sessions', 'files', 'events', 'ai_interactions', 'session_scores']
            has_tables = all(t in tables for t in required_tables)
            print_status("Database schema initialized", has_tables, f"Found {len(tables)} tables")
            conn.close()
        except Exception as e:
            print_status("Database query failed", False, str(e))
    else:
        print_status("Database schema initialized", False, "DB file missing")
        sys.exit(1)

    # 4. Verify Machine Learning Artifact Integrity
    artifacts_dir = os.environ.get("MODEL_ARTIFACTS_DIR", os.path.join(os.path.dirname(base_dir), "model", "models"))
    behavioral_path = os.path.join(artifacts_dir, "behavioral_classifier.joblib")
    prompt_path = os.path.join(artifacts_dir, "prompt_quality_classifier.joblib")
    
    has_models = os.path.exists(behavioral_path) and os.path.exists(prompt_path)
    print_status("Behavioral models available", has_models, artifacts_dir)
    
    fallback_mode = os.environ.get("SCORING_FALLBACK_MODE", "false").lower() == "true"
    print_status("SCORING_FALLBACK_MODE", True, str(fallback_mode))

    # 5. Connect to Gemini API Check
    api_key = os.environ.get("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        r = requests.get(url, timeout=5)
        print_status("Gemini API connection", r.status_code == 200, f"HTTP {r.status_code}")
    except Exception as e:
        print_status("Gemini API connection", False, str(e))
        
    print("\nHealth check completed.")

if __name__ == "__main__":
    run_healthcheck()
