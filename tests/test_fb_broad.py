#!/usr/bin/env python3
"""Test: broader FB search + try direct search."""
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
                'phone': row[idx_map['電話']].strip()
            })

browser = launch(headless=False, humanize=True, timezone="Asia/Taipei", locale="zh-TW")
page = browser.new_page()

# Test with蔡恭禮內兒科診所
name = "蔡恭禮內兒科診所"
print(f"Testing: {name}")

# Method 1: Google search with broader query
query = f"{name} facebook"
print(f"\n  🔍 Search: {query}")
page.goto(f"https://www.google.com/search?q={query}&hl=zh-TW&num=10")
time.sleep(4)

# Get ALL facebook.com links (not just /pages/)
links = page.evaluate("""() => {
    const seen = new Set();
    const results = [];
    document.querySelectorAll('a').forEach(a => {
        const href = a.getAttribute('href') || '';
        if (href.includes('facebook.com') && !href.includes('apps.facebook.com') && !href.includes('facebook.com/groups') && !href.includes('facebook.com/events')) {
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

print(f"  Found {len(links)} FB links from Google:")
for l in links[:5]:
    print(f"    {l}")

if links:
    # Try opening the first one
    print(f"\n  Opening: {links[0]}")
    page.goto(links[0])
    time.sleep(5)
    print(f"  Title: {page.title()}")
    print(f"  URL: {page.url}")
    
    # Find comment links
    all_links = page.evaluate("""() => {
        const links = [];
        document.querySelectorAll('a').forEach(a => {
            const href = a.getAttribute('href') || '';
            const text = a.textContent || '';
            if ((href.includes('/comment') || href.includes('comment.php') || text.includes('留言') || text.includes('Comment')) && href.length > 20) {
                links.push({href: href.substring(0, 120), text: text.substring(0, 50)});
            }
        });
        return links;
    }""")
    
    print(f"\n  Comment links found: {len(all_links)}")
    for cl in all_links[:5]:
        print(f"    href={cl['href']}")
        print(f"    text={cl['text']}")
    
    page.screenshot(path="/tmp/fb_test2.png")
    print("  Screenshot saved")

browser.close()
