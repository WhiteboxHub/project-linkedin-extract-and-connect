# # modules/persistence.py
# """
# Persistence Module
# Handles all database operations for LinkedIn bot.
# Responsible for bulk inserts, updates, queries, and data validation.
# """
# import logging
# from typing import List, Dict, Any, Optional
# from datetime import datetime
# from utils.db import bulk_insert_automation_contacts, bulk_insert_raw_job_listings, log_extraction_activity
# from utils.exceptions import ExtractionException
# logger = logging.getLogger(__name__)
# class PersistenceModule:
#     """
#     Handles database operations and data persistence.
#     Responsibilities:
#     - Bulk insert contacts
#     - Update existing records
#     - Query database
#     - Data validation
#     - Activity logging
#     """
#     def __init__(self, employee_id: int, candidate_id: int):
#         """
#         Initialize persistence module.
#         Args:
#             employee_id: Employee ID for tracking
#             candidate_id: Candidate ID for tracking
#         """
#         self.employee_id = employee_id
#         self.candidate_id = candidate_id
#         logger.info(f"PersistenceModule initialized (employee={employee_id}, candidate={candidate_id})")
#     def bulk_insert_contacts(self, contacts: List[Dict[str, Any]]) -> int:
#         """
#         Bulk insert contacts into database.
#         Args:
#             contacts: List of contact dictionaries
#         Returns:
#             Number of contacts inserted
#         Raises:
#             ExtractionException: If bulk insert fails
#         """
#         try:
#             if not contacts:
#                 logger.info("No contacts to insert")
#                 return 0
#             logger.info(f"Bulk inserting {len(contacts)} contacts...")
#             # Validate contacts before inserting
#             valid_contacts = []
#             for contact in contacts:
#                 if self.validate_contact_data(contact):
#                     valid_contacts.append(contact)
#                 else:
#                     logger.warning(f"Invalid contact skipped: {contact.get('full_name', 'Unknown')}")
#             if not valid_contacts:
#                 logger.warning("No valid contacts to insert")
#                 return 0
#             # Perform bulk insert to API using utils.db function
#             logger.info(f"Calling API bulk insert for {len(valid_contacts)} valid contacts...")
#             result = bulk_insert_automation_contacts(valid_contacts)
            
#             # Map over to RawJobListing positions
#             raw_positions = []
#             for contact in valid_contacts:
#                 raw_positions.append({
#                     "candidate_id": contact.get("candidate_id", self.candidate_id),
#                     "source": contact.get("source", "bot_linkedin_message_extraction"),
#                     "source_uid": str(contact.get("conversation_id", "") or ""),
#                     "extractor_version": contact.get("extractor_version", "v2"),
#                     "raw_title": str(contact.get("job_title", "") or ""),
#                     "raw_company": str(contact.get("company") or contact.get("company_name", "") or ""),
#                     "raw_location": str(contact.get("location") or contact.get("city", "") or ""),
#                     "raw_contact_info": f"{contact.get('email', '')} {contact.get('phone', '')}".strip() or None,
#                     "raw_payload": contact
#                 })
            
#             logger.info(f"Calling API bulk insert for {len(raw_positions)} raw positions...")
#             raw_result = bulk_insert_raw_job_listings(raw_positions)

#             if result.get('success'):
#                 inserted_count = result.get('inserted', 0)
#                 duplicates = result.get('duplicates', 0)
#                 failed = result.get('failed', 0)
                
#                 logger.info(f"✅ Contact Insert Results: Inserted={inserted_count}, Duplicates={duplicates}, Failed={failed}")
#                 logger.info(f"✅ Position Insert Results: Inserted={raw_result.get('inserted', 0)}, Skipped={raw_result.get('skipped', 0)}")
                
#                 # Log activity with actual inserted count
#                 self.log_activity(
#                     action="bulk_insert",
#                     details=f"Inserted {inserted_count} contacts, {raw_result.get('inserted', 0)} positions",
#                     activity_count=inserted_count  # Use actual contact inserted count
#                 )
                
