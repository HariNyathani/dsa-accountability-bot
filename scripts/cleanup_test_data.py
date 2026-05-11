import sqlite3
import os

def main():
    # Construct the absolute path to the database
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'db', 'dsa_bot.db'))
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Count the number of rows matching the legacy test string
        query_check = "SELECT COUNT(*) FROM progress_logs WHERE topics LIKE '%2 sum%'"
        cursor.execute(query_check)
        count = cursor.fetchone()[0]
        print(f"Found {count} rows containing '2 sum' in the topics column.")

        if count > 0:
            # Execute the deletion
            query_delete = "DELETE FROM progress_logs WHERE topics LIKE '%2 sum%'"
            cursor.execute(query_delete)
            conn.commit()
            deleted_count = cursor.rowcount
            print(f"Successfully deleted {deleted_count} orphaned legacy test rows.")
        else:
            print("No legacy test rows found.")

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()
