#!/usr/bin/env python3
"""
Diagnostic script to find HTML structure of FB intro and posts.
"""
import time
import sys
from pathlib import Path
from cloakbrowser import launch_persistent_context

WORKSPACE_DIR = Path(__file__).resolve().parent
PROFILE_DIR = WORKSPACE_DIR.parent / "browser_profile"

TARGET_URL = "https://www.facebook.com/LYHPED/"

def test_extract(page, url):
    print(f"🔵 導航至粉專: {url}")
    page.goto(url)
    time.sleep(6)
    
    extracted = page.evaluate("""() => {
        const results = {
            h1_text: '',
            h1_parent_text: '',
            h1_siblings: [],
            possible_intros: [],
            dir_auto_texts: []
        };
        
        const h1 = document.querySelector('h1');
        if (h1) {
            results.h1_text = h1.innerText;
            if (h1.parentElement) {
                results.h1_parent_text = h1.parentElement.innerText;
                Array.from(h1.parentElement.querySelectorAll('span, div')).forEach(el => {
                    if (el.innerText && el.innerText.length > 10 && el.innerText.length < 200) {
                        results.h1_siblings.push({tag: el.tagName, text: el.innerText});
                    }
                });
            }
        }
        
        // Find possible intro text in the left column (usually under "詳細資料" / "Details")
        // Facebook's Details card texts
        const details = Array.from(document.querySelectorAll('span, div'));
        details.forEach(el => {
            const text = (el.textContent || '').trim();
            // Intro text often contains "位於" (located at) or "守護" (protect) or general descriptions
            if (text.length > 15 && text.length < 300 && (text.includes('診所') || text.includes('位於') || text.includes('守護') || text.includes('醫師'))) {
                if (!results.possible_intros.includes(text)) {
                    results.possible_intros.push(text);
                }
            }
        });
        
        // Find div[dir="auto"] texts
        document.querySelectorAll('div[dir="auto"]').forEach(el => {
            const text = (el.textContent || '').trim();
            if (text.length > 5 && text.length < 500) {
                results.dir_auto_texts.push(text);
            }
        });
        
        return results;
    }""")
    
    print("\n📝 h1 Siblings:")
    for s in extracted['h1_siblings'][:10]:
        print(f"  [{s['tag']}]: {s['text']}")
        
    print("\n📝 Possible Intro Texts:")
    for intro in extracted['possible_intros'][:5]:
        print(f"  - {intro}")
        
    print("\n📝 dir='auto' Texts (top 15):")
    for text in extracted['dir_auto_texts'][:15]:
        print(f"  - {text}")

def main():
    try:
        context = launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            humanize=True,
            timezone="Asia/Taipei",
            locale="zh-TW"
        )
    except Exception as e:
        print(f"❌ 瀏覽器啟動失敗: {e}")
        sys.exit(1)
        
    page = context.pages[0] if context.pages else context.new_page()
    
    try:
        test_extract(page, TARGET_URL)
    except Exception as e:
        print(f"❌ 執行出錯: {e}")
        
    context.close()

if __name__ == "__main__":
    main()
