# # utils/db.py
# # ============================================
# # API OPERATIONS - WITH FULL DEBUG LOGGING
# # ============================================
# import base64
# import json
# import logging
# import os
# import re
# import time
# import requests
# from datetime import datetime
# logger = logging.getLogger(__name__)
# # ============================================
# # TOKEN HELPERS
# # ============================================
# # Path to config.py (one level above utils/)
# _CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.py")
# def _is_token_expired(token: str) -> bool:
#     """
#     Decode the JWT payload (no signature verification needed — the server
#     does that) and check whether 'exp' is in the past.
#     Returns True if expired or if the token can't be decoded.
#     """
#     try:
#         payload_b64 = token.split(".")[1]
#         # JWT uses base64url; pad to a multiple of 4
#         padding = 4 - len(payload_b64) % 4
#         payload = json.loads(base64.b64decode(payload_b64 + "=" * padding))
#         exp = payload.get("exp", 0)
#         expired = time.time() > exp
#         if expired:
#             from datetime import timezone
#             exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc)
#             logger.warning(
#                 "[TOKEN] JWT expired at %s (%.0f seconds ago)",
#                 exp_dt.strftime("%Y-%m-%d %H:%M UTC"),
#                 time.time() - exp,
#             )
#         return expired
#     except Exception as exc:
#         logger.warning("[TOKEN] Could not decode JWT to check expiry: %s", exc)
#         return True   # treat as expired if we can't read it
# def _refresh_token() -> str | None:
#     """
#     Re-login to the WBL API using credentials stored in .env
#     (WBL_EMAIL + WBL_PASSWORD) and return a fresh JWT token.
#     After obtaining the token this function:
#       1. Updates the in-memory WBL_CONFIG dict so the current run
#          uses the new token immediately.
#       2. Patches config.py on disk so future runs don't need to
#          re-login again.
#     Returns the new token string, or None on failure.
#     """
#     # ---- load credentials from .env ----
#     try:
#         from dotenv import load_dotenv
#         load_dotenv()
#     except ImportError:
#         pass   # python-dotenv is optional; os.getenv still works
#     email    = os.getenv("WBL_EMAIL")
#     password = os.getenv("WBL_PASSWORD")
#     api_url  = os.getenv("WBL_API_URL", "http://localhost:8000/api")
#     if not email or not password:
#         logger.error(
#             "[TOKEN] Cannot auto-refresh: WBL_EMAIL or WBL_PASSWORD "
#             "not found in .env  —  add them and retry."
#         )
#         return None
#     logger.info("[TOKEN] Refreshing token for %s …", email)
#     try:
#         response = requests.post(
#             f"{api_url}/login",
#             data={"username": email, "password": password},
#             headers={"Content-Type": "application/x-www-form-urlencoded"},
#             timeout=30,
#         )
#         if response.status_code == 200:
#             new_token = response.json().get("access_token")
#             if new_token:
#                 logger.info("[TOKEN] New token obtained successfully")
#                 _update_config_token(new_token, api_url)
#                 return new_token
#             logger.error("[TOKEN] Login succeeded but no access_token in response")
#             return None
#         logger.error(
#             "[TOKEN] Login failed — %s: %s",
#             response.status_code, response.text[:200],
#         )
#         return None
#     except requests.exceptions.ConnectionError:
#         logger.error("[TOKEN] Cannot connect to %s — is the WBL API running?", api_url)
#         return None
#     except Exception as exc:
#         logger.error("[TOKEN] Unexpected error during token refresh: %s", exc)
#         return None
# def _update_config_token(new_token: str, api_url: str | None = None) -> None:
#     """
#     1. Patch the in-memory WBL_CONFIG so the current process uses the
#        new token immediately (no restart needed).
#     2. Rewrite the TOKEN line in config.py so future runs start fresh.
#     """
#     # --- in-memory patch ---
#     try:
#         import importlib, sys
#         # Force re-import if already cached
#         if "config" in sys.modules:
#             cfg_module = sys.modules["config"]
#             cfg_module.WBL_CONFIG["TOKEN"] = new_token
#             if api_url:
#                 cfg_module.WBL_CONFIG["API_URL"] = api_url
#     except Exception as exc:
#         logger.debug("[TOKEN] In-memory patch skipped: %s", exc)
#     # --- file patch ---
#     try:
#         with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
#             content = fh.read()
#         content = re.sub(
#             r'"TOKEN":\s*"[^"]*"',
#             f'"TOKEN": "{new_token}"',
#             content,
#         )
#         content = re.sub(
#             r'"TOKEN_GENERATED_AT":\s*"[^"]*"',
#             f'"TOKEN_GENERATED_AT": "{datetime.now().isoformat()}"',
#             content,
#         )
#         with open(_CONFIG_PATH, "w", encoding="utf-8") as fh:
#             fh.write(content)
#         logger.info("[TOKEN] config.py updated with new token")
#     except Exception as exc:
#         logger.warning("[TOKEN] Could not update config.py on disk: %s", exc)
# # ============================================
# # WBL CONFIG LOADER
# # ============================================
# def get_wbl_config():
#     """
#     Load WBL configuration from config.py.
#     If the JWT token inside config.py is expired, this function
#     automatically re-logins using WBL_EMAIL + WBL_PASSWORD from .env
#     and refreshes the token before returning — no manual intervention
#     required.
#     """
#     logger.debug("[GET_CONFIG] Loading config.py...")
#     try:
#         from config import WBL_CONFIG
#         logger.debug("[GET_CONFIG] SUCCESS — API_URL: %s", WBL_CONFIG.get("API_URL"))
#         token = WBL_CONFIG.get("TOKEN", "")
#         if not token:
#             logger.error("[GET_CONFIG] TOKEN is empty or missing in config.py")
#             return None
#         # ---- auto-refresh if expired ----
#         if _is_token_expired(token):
#             logger.warning("[GET_CONFIG] Token is expired — attempting auto-refresh...")
#             new_token = _refresh_token()
#             if new_token:
#                 WBL_CONFIG["TOKEN"] = new_token
#                 logger.info("[GET_CONFIG] Token refreshed — continuing with new token")
#             else:
#                 logger.error(
#                     "[GET_CONFIG] Auto-refresh failed. "
#                     "Add WBL_EMAIL and WBL_PASSWORD to .env and retry, "
#                     "or run: python setup.py"
#                 )
#                 return None
#         else:
#             logger.debug("[GET_CONFIG] Token valid")
#         return WBL_CONFIG
#     except ImportError as exc:
#         logger.error("[GET_CONFIG] config.py not found: %s — run 'python setup.py' first", exc)
#         return None
#     except Exception as exc:
#         logger.error("[GET_CONFIG] Unexpected error: %s", exc, exc_info=True)
#         return None
# def get_api_headers(token):
#     """Get standard API headers."""
#     return {
#         "Authorization": f"Bearer {token}",
#         "Content-Type": "application/json"
#     }
# # ============================================
# # AUTOMATION CONTACT EXTRACTS (API)
# # ============================================
# def insert_automation_contact(
#     full_name=None, 
#     email=None, 
#     phone=None, 
#     company_name=None, 
#     job_title=None, 
#     city=None, 
#     state=None, 
#     country=None, 
#     postal_code=None, 
#     linkedin_id=None, 
#     linkedin_internal_id=None, 
#     source_reference=None,
#     raw_payload=None,
#     source_type="bot_linkedin_message_extraction"
# ):
#     """
#     Insert automation contact via API: POST /automation-extracts
#     Returns:
#         bool: True if successful, False otherwise
#     """
#     logger.info("=" * 60)
#     logger.info(f"[INSERT_AUTOMATION_CONTACT] START - Saving: {full_name}")
#     logger.info("=" * 60)
#     try:
#         # Step 1: Load config
#         logger.info("[INSERT_AUTOMATION_CONTACT] Step 1: Loading config...")
#         config = get_wbl_config()
#         if not config:
#             logger.error("[INSERT_AUTOMATION_CONTACT] FAILED: config is None")
#             return False
#         api_url = config.get("API_URL")
#         token = config.get("TOKEN")
#         if not api_url or not token:
#             logger.error("[INSERT_AUTOMATION_CONTACT] FAILED: API_URL or TOKEN missing")
#             return False
#         # Step 1b: Validate email (syntax + MX) before payload build
#         email_invalid = False
#         domain_invalid = False
#         mailbox_invalid = False
#         if email:
#             try:
#                 from utils.email_validator import validate_email as _v_email
#                 _vr = _v_email(email, check_mx=True, check_smtp=False)
#                 if not _vr["valid"]:
#                     email_invalid = True
#                     if not _vr["syntax_valid"]:
#                         domain_invalid = True
#                     else:
#                         mailbox_invalid = True
#                 logger.debug("[INSERT_AUTOMATION_CONTACT] Email validated: %s (Valid: %s)", email, _vr["valid"])
#             except ImportError:
#                 logger.warning("[INSERT_AUTOMATION_CONTACT] utils.email_validator not available.")
#         # Step 2: Prepare payload
#         logger.info("[INSERT_AUTOMATION_CONTACT] Step 2: Preparing payload...")
#         payload = {
#             "source_type": source_type,
#             "email_invalid": email_invalid,
#             "domain_invalid": domain_invalid,
#             "mailbox_invalid": mailbox_invalid
#         }
#         # Add optional fields only if they have values
#         if full_name: payload["full_name"] = full_name
#         if email: payload["email"] = email
#         if phone: payload["phone"] = phone
#         if company_name: payload["company_name"] = company_name
#         if job_title: payload["job_title"] = job_title
#         if city: payload["city"] = city
#         if state: payload["state"] = state
#         if country: payload["country"] = country
#         if postal_code: payload["postal_code"] = postal_code
#         if linkedin_id: payload["linkedin_id"] = linkedin_id
#         if linkedin_internal_id: payload["linkedin_internal_id"] = linkedin_internal_id
#         if source_reference: payload["source_reference"] = source_reference
#         if raw_payload: payload["raw_payload"] = raw_payload
#         logger.info(f"[INSERT_AUTOMATION_CONTACT] Payload ready (keys: {list(payload.keys())})")
#         # Step 3: Make API request
#         endpoint = f"{api_url}/automation-extracts"
#         headers = get_api_headers(token)
#         logger.info(f"[INSERT_AUTOMATION_CONTACT] Step 3: Calling API -> POST {endpoint}")
#         response = requests.post(
#             endpoint,
#             json=payload,
#             headers=headers,
#             timeout=30
#         )
#         # Step 4: Handle response
#         logger.info(f"[INSERT_AUTOMATION_CONTACT] Status Code: {response.status_code}")
#         if response.status_code in [200, 201]:
#             try:
#                 result = response.json()
#                 logger.info(f"[INSERT_AUTOMATION_CONTACT] SUCCESS! Created ID: {result.get('id', 'N/A')}")
#                 return True
#             except:
#                 logger.info("[INSERT_AUTOMATION_CONTACT] SUCCESS! (no JSON body)")
#                 return True
#         elif response.status_code == 401:
#             logger.error("[INSERT_AUTOMATION_CONTACT] FAILED: 401 Unauthorized")
#             return False
#         elif response.status_code == 409:
#             logger.info(f"[INSERT_AUTOMATION_CONTACT] SKIPPED: Contact already exists (409 Conflict)")
#             return True
#         elif response.status_code == 422:
#             logger.error(f"[INSERT_AUTOMATION_CONTACT] FAILED: 422 Validation Error -> {response.text}")
#             return False
#         else:
#             logger.error(f"[INSERT_AUTOMATION_CONTACT] FAILED: Unexpected status {response.status_code} -> {response.text}")
#             return False
#     except requests.exceptions.ConnectionError as e:
#         logger.error(f"[INSERT_AUTOMATION_CONTACT] FAILED: Connection Error: {e}")
#         return False
#     except requests.exceptions.Timeout as e:
#         logger.error(f"[INSERT_AUTOMATION_CONTACT] FAILED: Timeout: {e}")
#         return False
#     except Exception as e:
#         logger.error(f"[INSERT_AUTOMATION_CONTACT] FAILED: Unexpected Exception: {e}", exc_info=True)
#         return False
#     finally:
#         logger.info("[INSERT_AUTOMATION_CONTACT] END")
#         logger.info("=" * 60)
# def bulk_insert_automation_contacts(contacts_list):
#     """
#     Bulk insert automation contacts via API: POST /automation-extracts/bulk
#     Args:
#         contacts_list: List of dicts with automation contact data
#             Each dict mapping to AutomationContactExtractCreate
#     """
#     logger.info("=" * 60)
#     logger.info(f"[BULK_AUTOMATION_INSERT] START - Inserting {len(contacts_list)} contacts")
#     logger.info("=" * 60)
#     try:
#         # Step 1: Load config
#         logger.info("[BULK_AUTOMATION_INSERT] Step 1: Loading config...")
#         config = get_wbl_config()
#         if not config:
#             logger.error("[BULK_AUTOMATION_INSERT] FAILED: config is None")
#             return {'success': False, 'inserted': 0, 'failed': len(contacts_list), 'total': len(contacts_list)}
#         api_url = config.get("API_URL")
#         token = config.get("TOKEN")
#         if not api_url or not token:
#             logger.error("[BULK_AUTOMATION_INSERT] FAILED: API_URL or TOKEN missing")
#             return {'success': False, 'inserted': 0, 'failed': len(contacts_list), 'total': len(contacts_list)}
#         # Step 2: Prepare payload
#         logger.info("[BULK_AUTOMATION_INSERT] Step 2: Preparing bulk payload...")
#         # Add default source_type to any contacts missing it
#         for contact in contacts_list:
#             if "source_type" not in contact:
#                 contact["source_type"] = "bot_linkedin_message_extraction"
#             # Run email validation if they have an email but haven't been validated yet
#             if contact.get("email") and "email_invalid" not in contact:
#                 try:
#                     from utils.email_validator import validate_email as _v_email
#                     _vr = _v_email(contact["email"], check_mx=True, check_smtp=False)
#                     if not _vr["valid"]:
#                         contact["email_invalid"] = True
#                         if not _vr["syntax_valid"]:
#                             contact["domain_invalid"] = True
#                         else:
#                             contact["mailbox_invalid"] = True
#                     else:
#                         contact["email_invalid"] = False
#                         contact["domain_invalid"] = False
#                         contact["mailbox_invalid"] = False
#                 except ImportError:
#                     pass
#         payload = {"extracts": contacts_list}
#         # Step 3: Make API request
#         endpoint = f"{api_url}/automation-extracts/bulk"
        
