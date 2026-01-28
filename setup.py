"""
LinkedIn Bot Setup Script
- Login to WBL API
- Fetch marketing candidates (cache to CSV)
- Generate config.py with selected candidate
"""

import requests
import csv
import sys
import os
from datetime import datetime
from pathlib import Path
import getpass

# ============================================
# CONSTANTS
# ============================================

SCRIPT_DIR = Path(__file__).parent.absolute()
CONFIG_FILE = SCRIPT_DIR / "config.py"
CANDIDATE_CSV_FILE = SCRIPT_DIR / "marketing_candidates.csv"

DEFAULT_API_URLS = {
    "1": "http://localhost:8000/api",
    "2": "https://api.whitebox-learning.com/api"
}

# Job Type IDs for activity logging
EXTRACTION_JOB_ID = 120      # bot_linkedin_message_extraction
CONNECTOR_JOB_ID = 121       # bot_linkedin_friend_connector
EXTRACTION_UNIQUE_ID = "bot_linkedin_message_extraction"
CONNECTOR_UNIQUE_ID = "bot_linkedin_friend_connector"

# ============================================
# HELPER FUNCTIONS
# ============================================

def print_header(text):
    """Print formatted header."""
    print("\n" + "=" * 60)
    print(f" {text}")
    print("=" * 60)

def print_step(step, text):
    """Print step indicator."""
    print(f"\n[Step {step}] {text}")
    print("-" * 60)

def get_input(prompt, default=None, required=True, password=False):
    """Get user input with optional default."""
    if default is not None:
        display_prompt = f"{prompt} [default: {default}]: "
    else:
        display_prompt = f"{prompt}: "

    if password:
        value = getpass.getpass(display_prompt)
    else:
        value = input(display_prompt).strip()

    if not value and default is not None:
        return str(default)

    if required and not value:
        print("This field is required.")
        return get_input(prompt, default, required, password)

    return value

# ============================================
# API AUTHENTICATION
# ============================================

