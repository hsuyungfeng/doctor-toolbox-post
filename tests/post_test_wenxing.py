#!/usr/bin/env python3
"""
Test posting a single clinic promotional comment on FB and Google Maps.
Uses the persistent profile from `./browser_profile`.
Target: 文星外科診所 (臺中市南區文心南路９５１號１樓)
"""
import time
import os
import sys
from pathlib import Path
from cloakbrowser import launch_persistent_context

# Config
WORKSPACE_DIR = Path(__file__).resolve().parent
PROFILE_DIR = WORKSPACE_DIR.parent / "browser_profile"

FB_COMMENT = """🩺 看診對話，自動變成 SOAP 病歷！

醫師工具箱幫您：
🎙️ 語音即時記錄 → AI 轉 SOAP 病歷
📱 LINE 病史整合
🤖 LINE OA 自動回覆
💰 LINE + Voice Record 每月各 1000 人次，只要 1000 元

任何 HIS 都能橋接，不須更換 📋
👉 https://doctor-toolbox.com/ai-soap-generator
徐永峰醫師監製 · 品質保證"""

MAPS_COMMENT = """您好！🩺 醫師工具箱 — AI 語音記錄自動轉 SOAP 病歷。支援 LINE 病史整合、OA 自動回覆。任何 HIS 系統都能橋接，不須更換。徐永峰醫師監製。免費體驗：https://doctor-toolbox.com/ai-soap-generator"""

CLINIC_NAME = "文星外科診所"
CLINIC_ADDRESS = "臺中市南區文心南路９５１號１樓"

def search_clinic_facebook(page, clinic_name):
    search_query = f"{clinic_name} site:facebook.com"
    print(f"  🔍 FB 搜尋: {search_query}")
    try:
        page.goto(f"https://www.google.com/search?q={search_query}&hl=zh-TW&num=10")
        time.sleep(5)
        page.screenshot(path="/tmp/wenxing_fb_search_results.png")
        
        # Extract Facebook links
        links = page.evaluate("""() => {
            const results = [];
            const seen = new Set();
            document.querySelectorAll('a').forEach(a => {
                const href = a.getAttribute('href') || '';
                if (href.includes('facebook.com') && !href.includes('google.com') && !href.includes('apps.facebook.com')) {
                    let url = href;
                    if (url.includes('/url?q=')) {
                        url = url.split('/url?q=')[1].split('&')[0];
                    }
                    // Clean up URL
                    try {
                        const parsed = new URL(url);
                        // We want pages or profiles
                        if (parsed.pathname.length > 1) {
                            const cleanUrl = parsed.origin + parsed.pathname;
                            if (!seen.has(cleanUrl)) {
                                seen.add(cleanUrl);
                                results.push(cleanUrl);
                            }
                        }
                    } catch(e) {}
                }
            });
            return results;
        }""")
        
        for link in links:
            print(f"  ✅ 搜尋到 FB 網址: {link}")
            return link
            
        print("  ❌ 未在 Google 搜尋到 Facebook 專頁")
        return None
    except Exception as e:
        print(f"  ❌ FB 搜尋出錯: {e}")
        return None

def search_clinic_google_maps(page, clinic_name, address):
    query = f"{clinic_name} {address}"
    print(f"  🔍 Google Maps 搜尋: {query}")
    try:
        page.goto(f"https://www.google.com/maps/search/{query}/")
        time.sleep(6)
        page.screenshot(path="/tmp/wenxing_maps_search_results.png")
        
        current_url = page.url
        print(f"  Maps 導向 URL: {current_url}")
        return current_url
    except Exception as e:
        print(f"  ❌ Maps 搜尋出錯: {e}")
        return None