#                 return inserted_count
#             else:
#                 error = result.get('error', 'Unknown error')
#                 logger.error(f"❌ API Bulk Insert Failed: {error}")
#                 raise ExtractionException(f"API bulk insert failed: {error}")
#         except Exception as e:
#             logger.error(f"Bulk insert failed: {e}")
#             raise ExtractionException(f"Database insert failed: {e}")
#     def validate_contact_data(self, contact: Dict[str, Any]) -> bool:
#         """
#         Validate contact data before insertion.
#         Args:
#             contact: Contact dictionary
#         Returns:
#             True if valid, False otherwise
#         """
#         # Check required fields
#         if not contact.get('full_name'):
#             logger.debug("Contact missing full_name")
#             return False
#         # Check name is not invalid
#         invalid_names = ['LinkedIn Member', 'Unknown', '', None]
#         if contact.get('full_name') in invalid_names:
#             logger.debug(f"Invalid name: {contact.get('full_name')}")
#             return False
#         # At least one contact method should exist
#         has_contact_info = any([
#             contact.get('email'),
#             contact.get('phone'),
#             contact.get('profile_url'),
#             contact.get('linkedin_url'),
#         ])
#         if not has_contact_info:
#             logger.debug("Contact has no contact information")
#             return False
#         logger.debug(f"Contact validated: {contact.get('full_name')}")
#         return True
#     def log_activity(self, action: str, details: str, activity_count: Optional[int] = None) -> None:
#         """
#         Log extraction activity to database.
#         Args:
#             action: Action performed (e.g., 'bulk_insert', 'update')
#             details: Details about the action
#             activity_count: Optional activity count (extracted from details if not provided)
#         """
#         try:
#             # If activity_count not provided, try to extract from details
#             if activity_count is None:
#                 # Try to extract number from details like "Extracted 5 contacts" or "Inserted 3 contacts"
#                 import re
#                 match = re.search(r'(\d+)\s+contact', details.lower())
#                 if match:
#                     activity_count = int(match.group(1))
#                 else:
#                     activity_count = 1  # Default fallback
#             # Convert to the format expected by log_extraction_activity
#             # Signature: log_extraction_activity(candidate_id, employee_id, activity_count, notes=None)
#             log_extraction_activity(
#                 candidate_id=self.candidate_id,
#                 employee_id=self.employee_id,
#                 activity_count=activity_count,
#                 notes=f"{action}: {details}"
#             )
#             logger.debug(f"Activity logged: {action} - {details} (count={activity_count})")
#         except Exception as e:
#             logger.warning(f"Failed to log activity: {e}")
#     def get_contact_count(self) -> int:
#         """
#         Get total number of contacts in database.
#         Returns:
#             Number of contacts
#         """
#         # This would query the database
#         # For now, return 0 as placeholder
#         return 0
#     def contact_exists(self, name: str, profile_url: Optional[str] = None) -> bool:
#         """
#         Check if contact already exists in database.
#         Args:
#             name: Contact name
#             profile_url: Optional profile URL for matching
#         Returns:
#             True if exists, False otherwise
#         """
#         # This would query the database
#         # For now, return False as placeholder
#         return False







