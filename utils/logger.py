#utils/logger.py
# ============================================
# CSV LOGGING - WITH FULL DEBUG
# ============================================

import csv
import os
import logging

logger = logging.getLogger(__name__)

def log_csv(filepath, row):
    """
    Log a row to CSV file with full debug logging.
    
    Args:
        filepath: Path to CSV file
        row: List of values to write
    """
    logger.info("=" * 60)
    logger.info(f"[LOG_CSV] START - Writing to: {filepath}")
    logger.info("=" * 60)
    
    try:
        # Step 1: Log input data
        logger.info(f"[LOG_CSV] Row data ({len(row)} columns):")
        for i, value in enumerate(row):
            logger.debug(f"[LOG_CSV]   Column {i}: {value}")
        
        # Step 2: Ensure directory exists
        dir_path = os.path.dirname(filepath)
        if dir_path:
            logger.info(f"[LOG_CSV] Ensuring directory exists: {dir_path}")
            os.makedirs(dir_path, exist_ok=True)
            logger.info(f"[LOG_CSV] Directory ready: {os.path.exists(dir_path)}")
        else:
            logger.info("[LOG_CSV] No directory path (writing to current directory)")
        
        # Step 3: Check if file exists
        file_exists = os.path.isfile(filepath)
        logger.info(f"[LOG_CSV] File exists: {file_exists}")
        
        # Step 4: Get absolute path
        abs_path = os.path.abspath(filepath)
        logger.info(f"[LOG_CSV] Absolute path: {abs_path}")
        
        # Step 5: Open and write
        logger.info("[LOG_CSV] Opening file for append...")
        
        with open(filepath, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header if new file
            if not file_exists:
                logger.info("[LOG_CSV] New file - writing header...")
                
                if 'extracted_contacts' in filepath:
                    header = [
                        'Timestamp', 'Source_Email', 'Name', 'Company', 
                        'Location', 'Email', 'Phone', 'Profile_URL', 'Notes'
                    ]
                elif 'error' in filepath.lower():
                    header = ['Timestamp', 'Username', 'Context', 'Error']
                else:
                    header = ['Timestamp', 'Username', 'Name', 'Status', 'Notes']
                
                writer.writerow(header)
                logger.info(f"[LOG_CSV] Header written: {header}")
            
            # Write data row
            logger.info("[LOG_CSV] Writing data row...")
            writer.writerow(row)
            logger.info("[LOG_CSV] Row written successfully!")
        
        # Step 6: Verify file
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            logger.info(f"[LOG_CSV] File verified - Size: {file_size} bytes")
        
        logger.info("[LOG_CSV] SUCCESS!")
        return True
        
    except PermissionError as e:
        logger.error(f"[LOG_CSV] FAILED: Permission denied")
        logger.error(f"[LOG_CSV] Error: {e}")
        logger.error(f"[LOG_CSV] Is the file open in Excel or another program?")
        logger.error(f"[LOG_CSV] Close the file and try again.")
        return False
        
    except IOError as e:
        logger.error(f"[LOG_CSV] FAILED: IO Error")
        logger.error(f"[LOG_CSV] Error: {e}")
        return False
        
    except Exception as e:
        logger.error(f"[LOG_CSV] FAILED: Unexpected error")
        logger.error(f"[LOG_CSV] Error: {e}", exc_info=True)
        return False
    
    finally:
        logger.info("[LOG_CSV] END")
        logger.info("=" * 60)