#         # Step 3: Make API request with 1 Auto-Retry on 401
#         for attempt in range(2):
#             headers = get_api_headers(token)
#             logger.info(f"[BULK_AUTOMATION_INSERT] Step 3: Calling bulk API (Attempt {attempt+1}) -> POST {endpoint}")
#             response = requests.post(
#                 endpoint,
#                 json=payload,
#                 headers=headers,
#                 timeout=60
#             )
#             # Step 4: Handle response
#             logger.info(f"[BULK_AUTOMATION_INSERT] Status Code: {response.status_code}")
#             if response.status_code in [200, 201]:
#                 result = response.json()
#                 logger.info(f"[BULK_AUTOMATION_INSERT] SUCCESS!")
#                 logger.info(f"   Inserted: {result.get('inserted', 0)}")
#                 logger.info(f"   Duplicates: {result.get('duplicates', 0)}")
#                 logger.info(f"   Failed: {result.get('failed', 0)}")
#                 failed_contacts = result.get('errors', [])
#                 if failed_contacts:
#                     logger.error(f"[BULK_AUTOMATION_INSERT] Errors reported:")
#                     for err in failed_contacts:
#                         logger.error(f"   - {err}")
#                 return {
#                     'success': True,
#                     'inserted': result.get('inserted', 0),
#                     'duplicates': result.get('duplicates', 0),
#                     'failed': result.get('failed', 0),
#                     'total': result.get('total', 0),
#                     'errors': failed_contacts
#                 }
#             elif response.status_code == 401:
#                 logger.error("[BULK_AUTOMATION_INSERT] FAILED: 401 Unauthorized")
#                 if attempt == 0:
#                     logger.info("[BULK_AUTOMATION_INSERT] Attempting to auto-refresh WBL token from .env...")
#                     try:
#                         from utils.auth import refresh_wbl_token_in_config
#                         token = refresh_wbl_token_in_config()
#                         logger.info("[BULK_AUTOMATION_INSERT] Acquired new token. Retrying request.")
#                         continue # Retry the loop
#                     except ImportError:
#                         logger.error("[BULK_AUTOMATION_INSERT] utils.auth module missing. Cannot auto-refresh.")
#                         break
#                     except Exception as e:
#                         logger.error(f"[BULK_AUTOMATION_INSERT] Auto-refresh failed: {e}")
#                         break # Fall through to failure
#                 else:
#                     break # Already retried, give up
#             elif response.status_code == 422:
#                 logger.error(f"[BULK_AUTOMATION_INSERT] FAILED: 422 Validation Error -> {response.text}")
#                 return {'success': False, 'inserted': 0, 'failed': len(contacts_list), 'error': response.text}
#             else:
#                 logger.error(f"[BULK_AUTOMATION_INSERT] FAILED: Status {response.status_code} -> {response.text}")
#                 return {'success': False, 'inserted': 0, 'failed': len(contacts_list)}
                
