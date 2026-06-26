#!/usr/bin/env python3
"""Test: Google Maps search for clinic and find review area."""
from cloakbrowser import launch
import time
import csv

CSV_PATH = "/home/hsuyungfeng/文件/doctor-toolbox-post/clinics西醫.csv"

# Read first clinic
with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    header = next(reader)
    idx_map = {h: i for i, h in enumerate(header)}
    row = next(reader)
    name = row[idx_map['醫事機構名稱']].strip()
    address = row[idx_map['地址']].strip()
    print(f"Testing Google Maps for: {name}")
    print(f"Address: {address}")

browser = launch(headless=False, humanize=True, timezone="Asia/Taipei", locale="zh-TW")
page = browser.new_page()

# Search on Google Maps
query = f"{name} {address}"
print(f"\n🔍 Searching Google Maps: {query}")
page.goto(f"https://www.google.com/maps/search/{query}/")
time.sleep(5)

print(f"Title: {page.title()}")
print(f"URL: {page.url}")

# Get all links
links = page.evaluate("""() => {
    const results = [];
    document.querySelectorAll('a').forEach(a => {
        const href = a.getAttribute('href') || '';
        const text = (a.textContent || '').trim();
        if (href.includes('google.com/maps') && href.length < 200) {
            results.push({href: href.substring(0, 100), text: text.substring(0, 30)});
        }
    });
    return results;
}""")

print(f"\nGoogle Maps links: {len(links)}")
for l in links[:20]:
    print(f"  href={l['href']}")
    print(f"  text={l['text']}")

# Look for review/write review buttons
review_btns = page.evaluate("""() => {
    const results = [];
    document.querySelectorAll('button, a').forEach(el => {
        const text = (el.textContent || '').trim();
        const aria = el.getAttribute('aria-label') || '';
        if (text.includes('評論') || text.includes('Write a review') || 
            text.includes('寫評論') || aria.includes('review') || aria.includes('評論')) {
            results.push({
                type: el.tagName,
                text: text.substring(0, 50),
                aria: aria.substring(0, 50),
                href: (el.getAttribute('href') || '').substring(0, 80)
            });
        }
    });
    return results;
}""")

print(f"\nReview buttons: {len(review_btns)}")
for b in review_btns:
    print(f"  type={b['type']} text={b['text']} aria={b['aria']}")

# Look for stars rating
stars = page.evaluate("""() => {
    const results = [];
    document.querySelectorAll('[class*="star"], [data-st]').forEach(el => {
        const text = (el.textContent || '').trim();
        if (text.length > 0) {
            results.push({text: text.substring(0, 50), class: (el.className || '').substring(0, 60)});
        }
    });
    return results.slice(0, 10);
}""")

print(f"\nStar elements: {len(stars)}")
for s in stars:
    print(f"  {s}")

# Get page content
content = page.evaluate("""() => {
    const sections = document.querySelectorAll('h1, h2, h3, [data-tooltip]');
    return Array.from(sections).map(e => ({
        tag: e.tagName,
        text: (e.textContent || '').substring(0, 100),
        class: (e.className || '').substring(0, 60)
    }));
}""")

print(f"\nPage sections: {len(content)}")
for c in content:
    print(f"  {c['tag']}: {c['text']}")

# Take screenshot
page.screenshot(path="/tmp/maps_test.png")
print("\nScreenshot saved to /tmp/maps_test.png")

browser.close()
