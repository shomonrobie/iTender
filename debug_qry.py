# Create a temporary script or run in Python console
from database.db_manager import DatabaseManager

db = DatabaseManager()

# Method 1: List all users
conn = db.get_connection()
cursor = conn.cursor()
cursor.execute("SELECT id, email, full_name, role, company_id FROM users")
users = cursor.fetchall()

conn.close()

print("All users:")
for user in users:
    print(f"ID: {user[0]}, Email: {user[1]}, Name: {user[2]}, Role: {user[3]}, Company: {user[4]}")