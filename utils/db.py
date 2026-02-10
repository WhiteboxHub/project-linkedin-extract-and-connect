#fix for activity_log
# utils/db.py - HYBRID VERSION (Direct DB for contacts, API for activity)
# import mysql.connector
# from mysql.connector import Error
# import logging
# import os
# from dotenv import load_dotenv

# # Load environment variables from .env file
# load_dotenv()

# logger = logging.getLogger(__name__)

# def get_db_connection():
#     """Create and return database connection using environment variables"""
#     try:
#         connection = mysql.connector.connect(
#             host=os.getenv('DB_HOST', 'localhost'),
#             database=os.getenv('DB_NAME', 'whitebox_learning'),
#             user=os.getenv('DB_USER', 'root'),
#             password=os.getenv('DB_PASSWORD', 'Reddy@123!')
#         )
#         return connection
#     except Error as e:
#         logger.error(f"Database connection error: {e}")
#         return None

# def insert_contact(full_name, source_email, email, phone, linkedin_id, linkedin_internal_id, company_name, location):
#     """Insert contact into vendor_contact_extracts table (DIRECT DB)"""
#     try:
#         conn = get_db_connection()
#         if not conn:
#             logger.error("No database connection")
#             return False
            
#         cursor = conn.cursor()
        
#         # Check if contact already exists (same linkedin_id from same source_email)
#         check_query = """
#         SELECT COUNT(*) FROM vendor_contact_extracts 
#         WHERE linkedin_id = %s AND source_email = %s
#         """
#         cursor.execute(check_query, (linkedin_id, source_email))
#         count = cursor.fetchone()[0]
        
#         if count > 0:
#             logger.info(f"Contact already exists in DB (skipping duplicate): {full_name} ({linkedin_id})")
#             cursor.close()
#             conn.close()
#             return True
        
#         # Insert new contact
#         insert_query = """
#         INSERT INTO vendor_contact_extracts 
#         (full_name, source_email, email, phone, linkedin_id, linkedin_internal_id, company_name, location)
#         VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
#         """
        
#         cursor.execute(insert_query, (
#             full_name, source_email, email, phone, 
#             linkedin_id, linkedin_internal_id, company_name, location
#         ))
        
#         conn.commit()
#         cursor.close()
#         conn.close()
        
#         logger.info(f"Contact saved to DB: {full_name}")
#         return True
        
#     except Exception as e:
#         logger.error(f"Failed to save contact {full_name} to DB: {e}")
#         return False

# def log_activity(job_id, candidate_id, employee_id, activity_count):
#     """Log activity via API (uses secret token)"""
#     try:
#         from utils.api_logger import log_extraction_activity
        
#         # This is called from old code, so we adapt it
#         log_extraction_activity(
#             candidate_name=f"Candidate_{candidate_id}",
#             candidate_email="",
#             employee_id=employee_id,
#             activity_count=activity_count,
#             notes=f"Activity logged: {activity_count} extractions"
#         )
        
#     except Exception as e:
#         logger.error(f"Failed to log activity via API: {e}")


#---------------------------------------------------------------updated db.py----------------------------------------------------
# # utils/db.py
# # ============================================
# # API OPERATIONS - NO DATABASE
# # ============================================
# # All operations use WBL API with token from config.py
# # - insert_contact() -> POST /vendor_contact
# # - log_activity() -> POST /job_activity_logs
# # ============================================

# import logging
# import requests
# from datetime import datetime

# logger = logging.getLogger(__name__)

# # ============================================
# # WBL CONFIG LOADER
# # ============================================

# def get_wbl_config():
#     """Load WBL configuration from config.py."""
#     try:
#         from config import WBL_CONFIG
#         return WBL_CONFIG
#     except ImportError:
#         logger.error("config.py not found. Run 'python setup.py' first.")
#         return None
#     except Exception as e:
#         logger.error(f"Error loading config.py: {e}")
#         return None

# def get_api_headers(token):
#     """Get standard API headers."""
#     return {
#         "Authorization": f"Bearer {token}",
#         "Content-Type": "application/json"
#     }

# # ============================================
# # VENDOR CONTACT OPERATIONS (API)
# # ============================================

# def insert_contact(full_name, source_email, email, phone, linkedin_id, linkedin_internal_id, company_name, location):
#     """
#     Insert contact via API: POST /vendor_contact
    