#         # If loop finishes without returning, failure occurred
#         return {'success': False, 'inserted': 0, 'failed': len(contacts_list)}
#     except requests.exceptions.ConnectionError as e:
#         logger.error(f"[BULK_AUTOMATION_INSERT] FAILED: Connection Error: {e}")
#         return {'success': False, 'inserted': 0, 'failed': len(contacts_list)}
#     except requests.exceptions.Timeout as e:
#         logger.error(f"[BULK_AUTOMATION_INSERT] FAILED: Timeout: {e}")
#         return {'success': False, 'inserted': 0, 'failed': len(contacts_list)}
#     except Exception as e:
#         logger.error(f"[BULK_AUTOMATION_INSERT] FAILED: Unexpected Exception: {e}", exc_info=True)
#         return {'success': False, 'inserted': 0, 'failed': len(contacts_list)}
#     finally:
#         logger.info("[BULK_AUTOMATION_INSERT] END")
#         logger.info("=" * 60)

# # ============================================
# # RAW JOB LISTINGS (API)
# # ============================================

# def bulk_insert_raw_job_listings(positions_list):
#     """
#     Bulk insert positional data via API: POST /raw-positions/bulk
#     Args:
#         positions_list: List of dicts mapping to RawJobListingCreate schema
#     """
#     logger.info("=" * 60)
#     logger.info(f"[BULK_RAW_POSITIONS] START - Inserting {len(positions_list)} positions")
#     logger.info("=" * 60)
    
