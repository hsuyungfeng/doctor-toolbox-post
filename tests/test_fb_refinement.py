#!/usr/bin/env python3
"""
Test refined extraction logic for FB page intro and latest post.
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
            intro: '',
            posts: []
        };
        
        // 1. Extract Intro
        const h1 = document.querySelector('h1');
        if (h1 && h1.parentElement) {
            const spans = Array.from(h1.parentElement.querySelectorAll('span, div'));
            for (const el of spans) {
                const text = (el.textContent || '').trim();
                // Filter out metadata and title itself
                if (text.length > 12 && text.length < 250 && 
                    !text.includes('追蹤者') && !text.includes('位追蹤者') && 
                    !text.includes('正在追蹤') && !text.includes('發送訊息') && 
                    !text.includes('追蹤') && text !== h1.innerText.trim() &&
                    !text.includes('讚') && !text.includes('追蹤中') &&
                    !text.includes('評論') && !text.includes('評分')) {
                    results.intro = text;
                    break;
                }
            }
        }
        
        // 2. Extract Latest Posts
        const dirAutos = Array.from(document.querySelectorAll('div[dir="auto"]'));
        const skipWords = ['讚', '留言', '分享', '追蹤', '發送訊息', '追蹤中', '點讚', '回應'];
        
        for (const el of dirAutos) {
            const text = (el.textContent || '').trim();
            if (text.length >= 8 && text.length < 1000) {
                // Ensure it's not metadata or buttons
                const isMeta = skipWords.some(word => text === word || text.includes(word) && text.length < 15);
                // Also ignore if it is identical to the intro
                if (!isMeta && text !== results.intro && !results.posts.includes(text)) {
                    results.posts.push(text);
                }
            }
        }
        
        return results;
    }""")
    
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
        test_extract(page, TARGET_URL)
    except Exception as e:
        print(f"❌ 執行出錯: {e}")
        
    context.close()

if __name__ == "__main__":
    main()
