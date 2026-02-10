# modules/persistence.py
"""
Persistence Module

Handles all database operations for LinkedIn bot.
Responsible for bulk inserts, updates, queries, and data validation.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from utils.db import bulk_insert_contacts, log_extraction_activity
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
    
    def bulk_insert_contacts(self, contacts: List[Dict[str, Any]]) -> int:
        """
        Bulk insert contacts into database.
        
        Args:
            contacts: List of contact dictionaries
            
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
            
            # Validate contacts before inserting
            valid_contacts = []
            for contact in contacts:
                if self.validate_contact_data(contact):
                    valid_contacts.append(contact)
                else:
                    logger.warning(f"Invalid contact skipped: {contact.get('full_name', 'Unknown')}")
            
            if not valid_contacts:
                logger.warning("No valid contacts to insert")
                return 0
            
            # Perform bulk insert to API using utils.db function
            logger.info(f"Calling API bulk insert for {len(valid_contacts)} valid contacts...")
            result = bulk_insert_contacts(valid_contacts)
            
            if result.get('success'):
                inserted_count = result.get('inserted', 0)
                duplicates = result.get('duplicates', 0)
                failed = result.get('failed', 0)
                
                logger.info(f"✅ API Bulk Insert Results:")
                logger.info(f"   Inserted: {inserted_count}")
                logger.info(f"   Duplicates: {duplicates}")
                logger.info(f"   Failed: {failed}")
                
                # Log activity with actual inserted count
                self.log_activity(
                    action="bulk_insert",
                    details=f"Inserted {inserted_count} contacts (duplicates: {duplicates}, failed: {failed})",
                    activity_count=inserted_count  # Use actual inserted count
                )
                
                return inserted_count
            else:
                error = result.get('error', 'Unknown error')
                logger.error(f"❌ API Bulk Insert Failed: {error}")
                raise ExtractionException(f"API bulk insert failed: {error}")
            
        except Exception as e:
            logger.error(f"Bulk insert failed: {e}")
            raise ExtractionException(f"Database insert failed: {e}")
    
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
        ])
        
        if not has_contact_info:
            logger.debug("Contact has no contact information")
            return False
        
        logger.debug(f"Contact validated: {contact.get('full_name')}")
        return True
    
    def log_activity(self, action: str, details: str, activity_count: Optional[int] = None) -> None:
        """
        Log extraction activity to database.
        
        Args:
            action: Action performed (e.g., 'bulk_insert', 'update')
            details: Details about the action
            activity_count: Optional activity count (extracted from details if not provided)
        """
        try:
            # If activity_count not provided, try to extract from details
            if activity_count is None:
                # Try to extract number from details like "Extracted 5 contacts" or "Inserted 3 contacts"
                import re
                match = re.search(r'(\d+)\s+contact', details.lower())
                if match:
                    activity_count = int(match.group(1))
                else:
                    activity_count = 1  # Default fallback
            
            # Convert to the format expected by log_extraction_activity
            # Signature: log_extraction_activity(candidate_id, employee_id, activity_count, notes=None)
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
        """
        Get total number of contacts in database.
        
        Returns:
            Number of contacts
        """
        # This would query the database
        # For now, return 0 as placeholder
        return 0
    
    def contact_exists(self, name: str, profile_url: Optional[str] = None) -> bool:
        """
        Check if contact already exists in database.
        
        Args:
            name: Contact name
            profile_url: Optional profile URL for matching
            
        Returns:
            True if exists, False otherwise
        """
        # This would query the database
        # For now, return False as placeholder
        return False