#     try:
#         # Step 1: Load config
#         logger.info("[BULK_RAW_POSITIONS] Step 1: Loading config...")
#         config = get_wbl_config()
        
#         if not config:
#             logger.error("[BULK_RAW_POSITIONS] FAILED: config is None")
#             return {'success': False, 'inserted': 0, 'failed': len(positions_list), 'total': len(positions_list)}
        
#         api_url = config.get("API_URL")
#         token = config.get("TOKEN")
        
#         if not api_url or not token:
#             logger.error("[BULK_RAW_POSITIONS] FAILED: API_URL or TOKEN missing")
#             return {'success': False, 'inserted': 0, 'failed': len(positions_list), 'total': len(positions_list)}
        
#         # Step 2: Prepare payload
#         logger.info("[BULK_RAW_POSITIONS] Step 2: Preparing bulk payload...")
#         payload = {
#             "positions": positions_list
#         }
        
#         endpoint = f"{api_url}/raw-positions/bulk"
        
#         # Step 3: Make API request with 1 Auto-Retry on 401
#         for attempt in range(2):
#             headers = get_api_headers(token)
            
#             logger.info(f"[BULK_RAW_POSITIONS] Step 3: Calling API (Attempt {attempt+1}) -> POST {endpoint}")
#             response = requests.post(
#                 endpoint,
#                 json=payload,
#                 headers=headers,
#                 timeout=60
#             )
            
#             # Step 4: Handle response
#             logger.info(f"[BULK_RAW_POSITIONS] Status Code: {response.status_code}")
            
#             if response.status_code in [200, 201]:
#                 result = response.json()
#                 logger.info(f"[BULK_RAW_POSITIONS] SUCCESS!")
#                 logger.info(f"   Inserted: {result.get('inserted', 0)}")
#                 logger.info(f"   Skipped: {result.get('skipped', 0)}")
#                 logger.info(f"   Total Processed: {result.get('total', 0)}")
                
#                 failed_contacts = result.get('failed_contacts', [])
#                 if failed_contacts:
#                     logger.error(f"[BULK_RAW_POSITIONS] API reported {len(failed_contacts)} failures")
                
#                 return {
#                     'success': True,
#                     'inserted': result.get('inserted', 0),
#                     'skipped': result.get('skipped', 0),
#                     'total': result.get('total', 0),
#                     'failed': len(failed_contacts),
#                     'failed_contacts': failed_contacts
#                 }
                
#             elif response.status_code == 401:
#                 logger.error("[BULK_RAW_POSITIONS] FAILED: 401 Unauthorized")
#                 if attempt == 0:
#                     logger.info("[BULK_RAW_POSITIONS] Attempting to auto-refresh WBL token from .env...")
#                     try:
#                         from utils.auth import refresh_wbl_token_in_config
#                         token = refresh_wbl_token_in_config()
#                         logger.info("[BULK_RAW_POSITIONS] Acquired new token. Retrying request.")
#                         continue # Retry the loop
#                     except ImportError:
#                         logger.error("[BULK_RAW_POSITIONS] utils.auth module missing. Cannot auto-refresh.")
#                         break
#                     except Exception as e:
#                         logger.error(f"[BULK_RAW_POSITIONS] Auto-refresh failed: {e}")
#                         break # Fall through to failure
#                 else:
#                     break # Already retried, give up
                    
#             elif response.status_code == 422:
#                 logger.error(f"[BULK_RAW_POSITIONS] FAILED: 422 Validation Error -> {response.text}")
#                 return {'success': False, 'inserted': 0, 'failed': len(positions_list), 'total': len(positions_list), 'error': response.text}
                
#             else:
#                 logger.error(f"[BULK_RAW_POSITIONS] FAILED: Unexpected status {response.status_code} -> {response.text}")
#                 return {'success': False, 'inserted': 0, 'failed': len(positions_list), 'total': len(positions_list)}
                
#         # If loop finishes without returning, failure occurred
#         return {'success': False, 'inserted': 0, 'failed': len(positions_list), 'total': len(positions_list)}
#     except requests.exceptions.ConnectionError as e:
#         logger.error(f"[BULK_RAW_POSITIONS] FAILED: Connection Error: {e}")
#         return {'success': False, 'inserted': 0, 'failed': len(positions_list), 'total': len(positions_list)}
        
#     except requests.exceptions.Timeout as e:
#         logger.error(f"[BULK_RAW_POSITIONS] FAILED: Timeout: {e}")
#         return {'success': False, 'inserted': 0, 'failed': len(positions_list), 'total': len(positions_list)}
        
#     except Exception as e:
#         logger.error(f"[BULK_RAW_POSITIONS] FAILED: Unexpected Exception: {e}", exc_info=True)
#         return {'success': False, 'inserted': 0, 'failed': len(positions_list), 'total': len(positions_list)}
        
#     finally:
#         logger.info("[BULK_RAW_POSITIONS] END")
#         logger.info("=" * 60)

