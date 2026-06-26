#!/usr/bin/env python3
"""測試 Google Maps 登入後寫評論流程。"""
from cloakbrowser import launch
import time

browser = launch(
    headless=False, 
    humanize=True, 
    timezone="Asia/Taipei", 
    locale="zh-TW"
)
page = browser.new_page()

# Step 1: Go to Google and sign in
print("🔐 登入 Google 帳號...")
page.goto("https://accounts.google.com/SignUp")
time.sleep(3)

# Fill email
email_input = page.query_selector("input[type='email'], input[name='email'], input[name='identifier']")
if email_input:
    email_input.type("hsuyungfeng0409@gmail.com")
    time.sleep(2)
    # Click next
    next_btn = page.query_selector("button[type='submit'], input[type='submit']")
    if next_btn:
        next_btn.click()
    time.sleep(3)
    
    # Fill password
    pw_input = page.query_selector("input[type='password']")
    if pw_input:
        pw_input.type("chicken12345")
        time.sleep(2)
        pw_btn = page.query_selector("button[type='submit'], input[type='submit']")
        if pw_btn:
            pw_btn.click()
        time.sleep(5)

print(f"URL: {page.url}")
print(f"Title: {page.title()}")

# Step 2: Navigate to Google Maps and search for clinic
print("\n🗺️ 搜尋診所...")
page.goto("https://www.google.com/maps/search/榮恩耳鼻喉科小兒科聯合診所 臺北市松山區南京東路5段258號/")
time.sleep(5)

print(f"Maps URL: {page.url}")
print(f"Maps Title: {page.title()}")

# Step 3: Click 撰寫評論
print("\n📝 點擊撰寫評論...")
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

print(f"After click URL: {page.url}")

# Step 4: Check review dialog
print("\n🔍 檢查評論對話框...")
review_info = page.evaluate("""() => {
    const results = {
        dialogs: 0,
        textareas: [],
        stars: [],
        submit_btns: [],
        page_text: ''
    };
    
    results.dialogs = document.querySelectorAll('[role="dialog"], [role="alertdialog"]').length;
    
    // Get all textareas
    document.querySelectorAll('textarea').forEach(ta => {
        results.textareas.push({
            placeholder: ta.placeholder || '',
            aria_label: ta.getAttribute('aria-label') || '',
            rows: ta.rows || 0
        });
    });
    
    // Get star rating elements
    document.querySelectorAll('[role="radio"]').forEach(star => {
        results.stars.push({
            aria_label: star.getAttribute('aria-label') || '',
            role: star.getAttribute('role') || '',
            text: (star.textContent || '').substring(0, 20),
            class: (star.className || '').substring(0, 50)
        });
    });
    
    // Get submit buttons
    document.querySelectorAll('button').forEach(btn => {
        const text = (btn.textContent || '').trim();
        if (text.includes('送出') || text.includes('Submit') || text.includes('Send')) {
            results.submit_btns.push({text: text, aria: btn.getAttribute('aria-label') || ''});
        }
    });
    
    results.page_text = document.body.innerText.substring(0, 500);
    
    return results;
}""")

import json
print(json.dumps(review_info, ensure_ascii=False, indent=2))

# Step 5: Try to enter text
if review_info['textareas']:
    print(f"\n✅ 找到 {len(review_info['textareas'])} 個文字輸入框")
    comment = "您好！🩺 醫師工具箱 — AI 語音記錄自動轉 SOAP 病歷。支援 LINE 病史整合、OA 自動回覆。任何 HIS 系統都能橋接，不須更換。徐永峰醫師監製。免費體驗：https://doctor-toolbox.com/ai-soap-generator"
    
    page.evaluate("""() => {
        const textareas = document.querySelectorAll('textarea');
        for (const ta of textareas) {
            const ph = ta.placeholder || '';
            const aria = ta.getAttribute('aria-label') || '';
            if (ph.includes('評論') || ph.includes('review') || aria.includes('評論') || aria.includes('review')) {
                ta.click();
                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                nativeInputValueSetter.call(ta, """ + '"' + comment + '"' + """');
                ta.dispatchEvent(new Event('input', { bubbles: true }));
                break;
            }
        }
    }""")
    time.sleep(2)
    
    # Check submitted text
    submitted = page.evaluate("""() => {
        const textareas = document.querySelectorAll('textarea');
        for (const ta of textareas) {
            return ta.value;
        }
        return '';
    }""")
    print(f"文字填入: {len(submitted)} chars")
    
    # Click submit
    if review_info['submit_btns']:
        print(f"\n🚀 找到 {len(review_info['submit_btns'])} 個送出按鈕，點擊中...")
        page.evaluate("""() => {
            const btns = document.querySelectorAll('button');
            for (const btn of btns) {
                const text = (btn.textContent || '').trim();
                if (text.includes('送出') || text.includes('Submit')) {
                    btn.click();
                    break;
                }
            }
        }""")
        time.sleep(5)
        print(f"送出後 URL: {page.url}")
        
        posted = page.evaluate("""() => {
            const body = document.body.innerText;
            return body.includes('評論已發布') || body.includes('Review posted') || body.includes('Thank you') || body.includes('留言已發布');
        }""")
        print(f"評論已發布: {posted}")
    else:
        print("⚠️ 沒有找到送出按鈕")
else:
    print("❌ 沒有找到文字輸入框")
    
    # Screenshot
    page.screenshot(path="/tmp/gm_review.png")
    print("截圖已儲存到 /tmp/gm_review.png")

# Screenshot for debugging
page.screenshot(path="/tmp/gm_review2.png")
print("截圖已儲存到 /tmp/gm_review2.png")

browser.close()
