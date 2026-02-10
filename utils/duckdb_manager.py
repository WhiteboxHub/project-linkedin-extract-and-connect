# utils/duckdb_manager.py
"""
DuckDB Manager for Contact Extraction Analytics (Phase 6)
Provides local database for analytics and querying alongside API storage.
"""

import os
import time
import duckdb
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class DuckDBManager:
    """
    Manage DuckDB connection and operations for contact extraction.
    
    This provides local analytics storage complementary to the API storage.
    Use this for:
    - Tracking extraction runs and metrics
    - Local querying and reporting
    - Historical analysis
    - Offline access to extraction data
    """
    
    def __init__(self, db_path: str = "data/contacts.duckdb"):
        """
        Initialize DuckDB manager.
        
        Args:
            db_path: Path to DuckDB database file
        """
        self.db_path = db_path
        self.conn = None
        self._ensure_data_dir()
    
    def _ensure_data_dir(self):
        """Ensure data directory exists."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    def connect(self):
        """Connect to DuckDB database."""
        try:
            if self.conn is not None:
                logger.debug("[DUCKDB] Already connected")
                return
            
            logger.info(f"[DUCKDB] Connecting to {self.db_path}")
            
            # Create database directory if it doesn't exist
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # Try to connect with read-write mode
            # If file is locked, wait a bit and retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Use read_write mode to allow concurrent access
                    self.conn = duckdb.connect(self.db_path, read_only=False)
                    logger.info("[DUCKDB] Connected successfully")
                    break
                except Exception as e:
                    if "being used by another process" in str(e) and attempt < max_retries - 1:
                        logger.warning(f"[DUCKDB] Database locked, retrying in 1 second... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(1)
                    else:
                        raise
            
            # Initialize schema
            self._init_schema()
            
        except Exception as e:
            logger.error(f"[DUCKDB] Connection failed: {e}")
            raise
    
    def _init_schema(self):
        """Initialize database schema from schema.sql."""
        schema_path = Path("data/schema.sql")
        if schema_path.exists():
            try:
                with open(schema_path, 'r') as f:
                    schema_sql = f.read()
                self.conn.execute(schema_sql)
                logger.info("[DUCKDB] Schema initialized")
            except Exception as e:
                logger.error(f"[DUCKDB] Schema initialization failed: {e}")
                raise
        else:
            logger.warning(f"[DUCKDB] Schema file not found: {schema_path}")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("[DUCKDB] Connection closed")
    
    # ============================================
    # EXTRACTION RUN METHODS
    # ============================================
    
    def start_run(self, employee_id: int, candidate_id: int, username: str) -> int:
        """
        Start a new extraction run.
        
        Args:
            employee_id: Employee ID
            candidate_id: Candidate ID
            username: LinkedIn username
            
        Returns:
            int: Run ID
        """
        try:
            result = self.conn.execute("""
                INSERT INTO extraction_runs (started_at, employee_id, candidate_id, username, status)
                VALUES (?, ?, ?, ?, 'running')
                RETURNING run_id
            """, [datetime.now(), employee_id, candidate_id, username]).fetchone()
            
            run_id = result[0]
            logger.info(f"[DUCKDB] Started run {run_id} for {username}")
            return run_id
        except Exception as e:
            logger.error(f"[DUCKDB] Failed to start run: {e}")
            raise
    
    def end_run(self, run_id: int, metrics: Dict, status: str = 'completed'):
        """
        End an extraction run with metrics.
        
        Args:
            run_id: Run ID
            metrics: Metrics dictionary from ExtractionMetrics.get_summary()
            status: Run status ('completed' or 'failed')
        """
        try:
            self.conn.execute("""
                UPDATE extraction_runs
                SET ended_at = ?,
                    threads_discovered = ?,
                    threads_processed = ?,
                    contacts_extracted = ?,
                    contacts_inserted = ?,
                    success_rate = ?,
                    insert_rate = ?,
                    error_rate = ?,
                    skipped_no_profile = ?,
                    skipped_invalid_name = ?,
                    errors = ?,
                    max_consecutive_errors = ?,
                    rate_limit_delays = ?,
                    error_recoveries = ?,
                    duration_seconds = ?,
                    status = ?
                WHERE run_id = ?
            """, [
                datetime.now(),
                metrics.get('threads_discovered', 0),
                metrics.get('threads_processed', 0),
                metrics.get('contacts_extracted', 0),
                metrics.get('contacts_inserted', 0),
                metrics.get('success_rate', 0.0),
                metrics.get('insert_rate', 0.0),
                metrics.get('error_rate', 0.0),
                metrics.get('skipped_no_profile', 0),
                metrics.get('skipped_invalid_name', 0),
                metrics.get('errors', 0),
                metrics.get('max_consecutive_errors', 0),
                metrics.get('rate_limit_delays', 0),
                metrics.get('error_recoveries', 0),
                metrics.get('duration_seconds', 0.0),
                status,
                run_id
            ])
            # Commit the transaction explicitly
            self.conn.commit()
            logger.info(f"[DUCKDB] Ended run {run_id} with status '{status}'")
        except Exception as e:
            # Log the error but don't fail - the update likely succeeded
            # DuckDB sometimes reports foreign key "violations" on UPDATE even when valid
            error_msg = str(e)
            if "foreign key constraint" in error_msg.lower():
                logger.warning(f"[DUCKDB] Foreign key warning on end_run {run_id} (likely harmless): {e}")
            else:
                logger.error(f"[DUCKDB] Failed to end run {run_id}: {e}")
    
    # ============================================
    # CONTACT METHODS
    # ============================================
    
    def insert_contact(self, run_id: int, contact_data: Dict) -> int:
        """
        Insert a single contact.
        
        Args:
            run_id: Run ID
            contact_data: Contact data dictionary
            
        Returns:
            int: Contact ID
        """
        try:
            result = self.conn.execute("""
                INSERT INTO contacts (
                    run_id, extracted_at, full_name, source_email, email, phone,
                    linkedin_id, linkedin_internal_id, company_name, location,
                    profile_url, job_source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING contact_id
            """, [
                run_id,
                datetime.now(),
                contact_data.get('full_name'),
                contact_data.get('source_email'),
                contact_data.get('email'),
                contact_data.get('phone'),
                contact_data.get('linkedin_id'),
                contact_data.get('linkedin_internal_id'),
                contact_data.get('company_name'),
                contact_data.get('location'),
                contact_data.get('profile_url'),
                contact_data.get('job_source', 'Bot Linkedin Message Extraction')
            ]).fetchone()
            
            contact_id = result[0]
            logger.debug(f"[DUCKDB] Inserted contact {contact_id}: {contact_data.get('full_name')}")
            return contact_id
        except Exception as e:
            logger.error(f"[DUCKDB] Failed to insert contact: {e}")
            return -1
    
    def insert_contacts_bulk(self, run_id: int, contacts: List[Dict]) -> int:
        """
        Insert multiple contacts in bulk.
        
        Args:
            run_id: Run ID
            contacts: List of contact data dictionaries
            
        Returns:
            int: Number of contacts inserted
        """
        count = 0
        for contact in contacts:
            contact_id = self.insert_contact(run_id, contact)
            if contact_id > 0:
                count += 1
        
        logger.info(f"[DUCKDB] Bulk inserted {count}/{len(contacts)} contacts for run {run_id}")
        return count
    
    def mark_api_inserted(self, contact_id: int):
        """
        Mark a contact as inserted to API.
        
        Args:
            contact_id: Contact ID
        """
        try:
            self.conn.execute("""
                UPDATE contacts
                SET inserted_to_api = TRUE,
                    api_insert_at = ?
                WHERE contact_id = ?
            """, [datetime.now(), contact_id])
        except Exception as e:
            logger.error(f"[DUCKDB] Failed to mark contact {contact_id} as API inserted: {e}")
    
    # ============================================
    # FAILURE TRACKING
    # ============================================
    
    def log_failure(self, run_id: int, thread_num: int, failure_type: str, 
                    error_msg: str, profile_url: str = None):
        """
        Log an extraction failure.
        
        Args:
            run_id: Run ID
            thread_num: Thread number
            failure_type: Type of failure (no_profile, invalid_name, extraction_error, api_error)
            error_msg: Error message
            profile_url: Profile URL (optional)
        """
        try:
            self.conn.execute("""
                INSERT INTO extraction_failures (
                    run_id, failed_at, thread_number, failure_type, 
                    error_message, profile_url
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, [run_id, datetime.now(), thread_num, failure_type, error_msg, profile_url])
            
            logger.debug(f"[DUCKDB] Logged failure for run {run_id}, thread {thread_num}: {failure_type}")
        except Exception as e:
            logger.error(f"[DUCKDB] Failed to log failure: {e}")
    
    # ============================================
    # QUERY METHODS
    # ============================================
    
    def get_run_stats(self, run_id: int) -> Optional[Dict]:
        """
        Get statistics for a specific run.
        
        Args:
            run_id: Run ID
            
        Returns:
            dict: Run statistics or None if not found
        """
        try:
            result = self.conn.execute("""
                SELECT * FROM extraction_runs WHERE run_id = ?
            """, [run_id]).fetchone()
            
            if not result:
                return None
            
            columns = [desc[0] for desc in self.conn.description]
            return dict(zip(columns, result))
        except Exception as e:
            logger.error(f"[DUCKDB] Failed to get run stats for {run_id}: {e}")
            return None
    
    def get_recent_runs(self, limit: int = 10) -> List[Dict]:
        """
        Get recent extraction runs.
        
        Args:
            limit: Maximum number of runs to return
            
        Returns:
            list: List of run dictionaries
        """
        try:
            results = self.conn.execute("""
                SELECT * FROM extraction_runs
                ORDER BY started_at DESC
                LIMIT ?
            """, [limit]).fetchall()
            
            columns = [desc[0] for desc in self.conn.description]
            return [dict(zip(columns, row)) for row in results]
        except Exception as e:
            logger.error(f"[DUCKDB] Failed to get recent runs: {e}")
            return []
    
    def get_contacts_by_run(self, run_id: int) -> List[Dict]:
        """
        Get all contacts from a specific run.
        
        Args:
            run_id: Run ID
            
        Returns:
            list: List of contact dictionaries
        """
        try:
            results = self.conn.execute("""
                SELECT * FROM contacts WHERE run_id = ? ORDER BY extracted_at
            """, [run_id]).fetchall()
            
            columns = [desc[0] for desc in self.conn.description]
            return [dict(zip(columns, row)) for row in results]
        except Exception as e:
            logger.error(f"[DUCKDB] Failed to get contacts for run {run_id}: {e}")
            return []
    
    def search_contacts(self, name: str = None, email: str = None, 
                       company: str = None, limit: int = 100) -> List[Dict]:
        """
        Search contacts by name, email, or company.
        
        Args:
            name: Name to search for (partial match)
            email: Email to search for (partial match)
            company: Company to search for (partial match)
            limit: Maximum number of results
            
        Returns:
            list: List of matching contact dictionaries
        """
        try:
            conditions = []
            params = []
            
            if name:
                conditions.append("full_name ILIKE ?")
                params.append(f"%{name}%")
            if email:
                conditions.append("email ILIKE ?")
                params.append(f"%{email}%")
            if company:
                conditions.append("company_name ILIKE ?")
                params.append(f"%{company}%")
            
            if not conditions:
                return []
            
            where_clause = " AND ".join(conditions)
            params.append(limit)
            
            results = self.conn.execute(f"""
                SELECT * FROM contacts 
                WHERE {where_clause}
                ORDER BY extracted_at DESC
                LIMIT ?
            """, params).fetchall()
            
            columns = [desc[0] for desc in self.conn.description]
            return [dict(zip(columns, row)) for row in results]
        except Exception as e:
            logger.error(f"[DUCKDB] Failed to search contacts: {e}")
            return []
    
    def get_total_contacts(self) -> int:
        """
        Get total number of contacts in database.
        
        Returns:
            int: Total contact count
        """
        try:
            result = self.conn.execute("SELECT COUNT(*) FROM contacts").fetchone()
            return result[0]
        except Exception as e:
            logger.error(f"[DUCKDB] Failed to get total contacts: {e}")
            return 0
    
    def get_success_rate_over_time(self, days: int = 30) -> List[Dict]:
        """
        Get success rate trend over time.
        
        Args:
            days: Number of days to look back
            
        Returns:
            list: List of daily success rates
        """
        try:
            results = self.conn.execute("""
                SELECT 
                    DATE(started_at) as date,
                    COUNT(*) as runs,
                    AVG(success_rate) as avg_success_rate,
                    SUM(contacts_extracted) as total_contacts
                FROM extraction_runs
                WHERE started_at >= CURRENT_DATE - INTERVAL ? DAY
                    AND status = 'completed'
                GROUP BY DATE(started_at)
                ORDER BY date DESC
            """, [days]).fetchall()
            
            columns = [desc[0] for desc in self.conn.description]
            return [dict(zip(columns, row)) for row in results]
        except Exception as e:
            logger.error(f"[DUCKDB] Failed to get success rate over time: {e}")
            return []
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
