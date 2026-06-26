#!/usr/bin/env python3
"""Test: full Google Maps review flow."""
from cloakbrowser import launch
import time
import csv
import json
from datetime import datetime
from pathlib import Path

CSV_PATH = "/home/hsuyungfeng/文件/doctor-toolbox-post/clinics西醫.csv"
LOG_PATH = "/home/hsuyungfeng/文件/doctor-toolbox-post/post_log.jsonl"

FB_COMMENT = """您好！🩺 醫師工具箱 — AI 語音記錄自動轉 SOAP 病歷。支援 LINE 病史整合、OA 自動回覆。任何 HIS 系統都能橋接，不須更換。徐永峰醫師監製。免費體驗：https://doctor-toolbox.com/ai-soap-generator"""

# Read first clinic
with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    header = next(reader)
    idx_map = {h: i for i, h in enumerate(header)}
    row = next(reader)
    name = row[idx_map['醫事機構名稱']].strip()
    address = row[idx_map['地址']].strip()
    print(f"Testing for: {name}")
    print(f"Address: {address}")

browser = launch(headless=False, humanize=True, timezone="Asia/Taipei", locale="zh-TW")
page = browser.new_page()

# Step 1: Search Google Maps
query = f"{name} {address}"
print(f"\n🔍 Searching: {query}")
page.goto(f"https://www.google.com/maps/search/{query}/")
time.sleep(5)

print(f"URL: {page.url}")
print(f"Title: {page.title()}")

# Step 2: Find and click "Write a review" button
review_btn = page.evaluate("""() => {
    const btns = document.querySelectorAll('button');
    for (const btn of btns) {
        if ((btn.textContent || '').includes('撰寫評論')) {
            return btn;
        }
    }
    return null;
}""")

if review_btn:
    print("\n✅ Found '撰寫評論' button, clicking...")
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
    
    print(f"URL after click: {page.url}")
    print(f"Title: {page.title()}")
    
    # Look for review input
    review_area = page.evaluate("""() => {
        const results = {};
        
        // Find textarea or input for review
        const textareas = document.querySelectorAll('textarea, [contenteditable], input[type="text"]');
        for (const ta of textareas) {
            const ph = ta.getAttribute('placeholder') || '';
            const aria = ta.getAttribute('aria-label') || '';
            const name = ta.getAttribute('name') || '';
            if (ph.includes('評論') || ph.includes('review') || aria.includes('評論') || aria.includes('review')) {
                results.input = {
                    tag: ta.tagName,
                    placeholder: ph,
                    aria_label: aria,
                    name: name,
                    id: ta.id || ''
                };
            }
        }
        
        // Find star rating
        const stars = document.querySelectorAll('[role="radio"], [data-testid*="star"], [data-testid*="rating"]');
        results.stars = [];
        for (const star of stars) {
            results.stars.push({
                role: star.getAttribute('role'),
                testid: star.getAttribute('data-testid') || '',
                aria: star.getAttribute('aria-label') || '',
                text: (star.textContent || '').substring(0, 30)
            });
        }
        
        // Find submit button
        const submit_btns = document.querySelectorAll('button');
        for (const btn of submit_btns) {
            const text = (btn.textContent || '').trim();
            if (text.includes('送出') || text.includes('Submit') || text.includes('Send')) {
                results.submit = {text: text, aria: (btn.getAttribute('aria-label') || '')};
            }
        }
        
        // Also check for modal/dialog
        const dialogs = document.querySelectorAll('[role="dialog"], [role="alertdialog"]');
        results.dialogs = dialogs.length;
        
        return results;
    }""")
    
    print(f"\nReview area: {json.dumps(review_area, ensure_ascii=False, indent=2)}")
    
    # If there's a textarea, type the comment
    if review_area.get('input'):
        print(f"\n📝 Found review input: {review_area['input']}")
        
        # Click the input to focus
        page.evaluate("""() => {
            const textareas = document.querySelectorAll('textarea');
            for (const ta of textareas) {
                const ph = ta.getAttribute('placeholder') || '';
                const aria = ta.getAttribute('aria-label') || '';
                if (ph.includes('評論') || ph.includes('review') || aria.includes('評論') || aria.includes('review')) {
                    ta.click();
                    ta.focus();
                    // Try typing directly
                    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    nativeInputValueSetter.call(ta, '${FB_COMMENT.replace("'", "\\'")}');
                    ta.dispatchEvent(new Event('input', { bubbles: true }));
                }
            }
        }""")
        
        time.sleep(2)
        
        # Check if text was entered
        text_value = page.evaluate("""() => {
            const textareas = document.querySelectorAll('textarea');
            for (const ta of textareas) {
                const ph = ta.getAttribute('placeholder') || '';
                const aria = ta.getAttribute('aria-label') || '';
                if (ph.includes('評論') || ph.includes('review') || aria.includes('評論') || aria.includes('review')) {
                    return ta.value;
                }
            }
            return '';
        }""")
        
        print(f"Text entered: {text_value[:100]}")
        
        # Find submit button
        submit_btn = page.evaluate("""() => {
            const btns = document.querySelectorAll('button');
            for (const btn of btns) {
                const text = (btn.textContent || '').trim();
                if (text.includes('送出') || text.includes('Submit')) {
                    return btn;
                }
            }
            return null;
        }""")
        
        if submit_btn:
            print("\n🚀 Found submit button, clicking...")
            submit_btn.click()
            time.sleep(5)
            print(f"URL after submit: {page.url}")
            
            # Check if review was posted
            posted = page.evaluate("""() => {
                const body = document.body.innerText;
                return body.includes('評論已發布') || body.includes('Review posted') || body.includes('Thank you');
            }""")
            print(f"Review posted: {posted}")
        else:
            print("\n⚠️ No submit button found")
            page.screenshot(path="/tmp/maps_review.png")
            print("Screenshot saved to /tmp/maps_review.png")
    else:
        print("\n⚠️ No review input found")
        page.screenshot(path="/tmp/maps_review2.png")
        print("Screenshot saved to /tmp/maps_review2.png")
else:
    print("\n❌ No '撰寫評論' button found")
    page.screenshot(path="/tmp/maps_no_review.png")
    print("Screenshot saved to /tmp/maps_no_review.png")

browser.close()
print("\nTest complete!")
