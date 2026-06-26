#!/usr/bin/env python3
"""
Clean up 'not_found' markers from clinics西醫.csv and clinic_links.json
caused by browser crash / Google CAPTCHA blocks during the crawler run.
"""
import csv
import json
import os
from pathlib import Path

CSV_PATH = "/home/hsuyungfeng/文件/doctor-toolbox-post/clinics西醫.csv"
CACHE_PATH = "/home/hsuyungfeng/文件/doctor-toolbox-post/clinic_links.json"

def cleanup_csv():
    print(f"🧹 清理 CSV 資料庫: {CSV_PATH}")
    if not os.path.exists(CSV_PATH):
        print("❌ 找不到 CSV 檔案")
        return
        
    # Read rows
    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = list(next(reader))
        rows = [list(row) for row in reader]
        
    idx_fb = header.index('FB_URL')
    idx_email = header.index('Email')
    idx_msg = header.index('Messenger')
    
    cleaned_count = 0
    valid_fb_count = 0
    valid_email_count = 0
    
    # Reset 'not_found' values
    for row in rows:
        # Check FB
        if row[idx_fb] == 'not_found':
            row[idx_fb] = ''
            cleaned_count += 1
        elif row[idx_fb] != '':
            valid_fb_count += 1
            
        # Check Email
        if row[idx_email] == 'not_found':
            row[idx_email] = ''
        elif row[idx_email] != '':
            valid_email_count += 1
            
        # Check Messenger
        if row[idx_msg] == 'not_found':
            row[idx_msg] = ''
            
    # Save back
    temp_csv = CSV_PATH + ".tmp"
    with open(temp_csv, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
        
    if os.path.exists(CSV_PATH):
        os.remove(CSV_PATH)
    os.rename(temp_csv, CSV_PATH)
    
    print(f"  ✅ 成功清理 CSV 中的 {cleaned_count} 筆 'not_found' 紀錄")
    print(f"  ✅ 目前保留有效 FB_URL: {valid_fb_count} 筆，Email: {valid_email_count} 筆")

def cleanup_cache():
    print(f"🧹 清理 JSON 快取: {CACHE_PATH}")
    if not os.path.exists(CACHE_PATH):
        print("❌ 找不到 JSON 快取檔案")
        return
        
    with open(CACHE_PATH, 'r', encoding='utf-8') as f:
        cache_list = json.load(f)
        
    original_len = len(cache_list)
    
    # Filter out elements with not_found status/urls
    cleaned_cache = []
    for item in cache_list:
        if item.get('fb_url') == 'not_found':
            # Skip this item or clean it up
            continue
        cleaned_cache.append(item)
        
    temp_json = CACHE_PATH + ".tmp"
    with open(temp_json, 'w', encoding='utf-8') as f:
        json.dump(cleaned_cache, f, ensure_ascii=False, indent=2)
        
    if os.path.exists(CACHE_PATH):
        os.remove(CACHE_PATH)
    os.rename(temp_json, CACHE_PATH)
    
    print(f"  ✅ 成功將 JSON 快取從 {original_len} 筆清理至 {len(cleaned_cache)} 筆")

def main():
    cleanup_csv()
    cleanup_cache()

if __name__ == "__main__":
    main()
