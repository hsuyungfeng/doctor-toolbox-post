#!/usr/bin/env python3
"""
Clinic Facebook Post Pipeline v2
- Reads clinics西醫.csv
- Searches Google/FB for each clinic's Facebook page
- Searches Google Maps for clinic location
- Posts Doctor Toolbox promotional content via FB comment
- Tracks progress in post_log.jsonl
"""

import csv
import json
import time
import os
import re
from datetime import datetime
from pathlib import Path
from cloakbrowser import launch_persistent_context

# === Config ===
WORKSPACE_DIR = Path(__file__).resolve().parent
PROFILE_DIR = WORKSPACE_DIR / "browser_profile"
CSV_PATH = "/home/hsuyungfeng/文件/doctor-toolbox-post/clinics西醫.csv"
LOG_PATH = "/home/hsuyungfeng/文件/doctor-toolbox-post/post_log.jsonl"

# Facebook comment content
FB_COMMENT = """🩺 看診對話，自動變成 SOAP 病歷！

醫師工具箱幫您：
🎙️ 語音即時記錄 → AI 轉 SOAP 病歷
📱 LINE 病史整合
🤖 LINE OA 自動回覆
💰 LINE + Voice Record 每月各 1000 人次，只要 1000 元

任何 HIS 都能橋接，不須更換 📋
👉 https://doctor-toolbox.com/ai-soap-generator
徐永峰醫師監製 · 品質保證"""

# Google Maps comment content (shorter)
MAPS_COMMENT = """您好！🩺 醫師工具箱 — AI 語音記錄自動轉 SOAP 病歷。支援 LINE 病史整合、OA 自動回覆。任何 HIS 系統都能橋接，不須更換。徐永峰醫師監製。免費體驗：https://doctor-toolbox.com/ai-soap-generator"""

# === Load existing log ===
def load_log():
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, 'r', encoding='utf-8') as f:
            return [json.loads(line) for line in f if line.strip()]
    return []

def save_log(entries):
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

def is_processed(clinic_name):
    for entry in load_log():
        if entry.get('clinic_name') == clinic_name:
            return True
    return False

# === Search functions ===
def search_clinic_google_maps(page, clinic_name, address=''):
    """Search Google Maps for clinic and return URL."""
    query = clinic_name
    if address:
        query = f"{clinic_name} {address}"
    
    print(f"  🔍 Maps search: {query}")
    
    try:
        page.goto(f"https://www.google.com/maps/search/{query}/")
        time.sleep(4)
        
        # Get the URL after Google Maps redirects
        current_url = page.url
        print(f"  Maps URL: {current_url}")
        
        if 'google.com/maps' in current_url and '@' in current_url:
            return current_url
        elif 'place/' in current_url:
            return current_url
        elif 'maps.google.com' in current_url:
            return current_url
        
        return None
        
    except Exception as e:
        print(f"  ❌ Maps search error: {e}")
        return None

def search_clinic_facebook(page, clinic_name):
    """Search Google for clinic's Facebook page."""
    search_query = f"{clinic_name} site:facebook.com"
    print(f"  🔍 FB search: {search_query}")
    
    try:
        page.goto(f"https://www.google.com/search?q={search_query}&hl=zh-TW&num=10")
        time.sleep(4)
        
        # Extract Facebook links from page
        links = page.evaluate("""() => {
            const results = [];
            const seen = new Set();
            document.querySelectorAll('a').forEach(a => {
                const href = a.getAttribute('href') || '';
                if (href.includes('facebook.com') && href.includes('/pages/') && !href.includes('apps.facebook.com')) {
                    let url = href;
                    if (url.includes('/url?q=')) {
                        url = url.split('/url?q=')[1].split('&')[0];
                    }
                    if (!seen.has(url)) {
                        seen.add(url);
                        results.push(url);
                    }
                }
            });
            return results;
        }""")
        
        for link in links:
            print(f"  ✅ Found FB: {link}")
            return link
        
        # Try direct Facebook search
        print("  🔍 Trying FB search directly...")
        page.goto(f"https://www.facebook.com/search/top/?q={clinic_name}")
        time.sleep(4)
        
        fb_links = page.evaluate("""() => {
            const results = [];
            const seen = new Set();
            document.querySelectorAll('a').forEach(a => {
                const href = a.getAttribute('href') || '';
                if (href.includes('/pages/') && href.length > 20) {
                    if (!seen.has(href)) {
                        seen.add(href);
                        results.push(href);
                    }
                }
            });
            return results.slice(0, 3);
        }""")
        
        if fb_links:
            print(f"  ✅ Found via FB search: {fb_links[0]}")
            return fb_links[0]
        
        print("  ❌ No Facebook page found")
        return None
        
    except Exception as e:
        print(f"  ❌ FB search error: {e}")
        return None