def test_facebook(page, fb_url):
    print(f"\n🔵 Facebook 測試開始: {fb_url}")
    page.goto(fb_url)
    time.sleep(6)
    
    title = page.title()
    print(f"  頁面標題: {title}")
    page.screenshot(path="/tmp/wenxing_fb_loaded.png")
    
    has_no_posts = page.evaluate("""() => {
        return document.body.innerText.includes('沒有可顯示的貼文') || document.body.innerText.includes('No posts available');
    }""")
    if has_no_posts:
        print("  ⚠️ 此臉書專頁目前沒有任何貼文，無法進行留言測試！")
        return False
        
    print("  🔍 尋找留言輸入框...")
    
    clicked_comment_btn = page.evaluate("""() => {
        const elements = Array.from(document.querySelectorAll('div, span, [role="button"], button, a'));
        for (const el of elements) {
            const text = (el.textContent || '').trim();
            const ariaLabel = el.getAttribute('aria-label') || '';
            if ((text === '留言' || text === 'Comment' || ariaLabel.includes('留言') || ariaLabel.includes('Comment')) && el.offsetHeight > 0) {
                el.click();
                return true;
            }
        }
        return false;
    }""")
    
    if clicked_comment_btn:
        print("  ✅ 已點擊「留言」按鈕")
        time.sleep(3)
        page.screenshot(path="/tmp/wenxing_fb_after_click_comment.png")
    else:
        print("  ⚠️ 未找到或未點擊「留言」按鈕，直接尋找輸入框...")

    text_inserted = page.evaluate("""(commentText) => {
        const tb = document.querySelector('div[contenteditable="true"], [role="textbox"]');
        if (tb) {
            tb.focus();
            tb.click();
            document.execCommand('selectAll', false, null);
            document.execCommand('delete', false, null);
            document.execCommand('insertText', false, commentText);
            return true;
        }
        return false;
    }""", FB_COMMENT)
    
    if text_inserted:
        print("  ✅ 成功聚焦並填入完整留言內容")
        time.sleep(2)
        page.screenshot(path="/tmp/wenxing_fb_typed.png")
        
        print("  🚀 按下 Enter 送出留言...")
        page.keyboard.press("Enter")
        time.sleep(5)
        
        page.screenshot(path="/tmp/wenxing_fb_submitted.png")
        print("  ✅ FB 留言已送出，請檢查截圖 /tmp/wenxing_fb_submitted.png 或臉書頁面確認！")
        return True
    else:
        print("  ❌ 找不到留言輸入框")
        return False

def test_google_maps(page, maps_url):
    print(f"\n🔴 Google Maps 測試開始: {maps_url}")
    page.goto(maps_url)
    time.sleep(6)
    
    print(f"  頁面標題: {page.title()}")
    page.screenshot(path="/tmp/wenxing_maps_loaded.png")
    
    # Check if user is owner/manager
    is_owner = page.evaluate("""() => {
        const text = document.body.innerText;
        return text.includes('管理你的商家檔案') || text.includes('Manage your Business Profile') || text.includes('管理商家檔案');
    }""")
    if is_owner:
        print("  ⚠️ 偵測到您是此商家檔案的擁有者/管理者。Google Maps 不允許擁有者對自己的商家撰寫評論，因此無法進行評分與評論填寫測試。")
        return "owner_profile"

    print("  🔍 尋找「撰寫評論」按鈕...")
    has_btn = page.evaluate("""() => {
        const btns = document.querySelectorAll('button');
        for (const btn of btns) {
            const text = (btn.textContent || '').trim();
            if (text.includes('撰寫評論') || text.includes('Write a review')) {
                btn.click();
                return true;
            }
        }
        return false;
    }""")
    
    if not has_btn:
        print("  ❌ 未找到「撰寫評論」按鈕")
        return False
        
    print("  ✅ 已點擊「撰寫評論」按鈕，等待對話框載入...")
    time.sleep(6)
    page.screenshot(path="/tmp/wenxing_maps_active_dialog.png")
    
    # Click 5th star using robust JS pointer/mouse events targeted inside the VISIBLE review dialog modal
    print("  ⭐ 評分 5 顆星 (JS Event level)...")
    star_clicked = page.evaluate("""() => {
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
        
        // Find the active review dialog container by searching for visible dialogs containing "張貼" or "取消" buttons
        const dialogs = Array.from(document.querySelectorAll('[role="dialog"], [role="alertdialog"], div.vzFwxb, div'));
        const activeDialog = dialogs.find(d => {
            const style = window.getComputedStyle(d);
            const isVisible = style.display !== 'none' && style.visibility !== 'hidden' && d.offsetHeight > 50 && d.offsetWidth > 100;
            if (!isVisible) return false;
            
            const text = d.textContent || '';
            return text.includes('張貼') || text.includes('取消') || text.includes('Publish') || text.includes('Cancel');
        }) || document.body;
        
        const stars = deepQueryAll(activeDialog, '[role="radio"]');
        if (stars && stars.length >= 5) {
            const star = stars[4]; // Click the 5th star
            star.focus();
            
            star.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }));
            star.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
            star.dispatchEvent(new PointerEvent('pointerup', { bubbles: true }));
            star.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
            star.click();
            star.dispatchEvent(new Event('change', { bubbles: true }));
            return true;
        }
        return false;
    }""")
    
    if not star_clicked:
        print("  ❌ 未能成功點擊 5 星評分 (可能對話框未正確開啟)")
        return False
        
    print("  ✅ 已點擊 5 星")
    time.sleep(3)
    page.screenshot(path="/tmp/wenxing_maps_star_clicked.png")
    
    # Enter review text inside the active dialog
    print("  📝 輸入評論內容...")
    text_filled = page.evaluate("""(commentText) => {
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
        
        const dialogs = Array.from(document.querySelectorAll('[role="dialog"], [role="alertdialog"], div'));
        const activeDialog = dialogs.find(d => {
            const style = window.getComputedStyle(d);
            const isVisible = style.display !== 'none' && d.offsetHeight > 50 && d.offsetWidth > 100;
            if (!isVisible) return false;
            const text = d.textContent || '';
            return text.includes('張貼') || text.includes('取消') || text.includes('Publish') || text.includes('Cancel');
        }) || document.body;
        
        const ta = deepQueryAll(activeDialog, 'textarea, [contenteditable="true"]')[0];
        if (ta) {
            ta.click();
            ta.focus();
            document.execCommand('selectAll', false, null);
            document.execCommand('delete', false, null);
            document.execCommand('insertText', false, commentText);
            
            if (!ta.value && ta.tagName === 'TEXTAREA') {
                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                    window.HTMLTextAreaElement.prototype,
                    'value'
                );
                if (nativeInputValueSetter && nativeInputValueSetter.set) {
                    nativeInputValueSetter.set.call(ta, commentText);
                } else {
                    ta.value = commentText;
                }
                ta.dispatchEvent(new Event('input', { bubbles: true }));
            }
            return true;
        }
        return false;
    }""", MAPS_COMMENT)
    
    if not text_filled:
        print("  ❌ 未能填寫評論框")
        return False

    print("  ✅ 已填入評論文字")
    time.sleep(2)
    page.screenshot(path="/tmp/wenxing_maps_typed.png")
    
    # Submit review
    print("  🚀 點擊「送出」...")
    submit_clicked = page.evaluate("""() => {
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
        
        const dialogs = Array.from(document.querySelectorAll('[role="dialog"], [role="alertdialog"], div'));
        const activeDialog = dialogs.find(d => {
            const style = window.getComputedStyle(d);
            const isVisible = style.display !== 'none' && d.offsetHeight > 50 && d.offsetWidth > 100;
            if (!isVisible) return false;
            const text = d.textContent || '';
            return text.includes('張貼') || text.includes('取消') || text.includes('Publish') || text.includes('Cancel');
        }) || document.body;
        
        const btns = deepQueryAll(activeDialog, 'button');
        for (const btn of btns) {
            const text = (btn.textContent || '').trim();
            if (text.includes('送出') || text.includes('張貼') || text.includes('Publish') || text.includes('Submit')) {
                btn.click();
                return true;
            }
        }
        return false;
    }""")
    
    if submit_clicked:
        print("  ✅ 已點擊送出按鈕！等待提交...")
        time.sleep(5)
        page.screenshot(path="/tmp/wenxing_maps_submitted.png")
        print("  ✅ Maps 評論已送出，請檢查截圖 /tmp/wenxing_maps_submitted.png 確認！")
        return True
    else:
        print("  ❌ 未找到「送出」按鈕")
        return False

