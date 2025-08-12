import csv
import os

def log_csv(filepath, row):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    file_exists = os.path.isfile(filepath)

    with open(filepath, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['Timestamp', 'Username', 'Name', 'Title', 'Location', 'Pronouns', 'Connection', 'Profile URL']
                            if 'extracted_contacts' in filepath
                            else ['Timestamp', 'Username', 'Name', 'Status', 'Error'])
        writer.writerow(row)
