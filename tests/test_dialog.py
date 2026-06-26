#!/usr/bin/env python3
"""檢查未登入時點擊撰寫評論後的 dialog 內容。"""
from cloakbrowser import launch
import time

browser = launch(headless=False, humanize=True, timezone="Asia/Taipei", locale="zh-TW")
page = browser.new_page()

page.goto("https://www.google.com/maps/search/榮恩耳鼻喉科小兒科聯合診所 臺北市松山區南京東路5段258號/")
time.sleep(5)

# Click 撰寫評論
page.evaluate("""() => {
    const btns = document.querySelectorAll('button');
    for (const btn of btns) {
        if ((btn.textContent || '').includes('撰寫評論')) {
            btn.click();
            break;
        }
    }
}""")
time.sleep(5)

# Get dialog details
dialogs = page.evaluate("""() => {
    const results = [];
    document.querySelectorAll('[role="dialog"], [role="alertdialog"]').forEach(d => {
        const heading = d.querySelector('[role="heading"]');
        const headingText = heading ? heading.textContent : '';
        const text = d.textContent || '';
        
        // Find all interactive elements
        const inputs = [];
        d.querySelectorAll('input, textarea, button, [role="radio"]').forEach(el => {
            inputs.push({
                tag: el.tagName,
                type: el.type || '',
                text: (el.textContent || '').substring(0, 30),
                aria: (el.getAttribute('aria-label') || '').substring(0, 30),
                role: el.getAttribute('role') || '',
                id: el.id || ''
            });
        });
        
        // Find any text input
        const textInputs = [];
        d.querySelectorAll('input[type="text"], textarea, [contenteditable]').forEach(el => {
            textInputs.push({
                tag: el.tagName,
                type: el.type,
                placeholder: el.placeholder || '',
                aria: (el.getAttribute('aria-label') || '').substring(0, 50)
            });
        });
        
        results.push({
            role: d.getAttribute('role'),
            heading: headingText.substring(0, 100),
            text_preview: text.substring(0, 300),
            interactive_elements: inputs,
            text_inputs: textInputs
        });
    });
    return results;
}""")

import json
print(json.dumps(dialogs, ensure_ascii=False, indent=2))

# Also check for star rating elements
stars = page.evaluate("""() => {
    const results = [];
    document.querySelectorAll('[role="radio"], [data-testid]').forEach(el => {
        results.push({
            tag: el.tagName,
            role: el.getAttribute('role'),
            testid: el.getAttribute('data-testid') || '',
            text: (el.textContent || '').substring(0, 20),
            aria: (el.getAttribute('aria-label') || '').substring(0, 30),
            class: (el.className || '').substring(0, 50)
        });
    });
    return results.slice(0, 20);
}""")

print(f"\nStar elements: {len(stars)}")
for s in stars:
    print(f"  {s}")

browser.close()