def main():
    print("=" * 60)
    print("醫師工具箱 - 貼文測試腳本 (文星外科診所)")
    print("=" * 60)
    
    print(f"🚀 載入 Session Profile: {PROFILE_DIR}")
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
    
    fb_success = False
    maps_success = False
    
    # Step 1: Search URLs
    print("\n🔍 搜尋診所網頁...")
    fb_url = search_clinic_facebook(page, CLINIC_NAME)
    maps_url = search_clinic_google_maps(page, CLINIC_NAME, CLINIC_ADDRESS)
    
    # Step 2: Test Facebook
    if fb_url:
        try:
            fb_success = test_facebook(page, fb_url)
        except Exception as e:
            print(f"  ❌ FB 測試異常: {e}")
    else:
        print("  ❌ 未找到 Facebook 網址，跳過測試")
        
    # Step 3: Test Maps
    if maps_url:
        try:
            maps_success = test_google_maps(page, maps_url)
        except Exception as e:
            print(f"  ❌ Maps 測試異常: {e}")
    else:
        print("  ❌ 未找到 Google Maps 網址，跳過測試")
        
    context.close()
    
    print("\n" + "=" * 60)
    print("📊 測試結果摘要:")
    print(f"  - Facebook 貼文: {'🟢 成功' if fb_success else '🔴 失敗'}")
    
    if maps_success == "owner_profile":
        print(f"  - Google Maps 評論: ⚠️ 商家擁有者（無法撰寫評論）")
    else:
        print(f"  - Google Maps 評論: {'🟢 成功' if maps_success else '🔴 失敗'}")
    print("=" * 60)

if __name__ == "__main__":
    main()
