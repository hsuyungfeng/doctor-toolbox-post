#!/usr/bin/env python3
"""Test: analyze FB personal profile page structure."""
from cloakbrowser import launch
import time

browser = launch(headless=False, humanize=True, timezone="Asia/Taipei", locale="zh-TW")
page = browser.new_page()

page.goto("https://www.facebook.com/liu27603922/")
time.sleep(5)

print(f"Title: {page.title()}")
print(f"URL: {page.url}")

# Get all buttons
buttons = page.evaluate("""() => {
    const results = [];
    document.querySelectorAll('button').forEach(el => {
        const text = (el.textContent || '').trim();
        const ariaLabel = el.getAttribute('aria-label') || '';
        if (text.length > 0 && text.length < 100) {
            results.push({text: text.substring(0, 80), ariaLabel: ariaLabel.substring(0, 80)});
        }
    });
    return results;
}""")

print(f"\nButtons found: {len(buttons)}")
for b in buttons[:30]:
    print(f"  text={b['text']} aria={b['ariaLabel']}")

# Get all links
links = page.evaluate("""() => {
    const results = [];
    document.querySelectorAll('a').forEach(a => {
        const href = a.getAttribute('href') || '';
        const text = (a.textContent || '').trim();
        if (href.includes('facebook.com') && !href.includes('accounts.google')) {
            results.push({href: href.substring(0, 80), text: text.substring(0, 30)});
        }
    });
    return results;
}""")

print(f"\nFB links found: {len(links)}")
for l in links[:20]:
    print(f"  href={l['href']} text={l['text']}")

# Look for the "about" section or any content
about_divs = page.evaluate("""() => {
    const results = [];
    document.querySelectorAll('[data-testid]').forEach(el => {
        const testid = el.getAttribute('data-testid');
        const text = (el.textContent || '').substring(0, 100);
        results.push({testid, text});
    });
    return results.slice(0, 30);
}""")

print(f"\ndata-testid elements: {len(about_divs)}")
for d in about_divs:
    print(f"  testid={d['testid']} text={d['text']}")

# Check if there's a "message" button
msg_btns = page.evaluate("""() => {
    const results = [];
    document.querySelectorAll('a, button').forEach(el => {
        const text = (el.textContent || '').trim();
        const href = el.getAttribute('href') || '';
        const aria = el.getAttribute('aria-label') || '';
        if (text.includes('訊息') || text.includes('Message') || text.includes('私訊') || aria.includes('Message')) {
            results.push({type: el.tagName, text: text.substring(0, 50), href: href.substring(0, 80), aria: aria.substring(0, 50)});
        }
    });
    return results;
}""")

print(f"\nMessage buttons: {len(msg_btns)}")
for m in msg_btns:
    print(f"  type={m['type']} text={m['text']} href={m['href']}")

page.screenshot(path="/tmp/fb_profile.png")
print("\nScreenshot saved to /tmp/fb_profile.png")

browser.close()
