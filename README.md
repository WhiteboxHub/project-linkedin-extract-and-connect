# LinkedIn Automation Bot

### This project automates two main tasks on LinkedIn:

Extract contact info from the latest 10 conversations in your LinkedIn messages.

Send connection requests with a custom message to those extracted profiles.

```
.
├── credentials/
│   └── accounts.yaml             # Stores LinkedIn account usernames & passwords
├── logs/
│   ├── extracted_contacts.csv    # Output file for extracted contact info
│   ├── connection_logs.csv       # Log of sent connection requests
│   └── error_logs.csv            # Any errors encountered during execution
├── messages/
│   └── message.txt               # Your connection request message text
├── utils/
│   ├── browser.py                 # Sets up Selenium WebDriver
│   ├── helpers.py                 # Helper functions (e.g., loading message text)
│   └── logger.py                  # CSV logging utilities
├── main.py                        # Extracts contact info from latest 10 unread or recent chats
├── connections.py                 # Sends connection requests with a custom message
└── README.md
```


### How It Works

Both main.py and connections.py use the same credentials file to log into LinkedIn:


credentials/accounts.yaml
```
accounts:
  - username: your_email@example.com
    password: your_password
  - username: your_email@example.com
    password: your_password
```

### 📜 Script Functions
1️⃣ main.py
Logs into LinkedIn using credentials from accounts.yaml

Opens Messages

Extracts the latest 10 conversations (including unread)

Visits each sender's profile

Scrapes:

Name

Title

Location

Pronouns

Connection level

Profile URL

Contact info (if available)

Saves all results to: 
```
logs/extracted_contacts.csv

```


2️⃣ connections.py
Reads logs/extracted_contacts.csv for LinkedIn profile URLs

Reads your custom message from:
```
messages/message.txt
```



▶️ How to Run
1. Install dependencies:

```
pip install -r requirements.txt
```
2. Run extraction (scrapes contact info from latest 10 chats):
```
python main.py
```
➡ Output saved in logs/extracted_contacts.csv

3. Send connection requests:

```
python connections.py
```
➡ Logs saved in logs/connection_logs.csv