#     Args:
#         full_name: Contact's full name
#         source_email: LinkedIn account email used for extraction
#         email: Contact's email (if found)
#         phone: Contact's phone (if found)
#         linkedin_id: LinkedIn profile slug
#         linkedin_internal_id: LinkedIn internal ID
#         company_name: Contact's company
#         location: Contact's location
    
#     Returns:
#         bool: True if successful, False otherwise
#     """
#     try:
#         # Load config
#         config = get_wbl_config()
#         if not config:
#             logger.error("Cannot save contact: config.py not found")
#             return False
        
#         api_url = config.get("API_URL")
#         token = config.get("TOKEN")
        
#         if not api_url or not token:
#             logger.error("API_URL or TOKEN missing in config.py")
#             return False
        
#         # Prepare payload
#         payload = {
#             "full_name": full_name,
#             "source_email": source_email,
#             "linkedin_id": linkedin_id,
#             "linkedin_internal_id": linkedin_internal_id
#         }
        
#         # Add optional fields
#         if email:
#             payload["email"] = email
#         if phone:
#             payload["phone"] = phone
#         if company_name:
#             payload["company_name"] = company_name
#         if location:
#             payload["location"] = location
        
#         # Make API request
#         endpoint = f"{api_url}/vendor_contact"
#         headers = get_api_headers(token)
        
#         logger.debug(f"Saving contact to API: {endpoint}")
        
#         response = requests.post(
#             endpoint,
#             json=payload,
#             headers=headers,
#             timeout=30
#         )
        
#         # Handle response
#         if response.status_code in [200, 201]:
#             result = response.json()
#             logger.info(f"Contact saved via API: {full_name} (ID: {result.get('id', 'N/A')})")
#             return True
#         elif response.status_code == 401:
#             logger.error("Unauthorized. Token expired. Run setup.py again.")
#             return False
#         elif response.status_code == 409:
#             logger.info(f"Contact already exists (skipping): {full_name}")
#             return True
#         elif response.status_code == 422:
#             logger.error(f"Validation error: {response.text}")
#             return False
#         else:
#             logger.error(f"API error {response.status_code}: {response.text}")
#             return False
            
#     except requests.exceptions.ConnectionError:
#         logger.error("Cannot connect to API server")
#         return False
#     except requests.exceptions.Timeout:
#         logger.error("API request timeout")
#         return False
#     except Exception as e:
#         logger.error(f"Failed to save contact {full_name}: {e}")
#         return False

# # ============================================
# # ACTIVITY LOGGING (API)
# # ============================================

# def log_activity(job_id, candidate_id, employee_id, activity_count, notes=None):
#     """
#     Log activity via WBL API: POST /job_activity_logs
    
#     Args:
#         job_id: Job type ID (120 for extraction, 121 for connector)
#         candidate_id: Candidate ID
#         employee_id: Employee ID
#         activity_count: Number of activities
#         notes: Optional notes
    
#     Returns:
#         bool: True if successful, False otherwise
#     """
#     try:
#         # Load config
#         config = get_wbl_config()
#         if not config:
#             logger.error("Cannot log activity: config.py not found")
#             return False
        
#         api_url = config.get("API_URL")
#         token = config.get("TOKEN")
        
#         if not api_url or not token:
#             logger.error("API_URL or TOKEN missing in config.py")
#             return False
        
#         # Use config values if not provided
#         if not employee_id:
#             employee_id = config.get("EMPLOYEE_ID")
#         if not candidate_id:
#             candidate_id = config.get("CANDIDATE_ID")
        
#         # Prepare payload
#         payload = {
#             "job_type_id": int(job_id),
#             "employee_id": int(employee_id),
#             "activity_date": datetime.now().strftime("%Y-%m-%d"),
#             "activity_count": int(activity_count)
#         }
        
#         # Add optional fields
#         if candidate_id and int(candidate_id) > 0:
#             payload["candidate_id"] = int(candidate_id)
        
#         if notes:
#             payload["notes"] = str(notes)
        
#         # Make API request
#         endpoint = f"{api_url}/job_activity_logs"
#         headers = get_api_headers(token)
        
#         logger.info(f"Logging activity: Job={job_id}, Count={activity_count}")
        
#         response = requests.post(
#             endpoint,
#             json=payload,
#             headers=headers,
#             timeout=30
#         )
        
#         # Handle response
#         if response.status_code in [200, 201]:
#             result = response.json()
#             logger.info(f"Activity logged! ID: {result.get('id')}")
#             return True
#         elif response.status_code == 401:
#             logger.error("Unauthorized. Token expired. Run setup.py again.")
#             return False
#         elif response.status_code == 422:
#             logger.error(f"Validation error: {response.text}")
#             return False
#         else:
#             logger.error(f"API error {response.status_code}: {response.text}")
#             return False
            
