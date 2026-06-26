#!/usr/bin/env python3
"""Test CloakBrowser - search for clinic Facebook page."""
from cloakbrowser import launch
import time

browser = launch(headless=True)
page = browser.new_page()

# Test search
clinic = "蔡恭禮內兒科診所"
search_query = f"{clinic} site:facebook.com"
print(f"Searching: {search_query}")

page.goto(f"https://www.google.com/search?q={search_query}&hl=zh-TW&num=10")
time.sleep(5)

# Get all links
html = page.content()
print(f"Page title: {page.title()}")
print(f"Page length: {len(html)} chars")

# Extract links with simple parsing
import re
link_pattern = r'href="(/url\?q=[^"]+|https?://[^"]+)"'
matches = re.findall(link_pattern, html)

fb_links = []
for m in matches:
    if 'facebook.com' in m and 'apps.facebook.com' not in m:
        url = m
        if '/url?q=' in url:
            url = url.split('/url?q=')[1].split('&')[0]
        fb_links.append(url)

if fb_links:
    print(f"Found {len(fb_links)} Facebook links:")
    for l in fb_links[:5]:
        print(f"  {l}")
else:
    print("No Facebook links from Google, trying direct FB search...")
    
    page.goto(f"https://www.facebook.com/search/top/?q={clinic}")
    time.sleep(5)
    
    print(f"FB Page title: {page.title()}")
    print(f"FB Page length: {len(page.content())} chars")
    
    # Get page links from FB
    fb_links2 = page.evaluate("""() => {
        const links = [];
        document.querySelectorAll('a').forEach(a => {
            const href = a.getAttribute('href') || '';
            if (href.includes('/pages/') && href.length > 20) {
                links.push(href);
            }
        });
        return [...new Set(links)].slice(0, 10);
    }""")
    
    if fb_links2:
        print(f"Found {len(fb_links2)} Facebook pages:")
        for l in fb_links2[:5]:
            print(f"  {l}")
    else:
        page.screenshot(path="/tmp/test_search.png")
        print("Screenshot saved to /tmp/test_search.png")
        print("No pages found either")

browser.close()
