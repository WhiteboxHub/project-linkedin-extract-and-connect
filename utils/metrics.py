# utils/metrics.py
"""
Extraction Metrics Tracking (Phase 5)
Tracks and reports extraction performance metrics.
"""

import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class ExtractionMetrics:
    """
    Track extraction metrics for observability.
    
    Tracks:
    - Timing (start, end, duration)
    - Thread counts (discovered, processed)
    - Contact counts (extracted, inserted)
    - Skip counts (no profile, invalid name)
    - Error counts (total, consecutive, max consecutive)
    - Rate limiting (delays applied)
    - Error recovery (recoveries performed)
    """
    
    def __init__(self):
        """Initialize metrics with zero values."""
        # Timing
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        
        # Thread metrics
        self.threads_discovered: int = 0
        self.threads_processed: int = 0
        
        # Contact metrics
        self.contacts_extracted: int = 0
        self.contacts_inserted: int = 0
        
        # Skip metrics
        self.skipped_no_profile: int = 0
        self.skipped_invalid_name: int = 0
        
        # Error metrics
        self.errors: int = 0
        self.consecutive_errors: int = 0
        self.max_consecutive_errors: int = 0
        
        # Performance metrics
        self.rate_limit_delays: int = 0
        self.error_recoveries: int = 0
    
    def start_extraction(self):
        """Mark extraction start time."""
        self.start_time = datetime.now()
        logger.debug("[METRICS] Extraction started")
    
    def end_extraction(self):
        """Mark extraction end time."""
        self.end_time = datetime.now()
        logger.debug("[METRICS] Extraction ended")
    
    def increment_threads_discovered(self, count: int = 1):
        """Increment threads discovered count."""
        self.threads_discovered += count
    
    def increment_threads_processed(self, count: int = 1):
        """Increment threads processed count."""
        self.threads_processed += count
    
    def increment_contacts_extracted(self, count: int = 1):
        """Increment contacts extracted count."""
        self.contacts_extracted += count
    
    def increment_contacts_inserted(self, count: int):
        """Set contacts inserted count (from bulk insert result)."""
        self.contacts_inserted = count
    
    def increment_skipped_no_profile(self, count: int = 1):
        """Increment skipped (no profile) count."""
        self.skipped_no_profile += count
    
    def increment_skipped_invalid_name(self, count: int = 1):
        """Increment skipped (invalid name) count."""
        self.skipped_invalid_name += count
    
    def increment_errors(self, count: int = 1):
        """Increment error count."""
        self.errors += count
    
    def increment_consecutive_errors(self):
        """Increment consecutive error count and track max."""
        self.consecutive_errors += 1
        if self.consecutive_errors > self.max_consecutive_errors:
            self.max_consecutive_errors = self.consecutive_errors
    
    def reset_consecutive_errors(self):
        """Reset consecutive error count (on success)."""
        self.consecutive_errors = 0
    
    def increment_rate_limit_delays(self, count: int = 1):
        """Increment rate limit delay count."""
        self.rate_limit_delays += count
    
    def increment_error_recoveries(self, count: int = 1):
        """Increment error recovery count."""
        self.error_recoveries += count
    
    def get_duration(self) -> float:
        """
        Get extraction duration in seconds.
        
        Returns:
            float: Duration in seconds, or 0.0 if not started/ended
        """
        if not self.start_time or not self.end_time:
            return 0.0
        return (self.end_time - self.start_time).total_seconds()
    
    def get_success_rate(self) -> float:
        """
        Get extraction success rate as percentage.
        
        Returns:
            float: Success rate (0-100), or 0.0 if no threads processed
        """
        if self.threads_processed == 0:
            return 0.0
        return (self.contacts_extracted / self.threads_processed) * 100
    
    def get_insert_rate(self) -> float:
        """
        Get database insert success rate as percentage.
        
        Returns:
            float: Insert rate (0-100), or 0.0 if no contacts extracted
        """
        if self.contacts_extracted == 0:
            return 0.0
        return (self.contacts_inserted / self.contacts_extracted) * 100
    
    def get_error_rate(self) -> float:
        """
        Get error rate as percentage.
        
        Returns:
            float: Error rate (0-100), or 0.0 if no threads processed
        """
        if self.threads_processed == 0:
            return 0.0
        return (self.errors / self.threads_processed) * 100
    
    def get_summary(self) -> Dict:
        """
        Get comprehensive metrics summary.
        
        Returns:
            dict: All metrics in a dictionary
        """
        return {
            # Timing
            'duration_seconds': self.get_duration(),
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            
            # Thread metrics
            'threads_discovered': self.threads_discovered,
            'threads_processed': self.threads_processed,
            
            # Contact metrics
            'contacts_extracted': self.contacts_extracted,
            'contacts_inserted': self.contacts_inserted,
            
            # Rates
            'success_rate': self.get_success_rate(),
            'insert_rate': self.get_insert_rate(),
            'error_rate': self.get_error_rate(),
            
            # Skip metrics
            'skipped_no_profile': self.skipped_no_profile,
            'skipped_invalid_name': self.skipped_invalid_name,
            
            # Error metrics
            'errors': self.errors,
            'max_consecutive_errors': self.max_consecutive_errors,
            
            # Performance metrics
            'rate_limit_delays': self.rate_limit_delays,
            'error_recoveries': self.error_recoveries,
        }
    
    def log_summary(self):
        """Log comprehensive metrics summary."""
        summary = self.get_summary()
        
        logger.info("=" * 70)
        logger.info("EXTRACTION METRICS SUMMARY (Phase 5)")
        logger.info("=" * 70)
        
        # Timing
        logger.info(f"   Duration: {summary['duration_seconds']:.2f}s")
        if summary['start_time']:
            logger.info(f"   Started: {summary['start_time']}")
        if summary['end_time']:
            logger.info(f"   Ended: {summary['end_time']}")
        
        logger.info("-" * 70)
        
        # Thread metrics
        logger.info(f"   Threads discovered: {summary['threads_discovered']}")
        logger.info(f"   Threads processed: {summary['threads_processed']}")
        
        logger.info("-" * 70)
        
        # Contact metrics
        logger.info(f"   Contacts extracted: {summary['contacts_extracted']}")
        logger.info(f"   Contacts inserted: {summary['contacts_inserted']}")
        
        logger.info("-" * 70)
        
        # Rates
        logger.info(f"   Success rate: {summary['success_rate']:.1f}%")
        logger.info(f"   Insert rate: {summary['insert_rate']:.1f}%")
        logger.info(f"   Error rate: {summary['error_rate']:.1f}%")
        
        logger.info("-" * 70)
        
        # Skip metrics
        logger.info(f"   Skipped (no profile): {summary['skipped_no_profile']}")
        logger.info(f"   Skipped (invalid name): {summary['skipped_invalid_name']}")
        
        logger.info("-" * 70)
        
        # Error metrics
        logger.info(f"   Total errors: {summary['errors']}")
        logger.info(f"   Max consecutive errors: {summary['max_consecutive_errors']}")
        
        logger.info("-" * 70)
        
        # Performance metrics
        logger.info(f"   Rate limit delays: {summary['rate_limit_delays']}")
        logger.info(f"   Error recoveries: {summary['error_recoveries']}")
        
        logger.info("=" * 70)
    
    def __repr__(self) -> str:
        """String representation of metrics."""
        return (
            f"ExtractionMetrics("
            f"threads={self.threads_processed}/{self.threads_discovered}, "
            f"extracted={self.contacts_extracted}, "
            f"inserted={self.contacts_inserted}, "
            f"errors={self.errors})"
        )
