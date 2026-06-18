# Check subscription data
from database.unified_db_manager import db

with db.get_connection() as conn:
    cursor = db.db_conn.get_cursor(conn)
    
    # Show all subscriptions
    cursor.execute("SELECT * FROM subscriptions")
    rows = cursor.fetchall()
    print("=== ALL SUBSCRIPTIONS ===")
    for row in rows:
        print(dict(row))
    
    # Show subscription for company 1
    cursor.execute("SELECT * FROM subscriptions WHERE company_id = ?", (1,))
    rows = cursor.fetchall()
    print("\n=== SUBSCRIPTIONS FOR COMPANY 1 ===")
    for row in rows:
        print(dict(row))