#     except requests.exceptions.ConnectionError:
#         logger.error("Cannot connect to API server")
#         return False
#     except requests.exceptions.Timeout:
#         logger.error("API request timeout")
#         return False
#     except Exception as e:
#         logger.error(f"Activity log error: {e}")
#         return False

# def log_extraction_activity(candidate_id, employee_id, activity_count, notes=None):
#     """Log extraction activity (job_id=120)."""
#     try:
#         config = get_wbl_config()
#         job_id = config.get("EXTRACTION_JOB_ID", 120) if config else 120
        
#         return log_activity(
#             job_id=job_id,
#             candidate_id=candidate_id,
#             employee_id=employee_id,
#             activity_count=activity_count,
#             notes=notes or f"Extracted {activity_count} contacts"
#         )
#     except Exception as e:
#         logger.error(f"Failed to log extraction activity: {e}")
#         return False

# def log_connector_activity(candidate_id, employee_id, activity_count, notes=None):
#     """Log connector activity (job_id=121)."""
#     try:
#         config = get_wbl_config()
#         job_id = config.get("CONNECTOR_JOB_ID", 121) if config else 121
        
#         return log_activity(
#             job_id=job_id,
#             candidate_id=candidate_id,
#             employee_id=employee_id,
#             activity_count=activity_count,
#             notes=notes or f"Sent {activity_count} connections"
#         )
#     except Exception as e:
#         logger.error(f"Failed to log connector activity: {e}")
#         return False


#log activity and vendor fail
# utils/db.py
# ============================================
# API OPERATIONS - WITH FULL DEBUG LOGGING
# ============================================

import logging
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

# ============================================
# WBL CONFIG LOADER
# ============================================

def get_wbl_config():
    """Load WBL configuration from config.py."""
    logger.debug("[GET_CONFIG] Loading config.py...")
    
    try:
        from config import WBL_CONFIG
        
        logger.debug(f"[GET_CONFIG] SUCCESS - Keys found: {list(WBL_CONFIG.keys())}")
        logger.debug(f"[GET_CONFIG] API_URL: {WBL_CONFIG.get('API_URL')}")
        logger.debug(f"[GET_CONFIG] EMPLOYEE_ID: {WBL_CONFIG.get('EMPLOYEE_ID')}")
        logger.debug(f"[GET_CONFIG] CANDIDATE_ID: {WBL_CONFIG.get('CANDIDATE_ID')}")
        
        token = WBL_CONFIG.get('TOKEN', '')
        if token:
            logger.debug(f"[GET_CONFIG] TOKEN: {token[:30]}...{token[-10:]}")
        else:
            logger.error("[GET_CONFIG] TOKEN is empty or missing!")
        
        return WBL_CONFIG
        
    except ImportError as e:
        logger.error(f"[GET_CONFIG] FAILED - ImportError: {e}")
        logger.error("[GET_CONFIG] config.py not found. Run 'python setup.py' first.")
        return None
    except Exception as e:
        logger.error(f"[GET_CONFIG] FAILED - Exception: {e}", exc_info=True)
        return None

def get_api_headers(token):
    """Get standard API headers."""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

# ============================================
# VENDOR CONTACT OPERATIONS (API)
# ============================================

