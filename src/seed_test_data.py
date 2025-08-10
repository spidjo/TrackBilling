import bcrypt
from datetime import datetime
from db.database import get_db_connection


def import_sample_data():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Test code to verify what's being stored
    password = "testpass"
    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode('utf-8')
    print(f"Hash to be stored: {hashed_pw}")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (username, password, first_name, last_name, company_name, email, registration_date, is_verified, verification_token, role)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, password
    """, (
        "superadmin", hashed_pw, "Admin", "User", "Admin Company", "spidjo@gmail.com", 
        datetime.now(), 1, None, "superadmin"
    ))
    inserted_data = cursor.fetchone()
    print(f"Actually stored in DB: {inserted_data[1]}")
    conn.commit()
    conn.close()
    print("✅ Sample data imported successfully.")

if __name__ == "__main__":
    import_sample_data()
