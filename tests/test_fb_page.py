#!/usr/bin/env python3
"""Test CloakBrowser - browse a Facebook page and find post area."""
from cloakbrowser import launch
import time

browser = launch(headless=True)
page = browser.new_page()

# Open the found Facebook page
fb_url = "https://www.facebook.com/liu27603922/"
print(f"Opening: {fb_url}")

page.goto(fb_url)
time.sleep(5)

print(f"Title: {page.title()}")
print(f"Page length: {len(page.content())} chars")

# Screenshot for visual check
page.screenshot(path="/tmp/test_fb_page.png")
print("Screenshot saved to /tmp/test_fb_page.png")

# Find textarea elements
textareas = page.evaluate("""() => {
    const results = [];
    document.querySelectorAll('textarea').forEach(el => {
        const placeholder = el.getAttribute('placeholder') || '';
        const ariaLabel = el.getAttribute('aria-label') || '';
        const name = el.getAttribute('name') || '';
        results.push({
            placeholder: placeholder.substring(0, 100),
            aria_label: ariaLabel.substring(0, 100),
            name: name.substring(0, 100),
            visible: el.evaluate('el => el.offsetParent !== null')
        });
    });
    return results;
}""")

print(f"\nFound {len(textareas)} textarea elements:")
for i, ta in enumerate(textareas):
    print(f"  [{i}] placeholder={ta['placeholder']}, aria-label={ta['aria_label']}, name={ta['name']}, visible={ta['visible']}")

# Find buttons
buttons = page.evaluate("""() => {
    const results = [];
    document.querySelectorAll('button').forEach(el => {
        const text = el.textContent?.substring(0, 50) || '';
        const ariaLabel = el.getAttribute('aria-label') || '';
        if (text.includes('寫') || text.includes('post') || text.includes('Publish') || text.includes('分享')) {
            results.push({text: text, aria_label: ariaLabel});
        }
    });
    return results;
}""")

print(f"\nFound {len(buttons)} publish/post buttons:")
for b in buttons:
    print(f"  text={b['text']}, aria-label={b['aria_label']}")

browser.close()