def insert_contact(full_name, source_email, email, phone, linkedin_id, linkedin_internal_id, company_name, location):
    """
    Insert contact via API: POST /vendor_contact
    
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info("=" * 60)
    logger.info(f"[INSERT_CONTACT] START - Saving: {full_name}")
    logger.info("=" * 60)
    
    try:
        # Step 1: Load config
        logger.info("[INSERT_CONTACT] Step 1: Loading config...")
        config = get_wbl_config()
        
        if not config:
            logger.error("[INSERT_CONTACT] FAILED: config is None")
            return False
        
        api_url = config.get("API_URL")
        token = config.get("TOKEN")
        
        logger.info(f"[INSERT_CONTACT] API URL: {api_url}")
        logger.info(f"[INSERT_CONTACT] Token present: {bool(token)}")
        
        if not api_url:
            logger.error("[INSERT_CONTACT] FAILED: API_URL is missing")
            return False
            
        if not token:
            logger.error("[INSERT_CONTACT] FAILED: TOKEN is missing")
            return False
        
        # Step 2: Prepare payload
        logger.info("[INSERT_CONTACT] Step 2: Preparing payload...")
        
        payload = {
            "full_name": full_name,
            "source_email": source_email,
            "linkedin_id": linkedin_id,
            "linkedin_internal_id": linkedin_internal_id
        }
        
        # Add optional fields
        if email:
            payload["email"] = email
            logger.debug(f"[INSERT_CONTACT] Adding email: {email}")
        if phone:
            payload["phone"] = phone
            logger.debug(f"[INSERT_CONTACT] Adding phone: {phone}")
        if company_name:
            payload["company_name"] = company_name
            logger.debug(f"[INSERT_CONTACT] Adding company: {company_name}")
        if location:
            payload["location"] = location
            logger.debug(f"[INSERT_CONTACT] Adding location: {location}")
        
        logger.info(f"[INSERT_CONTACT] Payload: {payload}")
        
        # Step 3: Make API request
        endpoint = f"{api_url}/vendor_contact"
        headers = get_api_headers(token)
        
        logger.info(f"[INSERT_CONTACT] Step 3: Calling API...")
        logger.info(f"[INSERT_CONTACT] Endpoint: POST {endpoint}")
        logger.debug(f"[INSERT_CONTACT] Headers: {headers}")
        
        response = requests.post(
            endpoint,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        # Step 4: Handle response
        logger.info(f"[INSERT_CONTACT] Step 4: Processing response...")
        logger.info(f"[INSERT_CONTACT] Status Code: {response.status_code}")
        logger.info(f"[INSERT_CONTACT] Response Headers: {dict(response.headers)}")
        logger.info(f"[INSERT_CONTACT] Response Body: {response.text}")
        
        if response.status_code in [200, 201]:
            try:
                result = response.json()
                logger.info(f"[INSERT_CONTACT] SUCCESS! Created ID: {result.get('id', 'N/A')}")
                return True
            except:
                logger.info("[INSERT_CONTACT] SUCCESS! (no JSON body)")
                return True
                
        elif response.status_code == 401:
            logger.error("[INSERT_CONTACT] FAILED: 401 Unauthorized")
            logger.error("[INSERT_CONTACT] Token may have expired. Run 'python setup.py' again.")
            return False
            
        elif response.status_code == 409:
            logger.info(f"[INSERT_CONTACT] SKIPPED: Contact already exists (409 Conflict)")
            return True  # Not an error
            
        elif response.status_code == 422:
            logger.error(f"[INSERT_CONTACT] FAILED: 422 Validation Error")
            logger.error(f"[INSERT_CONTACT] Response: {response.text}")
            return False
            
        else:
            logger.error(f"[INSERT_CONTACT] FAILED: Unexpected status {response.status_code}")
            logger.error(f"[INSERT_CONTACT] Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError as e:
        logger.error(f"[INSERT_CONTACT] FAILED: Connection Error")
        logger.error(f"[INSERT_CONTACT] Cannot connect to API server: {e}")
        return False
        
    except requests.exceptions.Timeout as e:
        logger.error(f"[INSERT_CONTACT] FAILED: Timeout")
        logger.error(f"[INSERT_CONTACT] Request took too long: {e}")
        return False
        
    except Exception as e:
        logger.error(f"[INSERT_CONTACT] FAILED: Unexpected Exception")
        logger.error(f"[INSERT_CONTACT] Error: {e}", exc_info=True)
        return False
    
    finally:
        logger.info("[INSERT_CONTACT] END")
        logger.info("=" * 60)


# ============================================
# BULK INSERT CONTACTS
# ============================================

def bulk_insert_contacts(contacts_list):
    """
    Bulk insert multiple contacts via API: POST /vendor_contact/bulk
    
    Args:
        contacts_list: List of dicts with contact data
            Each dict should have:
            - full_name (required)
            - source_email (required)
            - linkedin_id (optional)
            - linkedin_internal_id (optional)
            - email (optional)
            - phone (optional)
            - company_name (optional)
            - location (optional)
    
    Returns:
        dict: {
            'success': bool,
            'inserted': int,
            'duplicates': int,
            'failed': int,
            'total': int,
            'failed_contacts': list,
            'duplicate_contacts': list
        }
    """
    logger.info("=" * 60)
    logger.info(f"[BULK_INSERT] START - Inserting {len(contacts_list)} contacts")
    logger.info("=" * 60)
    
    try:
        # Step 1: Load config
        logger.info("[BULK_INSERT] Step 1: Loading config...")
        config = get_wbl_config()
        
        if not config:
            logger.error("[BULK_INSERT] FAILED: config is None")
            return {
                'success': False,
                'inserted': 0,
                'duplicates': 0,
                'failed': len(contacts_list),
                'total': len(contacts_list),
                'error': 'Config not found'
            }
        
        api_url = config.get("API_URL")
        token = config.get("TOKEN")
        
        logger.info(f"[BULK_INSERT] API URL: {api_url}")
        logger.info(f"[BULK_INSERT] Token present: {bool(token)}")
        
        if not api_url or not token:
            logger.error("[BULK_INSERT] FAILED: API_URL or TOKEN missing")
            return {
                'success': False,
                'inserted': 0,
                'duplicates': 0,
                'failed': len(contacts_list),
                'total': len(contacts_list),
                'error': 'API credentials missing'
            }
        
        # Step 2: Prepare payload
        logger.info("[BULK_INSERT] Step 2: Preparing bulk payload...")
        
        payload = {
            "contacts": contacts_list
        }
        
        logger.info(f"[BULK_INSERT] Total contacts in payload: {len(contacts_list)}")
        
        # Step 3: Make API request
        endpoint = f"{api_url}/vendor_contact/bulk"
        headers = get_api_headers(token)
        
        logger.info(f"[BULK_INSERT] Step 3: Calling bulk API...")
        logger.info(f"[BULK_INSERT] Endpoint: POST {endpoint}")
        
        response = requests.post(
            endpoint,
            json=payload,
            headers=headers,
            timeout=60  # Longer timeout for bulk operations
        )
        
        # Step 4: Handle response
        logger.info(f"[BULK_INSERT] Step 4: Processing response...")
        logger.info(f"[BULK_INSERT] Status Code: {response.status_code}")
        
        if response.status_code in [200, 201]:
            result = response.json()
            logger.info(f"[BULK_INSERT] SUCCESS!")
            logger.info(f"[BULK_INSERT]   Inserted: {result.get('inserted', 0)}")
            logger.info(f"[BULK_INSERT]   Duplicates: {result.get('duplicates', 0)}")
            logger.info(f"[BULK_INSERT]   Failed: {result.get('failed', 0)}")
            logger.info(f"[BULK_INSERT]   Total: {result.get('total', 0)}")
            
            # Log duplicate contact details for debugging
            duplicate_contacts = result.get('duplicate_contacts', [])
            if duplicate_contacts:
                logger.warning(f"[BULK_INSERT] Duplicate contacts detected:")
                for dup in duplicate_contacts:
                    logger.warning(f"[BULK_INSERT]   - {dup.get('full_name', 'Unknown')} (LinkedIn ID: {dup.get('linkedin_id', 'N/A')})")
            
            # Log failed contact details for debugging
            failed_contacts = result.get('failed_contacts', [])
            if failed_contacts:
                logger.error(f"[BULK_INSERT] Failed contacts:")
                for fail in failed_contacts:
                    logger.error(f"[BULK_INSERT]   - {fail.get('full_name', 'Unknown')}: {fail.get('error', 'Unknown error')}")
            
            return {
                'success': True,
                'inserted': result.get('inserted', 0),
                'duplicates': result.get('duplicates', 0),
                'failed': result.get('failed', 0),
                'total': result.get('total', 0),
                'failed_contacts': result.get('failed_contacts', []),
                'duplicate_contacts': result.get('duplicate_contacts', [])
            }
        
        elif response.status_code == 401:
            logger.error("[BULK_INSERT] FAILED: 401 Unauthorized")
            logger.error("[BULK_INSERT] Token may have expired. Run 'python setup.py' again.")
            return {
                'success': False,
                'inserted': 0,
                'duplicates': 0,
                'failed': len(contacts_list),
                'total': len(contacts_list),
                'error': 'Unauthorized - token expired'
            }
        
        else:
            logger.error(f"[BULK_INSERT] FAILED: Status {response.status_code}")
            logger.error(f"[BULK_INSERT] Response: {response.text}")
            return {
                'success': False,
                'inserted': 0,
                'duplicates': 0,
                'failed': len(contacts_list),
                'total': len(contacts_list),
                'error': f'API error: {response.status_code}'
            }
    
    except requests.exceptions.ConnectionError as e:
        logger.error(f"[BULK_INSERT] FAILED: Connection Error")
        logger.error(f"[BULK_INSERT] Cannot connect to API server: {e}")
        return {
            'success': False,
            'inserted': 0,
            'duplicates': 0,
            'failed': len(contacts_list),
            'total': len(contacts_list),
            'error': 'Connection error'
        }
    
    except requests.exceptions.Timeout as e:
        logger.error(f"[BULK_INSERT] FAILED: Timeout")
        logger.error(f"[BULK_INSERT] Request took too long: {e}")
        return {
            'success': False,
            'inserted': 0,
            'duplicates': 0,
            'failed': len(contacts_list),
            'total': len(contacts_list),
            'error': 'Request timeout'
        }
    
    except Exception as e:
        logger.error(f"[BULK_INSERT] FAILED: Unexpected Exception")
        logger.error(f"[BULK_INSERT] Error: {e}", exc_info=True)
        return {
            'success': False,
            'inserted': 0,
            'duplicates': 0,
            'failed': len(contacts_list),
            'total': len(contacts_list),
            'error': str(e)
        }
    
    finally:
        logger.info("[BULK_INSERT] END")
        logger.info("=" * 60)

# ============================================
# ACTIVITY LOGGING (API)
# ============================================

def log_activity(job_id, candidate_id, employee_id, activity_count, notes=None):
    """Log activity via WBL API: POST /job_activity_logs"""
    
    logger.info("=" * 60)
    logger.info(f"[LOG_ACTIVITY] START - Job={job_id}, Count={activity_count}")
    logger.info("=" * 60)
    
    try:
        # Step 1: Load config
        logger.info("[LOG_ACTIVITY] Step 1: Loading config...")
        config = get_wbl_config()
        
        if not config:
            logger.error("[LOG_ACTIVITY] FAILED: config is None")
            return False
        
        api_url = config.get("API_URL")
        token = config.get("TOKEN")
        
        if not api_url or not token:
            logger.error("[LOG_ACTIVITY] FAILED: API_URL or TOKEN missing")
            return False
        
        # Use config values if not provided
        if not employee_id:
            employee_id = config.get("EMPLOYEE_ID")
            logger.debug(f"[LOG_ACTIVITY] Using config EMPLOYEE_ID: {employee_id}")
        if not candidate_id:
            candidate_id = config.get("CANDIDATE_ID")
            logger.debug(f"[LOG_ACTIVITY] Using config CANDIDATE_ID: {candidate_id}")
        
        # Step 2: Prepare payload
        logger.info("[LOG_ACTIVITY] Step 2: Preparing payload...")
        
        payload = {
            "job_id": int(job_id),
            "employee_id": int(employee_id),
            "activity_date": datetime.now().strftime("%Y-%m-%d"),
            "activity_count": int(activity_count)
        }
        
        if candidate_id and int(candidate_id) > 0:
            payload["candidate_id"] = int(candidate_id)
        
        if notes:
            payload["notes"] = str(notes)
        
        logger.info(f"[LOG_ACTIVITY] Payload: {payload}")
        
        # Step 3: Make API request
        endpoint = f"{api_url}/job_activity_logs"
        headers = get_api_headers(token)
        
        logger.info(f"[LOG_ACTIVITY] Step 3: Calling API...")
        logger.info(f"[LOG_ACTIVITY] Endpoint: POST {endpoint}")
        
        response = requests.post(
            endpoint,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        # Step 4: Handle response
        logger.info(f"[LOG_ACTIVITY] Status Code: {response.status_code}")
        logger.info(f"[LOG_ACTIVITY] Response: {response.text}")
        
        if response.status_code in [200, 201]:
            result = response.json()
            logger.info(f"[LOG_ACTIVITY] SUCCESS! Log ID: {result.get('id')}")
            return True
        else:
            logger.error(f"[LOG_ACTIVITY] FAILED: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"[LOG_ACTIVITY] FAILED: {e}", exc_info=True)
        return False
    
    finally:
        logger.info("[LOG_ACTIVITY] END")
        logger.info("=" * 60)

def log_extraction_activity(candidate_id, employee_id, activity_count, notes=None):
    """Log extraction activity (job_id=120)."""
    logger.info(f"[LOG_EXTRACTION] Calling with count={activity_count}")
    try:
        config = get_wbl_config()
        job_id = config.get("EXTRACTION_JOB_ID", 120) if config else 120
        logger.info(f"[LOG_EXTRACTION] Using job_id={job_id}")
        return log_activity(job_id, candidate_id, employee_id, activity_count, notes)
    except Exception as e:
        logger.error(f"[LOG_EXTRACTION] FAILED: {e}", exc_info=True)
        return False

