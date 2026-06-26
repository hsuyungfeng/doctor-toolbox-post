#!/usr/bin/env python3
"""Quick test: search first 3 clinics and show results."""
import csv
import time
from cloakbrowser import launch

CSV_PATH = "/home/hsuyungfeng/文件/doctor-toolbox-post/clinics西醫.csv"

clinics = []
with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    header = next(reader)
    idx_map = {h: i for i, h in enumerate(header)}
    
    for i, row in enumerate(reader):
        name = row[idx_map['醫事機構名稱']].strip()
        if name:
            clinics.append({
                'name': name,
                'address': row[idx_map['地址']].strip(),
                'dept': row[idx_map.get('診療科別', -1)].strip() if '診療科別' in idx_map else '',
                'phone': row[idx_map['電話']].strip()
            })

print(f"Loaded {len(clinics)} clinics. Testing first {min(3, len(clinics))}...\n")

browser = launch(headless=False, humanize=True, timezone="Asia/Taipei", locale="zh-TW")
page = browser.new_page()

for clinic in clinics[:3]:
    name = clinic['name']
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"  Phone: {clinic['phone']}")
    print(f"  Dept: {clinic['dept']}")
    
    # Search FB via Google
    query = f"{name} site:facebook.com"
    print(f"\n  🔍 Searching: {query}")
    page.goto(f"https://www.google.com/search?q={query}&hl=zh-TW&num=10")
    time.sleep(4)
    
    links = page.evaluate("""() => {
        const seen = new Set();
        const results = [];
        document.querySelectorAll('a').forEach(a => {
            const href = a.getAttribute('href') || '';
            if (href.includes('facebook.com') && href.includes('/pages/') && !href.includes('apps.facebook.com')) {
                let url = href;
                if (url.includes('/url?q=')) {
                    url = url.split('/url?q=')[1].split('&')[0];
                }
                if (!seen.has(url)) {
                    seen.add(url);
                    results.push(url);
                }
            }
        });
        return results;
    }""")
    
    if links:
        print(f"  ✅ FB found: {links[0]}")
        
        page.goto(links[0])
        time.sleep(5)
        print(f"  FB Title: {page.title()}")
        
        # Find comment links
        all_links = page.evaluate("""() => {
            const links = [];
            document.querySelectorAll('a').forEach(a => {
                const href = a.getAttribute('href') || '';
                const text = a.textContent || '';
                if (href.includes('/comment') || href.includes('comment.php') || text.includes('留言') || text.includes('Comment')) {
                    links.push({href: href.substring(0, 100), text: text.substring(0, 50)});
                }
            });
            return links;
        }""")
        
        if all_links:
            print(f"  📝 Found {len(all_links)} comment-related links:")
            for cl in all_links[:3]:
                print(f"    href={cl['href']}")
                print(f"    text={cl['text']}")
        else:
            print("  ⚠️ No comment links found")
            page.screenshot(path="/tmp/fb_test1.png")
    else:
        print("  ❌ No FB page found")
    
    time.sleep(2)

browser.close()
print("\nDone!")
