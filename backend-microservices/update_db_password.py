import os
import pymysql
import hashlib
import base64
import secrets

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": int(os.environ.get("DB_PORT", "3307")),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", "parksmartpass"),
    "database": os.environ.get("DB_NAME", "parksmartdb"),
    "charset": "utf8mb4",
}

def django_password_hash(password: str) -> str:
    salt = secrets.token_hex(12)
    iterations = 1000000
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations)
    hash_b64 = base64.b64encode(dk).decode()
    return f"pbkdf2_sha256${iterations}${salt}${hash_b64}"

def main():
    conn = pymysql.connect(**DB_CONFIG)
    try:
        cursor = conn.cursor()
        new_hash = django_password_hash("admin1234@")
        cursor.execute("UPDATE users_user SET password = %s WHERE email = 'admin@parksmart.com'", (new_hash,))
        conn.commit()
        if cursor.rowcount > 0:
            print("Successfully updated password for admin@parksmart.com database record.")
        else:
            print("admin@parksmart.com not found in the database. Password update skipped.")
    except Exception as e:
        print(f"Error updating DB: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
