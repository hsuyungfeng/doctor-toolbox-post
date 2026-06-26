#!/usr/bin/env python3
"""
Diagnostic script to inspect Google Maps Review popup window DOM.
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
    
    # Resolve the popup review page
    pages = context.pages
    print(f"總分頁數: {len(pages)}")
    review_page = page
    for p in pages:
        if "maps/reviews" in p.url or "google.com/maps" in p.url and p != page:
            review_page = p
            break
            
    print(f"切換到評論分頁: {review_page.url[:80]}...")
    
    # Run diagnostic queries on the popup page DOM/Shadow DOM
    dom_info = review_page.evaluate("""() => {
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
        
        const deepFindText = (root, substring) => {
            const list = [];
            const traverse = (node) => {
                if (!node) return;
                if (node.nodeType === Node.ELEMENT_NODE) {
                    for (const child of Array.from(node.childNodes)) {
                        if (child.nodeType === Node.TEXT_NODE && child.textContent.includes(substring)) {
                            list.push({
                                tagName: node.tagName,
                                text: child.textContent.trim(),
                                className: node.className,
                                parentTagName: node.parentElement ? node.parentElement.tagName : ''
                            });
                        }
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

        const all_radios = deepQueryAll(document.body, '[role="radio"]');
        const all_textareas = deepQueryAll(document.body, 'textarea, [contenteditable="true"]');
        const all_buttons = deepQueryAll(document.body, 'button');

        return {
            title: document.title,
            url: window.location.href,
            radios: all_radios.map(el => ({
                tagName: el.tagName,
                ariaLabel: el.getAttribute('aria-label') || '',
                id: el.id || '',
                className: el.className || ''
            })),
            textareas: all_textareas.map(el => ({
                tagName: el.tagName,
                placeholder: el.placeholder || el.getAttribute('placeholder') || '',
                ariaLabel: el.getAttribute('aria-label') || '',
                className: el.className || ''
            })),
            buttons: all_buttons.map(el => ({
                text: (el.textContent || '').trim().substring(0, 50),
                ariaLabel: el.getAttribute('aria-label') || ''
            })),
            text_matches: deepFindText(document.body, '貼文會連同')
        };
    }""")
    
    import json
    print("\n🔍 Popup DOM Diagnostic Results:")
    print(json.dumps(dom_info, ensure_ascii=False, indent=2))
    
    context.close()

if __name__ == "__main__":
    main()