# # ============================================
# # ACTIVITY LOGGING (API)
# # ============================================
# def log_activity(job_id, candidate_id, employee_id, activity_count, notes=None):
#     """Log activity via WBL API: POST /job_activity_logs"""
#     logger.info("=" * 60)
#     logger.info(f"[LOG_ACTIVITY] START - Job={job_id}, Count={activity_count}")
#     logger.info("=" * 60)
#     try:
#         # Step 1: Load config
#         logger.info("[LOG_ACTIVITY] Step 1: Loading config...")
#         config = get_wbl_config()
#         if not config:
#             logger.error("[LOG_ACTIVITY] FAILED: config is None")
#             return False
#         api_url = config.get("API_URL")
#         token = config.get("TOKEN")
#         if not api_url or not token:
#             logger.error("[LOG_ACTIVITY] FAILED: API_URL or TOKEN missing")
#             return False
#         # Use config values if not provided
#         if not employee_id:
#             employee_id = config.get("EMPLOYEE_ID")
#             logger.debug(f"[LOG_ACTIVITY] Using config EMPLOYEE_ID: {employee_id}")
#         if not candidate_id:
#             candidate_id = config.get("CANDIDATE_ID")
#             logger.debug(f"[LOG_ACTIVITY] Using config CANDIDATE_ID: {candidate_id}")
#         # Step 2: Prepare payload
#         logger.info("[LOG_ACTIVITY] Step 2: Preparing payload...")
#         payload = {
#             "job_id": int(job_id),
#             "employee_id": int(employee_id),
#             "activity_date": datetime.now().strftime("%Y-%m-%d"),
#             "activity_count": int(activity_count)
#         }
#         if candidate_id and int(candidate_id) > 0:
#             payload["candidate_id"] = int(candidate_id)
#         if notes:
#             payload["notes"] = str(notes)
#         logger.info(f"[LOG_ACTIVITY] Payload: {payload}")
#         # Step 3: Make API request
#         endpoint = f"{api_url}/job_activity_logs"
#         headers = get_api_headers(token)
#         logger.info(f"[LOG_ACTIVITY] Step 3: Calling API...")
#         logger.info(f"[LOG_ACTIVITY] Endpoint: POST {endpoint}")
#         response = requests.post(
#             endpoint,
#             json=payload,
#             headers=headers,
#             timeout=30
#         )
#         # Step 4: Handle response
#         logger.info(f"[LOG_ACTIVITY] Status Code: {response.status_code}")
#         logger.info(f"[LOG_ACTIVITY] Response: {response.text}")
#         if response.status_code in [200, 201]:
#             result = response.json()
#             logger.info(f"[LOG_ACTIVITY] SUCCESS! Log ID: {result.get('id')}")
#             return True
#         else:
#             logger.error(f"[LOG_ACTIVITY] FAILED: {response.status_code}")
#             return False
#     except Exception as e:
#         logger.error(f"[LOG_ACTIVITY] FAILED: {e}", exc_info=True)
#         return False
#     finally:
#         logger.info("[LOG_ACTIVITY] END")
#         logger.info("=" * 60)
# def log_extraction_activity(candidate_id, employee_id, activity_count, notes=None):
#     """Log extraction activity (job_id=120)."""
#     logger.info(f"[LOG_EXTRACTION] Calling with count={activity_count}")
#     try:
#         config = get_wbl_config()
#         job_id = config.get("EXTRACTION_JOB_ID", 120) if config else 120
#         logger.info(f"[LOG_EXTRACTION] Using job_id={job_id}")
#         return log_activity(job_id, candidate_id, employee_id, activity_count, notes)
#     except Exception as e:
#         logger.error(f"[LOG_EXTRACTION] FAILED: {e}", exc_info=True)
#         return False




#updated code
# utils/db.py
# ============================================
# API OPERATIONS - WITH FULL DEBUG LOGGING
# ============================================
import base64
import json
import logging
import os
import re
import time
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

# ============================================
# TOKEN HELPERS
# ============================================

# Path to config.py (one level above utils/)
_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.py")


def _is_token_expired(token: str) -> bool:
    """
    Decode the JWT payload (no signature verification needed — the server
    does that) and check whether 'exp' is in the past.
    Returns True if expired or if the token can't be decoded.
    """
    try:
        payload_b64 = token.split(".")[1]
        # JWT uses base64url; pad to a multiple of 4
        padding = 4 - len(payload_b64) % 4
        payload = json.loads(base64.b64decode(payload_b64 + "=" * padding))
        exp = payload.get("exp", 0)
        expired = time.time() > exp
        if expired:
            from datetime import timezone
            exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc)
            logger.warning(
                "[TOKEN] JWT expired at %s (%.0f seconds ago)",
                exp_dt.strftime("%Y-%m-%d %H:%M UTC"),
                time.time() - exp,
            )
        return expired
    except Exception as exc:
        logger.warning("[TOKEN] Could not decode JWT to check expiry: %s", exc)
        return True   # treat as expired if we can't read it


