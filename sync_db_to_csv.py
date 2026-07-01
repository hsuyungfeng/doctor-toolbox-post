#!/usr/bin/env python3
import sqlite3
import csv
import os
from pathlib import Path

# Paths relative to project root
DB_PATH = Path("clinics.db")
CSV_PATH = Path("clinics西醫.csv")

if not DB_PATH.exists():
    # Try absolute fallback
    DB_PATH = Path("/home/hsuyungfeng/DevSoft/doctor-toolbox-post/clinics.db")

if not CSV_PATH.exists():
    # Try absolute fallback
    CSV_PATH = Path("/home/hsuyungfeng/DevSoft/doctor-toolbox-post/clinics西醫.csv")

if not DB_PATH.exists():
    print(f"❌ Database not found: {DB_PATH}")
    exit(1)

if not CSV_PATH.exists():
    print(f"❌ CSV not found: {CSV_PATH}")
    exit(1)

print("Reading SQLite database...")
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute("SELECT * FROM clinics")
db_data = {row['id']: dict(row) for row in cursor.fetchall()}
conn.close()
print(f"Loaded {len(db_data)} clinics from SQLite.")

print("Reading CSV file...")
with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = list(reader)

idx_id = header.index('醫事機構代碼')
idx_fb = header.index('FB_URL') if 'FB_URL' in header else -1
idx_email = header.index('Email') if 'Email' in header else -1
idx_msg = header.index('Messenger') if 'Messenger' in header else -1
idx_intro = header.index('Intro') if 'Intro' in header else -1
idx_post = header.index('Latest_Post') if 'Latest_Post' in header else -1
idx_copy = header.index('Personalized_Copy') if 'Personalized_Copy' in header else -1
idx_status = header.index('Messenger_Status') if 'Messenger_Status' in header else -1
idx_time = header.index('Outreach_Time') if 'Outreach_Time' in header else -1

# Add columns if they do not exist
for col_name, idx_ref in [('FB_URL', idx_fb), ('Email', idx_email), ('Messenger', idx_msg), 
                         ('Intro', idx_intro), ('Latest_Post', idx_post), 
                         ('Personalized_Copy', idx_copy), ('Messenger_Status', idx_status), 
                         ('Outreach_Time', idx_time)]:
    if idx_ref == -1:
        header.append(col_name)

# Refresh indices
idx_fb = header.index('FB_URL')
idx_email = header.index('Email')
idx_msg = header.index('Messenger')
idx_intro = header.index('Intro')
idx_post = header.index('Latest_Post')
idx_copy = header.index('Personalized_Copy')
idx_status = header.index('Messenger_Status')
idx_time = header.index('Outreach_Time')

print("Syncing CSV rows with database...")
updated_count = 0
for row in rows:
    while len(row) < len(header):
        row.append('')
        
    clinic_id = row[idx_id].strip()
    if clinic_id in db_data:
        db_row = db_data[clinic_id]
        
        # Sync values
        row[idx_fb] = db_row.get('fb_url') or ''
        row[idx_email] = db_row.get('email') or ''
        row[idx_msg] = db_row.get('messenger') or ''
        row[idx_intro] = db_row.get('intro') or ''
        row[idx_post] = db_row.get('latest_post') or ''
        row[idx_copy] = db_row.get('personalized_copy') or ''
        
        # Only keep positive statuses in CSV (sent, dry_run, fb_commented, email_sent)
        # Clear other failed/NULL statuses to empty (unsent)
        db_status = db_row.get('messenger_status') or ''
        if db_status in ['sent', 'dry_run', 'fb_commented', 'email_sent']:
            row[idx_status] = db_status
            row[idx_time] = db_row.get('outreach_time') or ''
        else:
            row[idx_status] = ''
            row[idx_time] = ''
            
        updated_count += 1

print(f"Writing updated CSV to {CSV_PATH}...")
temp_csv = str(CSV_PATH) + ".tmp"
with open(temp_csv, 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(header)
    writer.writerows(rows)

if os.path.exists(CSV_PATH):
    os.remove(CSV_PATH)
os.rename(temp_csv, CSV_PATH)

print(f"✅ Sync complete! Synced {updated_count} rows back to CSV.")
