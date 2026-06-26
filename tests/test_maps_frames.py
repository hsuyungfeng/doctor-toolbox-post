#!/usr/bin/env python3
"""
Inspect all iframe frames on Google Maps to find the review widget DOM.
"""
import time
import os
import sys
from pathlib import Path
from cloakbrowser import launch_persistent_context

WORKSPACE_DIR = Path(__file__).resolve().parent
PROFILE_DIR = WORKSPACE_DIR.parent / "browser_profile"

CLINIC_NAME = "林志聖眼科診所"
CLINIC_ADDRESS = "臺北市松山區三民路１４０號"
MAPS_URL = f"https://www.google.com/maps/search/{CLINIC_NAME}+{CLINIC_ADDRESS}/"

def main():
    print(f"🚀 載入 Session Profile: {PROFILE_DIR}")
    context = launch_persistent_context(
        user_data_dir=PROFILE_DIR,
        headless=False,
        humanize=True,
        timezone="Asia/Taipei",
        locale="zh-TW"
    )
    page = context.pages[0] if context.pages else context.new_page()
    
    print(f"導航至 Maps: {MAPS_URL}")
    page.goto(MAPS_URL)
    time.sleep(6)
    
    print("點擊撰寫評論...")
    page.evaluate("""() => {
        const btns = document.querySelectorAll('button');
        for (const btn of btns) {
            const text = (btn.textContent || '').trim();
            if (text.includes('撰寫評論') || text.includes('Write a review')) {
                btn.click();
                break;
            }
        }
    }""")
    time.sleep(6)
    
    # List all frames
    frames = page.frames
    print(f"\n🖥️ 總偵測到 {len(frames)} 個 Frame (含主頁):")
    
    for idx, frame in enumerate(frames):
        print(f"\n--- Frame [{idx}] Name: '{frame.name}' | URL: {frame.url[:120]}... ---")
        try:
            # Query inside frame context
            info = frame.evaluate("""() => {
                const deepQueryAll = (root, selector) => {
                    const list = [];
                    const traverse = (node) => {
                        if (!node) return;
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            if (node.matches(selector)) {
                                list.push(node);
                            }
                        }
                        if (node.shadowRoot) {
                            traverse(node.shadowRoot);
                        }
                        for (const child of Array.from(node.childNodes || [])) {
                            traverse(child);
                        }
                    };
                    traverse(root);
                    return list;
                };
                
                return {
                    title: document.title,
                    text_sample: document.body.innerText.substring(0, 300),
                    radios_count: deepQueryAll(document.body, '[role="radio"]').length,
                    textareas_count: deepQueryAll(document.body, 'textarea, [contenteditable="true"]').length,
                    buttons_count: deepQueryAll(document.body, 'button').length
                };
            }""")
            print(f"    標題: {info['title']}")
            print(f"    文字範例: {repr(info['text_sample'])}")
            print(f"    Radio 數量: {info['radios_count']} | Textarea 數量: {info['textareas_count']} | Button 數量: {info['buttons_count']}")
        except Exception as e:
            print(f"    ❌ 無法評估此 Frame DOM: {e}")
            
    context.close()

if __name__ == "__main__":
    main()
