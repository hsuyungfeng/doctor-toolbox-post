#!/usr/bin/env python3
"""
批量搜尋診所 FB 個人頁面 + Google Maps 連結。
FB 搜尋使用 Google site:facebook.com 方式。
"""
import csv
import time
import json
import os
import re
from cloakbrowser import launch

CSV_PATH = "/home/hsuyungfeng/文件/doctor-toolbox-post/clinics西醫.csv"
RESULTS_PATH = "/home/hsuyungfeng/文件/doctor-toolbox-post/clinic_links.json"
PROCESSED_LOG = "/home/hsuyungfeng/文件/doctor-toolbox-post/processed_clinics.json"

def load_json(path, default=None):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default if default is not None else []

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 讀取診所清單
clinics = []
with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    header = next(reader)
    idx_map = {h: i for i, h in enumerate(header)}
    for row in reader:
        name = row[idx_map['醫事機構名稱']].strip()
        address = row[idx_map['地址']].strip()
        if name:
            clinics.append({'name': name, 'address': address})

print(f"共 {len(clinics)} 筆診所")

# 載入既有資料
existing = load_json(RESULTS_PATH, [])
existing_links = {r['clinic_name']: r for r in existing}
processed = set(load_json(PROCESSED_LOG, []))

to_process = [c for c in clinics if c['name'] not in existing_links]
print(f"需要搜尋: {len(to_process)} 筆\n")

# 啟動瀏覽器
browser = launch(headless=True, humanize=True, timezone="Asia/Taipei", locale="zh-TW")
page = browser.new_page()

for idx, clinic in enumerate(to_process):
    name = clinic['name']
    address = clinic['address']
    
    print(f"[{idx+1}/{len(to_process)}] {name}")
    
    result = existing_links.get(name, {
        'clinic_name': name,
        'address': address,
        'fb_url': None,
        'fb_type': None,
        'maps_url': None,
        'status': 'pending'
    })
    
    # === Search FB via Google site:facebook.com ===
    fb_query = f"{name} site:facebook.com"
    print(f"  🔍 FB: {fb_query}")
    
    try:
        page.goto(f"https://www.google.com/search?q={fb_query}")
        time.sleep(4)
        
        fb_links = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('a').forEach(a => {
                const href = a.getAttribute('href') || '';
                const text = (a.textContent || '').trim();
                
                // Clean up Google search URLs
                let cleanHref = href;
                if (href.startsWith('/url?q=')) {
                    cleanHref = href.replace('/url?q=', '').split('&')[0];
                }
                
                if (cleanHref.includes('facebook.com') && (cleanHref.includes('/p/') || cleanHref.includes('/page/') || cleanHref.includes('/profile/'))) {
                    results.push({
                        href: cleanHref.substring(0, 200),
                        text: text.substring(0, 50)
                    });
                }
            });
            return results;
        }""")
        
        # Find matching link
        for link in fb_links:
            link_text = link.get('text', '')
            link_href = link.get('href', '')
            if name in link_text:
                result['fb_url'] = link_href
                result['fb_type'] = 'page'
                print(f"  ✅ FB: {link_href[:80]}...")
                break
        
        if not result['fb_url']:
            # Try partial match
            for link in fb_links[:10]:
                link_text = link.get('text', '')
                link_href = link.get('href', '')
                overlap = sum(1 for c in name[:8] if c in link_text[:15])
                if overlap >= 3:
                    result['fb_url'] = link_href
                    result['fb_type'] = 'page'
                    print(f"  ⚠️ FB (partial): {link_href[:80]}...")
                    break
        
        if not result['fb_url']:
            print(f"  ❌ FB: 找不到")
            
    except Exception as e:
        print(f"  ❌ FB 錯誤: {e}")
    
    # === Search Google Maps ===
    maps_query = f"{name} {address}"
    print(f"  🔍 Maps: {maps_query}")
    
    try:
        page.goto(f"https://www.google.com/maps/search/{maps_query}/")
        time.sleep(4)
        
        current_url = page.url
        if 'google.com/maps' in current_url:
            result['maps_url'] = current_url
            result['status'] = 'maps_found'
            print(f"  ✅ Maps: {current_url[:80]}...")
        else:
            result['status'] = 'maps_redirect'
            print(f"  ⚠️ Maps redirect: {current_url[:80]}...")
            
    except Exception as e:
        print(f"  ❌ Maps 錯誤: {e}")
        result['status'] = 'error'
    
    existing_links[name] = result
    processed.add(name)
    
    # 每 10 筆存一次
    if (idx + 1) % 10 == 0:
        save_json(RESULTS_PATH, list(existing_links.values()))
        save_json(PROCESSED_LOG, list(processed))
        print(f"  進度: {idx+1}/{len(to_process)}")
    
    time.sleep(3)

browser.close()

# 儲存最終結果
save_json(RESULTS_PATH, list(existing_links.values()))
save_json(PROCESSED_LOG, list(processed))

# 總結
fb_found = sum(1 for r in existing_links.values() if r.get('fb_url'))
maps_found = sum(1 for r in existing_links.values() if r.get('maps_url'))
no_link = sum(1 for r in existing_links.values() if not r.get('fb_url') and not r.get('maps_url'))

print(f"\n{'='*60}")
print(f"📊 搜尋結果:")
print(f"  FB 連結: {fb_found} 筆")
print(f"  Maps 連結: {maps_found} 筆")
print(f"  無連結: {no_link} 筆")
print(f"  總計: {len(existing_links)} 筆")
print(f"{'='*60}")