def login_to_wbl(api_url, email, password):
    """Login to WBL API and return access token."""
    try:
        print(f"Connecting to: {api_url}/login")
        response = requests.post(
            f"{api_url}/login",
            data={"username": email, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        token = data.get("access_token")
        if not token:
            raise Exception("No access_token in response")
        
        return token
        
    except requests.exceptions.ConnectionError:
        raise Exception(f"Cannot connect to {api_url}. Is the server running?")
    except requests.exceptions.HTTPError as e:
        raise Exception(f"Login failed: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        raise Exception(f"Login error: {str(e)}")

# ============================================
# CSV CANDIDATE CACHE
# ============================================

def save_candidates_to_csv(candidates):
    """Save candidates to CSV for caching."""
    try:
        with open(CANDIDATE_CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["id", "name"])
            writer.writeheader()
            writer.writerows(candidates)

        print(f"Candidates cached to: {CANDIDATE_CSV_FILE}")
        print(f"Total candidates saved: {len(candidates)}")
    except Exception as e:
        print(f"Error saving candidates to CSV: {e}")

def load_candidates_from_csv():
    """Load candidates from cached CSV."""
    if not CANDIDATE_CSV_FILE.exists():
        return []

    try:
        with open(CANDIDATE_CSV_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            candidates = []
            for row in reader:
                try:
                    candidates.append({
                        "id": int(row["id"]),
                        "name": row["name"]
                    })
                except (ValueError, KeyError):
                    continue
        return candidates
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return []

# ============================================
# FETCH CANDIDATES (CSV -> API fallback)
# ============================================

def get_candidates(api_url, token):
    """
    Get candidates with smart caching:
    1. Check for --refresh-candidates flag
    2. If not refresh, try to load from CSV
    3. If CSV empty or refresh, fetch from API and cache
    """
    force_refresh = "--refresh-candidates" in sys.argv

    # Try CSV first (if not forcing refresh)
    if not force_refresh:
        cached = load_candidates_from_csv()
        if cached:
            print(f"Loaded {len(cached)} candidates from cached CSV")
            return cached

    # Fetch from API
    print("Fetching candidates from API...")
    try:
        response = requests.get(
            f"{api_url}/candidate/marketing",
            params={"limit": 1000},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30
        )
        response.raise_for_status()

        data = response.json()
        candidates = []
        
        for record in data.get("data", []):
            if record.get("status") == "active" and record.get("candidate"):
                candidates.append({
                    "id": record["candidate"]["id"],
                    "name": record["candidate"]["full_name"]
                })

        if candidates:
            save_candidates_to_csv(candidates)
            print(f"Fetched {len(candidates)} active candidates from API")
        else:
            print("No active candidates found from API")
            
        return candidates
        
    except Exception as e:
        print(f"Failed to fetch candidates from API: {e}")
        
        # Try CSV as fallback
        cached = load_candidates_from_csv()
        if cached:
            print(f"Using cached CSV ({len(cached)} candidates)")
            return cached
            
        return []

# ============================================
# JOB TYPE VERIFICATION
# ============================================

def verify_job_types(api_url, token, employee_id):
    """Verify job types exist and return their IDs."""
    try:
        print("Verifying job types...")
        response = requests.get(
            f"{api_url}/job-types",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30
        )
        response.raise_for_status()
        job_types = response.json()

        extraction_id = None
        connector_id = None

        for job in job_types:
            unique_id = job.get("unique_id", "")
            if unique_id == EXTRACTION_UNIQUE_ID:
                extraction_id = job["id"]
                print(f"   Extraction job found (ID: {extraction_id})")
            if unique_id == CONNECTOR_UNIQUE_ID:
                connector_id = job["id"]
                print(f"   Connector job found (ID: {connector_id})")

        # Use defaults if not found
        if not extraction_id:
            extraction_id = EXTRACTION_JOB_ID
            print(f"   Using default extraction job ID: {extraction_id}")
        if not connector_id:
            connector_id = CONNECTOR_JOB_ID
            print(f"   Using default connector job ID: {connector_id}")

        return extraction_id, connector_id

    except Exception as e:
        print(f"Could not verify job types: {e}")
        print(f"Using defaults - Extraction: {EXTRACTION_JOB_ID}, Connector: {CONNECTOR_JOB_ID}")
        return EXTRACTION_JOB_ID, CONNECTOR_JOB_ID

# ============================================
# API TEST
# ============================================

def test_activity_log_api(api_url, token, employee_id, candidate_id, job_type_id):
    """Test the activity log API endpoint."""
    try:
        print("\nTesting Activity Log API...")
        
        test_payload = {
            "job_id": job_type_id,
            "employee_id": employee_id,
            "activity_date": datetime.now().strftime("%Y-%m-%d"),
            "activity_count": 0,
            "notes": "Setup test - please ignore"
        }
        
        if candidate_id and int(candidate_id) > 0:
            test_payload["candidate_id"] = int(candidate_id)
        
        response = requests.post(
            f"{api_url}/job_activity_logs",
            json=test_payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            print(f"   API test successful! Log ID: {result.get('id', 'N/A')}")
            return True
        else:
            print(f"   API test failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"   API test error: {e}")
        return False

def test_vendor_contact_api(api_url, token):
    """Test the vendor contact API endpoint."""
    try:
        print("Testing Vendor Contact API...")
        
        # Just test GET endpoint
        response = requests.get(
            f"{api_url}/vendor_contact_extracts",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            print(f"   Vendor Contact API accessible!")
            return True
        else:
            print(f"   API test failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   API test error: {e}")
        return False

# ============================================
# CONFIG GENERATION
# ============================================

def generate_config_py(config):
    """Generate config.py file."""
    content = f'''# ============================================
# WBL BOT CONFIGURATION
# Generated by setup.py on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
# ============================================
# DO NOT COMMIT THIS FILE TO VERSION CONTROL
# ============================================

WBL_CONFIG = {{
    # API Configuration
    "API_URL": "{config['api_url']}",
    "TOKEN": "{config['token']}",
    
    # User Configuration
    "EMAIL": "{config['email']}",
    "EMPLOYEE_ID": {config['employee_id']},
    "CANDIDATE_ID": {config['candidate_id']},
    "CANDIDATE_NAME": "{config.get('candidate_name', '')}",
    
    # Job Configuration (for activity logging)
    "EXTRACTION_JOB_ID": {config['extraction_job_id']},    # bot_linkedin_message_extraction
    "CONNECTOR_JOB_ID": {config['connector_job_id']},      # bot_linkedin_friend_connector
    
    # Token Metadata
    "TOKEN_GENERATED_AT": "{config['generated_at']}",
    
    # Environment
    "ENVIRONMENT": "{config['environment']}"
}}
'''

    try:
        CONFIG_FILE.write_text(content, encoding='utf-8')
        print(f"Config file created: {CONFIG_FILE}")
    except Exception as e:
        print(f"Error creating config file: {e}")
        raise

def update_gitignore():
    """Update .gitignore to exclude sensitive files."""
    gitignore_path = SCRIPT_DIR / ".gitignore"
    
    entries = [
        "config.py",
        "marketing_candidates.csv",
        "__pycache__/",
        "*.pyc",
        "logs/",
        "*.log",
        "debug_*.png",
        "venv/",
        ".venv/"
    ]
    
    existing = ""
    if gitignore_path.exists():
        try:
            existing = gitignore_path.read_text()
        except:
            pass
    
    new_entries = [e for e in entries if e not in existing]
    
    if new_entries:
        try:
            with open(gitignore_path, 'a') as f:
                if existing and not existing.endswith('\n'):
                    f.write('\n')
                f.write('\n'.join(new_entries) + '\n')
            print("Updated .gitignore")
        except Exception as e:
            print(f"Could not update .gitignore: {e}")

# ============================================
# MAIN SETUP FLOW
# ============================================

def run_setup():
    """Main setup function."""
    print_header("LINKEDIN BOT SETUP")
    print("\nThis script configures the LinkedIn bot with your WBL credentials.")
    print("Candidates are fetched from API and cached locally.")
    print("\nUsage:")
    print("  python setup.py                     - Normal run")
    print("  python setup.py --refresh-candidates - Force refresh from API")

    # Step 1: Select Environment
    print_step(1, "Select Environment")
    print("1. Local (localhost:8000)")
    print("2. Production (whitebox-learning.com)")
    
    choice = get_input("Choose", default="2")
    
    if choice == "1":
        api_url = DEFAULT_API_URLS["1"]
        environment = "local"
    else:
        api_url = DEFAULT_API_URLS["2"]
        environment = "production"
    
    print(f"Using: {api_url}")

    # Step 2: Login
    print_step(2, "Login to WBL")
    
    email = get_input("WBL Email")
    password = get_input("WBL Password", password=True)
    employee_id_str = get_input("Employee ID (e.g., 351)")
    
    try:
        employee_id = int(employee_id_str)
    except ValueError:
        print("ERROR: Employee ID must be a number")
        return

    try:
        print("Authenticating...")
        token = login_to_wbl(api_url, email, password)
        print("Login successful!")
        print(f"   Token: {token[:30]}...{token[-10:]}")
    except Exception as e:
        print(f"ERROR: {e}")
        return

    # Step 3: Load Candidates
    print_step(3, "Load Candidates")
    
    candidates = get_candidates(api_url, token)
    
    selected_candidate_id = 0
    selected_candidate_name = ""
    
    if candidates:
        print(f"\n{'ID':<8} | {'Name':<40}")
        print("-" * 52)
        
        display_count = min(30, len(candidates))
        for c in candidates[:display_count]:
            print(f"{c['id']:<8} | {c['name']:<40}")
        
        if len(candidates) > 30:
            print(f"... and {len(candidates) - 30} more candidates")
        
        candidate_input = get_input("\nEnter Candidate ID (or Enter to skip)", default="0", required=False)
        
        try:
            selected_candidate_id = int(candidate_input) if candidate_input else 0
            
            for c in candidates:
                if c['id'] == selected_candidate_id:
                    selected_candidate_name = c['name']
                    print(f"Selected: {selected_candidate_name}")
                    break
                    
        except ValueError:
            selected_candidate_id = 0
            print("Invalid ID, skipping candidate selection")
    else:
        print("No candidates found.")
        manual_id = get_input("Enter Candidate ID manually (or 0 to skip)", default="0", required=False)
        try:
            selected_candidate_id = int(manual_id) if manual_id else 0
        except:
            selected_candidate_id = 0

    # Step 4: Verify Job Types
    print_step(4, "Verify Job Types")
    
    extraction_job_id, connector_job_id = verify_job_types(api_url, token, employee_id)

    # Step 5: Test APIs
    print_step(5, "Test API Endpoints")
    
    activity_test = test_activity_log_api(api_url, token, employee_id, selected_candidate_id, extraction_job_id)
    contact_test = test_vendor_contact_api(api_url, token)
    
    if not activity_test or not contact_test:
        print("\nWARNING: Some API tests failed.")
        proceed = get_input("Continue anyway? (y/n)", default="y")
        if proceed.lower() != 'y':
            print("Setup cancelled.")
            return

    # Step 6: Generate Config
    print_step(6, "Generate Configuration")
    
    config = {
        "api_url": api_url,
        "token": token,
        "email": email,
        "employee_id": employee_id,
        "candidate_id": selected_candidate_id,
        "candidate_name": selected_candidate_name,
        "extraction_job_id": extraction_job_id,
        "connector_job_id": connector_job_id,
        "environment": environment,
        "generated_at": datetime.now().isoformat()
    }
    
    generate_config_py(config)
    update_gitignore()

    # Done!
    print_header("SETUP COMPLETE!")
    print(f"""
Configuration saved to: config.py
Candidates cached to:   marketing_candidates.csv

Summary:
   Environment:      {environment}
   API URL:          {api_url}
   Email:            {email}
   Employee ID:      {employee_id}
   Candidate ID:     {selected_candidate_id or 'None'}
   Candidate Name:   {selected_candidate_name or 'N/A'}
   Extraction Job:   {extraction_job_id}
   Connector Job:    {connector_job_id}

Next Steps:
   1. Update credentials/accounts.yaml with LinkedIn accounts
   2. Run extraction: python main.py
   3. Run connector:  python connections.py

To refresh candidates from API:
   python setup.py --refresh-candidates

Note: Token expires after some time. Run setup.py again to refresh.
""")

# ============================================
# ENTRY POINT
# ============================================

if __name__ == "__main__":
    try:
        run_setup()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)