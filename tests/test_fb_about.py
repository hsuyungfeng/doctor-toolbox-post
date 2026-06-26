#!/usr/bin/env python3
"""Test: click 'About' on FB profile and look for message/comment area."""
from cloakbrowser import launch
import time

browser = launch(headless=False, humanize=True, timezone="Asia/Taipei", locale="zh-TW")
page = browser.new_page()

page.goto("https://www.facebook.com/liu27603922/")
time.sleep(4)

# Click the "About" link
about_link = page.evaluate("document.querySelector('a[href*=\"/about\"]')")
if about_link:
    page.evaluate("document.querySelector('a[href*=\"/about\"]').click()")
    time.sleep(5)

print(f"After clicking About: {page.title()}")
print(f"URL: {page.url}")

# Get all links on the about page
links = page.evaluate("""() => {
    const results = [];
    document.querySelectorAll('a').forEach(a => {
        const href = a.getAttribute('href') || '';
        const text = (a.textContent || '').trim();
        if (href.includes('facebook.com')) {
            results.push({href: href.substring(0, 100), text: text.substring(0, 30)});
        }
    });
    return results;
}""")

print(f"\nLinks on About page: {len(links)}")
for l in links[:20]:
    print(f"  href={l['href']}")
    print(f"  text={l['text']}")

# Check for message button
msg_buttons = page.evaluate("""() => {
    const results = [];
    document.querySelectorAll('a, button').forEach(el => {
        const text = (el.textContent || '').trim();
        const href = el.getAttribute('href') || '';
        const aria = el.getAttribute('aria-label') || '';
        if (text.includes('訊息') || text.includes('Message') || text.includes('私訊') || 
            text.includes('Send') || aria.includes('Message') || aria.includes('Message')) {
            results.push({
                type: el.tagName,
                text: text.substring(0, 50),
                href: href.substring(0, 80),
                aria: aria.substring(0, 50)
            });
        }
    });
    return results;
}""")

print(f"\nMessage buttons: {len(msg_buttons)}")
for m in msg_buttons:
    print(f"  type={m['type']} text={m['text']} href={m['href']}")

# Get the about page content
about_text = page.evaluate("""() => {
    const els = document.querySelectorAll('[class*="about"], [class*="About"], h1, h2, h3');
    return Array.from(els).map(e => ({
        tag: e.tagName,
        text: (e.textContent || '').substring(0, 100),
        class: (e.className || '').substring(0, 60)
    }));
}""")

print(f"\nAbout page elements: {len(about_text)}")
for a in about_text:
    print(f"  {a['tag']}: {a['text']}")

page.screenshot(path="/tmp/fb_about.png")
print("\nScreenshot saved to /tmp/fb_about.png")

browser.close()
