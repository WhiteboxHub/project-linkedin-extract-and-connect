import mysql.connector
from mysql.connector import Error

def get_connection():
    try:
        connection = mysql.connector.connect(
            host="",        # change if DB is on another host
            user="",     # your DB username
            password="", # your DB password
            database=""  # your database name
        )
        return connection
    except Error as e:
        print("❌ Database connection error:", e)
        return None

def insert_contact(full_name, source_email, email, phone, linkedin_id, company_name, location):
    conn = get_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        sql = """
            INSERT INTO vendor_contact_extracts 
            (full_name, source_email, email, phone, linkedin_id, company_name, location, extraction_date, moved_to_vendor) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, CURDATE(), 0)
        """
        cursor.execute(sql, (full_name, source_email, email, phone, linkedin_id, company_name, location))
        conn.commit()
        print(f"💾 Saved to DB: {full_name} ({linkedin_id})")
    except Error as e:
        print("❌ Insert error:", e)
    finally:
        cursor.close()
        conn.close()
