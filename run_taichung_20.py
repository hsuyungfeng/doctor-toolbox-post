#!/usr/bin/env python3
"""
整合腳本：將 JSON cache 中的台中診所資料寫回 CSV，
然後自動執行 generate_copy_llm.py 和 send_outreach.py。
"""
import csv
import json
import os
import subprocess
import sys

# === Paths ===
CSV_PATH = "/home/hsuyungfeng/文件/doctor-toolbox-post/clinics西醫.csv"
CACHE_PATH = "/home/hsuyungfeng/文件/doctor-toolbox-post/clinic_links.json"

def load_cache():
    with open(CACHE_PATH, 'r', encoding='utf-8') as f:
        cache_list = json.load(f)
    return {c['clinic_name']: c for c in cache_list}

def load_csv():
    rows = []
    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            rows.append(row)
    
    # Add new columns to header
    new_cols = ['FB_URL', 'Email', 'Messenger', 'Intro', 'Latest_Post', 'Personalized_Copy', 'Messenger_Status', 'Outreach_Time']
    for col in new_cols:
        if col not in header:
            header.append(col)
    
    # Pad rows
    for row in rows:
        while len(row) < len(header):
            row.append('')
    
    return header, rows

def save_csv(header, rows):
    temp_csv = CSV_PATH + ".tmp"
    with open(temp_csv, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    if os.path.exists(CSV_PATH):
        os.remove(CSV_PATH)
    os.rename(temp_csv, CSV_PATH)
    print("  ✅ CSV 已更新")

def merge_cache_to_csv(header, rows, cache):
    idx_name = header.index('醫事機構名稱')
    idx_addr = header.index('地址')
    col_map = {
        'FB_URL': header.index('FB_URL'),
        'Email': header.index('Email'),
        'Messenger': header.index('Messenger'),
        'Intro': header.index('Intro'),
        'Latest_Post': header.index('Latest_Post'),
    }
    
    taichung_count = 0
    taichung_with_data = 0
    
    for i, row in enumerate(rows):
        name = row[idx_name].strip()
        addr = row[idx_addr].strip()
        is_tc = '台中' in addr or '臺中' in addr
        
        if is_tc:
            taichung_count += 1
            if name in cache:
                c = cache[name]
                has_data = False
                for col, idx in col_map.items():
                    val = c.get(col.lower(), c.get(col, ''))
                    if val and val != 'None':
                        row[idx] = str(val)
                        has_data = True
                if has_data:
                    taichung_with_data += 1
    
    print(f"\n📊 台中診所統計:")
    print(f"  - 總數: {taichung_count}")
    print(f"  - 已爬取有資料的: {taichung_with_data}")
    return taichung_with_data

def check_sendable(header, rows):
    idx_name = header.index('醫事機構名稱')
    idx_addr = header.index('地址')
    idx_msg = header.index('Messenger')
    idx_intro = header.index('Intro')
    idx_copy = header.index('Personalized_Copy')
    idx_status = header.index('Messenger_Status')
    
    sendable = []
    for i, row in enumerate(rows):
        name = row[idx_name].strip()
        addr = row[idx_addr].strip()
        is_tc = '台中' in addr or '臺中' in addr
        msg = row[idx_msg].strip()
        intro = row[idx_intro].strip()
        copy = row[idx_copy].strip()
        status = row[idx_status].strip()
        
        if is_tc and msg and msg != 'not_found' and msg.startswith('http') and intro and intro != 'not_found' and not copy and status not in ('sent', 'dry_run'):
            sendable.append((i, name, addr, msg, intro))
    
    return sendable

def main():
    print("=" * 60)
    print("醫師工具箱 Messenger 開發流程 — 台中 20 筆")
    print("=" * 60)
    
    # Step 1: Load cache and CSV
    print("\n📂 載入 JSON cache...")
    cache = load_cache()
    print(f"  - 載入 {len(cache)} 筆爬取資料")
    
    print("\n📂 載入 CSV...")
    header, rows = load_csv()
    print(f"  - 載入 {len(rows)} 筆診所資料")
    
    # Step 2: Merge
    print("\n🔄 合併 JSON cache 到 CSV...")
    merge_cache_to_csv(header, rows, cache)
    save_csv(header, rows)
    
    # Step 3: Check what's sendable
    print("\n📊 檢查可發送名單...")
    sendable = check_sendable(header, rows)
    print(f"  - 可發送（台中、有Messenger、有Intro、無文案）: {len(sendable)} 筆")
    
    if len(sendable) == 0:
        print("\n⚠️ 沒有可發送的診所！")
        print("需要更多爬取。執行: python3 scrape_fb_info.py")
        return
    
    # Step 4: Run generate_copy_llm.py
    print("\n" + "=" * 60)
    print("第二步：生成個人化文案")
    print("=" * 60)
    result = subprocess.run(
        ['python3', '/home/hsuyungfeng/DevSoft/doctor-toolbox-post/generate_copy_llm.py'],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    if result.returncode != 0:
        print(f"⚠️ generate_copy_llm.py 退出碼: {result.returncode}")
        print("繼續檢查是否有生成文案...")
    
    # Re-read CSV after copy generation
    header, rows = load_csv()
    sendable = check_sendable(header, rows)
    
    # Step 5: Run send_outreach.py
    print("\n" + "=" * 60)
    print("第三步：慢速發送 Messenger 開發訊息（前 20 筆）")
    print("=" * 60)
    print(f"📊 目前可發送: {len(sendable)} 筆")
    
    limit = min(20, len(sendable))
    print(f"🎬 本次發送前 {limit} 筆診所")
    
    result = subprocess.run(
        ['python3', '/home/hsuyungfeng/DevSoft/doctor-toolbox-post/send_outreach.py', '--limit', str(limit)],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    if result.returncode != 0:
        print(f"⚠️ send_outreach.py 退出碼: {result.returncode}")
    
    print("\n" + "=" * 60)
    print("流程完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
