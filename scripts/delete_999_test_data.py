import sqlite3
import os

def main():
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'db', 'dsa_bot.db'))
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # The progress_logs table doesn't have a direct 'question_count' column.
        # The count is stored in the JSON 'parsed_fields' column.
        query_check = "SELECT COUNT(*) FROM progress_logs WHERE parsed_fields LIKE '%\"question_count\": 999%'"
        cursor.execute(query_check)
        count = cursor.fetchone()[0]
        
        print(f"Found {count} rows where question_count is 999 in parsed_fields.")

        if count > 0:
            query_delete = "DELETE FROM progress_logs WHERE parsed_fields LIKE '%\"question_count\": 999%'"
            cursor.execute(query_delete)
            conn.commit()
            print(f"Successfully deleted {cursor.rowcount} rows.")
        else:
            print("No rows found to delete.")

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    main()
