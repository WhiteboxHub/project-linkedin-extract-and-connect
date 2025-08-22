

import mysql.connector
from mysql.connector import Error
import yaml
import os

# Path to config.yaml
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")

# Load config
try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f) or {}
except FileNotFoundError:
    print(f"❌ config.yaml not found at {CONFIG_PATH}")
    config_data = {}

db_config = config_data.get("db", {})

def get_connection():
    try:
        connection = mysql.connector.connect(
            host=db_config.get("host", "localhost"),
            user=db_config.get("user", "root"),
            password=db_config.get("password", ""),
            database=db_config.get("database", "")
        )
        return connection
    except Error as e:
        print("❌ Database connection error:", e)
        return None

def insert_contact(full_name, source_email, email, phone, linkedin_id, linkedin_internal_id, company_name, location):
    conn = get_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        sql = """
            INSERT INTO vendor_contact_extracts 
            (full_name, source_email, email, phone, linkedin_id, linkedin_internal_id, company_name, location, extraction_date, moved_to_vendor) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURDATE(), 0)
        """
        cursor.execute(sql, (full_name, source_email, email, phone, linkedin_id, linkedin_internal_id, company_name, location))
        conn.commit()
        print(f"💾 Saved to DB: {full_name} ({linkedin_id}, internal_id={linkedin_internal_id})")
    except Error as e:
        print("❌ Insert error:", e)
    finally:
        cursor.close()
        conn.close()