def _refresh_token() -> str | None:
    """
    Re-login to the WBL API using credentials stored in .env
    (WBL_EMAIL + WBL_PASSWORD) and return a fresh JWT token.
    After obtaining the token this function:
      1. Updates the in-memory WBL_CONFIG dict so the current run
         uses the new token immediately.
      2. Patches config.py on disk so future runs don't need to
         re-login again.
    Returns the new token string, or None on failure.
    """
    # ---- load credentials from .env ----
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass   # python-dotenv is optional; os.getenv still works

    email    = os.getenv("WBL_EMAIL")
    password = os.getenv("WBL_PASSWORD")
    api_url  = os.getenv("WBL_API_URL", "http://localhost:8000/api")

    if not email or not password:
        logger.error(
            "[TOKEN] Cannot auto-refresh: WBL_EMAIL or WBL_PASSWORD "
            "not found in .env  —  add them and retry."
        )
        return None

    logger.info("[TOKEN] Refreshing token for %s …", email)

    try:
        response = requests.post(
            f"{api_url}/login",
            data={"username": email, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        if response.status_code == 200:
            new_token = response.json().get("access_token")
            if new_token:
                logger.info("[TOKEN] New token obtained successfully")
                _update_config_token(new_token, api_url)
                return new_token
            logger.error("[TOKEN] Login succeeded but no access_token in response")
            return None
        logger.error(
            "[TOKEN] Login failed — %s: %s",
            response.status_code, response.text[:200],
        )
        return None
    except requests.exceptions.ConnectionError:
        logger.error("[TOKEN] Cannot connect to %s — is the WBL API running?", api_url)
        return None
    except Exception as exc:
        logger.error("[TOKEN] Unexpected error during token refresh: %s", exc)
        return None


def _update_config_token(new_token: str, api_url: str | None = None) -> None:
    """
    1. Patch the in-memory WBL_CONFIG so the current process uses the
       new token immediately (no restart needed).
    2. Rewrite the TOKEN line in config.py so future runs start fresh.
    """
    # --- in-memory patch ---
    try:
        import importlib, sys
        # Force re-import if already cached
        if "config" in sys.modules:
            cfg_module = sys.modules["config"]
            cfg_module.WBL_CONFIG["TOKEN"] = new_token
            if api_url:
                cfg_module.WBL_CONFIG["API_URL"] = api_url
    except Exception as exc:
        logger.debug("[TOKEN] In-memory patch skipped: %s", exc)

    # --- file patch ---
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
            content = fh.read()
        content = re.sub(
            r'"TOKEN":\s*"[^"]*"',
            f'"TOKEN": "{new_token}"',
            content,
        )
        content = re.sub(
            r'"TOKEN_GENERATED_AT":\s*"[^"]*"',
            f'"TOKEN_GENERATED_AT": "{datetime.now().isoformat()}"',
            content,
        )
        with open(_CONFIG_PATH, "w", encoding="utf-8") as fh:
            fh.write(content)
        logger.info("[TOKEN] config.py updated with new token")
    except Exception as exc:
        logger.warning("[TOKEN] Could not update config.py on disk: %s", exc)


# ============================================
# WBL CONFIG LOADER
# ============================================

def get_wbl_config():
    """
    Load WBL configuration from config.py.
    If the JWT token inside config.py is expired, this function
    automatically re-logins using WBL_EMAIL + WBL_PASSWORD from .env
    and refreshes the token before returning — no manual intervention
    required.
    """
    logger.debug("[GET_CONFIG] Loading config.py...")
    try:
        from config import WBL_CONFIG
        logger.debug("[GET_CONFIG] SUCCESS — API_URL: %s", WBL_CONFIG.get("API_URL"))
        token = WBL_CONFIG.get("TOKEN", "")
        if not token:
            logger.error("[GET_CONFIG] TOKEN is empty or missing in config.py")
            return None
        # ---- auto-refresh if expired ----
        if _is_token_expired(token):
            logger.warning("[GET_CONFIG] Token is expired — attempting auto-refresh...")
            new_token = _refresh_token()
            if new_token:
                WBL_CONFIG["TOKEN"] = new_token
                logger.info("[GET_CONFIG] Token refreshed — continuing with new token")
            else:
                logger.error(
                    "[GET_CONFIG] Auto-refresh failed. "
                    "Add WBL_EMAIL and WBL_PASSWORD to .env and retry, "
                    "or run: python setup.py"
                )
                return None
        else:
            logger.debug("[GET_CONFIG] Token valid")
        return WBL_CONFIG
    except ImportError as exc:
        logger.error("[GET_CONFIG] config.py not found: %s — run 'python setup.py' first", exc)
        return None
    except Exception as exc:
        logger.error("[GET_CONFIG] Unexpected error: %s", exc, exc_info=True)
        return None


def get_api_headers(token):
    """Get standard API headers."""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


# ============================================
# AUTOMATION CONTACT EXTRACTS (API)
# ============================================

def insert_automation_contact(
    full_name=None, 
    email=None, 
    phone=None, 
    company_name=None, 
    job_title=None, 
    city=None, 
    state=None, 
    country=None, 
    postal_code=None, 
    linkedin_id=None, 
    linkedin_internal_id=None, 
    source_reference=None,
    raw_payload=None,
    source_type="bot_linkedin_message_extraction"
):
    """
    Insert automation contact via API: POST /automation-extracts
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info("=" * 60)
    logger.info(f"[INSERT_AUTOMATION_CONTACT] START - Saving: {full_name}")
    logger.info("=" * 60)
    try:
        # Step 1: Load config
        logger.info("[INSERT_AUTOMATION_CONTACT] Step 1: Loading config...")
        config = get_wbl_config()
        if not config:
            logger.error("[INSERT_AUTOMATION_CONTACT] FAILED: config is None")
            return False
        api_url = config.get("API_URL")
        token = config.get("TOKEN")
        if not api_url or not token:
            logger.error("[INSERT_AUTOMATION_CONTACT] FAILED: API_URL or TOKEN missing")
            return False

        # Step 1b: Validate email (syntax + MX) before payload build
        email_invalid = False
        domain_invalid = False
        mailbox_invalid = False
        if email:
            try:
                from utils.email_validator import validate_email as _v_email
                _vr = _v_email(email, check_mx=True, check_smtp=False)
                if not _vr["valid"]:
                    email_invalid = True
                    if not _vr["syntax_valid"]:
                        domain_invalid = True
                    else:
                        mailbox_invalid = True
                logger.debug("[INSERT_AUTOMATION_CONTACT] Email validated: %s (Valid: %s)", email, _vr["valid"])
            except ImportError:
                logger.warning("[INSERT_AUTOMATION_CONTACT] utils.email_validator not available.")

        # Step 2: Prepare payload
        logger.info("[INSERT_AUTOMATION_CONTACT] Step 2: Preparing payload...")
        payload = {
            "source_type": source_type,
            "email_invalid": email_invalid,
            "domain_invalid": domain_invalid,
            "mailbox_invalid": mailbox_invalid
        }
        # Add optional fields only if they have values
        if full_name: payload["full_name"] = full_name
        if email: payload["email"] = email
        if phone: payload["phone"] = phone
        if company_name: payload["company_name"] = company_name
        if job_title: payload["job_title"] = job_title
        if city: payload["city"] = city
        if state: payload["state"] = state
        if country: payload["country"] = country
        if postal_code: payload["postal_code"] = postal_code
        if linkedin_id: payload["linkedin_id"] = linkedin_id
        if linkedin_internal_id: payload["linkedin_internal_id"] = linkedin_internal_id
        if source_reference: payload["source_reference"] = source_reference
        if raw_payload: payload["raw_payload"] = raw_payload

        logger.info(f"[INSERT_AUTOMATION_CONTACT] Payload ready (keys: {list(payload.keys())})")

        # Step 3: Make API request
        endpoint = f"{api_url}/automation-extracts"
        headers = get_api_headers(token)
        logger.info(f"[INSERT_AUTOMATION_CONTACT] Step 3: Calling API -> POST {endpoint}")
        response = requests.post(
            endpoint,
            json=payload,
            headers=headers,
            timeout=30
        )

        # Step 4: Handle response
        logger.info(f"[INSERT_AUTOMATION_CONTACT] Status Code: {response.status_code}")
        if response.status_code in [200, 201]:
            try:
                result = response.json()
                logger.info(f"[INSERT_AUTOMATION_CONTACT] SUCCESS! Created ID: {result.get('id', 'N/A')}")
                return True
            except:
                logger.info("[INSERT_AUTOMATION_CONTACT] SUCCESS! (no JSON body)")
                return True
        elif response.status_code == 401:
            logger.error("[INSERT_AUTOMATION_CONTACT] FAILED: 401 Unauthorized")
            return False
        elif response.status_code == 409:
            logger.info(f"[INSERT_AUTOMATION_CONTACT] SKIPPED: Contact already exists (409 Conflict)")
            return True
        elif response.status_code == 422:
            logger.error(f"[INSERT_AUTOMATION_CONTACT] FAILED: 422 Validation Error -> {response.text}")
            return False
        else:
            logger.error(f"[INSERT_AUTOMATION_CONTACT] FAILED: Unexpected status {response.status_code} -> {response.text}")
            return False

    except requests.exceptions.ConnectionError as e:
        logger.error(f"[INSERT_AUTOMATION_CONTACT] FAILED: Connection Error: {e}")
        return False
    except requests.exceptions.Timeout as e:
        logger.error(f"[INSERT_AUTOMATION_CONTACT] FAILED: Timeout: {e}")
        return False
    except Exception as e:
        logger.error(f"[INSERT_AUTOMATION_CONTACT] FAILED: Unexpected Exception: {e}", exc_info=True)
        return False
    finally:
        logger.info("[INSERT_AUTOMATION_CONTACT] END")
        logger.info("=" * 60)


def bulk_insert_automation_contacts(contacts_list):
    """
    Bulk insert automation contacts via API: POST /automation-extracts/bulk
    Args:
        contacts_list: List of dicts with automation contact data
            Each dict mapping to AutomationContactExtractCreate
    """
    logger.info("=" * 60)
    logger.info(f"[BULK_AUTOMATION_INSERT] START - Inserting {len(contacts_list)} contacts")
    logger.info("=" * 60)
    try:
        # Step 1: Load config
        logger.info("[BULK_AUTOMATION_INSERT] Step 1: Loading config...")
        config = get_wbl_config()
        if not config:
            logger.error("[BULK_AUTOMATION_INSERT] FAILED: config is None")
            return {'success': False, 'inserted': 0, 'failed': len(contacts_list), 'total': len(contacts_list)}
        api_url = config.get("API_URL")
        token = config.get("TOKEN")
        if not api_url or not token:
            logger.error("[BULK_AUTOMATION_INSERT] FAILED: API_URL or TOKEN missing")
            return {'success': False, 'inserted': 0, 'failed': len(contacts_list), 'total': len(contacts_list)}

        # Step 2: Prepare payload
        logger.info("[BULK_AUTOMATION_INSERT] Step 2: Preparing bulk payload...")

        # ========================================================
        # FIXED: Add default source_type to any contacts missing it
        # ========================================================
        for contact in contacts_list:
            if "source_type" not in contact:
                contact["source_type"] = "bot_linkedin_message_extraction"
            
            # Ensure linkedin_internal_id is passed (can be None)
            if "linkedin_internal_id" not in contact:
                contact["linkedin_internal_id"] = None
            
            # Run email validation if they have an email but haven't been validated yet
            if contact.get("email") and "email_invalid" not in contact:
                try:
                    from utils.email_validator import validate_email as _v_email
                    _vr = _v_email(contact["email"], check_mx=True, check_smtp=False)
                    if not _vr["valid"]:
                        contact["email_invalid"] = True
                        if not _vr["syntax_valid"]:
                            contact["domain_invalid"] = True
                        else:
                            contact["mailbox_invalid"] = True
                    else:
                        contact["email_invalid"] = False
                        contact["domain_invalid"] = False
                        contact["mailbox_invalid"] = False
                except ImportError:
                    pass

        payload = {"extracts": contacts_list}

        # Step 3: Make API request
        endpoint = f"{api_url}/automation-extracts/bulk"
        
        # Step 3: Make API request with 1 Auto-Retry on 401
        for attempt in range(2):
            headers = get_api_headers(token)
            logger.info(f"[BULK_AUTOMATION_INSERT] Step 3: Calling bulk API (Attempt {attempt+1}) -> POST {endpoint}")
            response = requests.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=60
            )
            # Step 4: Handle response
            logger.info(f"[BULK_AUTOMATION_INSERT] Status Code: {response.status_code}")
            if response.status_code in [200, 201]:
                result = response.json()
                logger.info(f"[BULK_AUTOMATION_INSERT] SUCCESS!")
                logger.info(f"   Inserted: {result.get('inserted', 0)}")
                logger.info(f"   Duplicates: {result.get('duplicates', 0)}")
                logger.info(f"   Failed: {result.get('failed', 0)}")
                failed_contacts = result.get('errors', [])
                if failed_contacts:
                    logger.error(f"[BULK_AUTOMATION_INSERT] Errors reported:")
                    for err in failed_contacts:
                        logger.error(f"   - {err}")
                return {
                    'success': True,
                    'inserted': result.get('inserted', 0),
                    'duplicates': result.get('duplicates', 0),
                    'failed': result.get('failed', 0),
                    'total': result.get('total', 0),
                    'errors': failed_contacts
                }
            elif response.status_code == 401:
                logger.error("[BULK_AUTOMATION_INSERT] FAILED: 401 Unauthorized")
                if attempt == 0:
                    logger.info("[BULK_AUTOMATION_INSERT] Attempting to auto-refresh WBL token from .env...")
                    try:
                        from utils.auth import refresh_wbl_token_in_config
                        token = refresh_wbl_token_in_config()
                        logger.info("[BULK_AUTOMATION_INSERT] Acquired new token. Retrying request.")
                        continue # Retry the loop
                    except ImportError:
                        logger.error("[BULK_AUTOMATION_INSERT] utils.auth module missing. Cannot auto-refresh.")
                        break
                    except Exception as e:
                        logger.error(f"[BULK_AUTOMATION_INSERT] Auto-refresh failed: {e}")
                        break # Fall through to failure
                else:
                    break # Already retried, give up
            elif response.status_code == 422:
                logger.error(f"[BULK_AUTOMATION_INSERT] FAILED: 422 Validation Error -> {response.text}")
                return {'success': False, 'inserted': 0, 'failed': len(contacts_list), 'error': response.text}
            else:
                logger.error(f"[BULK_AUTOMATION_INSERT] FAILED: Status {response.status_code} -> {response.text}")
                return {'success': False, 'inserted': 0, 'failed': len(contacts_list)}
                
        # If loop finishes without returning, failure occurred
        return {'success': False, 'inserted': 0, 'failed': len(contacts_list)}
    except requests.exceptions.ConnectionError as e:
        logger.error(f"[BULK_AUTOMATION_INSERT] FAILED: Connection Error: {e}")
        return {'success': False, 'inserted': 0, 'failed': len(contacts_list)}
    except requests.exceptions.Timeout as e:
        logger.error(f"[BULK_AUTOMATION_INSERT] FAILED: Timeout: {e}")
        return {'success': False, 'inserted': 0, 'failed': len(contacts_list)}
    except Exception as e:
        logger.error(f"[BULK_AUTOMATION_INSERT] FAILED: Unexpected Exception: {e}", exc_info=True)
        return {'success': False, 'inserted': 0, 'failed': len(contacts_list)}
    finally:
        logger.info("[BULK_AUTOMATION_INSERT] END")
        logger.info("=" * 60)


# ============================================
# RAW JOB LISTINGS (API)
# ============================================

def bulk_insert_raw_job_listings(positions_list):
    """
    Bulk insert positional data via API: POST /raw-positions/bulk
    Args:
        positions_list: List of dicts mapping to RawJobListingCreate schema
    """
    logger.info("=" * 60)
    logger.info(f"[BULK_RAW_POSITIONS] START - Inserting {len(positions_list)} positions")
    logger.info("=" * 60)
    
    try:
        # Step 1: Load config
        logger.info("[BULK_RAW_POSITIONS] Step 1: Loading config...")
        config = get_wbl_config()
        
        if not config:
            logger.error("[BULK_RAW_POSITIONS] FAILED: config is None")
            return {'success': False, 'inserted': 0, 'failed': len(positions_list), 'total': len(positions_list)}
        
        api_url = config.get("API_URL")
        token = config.get("TOKEN")
        
        if not api_url or not token:
            logger.error("[BULK_RAW_POSITIONS] FAILED: API_URL or TOKEN missing")
            return {'success': False, 'inserted': 0, 'failed': len(positions_list), 'total': len(positions_list)}
        
        # Step 2: Prepare payload
        logger.info("[BULK_RAW_POSITIONS] Step 2: Preparing bulk payload...")
        
        # Ensure source is correct for all positions
        for position in positions_list:
            if "source" not in position:
                position["source"] = "bot_linkedin_message_extraction"
        
        payload = {
            "positions": positions_list
        }
        
        endpoint = f"{api_url}/raw-positions/bulk"
        
        # Step 3: Make API request with 1 Auto-Retry on 401
        for attempt in range(2):
            headers = get_api_headers(token)
            
            logger.info(f"[BULK_RAW_POSITIONS] Step 3: Calling API (Attempt {attempt+1}) -> POST {endpoint}")
            response = requests.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=60
            )
            
            # Step 4: Handle response
            logger.info(f"[BULK_RAW_POSITIONS] Status Code: {response.status_code}")
            
            if response.status_code in [200, 201]:
                result = response.json()
                logger.info(f"[BULK_RAW_POSITIONS] SUCCESS!")
                logger.info(f"   Inserted: {result.get('inserted', 0)}")
                logger.info(f"   Skipped: {result.get('skipped', 0)}")
                logger.info(f"   Total Processed: {result.get('total', 0)}")
                
                failed_contacts = result.get('failed_contacts', [])
                if failed_contacts:
                    logger.error(f"[BULK_RAW_POSITIONS] API reported {len(failed_contacts)} failures")
                
                return {
                    'success': True,
                    'inserted': result.get('inserted', 0),
                    'skipped': result.get('skipped', 0),
                    'total': result.get('total', 0),
                    'failed': len(failed_contacts),
                    'failed_contacts': failed_contacts
                }
                
            elif response.status_code == 401:
                logger.error("[BULK_RAW_POSITIONS] FAILED: 401 Unauthorized")
                if attempt == 0:
                    logger.info("[BULK_RAW_POSITIONS] Attempting to auto-refresh WBL token from .env...")
                    try:
                        from utils.auth import refresh_wbl_token_in_config
                        token = refresh_wbl_token_in_config()
                        logger.info("[BULK_RAW_POSITIONS] Acquired new token. Retrying request.")
                        continue # Retry the loop
                    except ImportError:
                        logger.error("[BULK_RAW_POSITIONS] utils.auth module missing. Cannot auto-refresh.")
                        break
                    except Exception as e:
                        logger.error(f"[BULK_RAW_POSITIONS] Auto-refresh failed: {e}")
                        break # Fall through to failure
                else:
                    break # Already retried, give up
                    
            elif response.status_code == 422:
                logger.error(f"[BULK_RAW_POSITIONS] FAILED: 422 Validation Error -> {response.text}")
                return {'success': False, 'inserted': 0, 'failed': len(positions_list), 'total': len(positions_list), 'error': response.text}
                
            else:
                logger.error(f"[BULK_RAW_POSITIONS] FAILED: Unexpected status {response.status_code} -> {response.text}")
                return {'success': False, 'inserted': 0, 'failed': len(positions_list), 'total': len(positions_list)}
                
        # If loop finishes without returning, failure occurred
        return {'success': False, 'inserted': 0, 'failed': len(positions_list), 'total': len(positions_list)}
    except requests.exceptions.ConnectionError as e:
        logger.error(f"[BULK_RAW_POSITIONS] FAILED: Connection Error: {e}")
        return {'success': False, 'inserted': 0, 'failed': len(positions_list), 'total': len(positions_list)}
        
    except requests.exceptions.Timeout as e:
        logger.error(f"[BULK_RAW_POSITIONS] FAILED: Timeout: {e}")
        return {'success': False, 'inserted': 0, 'failed': len(positions_list), 'total': len(positions_list)}
        
    except Exception as e:
        logger.error(f"[BULK_RAW_POSITIONS] FAILED: Unexpected Exception: {e}", exc_info=True)
        return {'success': False, 'inserted': 0, 'failed': len(positions_list), 'total': len(positions_list)}
        
    finally:
        logger.info("[BULK_RAW_POSITIONS] END")
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