#updted code
# modules/persistence.py
"""
Persistence Module
Handles all database operations for LinkedIn bot.
Responsible for bulk inserts, updates, queries, and data validation.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from utils.db import bulk_insert_automation_contacts, bulk_insert_raw_job_listings, log_extraction_activity
from utils.exceptions import ExtractionException

logger = logging.getLogger(__name__)


class PersistenceModule:
    """
    Handles database operations and data persistence.
    Responsibilities:
    - Bulk insert contacts
    - Update existing records
    - Query database
    - Data validation
    - Activity logging
    """

    def __init__(self, employee_id: int, candidate_id: int):
        """
        Initialize persistence module.
        Args:
            employee_id: Employee ID for tracking
            candidate_id: Candidate ID for tracking
        """
        self.employee_id = employee_id
        self.candidate_id = candidate_id
        logger.info(f"PersistenceModule initialized (employee={employee_id}, candidate={candidate_id})")

    def bulk_insert_contacts(
        self,
        contacts: List[Dict[str, Any]],
        job_listings: Optional[List[Dict[str, Any]]] = None,
    ) -> int:
        """
        Bulk insert contacts into database.
        Args:
            contacts:     List of contact dictionaries.
            job_listings: Optional explicit per-message job listing records.
                          When provided, these replace the contact-derived positions.
                          When None, falls back to generating one listing per contact.
        Returns:
            Number of contacts inserted
        Raises:
            ExtractionException: If bulk insert fails
        """
        try:
            if not contacts:
                logger.info("No contacts to insert")
                return 0

            logger.info(f"Bulk inserting {len(contacts)} contacts...")

            # Validate and prepare contacts
            valid_contacts = []
            for contact in contacts:
                if self.validate_contact_data(contact):
                    # Ensure all required fields are present
                    prepared = self.prepare_contact_for_insert(contact)
                    valid_contacts.append(prepared)
                else:
                    logger.warning(f"Invalid contact skipped: {contact.get('full_name', 'Unknown')}")

            if not valid_contacts:
                logger.warning("No valid contacts to insert")
                return 0

            # Perform bulk insert to API
            logger.info(f"Calling API bulk insert for {len(valid_contacts)} valid contacts...")
            result = bulk_insert_automation_contacts(valid_contacts)
            
            # Build raw_job_listings records
            if job_listings is not None:
                # NEW: use the explicit per-message job listings
                raw_positions = []
                for jl in job_listings:
                    entry = dict(jl)  # copy
                    entry.setdefault("candidate_id", self.candidate_id)
                    raw_positions.append(entry)
                logger.info(
                    f"Using {len(raw_positions)} explicit per-message job listing(s)."
                )
            else:
                # LEGACY: derive one listing per contact (old behaviour)
                raw_positions = []
                for contact in valid_contacts:
                    job_title = contact.get("job_title", "") or ""
                    company   = contact.get("company_name", "") or contact.get("company", "") or ""

                    if not job_title and not company:
                        continue

                    raw_positions.append({
                        "candidate_id":      contact.get("candidate_id", self.candidate_id),
                        "source":            "bot_linkedin_message_extraction",
                        "source_uid":        str(contact.get("conversation_id", "") or ""),
                        "extractor_version": "v2",
                        "raw_title":         job_title,
                        "raw_company":       company,
                        "raw_location":      contact.get("location") or contact.get("city", "") or "",
                        "raw_zip":           "",
                        "raw_description":   "",
                        "raw_contact_info":  f"{contact.get('email', '')} {contact.get('phone', '')}".strip() or None,
                        "raw_notes":         "",
                        "raw_payload":       contact.get("raw_payload"),
                    })
            
            # Only insert job listings if we have any
            raw_result = {"inserted": 0, "skipped": 0}
            if raw_positions:
                logger.info(f"Calling API bulk insert for {len(raw_positions)} raw positions...")
                raw_result = bulk_insert_raw_job_listings(raw_positions)

            if result.get('success'):
                inserted_count = result.get('inserted', 0)
                duplicates = result.get('duplicates', 0)
                failed = result.get('failed', 0)
                
                logger.info(f"✅ Contact Insert Results: Inserted={inserted_count}, Duplicates={duplicates}, Failed={failed}")
                logger.info(f"✅ Position Insert Results: Inserted={raw_result.get('inserted', 0)}, Skipped={raw_result.get('skipped', 0)}")
                
                # Log activity with actual inserted count
                self.log_activity(
                    action="bulk_insert",
                    details=f"Inserted {inserted_count} contacts, {raw_result.get('inserted', 0)} positions",
                    activity_count=inserted_count
                )
                
                return inserted_count
            else:
                error = result.get('error', 'Unknown error')
                logger.error(f"❌ API Bulk Insert Failed: {error}")
                raise ExtractionException(f"API bulk insert failed: {error}")

        except Exception as e:
            logger.error(f"Bulk insert failed: {e}")
            raise ExtractionException(f"Database insert failed: {e}")

    def prepare_contact_for_insert(self, contact: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare contact with all required fields for database insertion.
        """
        # Ensure source_type is correct
        contact["source_type"] = "bot_linkedin_message_extraction"
        
        # Ensure linkedin_internal_id exists
        if "linkedin_internal_id" not in contact:
            contact["linkedin_internal_id"] = None
        
        # Ensure classification exists
        if "classification" not in contact:
            email = contact.get("email", "")
            linkedin = contact.get("linkedin_id", "")
            contact["classification"] = self._classify_contact(email, linkedin)
        
        # Ensure source_reference exists
        if "source_reference" not in contact:
            contact["source_reference"] = contact.get("conversation_id", "")
        
        # Ensure raw_payload exists
        if "raw_payload" not in contact:
            contact["raw_payload"] = None
        
        return contact

    def _classify_contact(self, email: str, linkedin_id: str) -> str:
        """Classify contact type."""
        if email:
            domain = email.split("@")[1].lower()
            personal = {
                "gmail.com", "googlemail.com", "yahoo.com", "ymail.com",
                "hotmail.com", "outlook.com", "live.com", "icloud.com",
                "me.com", "aol.com", "protonmail.com", "proton.me",
                "mail.com", "zoho.com", "fastmail.com", "hey.com"
            }
            if domain in personal:
                return "personal_domain_contact"
            return "company_contact"
        
        if linkedin_id:
            return "linkedin_only_contact"
        
        return "unknown"

    def validate_contact_data(self, contact: Dict[str, Any]) -> bool:
        """
        Validate contact data before insertion.
        Args:
            contact: Contact dictionary
        Returns:
            True if valid, False otherwise
        """
        # Check required fields
        if not contact.get('full_name'):
            logger.debug("Contact missing full_name")
            return False
        
        # Check name is not invalid
        invalid_names = ['LinkedIn Member', 'Unknown', '', None]
        if contact.get('full_name') in invalid_names:
            logger.debug(f"Invalid name: {contact.get('full_name')}")
            return False
        
        # At least one contact method should exist
        has_contact_info = any([
            contact.get('email'),
            contact.get('phone'),
            contact.get('profile_url'),
            contact.get('linkedin_url'),
            contact.get('linkedin_id'),
        ])
        
        if not has_contact_info:
            logger.debug("Contact has no contact information")
            return False
        
        logger.debug(f"Contact validated: {contact.get('full_name')}")
        return True

    def log_activity(self, action: str, details: str, activity_count: Optional[int] = None) -> None:
        """
        Log extraction activity to database.
        """
        try:
            if activity_count is None:
                import re
                match = re.search(r'(\d+)\s+contact', details.lower())
                if match:
                    activity_count = int(match.group(1))
                else:
                    activity_count = 1

            log_extraction_activity(
                candidate_id=self.candidate_id,
                employee_id=self.employee_id,
                activity_count=activity_count,
                notes=f"{action}: {details}"
            )
            logger.debug(f"Activity logged: {action} - {details} (count={activity_count})")
        except Exception as e:
            logger.warning(f"Failed to log activity: {e}")

    def get_contact_count(self) -> int:
        """Get total number of contacts in database."""
        return 0

    def contact_exists(self, name: str, profile_url: Optional[str] = None) -> bool:
        """Check if contact already exists in database."""
        return False