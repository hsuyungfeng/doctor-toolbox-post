#!/usr/bin/env python3
"""Test: look for message button on FB personal profile."""
from cloakbrowser import launch
import time

browser = launch(headless=False, humanize=True, timezone="Asia/Taipei", locale="zh-TW")
page = browser.new_page()

page.goto("https://www.facebook.com/liu27603922/")
time.sleep(5)

# Get ALL href attributes that aren't login-related
all_links = page.evaluate("""() => {
    const results = [];
    document.querySelectorAll('a').forEach(a => {
        const href = a.getAttribute('href') || '';
        results.push(href.substring(0, 150));
    });
    return [...new Set(results)];
}""")

print("ALL links on page:")
for l in all_links:
    print(f"  {l}")

# Check for the "About" section content
about_content = page.evaluate("""() => {
    const about_link = document.querySelector('a[href*="/about"]');
    if (about_link) {
        const parent = about_link.closest('[data-reactid], [class]');
        return {
            text: about_link.textContent || '',
            class: about_link.className || '',
            parent_class: parent?.className || ''
        };
    }
    return null;
}""")

print(f"\nAbout link info: {about_content}")

# Look for the full page HTML snippet around the name section
page_section = page.evaluate("""() => {
    const name = document.querySelector('[itemtype*="schema.org/Person"], [itemprop="name"]');
    if (name) {
        return name.outerHTML.substring(0, 500);
    }
    // Try another selector
    const els = document.querySelectorAll('h1, h2, h3');
    return Array.from(els).map(e => ({tag: e.tagName, text: e.textContent.substring(0, 100)}));
}""")

print(f"\nPage section: {page_section}")

# Get the raw HTML of the page (first 10KB)
html = page.evaluate("document.documentElement.outerHTML.substring(0, 10000)")
print(f"\nFirst 10KB of HTML:")
print(html)

page.screenshot(path="/tmp/fb_profile2.png")
print("\nScreenshot saved to /tmp/fb_profile2.png")

browser.close()
