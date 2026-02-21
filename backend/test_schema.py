from sqlalchemy import inspect
from db import engine

def test_all_tables_exist():
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    required = [
        'sessions','files','events','ai_interactions',
        'ai_suggestions','chunk_decisions','editor_events','session_scores'
    ]
    for t in required:
        assert t in tables, f"Missing table {t}"
    print("All required tables are present.")

if __name__ == "__main__":
    test_all_tables_exist()
