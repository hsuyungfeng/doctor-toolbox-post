#!/usr/bin/env python3
"""
Test leaf node based extraction logic for FB page intro.
"""
import time
import sys
from pathlib import Path
from cloakbrowser import launch_persistent_context

WORKSPACE_DIR = Path(__file__).resolve().parent
PROFILE_DIR = WORKSPACE_DIR.parent / "browser_profile"

TARGET_URL = "https://www.facebook.com/LYHPED/"
CLINIC_NAME = "林永祥小兒科診所"

def test_extract(page, url, clinic_name):
    print(f"🔵 導航至粉專: {url}")
    page.goto(url)
    time.sleep(6)
    
    extracted = page.evaluate("""(clinicName) => {
        const results = {
            intro: '',
            posts: []
        };
        
        // 1. Scan leaf nodes for Intro
        const elements = Array.from(document.querySelectorAll('span, div'));
        const cleanName = clinicName.replace('診所', '');
        
        for (const el of elements) {
            // Only look at leaf elements (or elements without other element children) to get clean text
            if (el.children.length === 0) {
                const text = (el.textContent || '').trim();
                if (text.length > 10 && text.length < 200) {
                    if ((text.includes(cleanName) || text.includes('診所') || text.includes('位於') || text.includes('守護') || text.includes('服務') || text.includes('照護') || text.includes('醫師')) &&
                        !text.includes('追蹤') && !text.includes('發送訊息') && !text.includes('讚') &&
                        !text.includes('首頁') && !text.includes('關於') && !text.includes('相片') &&
                        !text.includes('分享') && !text.includes('影片') && text !== clinicName) {
                        results.intro = text;
                        break;
                    }
                }
            }
        }
        
        // 2. Extract Latest Posts
        const dirAutos = Array.from(document.querySelectorAll('div[dir="auto"]'));
        const skipWords = ['讚', '留言', '分享', '追蹤', '發送訊息', '追蹤中', '點讚', '回應'];
        
        for (const el of dirAutos) {
            const text = (el.textContent || '').trim();
            if (text.length >= 8 && text.length < 1000) {
                const isMeta = skipWords.some(word => text === word || text.includes(word) && text.length < 15);
                if (!isMeta && text !== results.intro && !results.posts.includes(text)) {
                    results.posts.push(text);
                }
            }
        }
        
        return results;
    }""", clinic_name)
    
    print("\n📝 提取結果:")
    print("-" * 50)
    print(f"【簡介 (Intro)】:\n{extracted['intro'] or '❌ 未找到簡介'}")
    print("-" * 50)
    print(f"【最新貼文 (Latest Posts)】(共 {len(extracted['posts'])} 則):")
    for i, post in enumerate(extracted['posts'][:3]):
        print(f"  [貼文 {i+1}]:\n{post}")
        print("  " + "~" * 30)
    print("-" * 50)

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
        test_extract(page, TARGET_URL, CLINIC_NAME)
    except Exception as e:
        print(f"❌ 執行出錯: {e}")
        
    context.close()

if __name__ == "__main__":
    main()
