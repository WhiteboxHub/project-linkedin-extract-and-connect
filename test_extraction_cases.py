import json
import os
import sys
from pprint import pprint

# Ensure we can import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.offline_extractor import OfflineExtractor

TEST_DIR = "test_extraction_data"
RAW_DIR = os.path.join(TEST_DIR, "raw_messages", "2026-03-10", "test_candidate")
OUT_DIR = os.path.join(TEST_DIR, "output")

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)

CANDIDATE_EMAIL = "candidate@example.com"

# ─── CASE 1: Standard Recruiter Job Message ────────────────────────────
case1 = {
    "conversation_id": "case1_standard",
    "participant_name": "Recruiter Alice",
    "participant_profile_url": "https://linkedin.com/in/alice",
    "candidate_email": CANDIDATE_EMAIL,
    "messages": [
        {
            "sender_name": "Recruiter Alice",
            "is_outgoing": False,
            "date_heading": "Monday",
            "msg_timestamp": "Monday 10:00 AM",
            "text": "Hello! We are hiring.\nRole: Frontend Dev\nCompany: TechCorp\nLocation: Remote\nEmail me at alice@techcorp.com or call 555-0001. Apply here: https://techcorp.com/jobs/1",
            "email_links": ["alice@techcorp.com"],
            "linkedin_links": []
        }
    ]
}

# ─── CASE 2: Candidate Replies with their Info ─────────────────────────
case2 = {
    "conversation_id": "case2_candidate_reply",
    "participant_name": "Recruiter Bob",
    "participant_profile_url": "https://linkedin.com/in/bob",
    "candidate_email": CANDIDATE_EMAIL,
    "messages": [
        {
            "sender_name": "Recruiter Bob",
            "is_outgoing": False,
            "date_heading": "Tuesday",
            "msg_timestamp": "Tuesday 1:00 PM",
            "text": "Hi, I have a new opportunity.\nRole: Backend Engineer\nCompany: DataSys\nPlease review.",
            "email_links": ["bob@datasys.com"],
            "linkedin_links": []
        },
        {
            "sender_name": "Me",
            "is_outgoing": True,
            "date_heading": "Tuesday",
            "msg_timestamp": "Tuesday 2:00 PM",
            "text": f"Thanks Bob! My email is {CANDIDATE_EMAIL} and my number is 555-9999. I am interested in the Backend Engineer role.",
            "email_links": [CANDIDATE_EMAIL],
            "linkedin_links": []
        }
    ]
}

# ─── CASE 3: Multiple Jobs from same recruiter ─────────────────────────
case3 = {
    "conversation_id": "case3_multi_job",
    "participant_name": "Recruiter Charlie",
    "participant_profile_url": "https://linkedin.com/in/charlie",
    "candidate_email": CANDIDATE_EMAIL,
    "messages": [
        {
            "sender_name": "Recruiter Charlie",
            "is_outgoing": False,
            "date_heading": "Wednesday",
            "msg_timestamp": "Wednesday 9:00 AM",
            "text": "Here is an opening:\nRole: Data Scientist\nCompany: AIWorks\nSalary $150k. Email charlie@aiworks.com.",
            "email_links": ["charlie@aiworks.com"],
            "linkedin_links": []
        },
        {
            "sender_name": "Recruiter Charlie",
            "is_outgoing": False,
            "date_heading": "Thursday",
            "msg_timestamp": "Thursday 10:00 AM",
            "text": "Another opening:\nRole: Machine Learning Engineer\nCompany: AIWorks\nLet me know!",
            "email_links": [],
            "linkedin_links": []
        },
        {
            "sender_name": "Me",
            "is_outgoing": True,
            "date_heading": "Thursday",
            "msg_timestamp": "Thursday 11:00 AM",
            "text": "I like Role 2.",
            "email_links": [],
            "linkedin_links": []
        }
    ]
}

# ─── CASE 4: Legacy JSON (no is_outgoing flag) ─────────────────────────
case4 = {
    "conversation_id": "case4_legacy",
    "participant_name": "Recruiter Dave",
    "participant_profile_url": "https://linkedin.com/in/dave",
    "candidate_email": CANDIDATE_EMAIL,
    "messages": [
        {
            "sender_name": "Recruiter Dave",
            "text": "Job title: Software Engineer\nCompany: Legacy Inc\nEmail dave@legacy.com",
            "email_links": ["dave@legacy.com"],
            "linkedin_links": []
        },
        {
            "sender_name": "Me",
            "text": f"Sounds good. Reach me at {CANDIDATE_EMAIL}.",
            "email_links": [CANDIDATE_EMAIL],
            "linkedin_links": []
        }
    ]
}

# ─── CASE 5: Just chatting, no job info ────────────────────────────────
case5 = {
    "conversation_id": "case5_no_job",
    "participant_name": "Recruiter Eve",
    "participant_profile_url": "https://linkedin.com/in/eve",
    "candidate_email": CANDIDATE_EMAIL,
    "messages": [
        {
            "sender_name": "Recruiter Eve",
            "is_outgoing": False,
            "text": "Hi, how have you been? Are you still at your current company? eve@agency.com",
            "email_links": ["eve@agency.com"],
            "linkedin_links": []
        }
    ]
}

# Save test cases
os.makedirs(RAW_DIR, exist_ok=True)
for i, case in enumerate([case1, case2, case3, case4, case5], 1):
    with open(os.path.join(RAW_DIR, f"case{i}.json"), "w") as f:
        json.dump(case, f)

# Run extraction
extractor = OfflineExtractor(
    input_dir=RAW_DIR,
    output_dir=OUT_DIR,
    date_str="2026-03-10",
    exclude_personal=True
)

res = extractor.run()
contacts = res.get("contacts", [])
jobs = res.get("job_listings", [])

print(f"\\n--- EXTRACTION RESULTS ---")
print(f"Extracted {len(contacts)} contacts and {len(jobs)} jobs.")

print("\\n--- CONTACTS ---")
for c in contacts:
    print(f"Name: {c.get('full_name')} | Email: {c.get('email')} | Phone: {c.get('phone')} | Src: {c.get('conversation_id')}")

print("\\n--- JOB LISTINGS ---")
for j in jobs:
    print(f"UID: {j.get('source_uid')} | Title: {j.get('raw_title')} | Company: {j.get('raw_company')} | Contact: {j.get('raw_contact_info')}")

# cleanup
import shutil
shutil.rmtree(TEST_DIR)
