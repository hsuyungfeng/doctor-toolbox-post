#!/usr/bin/env python3
"""
測試 Google Maps 留言流程
"""
from cloakbrowser import launch
import time

browser = launch(headless=False, humanize=True, timezone="Asia/Taipei", locale="zh-TW")
page = browser.new_page()

# 搜尋診所
query = "榮恩耳鼻喉科小兒科聯合診所 臺北市松山區南京東路5段258號"
print(f"🔍 搜尋: {query}")
page.goto(f"https://www.google.com/maps/search/{query}/")
time.sleep(6)

# 點擊撰寫評論
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

# 檢查當前頁面狀態
state = page.evaluate("""() => {
    return {
        url: window.location.href,
        text_preview: document.body.innerText.substring(0, 500),
        all_buttons: Array.from(document.querySelectorAll('button')).map(b => ({
            text: (b.textContent || '').substring(0, 30),
            aria: (b.getAttribute('aria-label') || '').substring(0, 30)
        })).slice(0, 20),
        all_inputs: Array.from(document.querySelectorAll('input, textarea')).map(el => ({
            tag: el.tagName,
            type: el.type || '',
            placeholder: (el.placeholder || '').substring(0, 50),
            aria: (el.getAttribute('aria-label') || '').substring(0, 50)
        }))
    };
}""")

import json
print(json.dumps(state, ensure_ascii=False, indent=2))

page.screenshot(path="/tmp/gm_review_test.png")
print("截圖: /tmp/gm_review_test.png")

input("\n按 Enter 關閉瀏覽器")
browser.close()