def post_facebook_comment(page, fb_url, comment_text):
    """Navigate to FB page and find a post to comment on."""
    print(f"  📝 Commenting on FB: {fb_url[:80]}...")
    
    try:
        page.goto(fb_url)
        time.sleep(6)
        
        has_no_posts = page.evaluate("""() => {
            return document.body.innerText.includes('沒有可顯示的貼文') || document.body.innerText.includes('No posts available');
        }""")
        if has_no_posts:
            print("  ⚠️ 此臉書專頁目前沒有任何貼文，無法留言")
            return False
            
        # Try to click comment button first
        page.evaluate("""() => {
            const elements = Array.from(document.querySelectorAll('div, span, [role="button"], button, a'));
            for (const el of elements) {
                const text = (el.textContent || '').trim();
                const ariaLabel = el.getAttribute('aria-label') || '';
                if ((text === '留言' || text === 'Comment' || ariaLabel.includes('留言') || ariaLabel.includes('Comment')) && el.offsetHeight > 0) {
                    el.click();
                    break;
                }
            }
        }""")
        time.sleep(3)
        
        # Enter text in the contenteditable comment field
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
        }""", comment_text)
        
        if text_inserted:
            time.sleep(2)
            page.keyboard.press("Enter")
            time.sleep(5)
            page.screenshot(path="/tmp/fb_comment_submitted.png")
            return True
        else:
            page.screenshot(path="/tmp/fb_comment_failed.png")
            return False
            
    except Exception as e:
        print(f"  ❌ FB comment error: {e}")
        return False

def post_maps_comment(page, maps_url, comment_text):
    """Navigate to Google Maps and post a 5-star review with comment."""
    print(f"  📝 Commenting on Maps: {maps_url[:80]}...")
    
    try:
        page.goto(maps_url)
        time.sleep(6)
        
        # Check if owner
        is_owner = page.evaluate("""() => {
            const text = document.body.innerText;
            return text.includes('管理你的商家檔案') || text.includes('Manage your Business Profile') || text.includes('管理商家檔案');
        }""")
        if is_owner:
            print("  ⚠️ 商家擁有者帳號，無法撰寫評論")
            return "owner_profile"
            
        # Click "Write a review" button
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
            page.screenshot(path="/tmp/maps_no_review_btn.png")
            return False
            
        time.sleep(6)
        
        # Click 5th star
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
                const star = stars[4];
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
            page.screenshot(path="/tmp/maps_star_click_failed.png")
            return False
            
        time.sleep(3)
        
        # Enter review comment
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
                    const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
                    if (setter) {
                        setter.call(ta, commentText);
                    } else {
                        ta.value = commentText;
                    }
                    ta.dispatchEvent(new Event('input', { bubbles: true }));
                }
                return true;
            }
            return false;
        }""", comment_text)
        
        if not text_filled:
            page.screenshot(path="/tmp/maps_text_fill_failed.png")
            return False
            
        time.sleep(2)
        
        # Click submit
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
            time.sleep(5)
            page.screenshot(path="/tmp/maps_review_submitted.png")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"  ❌ Maps comment error: {e}")
        return False

