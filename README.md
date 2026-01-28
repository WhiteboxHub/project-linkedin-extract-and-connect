🔗 LinkedIn Auto-Connect Bot

An automated LinkedIn connection tool that helps you extract contacts and send personalized connection requests using multiple LinkedIn accounts and Chrome profiles.

✨ Features
✅ Extracts contacts from LinkedIn search results
✅ Sends personalized connection requests
✅ Each account connects only to its own contacts
✅ Clicks only the main Connect button (never sidebar)
✅ Handles Connect inside the “More” dropdown
✅ Supports multiple Chrome profiles
✅ Session-based login (no repeated authentication)

📁 Project Structure
project-linkedin-extract-and-connect/
├── setup.py                 # 1️⃣ Initial setup
├── validate_profiles.py     # 2️⃣ Validate configuration
├── main.py                  # 3️⃣ Extract contacts
├── connections.py           # 4️⃣ Send connections
├── config.py                # Auto-generated config
├── config.yaml              # Connection messages
├── requirements.txt         # Dependencies
├── credentials/
│   └── accounts.yaml        # LinkedIn credentials
├── logs/
│   └── extracted_contacts.csv
└── utils/
    ├── browser.py           # Browser setup
    ├── db.py                # Database utilities
    ├── linkedin_bot.py      # Bot helper functions
    ├── logger.py            # Logging configuration
    └── helpers.py           # General helpers

🚀 Installation
1️⃣ Clone / Download Project
cd project-linkedin-extract-and-connect

2️⃣ Create Virtual Environment
python -m venv venv

3️⃣ Activate Virtual Environment

 For Windows (CMD)

venv\Scripts\activate

Windows (PowerShell)

.\venv\Scripts\Activate.ps1

Mac / Linux

source venv/bin/activate

4️⃣ Install Dependencies
pip install -r requirements.txt
pip install -U selenium

🔧 Configuration
1️⃣ Chrome Profiles Setup

This project uses Chrome profiles to maintain LinkedIn login sessions.

Locate Chrome profiles directory:

C:\Users\YOUR_USERNAME\AppData\Local\Google\Chrome\User Data

Find Profile Folder Name

1.Open Chrome using your profile
2.Go to: chrome://version
3.Check Profile Path

Example:

Display Name	 Folder Name
 Account 1	       Profile 1
 Account 2    	   Profile 2

2️⃣ Configure Accounts
Edit:
credentials/accounts.yaml

Example:

accounts:
  - username: "account1@gmail.com"
    password: "your_password"
    chrome_profile: "Profile 1"
    candidate_id: 123 #id from database
 
⚠️ Make sure chrome_profile matches the folder name exactly.

3️⃣ Configure Messages

Edit:
config.yaml

Example:

MESSAGE: "Hi! I'd love to connect with you."

# Optional per-account messages
account1@gmail.com: "Custom message for account 1"
account2@gmail.com: "Custom message for account 2"

4️⃣ Manual Login (Required)
Before running the bot, you must log in once manually.
For each account:
open Chrome with its profile
Log in to LinkedIn
Close Chrome fully
This saves session cookies for automation.

📖 Usage
Activate Environment
venv\Scripts\activate

Run Scripts in Order
python setup.py             # 1️⃣ Generate config
python validate_profiles.py # 2️⃣ Validate setup
python main.py              # 3️⃣ Extract contacts
python connections.py       # 4️⃣ Send requests

📂 Output & Logs
Extracted Contacts

Saved to:
logs/extracted_contacts.csv

Logging
Runtime logs
Errors
Connection status
All stored in:
/logs

⚙️ How It Works

1️⃣ Loads Chrome profiles
2️⃣ Uses stored LinkedIn sessions
3️⃣ Scrapes search/contact results
4️⃣ Assigns contacts per account
5️⃣ Sends personalized requests
6️⃣ Tracks progress via database