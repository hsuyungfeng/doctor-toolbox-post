#!/usr/bin/env python3
"""
Scrape Facebook Page contact emails and Messenger links for all clinics.
Reads clinics西醫.csv, crawls Facebook, writes data back to the CSV.
Uses persistent browser profile to bypass bot checks.
"""
import csv
import json
import time
import os
import re
import sys
import signal
from datetime import datetime
from pathlib import Path
from cloakbrowser import launch_persistent_context

# === Paths ===
WORKSPACE_DIR = Path(__file__).resolve().parent
PROFILE_DIR = WORKSPACE_DIR / "browser_profile"

# Use the file locations configured in post_clinics.py
CSV_PATH = "/home/hsuyungfeng/文件/doctor-toolbox-post/clinics西醫.csv"
CACHE_PATH = "/home/hsuyungfeng/文件/doctor-toolbox-post/clinic_links.json"

# State variables
csv_header = []
csv_rows = []
cache_data = {}
browser_context = None
interrupted = False

def load_data():
    global csv_header, csv_rows, cache_data, CSV_PATH
    
    # 1. Load CSV
    print(f"📂 載入 CSV 資料庫: {CSV_PATH}")
    if not os.path.exists(CSV_PATH):
        # Check workspace backup
        local_csv = WORKSPACE_DIR / "clinics西醫.csv"
        if local_csv.exists():
            print(f"⚠️ {CSV_PATH} 不存在，改為載入本地: {local_csv}")
            CSV_PATH = str(local_csv)
        else:
            print("❌ 找不到 clinics西醫.csv 檔案")
            sys.exit(1)
            
    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        csv_header = list(next(reader))
        csv_rows = [list(row) for row in reader]
    
    # Ensure headers for FB_URL, Email, Messenger, Intro, Latest_Post exist
    new_cols = ['FB_URL', 'Email', 'Messenger', 'Intro', 'Latest_Post']
    for col in new_cols:
        if col not in csv_header:
            csv_header.append(col)
            
    # Pad all rows to match new header length
    for row in csv_rows:
        while len(row) < len(csv_header):
            row.append('')
            
    print(f"  - 共載入 {len(csv_rows)} 筆診所資料")
    print(f"  - 目前 CSV 欄位: {', '.join(csv_header)}")
    
    # 2. Load JSON Cache
    print(f"📂 載入 JSON 快取: {CACHE_PATH}")
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, 'r', encoding='utf-8') as f:
                raw_cache = json.load(f)
                # Map by clinic_name
                for item in raw_cache:
                    name = item.get('clinic_name')
                    if name:
                        cache_data[name] = item
            print(f"  - 載入快取紀錄 {len(cache_data)} 筆")
        except Exception as e:
            print(f"⚠️ 載入快取出錯 (建立新快取): {e}")
            cache_data = {}
    else:
        print("  - 未找到既有快取，將建立新快取檔案")

