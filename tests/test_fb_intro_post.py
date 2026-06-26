#!/usr/bin/env python3
"""
Test script to scrape Intro and Latest Post text from a Facebook page.
Uses the persistent profile from `./browser_profile`.
Target page: https://www.facebook.com/LYHPED/ (林永祥小兒科診所)
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
    page.screenshot(path="/tmp/fb_intro_test.png")
    
    extracted = page.evaluate("""() => {
        const results = {
            intro: '',
            posts: []
        };
        
        // 1. Try to find the Intro Card
        // Facebook's intro card usually has h2 with text "Intro" or "簡介"
        const headings = Array.from(document.querySelectorAll('h2, h3, span, div'));
        const introHeading = headings.find(el => {
            const text = (el.textContent || '').trim();
            return text === '簡介' || text === 'Intro';
        });
        
        if (introHeading) {
            // Find parent container or subsequent siblings
            let parent = introHeading.parentElement;
            // Go up a few levels to find the card container
            for (let i = 0; i < 4; i++) {
                if (parent && parent.innerText.includes('粉專') || parent.innerText.includes('診所')) {
                    break;
                }
                if (parent && parent.parentElement) {
                    parent = parent.parentElement;
                }
            }
            if (parent) {
                results.intro = parent.innerText.replace('簡介\\n', '').replace('Intro\\n', '').substring(0, 500);
            }
        }
        
        // Fallback for Intro: search for divs containing intro text
        if (!results.intro) {
            const introDiv = document.querySelector('div[class*="Intro"], div[class*="intro"]');
            if (introDiv) {
                results.intro = introDiv.innerText.substring(0, 500);
            }
        }
        
        // 2. Try to find Post Messages
        // Facebook post text containers usually have data-ad-comet-preview="message"
        const postElements = document.querySelectorAll('div[data-ad-comet-preview="message"], [data-testid="post_message"], div[dir="auto"]');
        const seenPosts = new Set();
        
        postElements.forEach(el => {
            const text = (el.textContent || '').trim();
            // Filter out short texts (like buttons, dates) and duplicates
            if (text.length > 30 && !seenPosts.has(text)) {
                // Ensure it's not the intro text
                if (!results.intro.includes(text)) {
                    seenPosts.add(text);
                    results.posts.push(text.substring(0, 800));
                }
            }
        });
        
        return results;
    }""")
    
    print("\n📝 提取結果:")
    print("-" * 50)
    print(f"【簡介 (Intro)】:\n{extracted['intro'] or '❌ 未找到簡介'}")
    print("-" * 50)
    print(f"【最新貼文 (Latest Posts)】(共 {len(extracted['posts'])} 則):")
    for i, post in enumerate(extracted['posts'][:2]):
        print(f"  [貼文 {i+1}]:\n{post}")
        print("  " + "~" * 30)
    print("-" * 50)

def main():
    print("🚀 啟動 CloakBrowser...")
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