def main():
    print("=" * 60)
    print("醫師工具箱 - 診所 FB/Maps 留言自動化")
    print("=" * 60)
    
    # Load CSV
    clinics = []
    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader)
        
        idx_map = {h: i for i, h in enumerate(header)}
        
        for i, row in enumerate(reader):
            clinic_name = row[idx_map['醫事機構名稱']].strip()
            address = row[idx_map.get('地址', -1)].strip() if '地址' in idx_map else ''
            phone = row[idx_map.get('電話', -1)].strip() if '電話' in idx_map else ''
            dept = row[idx_map.get('診療科別', -1)].strip() if '診療科別' in idx_map else ''
            
            if clinic_name:
                clinics.append({
                    'name': clinic_name,
                    'address': address,
                    'phone': phone,
                    'dept': dept,
                    'row_num': i + 2
                })
    
    print(f"\n📋 共 {len(clinics)} 筆診所資料")
    
    existing = load_log()
    if existing:
        print(f"📝 已有 {len(existing)} 筆紀錄，跳過重複")
    
    # Launch CloakBrowser with persistent context
    print(f"\n🚀 啟動 CloakBrowser with profile: {PROFILE_DIR}...")
    try:
        browser = launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            humanize=True,
            timezone="Asia/Taipei",
            locale="zh-TW",
            args=["--fingerprint=88888"]
        )
    except Exception as e:
        print(f"❌ 瀏覽器啟動失敗: {e}")
        sys.exit(1)
        
    page = browser.pages[0] if browser.pages else browser.new_page()
    
    posted = 0
    failed = 0
    skipped = 0
    
    for idx, clinic in enumerate(clinics):
        clinic_name = clinic['name']
        row_num = clinic['row_num']
        
        print(f"\n{'='*60}")
        print(f"[{idx+1}/{len(clinics)}] {clinic_name} (第{row_num}行)")
        print(f"  地址: {clinic['address']}")
        print(f"  科別: {clinic['dept']}")
        
        if is_processed(clinic_name):
            print(f"  ⏭️ 已處理過，跳過")
            skipped += 1
            continue
        
        # 1. Search Facebook
        fb_url = search_clinic_facebook(page, clinic_name)
        
        if fb_url:
            # 2. Post to Facebook
            success = post_facebook_comment(page, fb_url, FB_COMMENT)
            if success:
                posted += 1
                save_log([{
                    'clinic_name': clinic_name,
                    'fb_url': fb_url,
                    'maps_url': None,
                    'status': 'fb_commented',
                    'timestamp': datetime.now().isoformat(),
                    'row_num': row_num
                }])
            else:
                failed += 1
                save_log([{
                    'clinic_name': clinic_name,
                    'fb_url': fb_url,
                    'maps_url': None,
                    'status': 'fb_post_failed',
                    'timestamp': datetime.now().isoformat(),
                    'row_num': row_num
                }])
        else:
            # 3. Search Google Maps as fallback
            maps_url = search_clinic_google_maps(page, clinic_name, clinic['address'])
            
            if maps_url:
                success = post_maps_comment(page, maps_url, MAPS_COMMENT)
                if success == "owner_profile":
                    skipped += 1
                    save_log([{
                        'clinic_name': clinic_name,
                        'fb_url': None,
                        'maps_url': maps_url,
                        'status': 'maps_owner_profile',
                        'timestamp': datetime.now().isoformat(),
                        'row_num': row_num
                    }])
                elif success:
                    posted += 1
                    save_log([{
                        'clinic_name': clinic_name,
                        'fb_url': None,
                        'maps_url': maps_url,
                        'status': 'maps_commented',
                        'timestamp': datetime.now().isoformat(),
                        'row_num': row_num
                    }])
                else:
                    failed += 1
                    save_log([{
                        'clinic_name': clinic_name,
                        'fb_url': None,
                        'maps_url': maps_url,
                        'status': 'maps_post_failed',
                        'timestamp': datetime.now().isoformat(),
                        'row_num': row_num
                    }])
            else:
                skipped += 1
                save_log([{
                    'clinic_name': clinic_name,
                    'fb_url': None,
                    'maps_url': None,
                    'status': 'not_found',
                    'timestamp': datetime.now().isoformat(),
                    'row_num': row_num
                }])
        
        # Rate limit
        time.sleep(3)
    
    browser.close()
    
    print(f"\n{'='*60}")
    print(f"📊 完成統計:")
    print(f"  ✅ 已留言: {posted}")
    print(f"  ❌ 失敗: {failed}")
    print(f"  ⏭️ 跳過: {skipped}")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