def save_data():
    global csv_header, csv_rows, cache_data
    print(f"\n💾 正在儲存資料...")
    
    # 1. Save CSV
    try:
        # Write to temporary file first, then replace to avoid corruption
        temp_csv = CSV_PATH + ".tmp"
        with open(temp_csv, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(csv_header)
            writer.writerows(csv_rows)
        if os.path.exists(CSV_PATH):
            os.remove(CSV_PATH)
        os.rename(temp_csv, CSV_PATH)
        print(f"  ✅ 成功更新 CSV 資料庫: {CSV_PATH}")
    except Exception as e:
        print(f"  ❌ 儲存 CSV 失敗: {e}")
        
    # 2. Save JSON Cache
    try:
        temp_json = CACHE_PATH + ".tmp"
        with open(temp_json, 'w', encoding='utf-8') as f:
            json.dump(list(cache_data.values()), f, ensure_ascii=False, indent=2)
        if os.path.exists(CACHE_PATH):
            os.remove(CACHE_PATH)
        os.rename(temp_json, CACHE_PATH)
        print(f"  ✅ 成功更新 JSON 快取: {CACHE_PATH}")
    except Exception as e:
        print(f"  ❌ 儲存 JSON 失敗: {e}")

def handle_signal(sig, frame):
    global interrupted
    print("\n🛑 偵測到中斷訊號 (Ctrl+C)... 正在安全結束並儲存資料...")
    interrupted = True

# Register Ctrl+C handler
signal.signal(signal.SIGINT, handle_signal)

def search_clinic_facebook(page, clinic_name):
    """Search Google for clinic's Facebook page."""
    search_query = f"{clinic_name} site:facebook.com"
    try:
        page.goto(f"https://www.google.com/search?q={search_query}&hl=zh-TW&num=10")
        time.sleep(5)
        
        # Check for CAPTCHA block
        is_blocked = page.evaluate("""() => {
            const text = document.body.innerText;
            return text.includes('異常流量') || 
                   text.includes('Unusual traffic') ||
                   text.includes('recaptcha') ||
                   !!document.querySelector('#captcha-form') ||
                   (document.title === 'Google' && !document.querySelector('#search') && !document.querySelector('[role="main"]'));
        }""")
        if is_blocked:
            print("\n" + "!" * 60)
            print("⚠️ 偵測到 Google 阻擋驗證碼 (CAPTCHA / Unusual Traffic)！")
            print("👉 請在您的桌面瀏覽器視窗中手動完成驗證碼挑戰。")
            print("!" * 60)
            
            # Wait for user input to retry
            input("\n👉 手動完成驗證後，請在此處按下 [Enter] 鍵繼續爬取... ")
            
            # Re-attempt the search query
            page.goto(f"https://www.google.com/search?q={search_query}&hl=zh-TW&num=10")
            time.sleep(5)
            
            # Re-check block status
            is_blocked_again = page.evaluate("""() => {
                const text = document.body.innerText;
                return text.includes('異常流量') || 
                       text.includes('Unusual traffic') ||
                       text.includes('recaptcha') ||
                       !!document.querySelector('#captcha-form') ||
                       (document.title === 'Google' && !document.querySelector('#search') && !document.querySelector('[role="main"]'));
            }""")
            if is_blocked_again:
                raise Exception("Google blocked us (CAPTCHA challenge failed to resolve)")
            
        # Extract Facebook links
        links = page.evaluate("""() => {
            const results = [];
            const seen = new Set();
            document.querySelectorAll('a').forEach(a => {
                const href = a.getAttribute('href') || '';
                if (href.includes('facebook.com') && !href.includes('google.com') && !href.includes('apps.facebook.com') && !href.includes('facebook.com/groups')) {
                    let url = href;
                    if (url.includes('/url?q=')) {
                        url = url.split('/url?q=')[1].split('&')[0];
                    }
                    try {
                        const parsed = new URL(url);
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
            return link
        return None
    except Exception as e:
        print(f"    ❌ Google 搜尋 FB 失敗: {e}")
        # Propagate browser crash/closed or captcha errors to stop script immediately
        err = str(e).lower()
        if "closed" in err or "context" in err or "navigation" in err or "blocked" in err or "captcha" in err:
            raise e
        return None

def scrape_fb_page_details(page, fb_url, clinic_name):
    """Scrape Email, Messenger, page Intro, and Latest Posts from FB page."""
    try:
        page.goto(fb_url)
        time.sleep(6)
        
        # Check if browser was closed/blocked
        is_blocked = page.evaluate("""() => {
            const text = document.body.innerText;
            return text.includes('Security Check') || text.includes('安全檢查') || text.includes('Robot') || document.title.includes('Blocked');
        }""")
        if is_blocked:
            print("    ⚠️ 偵測到 Facebook 阻擋安全檢查！")
            raise Exception("Facebook blocked us (Security Check)")
            
        info = page.evaluate("""(clinicName) => {
            const results = {
                emails: [],
                messenger_links: [],
                intro: '',
                posts: []
            };
            
            const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}/g;
            
            // 1. Scan mailto links
            document.querySelectorAll('a[href^="mailto:"]').forEach(a => {
                const email = a.getAttribute('href').replace('mailto:', '').split('?')[0].trim();
                if (email && !results.emails.includes(email)) {
                    results.emails.push(email);
                }
            });
            
            // 2. Scan all page text
            const pageText = document.body.innerText;
            const matchedEmails = pageText.match(emailRegex);
            if (matchedEmails) {
                matchedEmails.forEach(email => {
                    const cleaned = email.trim();
                    if (cleaned && !results.emails.includes(cleaned)) {
                        results.emails.push(cleaned);
                    }
                });
            }
            
            // 3. Scan for messenger links
            document.querySelectorAll('a').forEach(a => {
                const href = a.getAttribute('href') || '';
                if (href.includes('m.me/') || href.includes('messenger.com/t/')) {
                    let cleanHref = href.split('?')[0].trim();
                    if (!results.messenger_links.includes(cleanHref)) {
                        results.messenger_links.push(cleanHref);
                    }
                }
            });
            
            // 4. Scan leaf nodes for Intro
            const elements = Array.from(document.querySelectorAll('span, div'));
            const cleanName = clinicName.replace('診所', '');
            
            for (const el of elements) {
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
            
            // 5. Extract Latest Posts
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
        
        # Get username from URL
        page_username = ""
        parsed_url = re.search(r'facebook\.com/([^/?]+)', fb_url)
        if parsed_url:
            page_username = parsed_url.group(1)
            if page_username == "profile.php" or page_username == "p":
                p_match = re.search(r'facebook\.com/p/([^/?]+)', fb_url)
                if p_match:
                    page_username = p_match.group(1)
                    
        if page_username and not any('m.me/' in link for link in info['messenger_links']):
            info['messenger_links'].append(f"https://m.me/{page_username}")
            
        # Parse intro and posts
        intro_text = info.get('intro', '')
        posts_list = info.get('posts', [])
        latest_post_text = " | ".join([p.replace('\n', ' ') for p in posts_list[:2]]) if posts_list else ''
        
        # Fallback to /about tab if email not found
        if not info['emails']:
            about_url = fb_url.rstrip('/') + '/about'
            try:
                page.goto(about_url)
                time.sleep(5)
                
                about_info = page.evaluate("""() => {
                    const results = { emails: [] };
                    const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}/g;
                    
                    document.querySelectorAll('a[href^="mailto:"]').forEach(a => {
                        const email = a.getAttribute('href').replace('mailto:', '').split('?')[0].trim();
                        if (email && !results.emails.includes(email)) {
                            results.emails.push(email);
                        }
                    });
                    
                    const pageText = document.body.innerText;
                    const matchedEmails = pageText.match(emailRegex);
                    if (matchedEmails) {
                        matchedEmails.forEach(email => {
                            const cleaned = email.trim();
                            if (cleaned && !results.emails.includes(cleaned)) {
                                results.emails.push(cleaned);
                            }
                        });
                    }
                    return results;
                }""")
                info['emails'] = list(set(info['emails'] + about_info['emails']))
            except Exception as e:
                print(f"    ⚠️ Fallback to /about page failed: {e}")
            
        return {
            'email': info['emails'][0] if info['emails'] else '',
            'messenger': info['messenger_links'][0] if info['messenger_links'] else (f"https://m.me/{page_username}" if page_username else ''),
            'intro': intro_text,
            'latest_post': latest_post_text
        }
    except Exception as e:
        print(f"    ❌ 爬取 FB 內容失敗: {e}")
        err = str(e).lower()
        if "closed" in err or "context" in err or "blocked" in err:
            raise e
        return {'email': '', 'messenger': '', 'intro': '', 'latest_post': ''}

def main():
    global browser_context, interrupted
    
    # 1. Load CSV and JSON Cache
    load_data()
    
    # 2. Map Column indices
    idx_name = csv_header.index('醫事機構名稱')
    idx_addr = csv_header.index('地址')
    idx_fb = csv_header.index('FB_URL')
    idx_email = csv_header.index('Email')
    idx_msg = csv_header.index('Messenger')
    idx_intro = csv_header.index('Intro')
    idx_post = csv_header.index('Latest_Post')
    
    # 3. Launch CloakBrowser
    print(f"\n🚀 啟動 CloakBrowser 載入 Profile: {PROFILE_DIR}")
    try:
        browser_context = launch_persistent_context(
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
        
    page = browser_context.pages[0] if browser_context.pages else browser_context.new_page()
    
    processed_count = 0
    newly_saved = 0
    skipped_count = 0
    
    # Prioritize Taichung City clinics
    taichung_indices = []
    other_indices = []
    for i, row in enumerate(csv_rows):
        addr = row[idx_addr].strip()
        if '台中' in addr or '臺中' in addr:
            taichung_indices.append(i)
        else:
            other_indices.append(i)
            
    prioritized_indices = taichung_indices + other_indices
    print(f"📊 診所排序優先級統計:")
    print(f"  - 台中市診所: {len(taichung_indices)} 筆 (將優先爬取)")
    print(f"  - 其他地區診所: {len(other_indices)} 筆")
    
    print("\n" + "=" * 60)
    print("🎬 開始進行 Facebook 爬取流程 (直接填入 CSV 與 快取)...")
    print("提示: 可隨時按下 Ctrl+C 安全停止並儲存當前進度。")
    print("=" * 60)
    
    try:
        for loop_idx, original_idx in enumerate(prioritized_indices):
            if interrupted:
                break
                
            row = csv_rows[original_idx]
            clinic_name = row[idx_name].strip()
            address = row[idx_addr].strip()
            
            # Check if already processed (has Email/Messenger filled, or marked not_found)
            # We allow re-scraping if FB_URL is known but Email/Messenger or Intro/Post is empty
            has_fb_url = row[idx_fb].strip() != ''
            has_email = row[idx_email].strip() != ''
            has_messenger = row[idx_msg].strip() != ''
            has_intro = row[idx_intro].strip() != ''
            has_post = row[idx_post].strip() != ''
            
            # Check cache as well
            cached_info = cache_data.get(clinic_name)
            if cached_info:
                if not has_fb_url and cached_info.get('fb_url'):
                    row[idx_fb] = cached_info.get('fb_url', '')
                    has_fb_url = True
                if not has_email and cached_info.get('email'):
                    row[idx_email] = cached_info.get('email', '')
                    has_email = True
                if not has_messenger and cached_info.get('messenger'):
                    row[idx_msg] = cached_info.get('messenger', '')
                    has_messenger = True
                if not has_intro and cached_info.get('intro'):
                    row[idx_intro] = cached_info.get('intro', '')
                    has_intro = True
                if not has_post and cached_info.get('latest_post'):
                    row[idx_post] = cached_info.get('latest_post', '')
                    has_post = True
                    
            fb_url = row[idx_fb].strip()
            
            # Skip if FB_URL is marked not_found or (has_email and has_messenger and (has_intro or has_post))
            if fb_url == 'not_found' or (has_email and has_messenger and (has_intro or has_post)):
                skipped_count += 1
                continue
                
            print(f"\n[{loop_idx+1}/{len(csv_rows)}] 診所: {clinic_name}")
            print(f"  地址: {address}")
            
            # Step A: Find FB URL if not present
            if not fb_url:
                print("  🔍 正在搜尋 Facebook 專頁...")
                fb_url = search_clinic_facebook(page, clinic_name)
                if fb_url:
                    print(f"    ✅ 搜尋到 FB: {fb_url}")
                    row[idx_fb] = fb_url
                    # Save to cache
                    if clinic_name not in cache_data:
                        cache_data[clinic_name] = {'clinic_name': clinic_name, 'address': address}
                    cache_data[clinic_name]['fb_url'] = fb_url
                else:
                    print("    ❌ 搜尋不到 Facebook 專頁")
                    row[idx_fb] = 'not_found'
                    row[idx_email] = 'not_found'
                    row[idx_msg] = 'not_found'
                    row[idx_intro] = 'not_found'
                    row[idx_post] = 'not_found'
                    if clinic_name not in cache_data:
                        cache_data[clinic_name] = {'clinic_name': clinic_name, 'address': address}
                    cache_data[clinic_name]['fb_url'] = 'not_found'
                    cache_data[clinic_name]['email'] = 'not_found'
                    cache_data[clinic_name]['messenger'] = 'not_found'
                    cache_data[clinic_name]['intro'] = 'not_found'
                    cache_data[clinic_name]['latest_post'] = 'not_found'
                    processed_count += 1
                    newly_saved += 1
                    continue
                    
            # Step B: Scrape Email & Messenger & Details if we have FB URL
            if fb_url and fb_url != 'not_found':
                print(f"  🌐 正在爬取 FB 聯絡與簡介貼文資料: {fb_url}")
                fb_details = scrape_fb_page_details(page, fb_url, clinic_name)
                
                email = fb_details.get('email', '')
                messenger = fb_details.get('messenger', '')
                intro = fb_details.get('intro', '')
                latest_post = fb_details.get('latest_post', '')
                
                row[idx_email] = email
                row[idx_msg] = messenger
                row[idx_intro] = intro
                row[idx_post] = latest_post
                
                # Save to cache
                if clinic_name not in cache_data:
                    cache_data[clinic_name] = {'clinic_name': clinic_name, 'address': address}
                cache_data[clinic_name]['fb_url'] = fb_url
                cache_data[clinic_name]['email'] = email
                cache_data[clinic_name]['messenger'] = messenger
                cache_data[clinic_name]['intro'] = intro
                cache_data[clinic_name]['latest_post'] = latest_post
                
                print(f"    📧 Email: {email if email else '未公開'}")
                print(f"    💬 Messenger: {messenger if messenger else '未生成'}")
                print(f"    📝 Intro: {intro[:40] if intro else '未找到簡介'}...")
                print(f"    貼文: {latest_post[:40] if latest_post else '未找到貼文'}...")
                
                processed_count += 1
                newly_saved += 1
                
            # Batch save to prevent data loss - save after every clinic
            if newly_saved >= 1:
                save_data()
                newly_saved = 0
                
            # Rate limit delay
            time.sleep(4)
    except Exception as e:
        print(f"\n❌ 爬取中斷，錯誤原因: {e}")
    finally:
        # Close browser and save final results
        print("\n💾 正在儲存資料並關閉瀏覽器...")
        try:
            browser_context.close()
        except:
            pass
        save_data()
    
    print("\n" + "=" * 60)
    print("📊 執行統計完成:")
    print(f"  - 跳過已處理: {skipped_count} 筆")
    print(f"  - 本次成功處理: {processed_count} 筆")
    print("=" * 60)

if __name__ == "__main__":
    main()
