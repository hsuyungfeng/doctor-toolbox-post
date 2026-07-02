#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Per-Clinic Pipeline (SQLite 版 / SQLite Version): Scrape → Generate Copy (A/B Test) → Send → Mark
一邊處理一間診所，一邊將狀態儲存至 SQLite 資料庫，確保防當機與高可靠性。
"""

import argparse
import json
import os
import random
import re
import signal
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

# 載入 SQLite 資料庫管理模組 / Import database module
import db

# === Config ===
WORKSPACE_DIR = Path(__file__).resolve().parent
LOG_PATH = str(WORKSPACE_DIR / "outreach_sent_log.jsonl")
LLM_API_URL = os.environ.get("LLM_API_URL", "http://localhost:8080/v1/chat/completions")
PROFILE_DIR = WORKSPACE_DIR / "browser_profile"

GENERIC_COPY = """🩺 看診對話，自動變成 SOAP 病歷

每次看診都要手寫病歷？花掉你一半的時間？
現在，醫師工具箱幫你自動搞定。

🎙️ 語音即時記錄 → AI 轉成結構化 SOAP 病歷
看診過程自然對話，不用打字、不用分心。

📱 LINE 病史整合
病人原始病史直接同步，完整脈絡一鍵掌握，不再遺漏任何關鍵資訊。

🤖 LINE OA 自動回覆
診所常見問題（專長、看診時間、費用）自動回覆，減輕前台負擔。

💰 高用量方案
LINE + Voice Record 每月各 1000 人次，費用每月 1000 元。
輕鬆應對門診需求。

🔗 任何系統都能橋接，不須更換 HIS

⚠️ 建議先註冊，再免費體驗！
避免病人資料流失，錯過每一次完整的病史記錄。

👉 https://doctor-toolbox.com/ai-soap-generator

徐永峰醫師監製 · 品質保證
歡迎免費體驗分享！"""

interrupted = False

def handle_signal(sig, frame):
    global interrupted
    print("\n🛑 收到中斷訊號，完成目前診所後安全退出...")
    interrupted = True

signal.signal(signal.SIGINT, handle_signal)

def log_outreach(entry):
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')

def show_stats(city):
    stats = db.get_city_stats(city)
    print(f"\n{'='*60}")
    print(f"📊 {city} 診所統計 (SQLite)")
    print(f"{'='*60}")
    print(f"  診所總數 (排除中醫/牙醫):  {stats['total']}")
    print(f"  已有 FB 頁面:              {stats['has_fb']}")
    print(f"  已有 Messenger:            {stats['has_msg']}")
    print(f"  已有個人化文案:            {stats['has_copy']}")
    print(f"  已發送 (sent/dry_run):     {stats['sent']}")
    print(f"  待處理:                    {stats['total'] - stats['sent']}")
    print(f"{'='*60}")

# ═══════════════════════════════════════════════════════════════════
# Step 1: Scrape FB (Google & FB crawler)
# ═══════════════════════════════════════════════════════════════════

def search_clinic_website(page, clinic_name):
    """Search Google for the clinic's official website."""
    search_query = f"{clinic_name} 官網"
    print(f"  🔍 Website search: {search_query}")
    try:
        page.goto(f"https://www.google.com/search?q={search_query}&hl=zh-TW&num=10")
        time.sleep(4)
        
        # Extract the first organic search link that is not FB/Maps/Youtube/Instagram
        website = page.evaluate("""() => {
            const forbidden = ['facebook.com', 'google.com', 'youtube.com', 'instagram.com', 'twitter.com', 'line.me', 'pixnet.net', 'xuite.net'];
            const links = Array.from(document.querySelectorAll('a'));
            for (const a of links) {
                const href = a.getAttribute('href') || '';
                if (href.startsWith('http') && !forbidden.some(domain => href.includes(domain))) {
                    // Check if inside organic results (e.g. h3 headers)
                    let parent = a.parentElement;
                    while (parent) {
                        if (parent.tagName === 'H3' || parent.querySelector('h3')) {
                            return href;
                        }
                        parent = parent.parentElement;
                    }
                }
            }
            return null;
        }""")
        return website
    except Exception as e:
        print(f"  ❌ Website search error: {e}")
        return None

def search_clinic_facebook(page, clinic_name):
    """Google search for clinic's Facebook page."""
    search_query = f"{clinic_name} site:facebook.com"
    try:
        page.goto(f"https://www.google.com/search?q={search_query}&hl=zh-TW&num=10")
        time.sleep(5)

        # Check CAPTCHA
        is_blocked = page.evaluate("""() => {
            const text = document.body.innerText;
            return text.includes('異常流量') || text.includes('Unusual traffic') ||
                   text.includes('recaptcha') || !!document.querySelector('#captcha-form') ||
                   (document.title === 'Google' && !document.querySelector('#search') && !document.querySelector('[role="main"]'));
        }""")
        if is_blocked:
            print("  ⚠️ Google CAPTCHA 偵測到！請在瀏覽器中手動完成驗證。")
            input("  👉 完成後按 [Enter] 繼續...")
            page.goto(f"https://www.google.com/search?q={search_query}&hl=zh-TW&num=10")
            time.sleep(5)

        # Extract FB links
        links = page.evaluate("""() => {
            const results = [];
            const seen = new Set();
            document.querySelectorAll('a').forEach(a => {
                const href = a.getAttribute('href') || '';
                if (href.includes('facebook.com') && !href.includes('google.com') &&
                    !href.includes('apps.facebook.com') && !href.includes('facebook.com/groups')) {
                    let url = href;
                    if (url.includes('/url?q=')) url = url.split('/url?q=')[1].split('&')[0];
                    try {
                        const parsed = new URL(url);
                        if (parsed.pathname.length > 1) {
                            const cleanUrl = parsed.origin + parsed.pathname;
                            if (!seen.has(cleanUrl)) { seen.add(cleanUrl); results.push(cleanUrl); }
                        }
                    } catch(e) {}
                }
            });
            return results;
        }""")

        return links[0] if links else None
    except Exception as e:
        print(f"    ❌ Google 搜尋 FB 失敗: {e}")
        err = str(e).lower()
        if "closed" in err or "context" in err or "blocked" in err:
            raise
        return None

def scrape_fb_page_details(page, fb_url, clinic_name):
    """Scrape Email, Messenger, Intro, Latest Post from FB page."""
    try:
        page.goto(fb_url)
        time.sleep(6)

        info = page.evaluate("""(clinicName) => {
            const results = { emails: [], messenger_links: [], intro: '', posts: [] };
            const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}/g;

            // mailto links
            document.querySelectorAll('a[href^="mailto:"]').forEach(a => {
                const email = a.getAttribute('href').replace('mailto:', '').split('?')[0].trim();
                if (email && !results.emails.includes(email)) results.emails.push(email);
            });

            // page text emails
            const matchedEmails = document.body.innerText.match(emailRegex);
            if (matchedEmails) matchedEmails.forEach(e => {
                if (!results.emails.includes(e.trim())) results.emails.push(e.trim());
            });

            // messenger links
            document.querySelectorAll('a').forEach(a => {
                const href = a.getAttribute('href') || '';
                if (href.includes('m.me/') || href.includes('messenger.com/t/')) {
                    let clean = href.split('?')[0].trim();
                    if (!results.messenger_links.includes(clean)) results.messenger_links.push(clean);
                }
            });

            // Intro
            const cleanName = clinicName.replace('診所', '');
            for (const el of document.querySelectorAll('span, div')) {
                if (el.children.length === 0) {
                    const text = (el.textContent || '').trim();
                    if (text.length > 10 && text.length < 200 &&
                        (text.includes(cleanName) || text.includes('診所') || text.includes('位於') ||
                         text.includes('守護') || text.includes('服務') || text.includes('照護') || text.includes('醫師')) &&
                        !text.includes('追蹤') && !text.includes('發送訊息') && !text.includes('讚') &&
                        !text.includes('首頁') && !text.includes('關於') && !text.includes('相片') &&
                        !text.includes('分享') && !text.includes('影片') && text !== clinicName) {
                        results.intro = text;
                        break;
                    }
                }
            }

            // Latest Posts
            const skipWords = ['讚', '留言', '分享', '追蹤', '發送訊息', '追蹤中', '點讚', '回應'];
            for (const el of document.querySelectorAll('div[dir="auto"]')) {
                const text = (el.textContent || '').trim();
                if (text.length >= 8 && text.length < 1000) {
                    const isMeta = skipWords.some(w => text === w || (text.includes(w) && text.length < 15));
                    if (!isMeta && text !== results.intro && !results.posts.includes(text))
                        results.posts.push(text);
                }
            }
            return results;
        }""", clinic_name)

        # Derive messenger URL from page username
        page_username = ""
        parsed = re.search(r'facebook\.com/([^/?]+)', fb_url)
        if parsed:
            page_username = parsed.group(1)
            if page_username in ("profile.php", "p"):
                p_match = re.search(r'facebook\.com/p/([^/?]+)', fb_url)
                if p_match:
                    page_username = p_match.group(1)

        if page_username and not any('m.me/' in lnk for lnk in info['messenger_links']):
            info['messenger_links'].append(f"https://m.me/{page_username}")

        intro_text = info.get('intro', '')
        posts_list = info.get('posts', [])
        latest_post = " | ".join([p.replace('\n', ' ') for p in posts_list[:2]]) if posts_list else ''

        return {
            'email': info['emails'][0] if info['emails'] else '',
            'messenger': info['messenger_links'][0] if info['messenger_links'] else (f"https://m.me/{page_username}" if page_username else ''),
            'intro': intro_text,
            'latest_post': latest_post,
        }
    except Exception as e:
        print(f"    ❌ 爬取 FB 內容失敗: {e}")
        err = str(e).lower()
        if "closed" in err or "context" in err or "blocked" in err:
            raise
        return {'email': '', 'messenger': '', 'intro': '', 'latest_post': ''}

# ═══════════════════════════════════════════════════════════════════
# Step 2: Generate Copy via LLM
# ═══════════════════════════════════════════════════════════════════

def call_local_llm(prompt):
    """Call local LLM API (Qwythos-9B reasoning model)."""
    data = {
        "messages": [
            {"role": "system", "content": "你是醫療行銷文案助手。直接輸出 JSON，不要解釋。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 1024,
        "response_format": {"type": "json_object"}
    }
    try:
        req = urllib.request.Request(
            LLM_API_URL,
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=120) as response:
            res_json = json.loads(response.read().decode('utf-8'))
            choice = res_json.get('choices', [{}])[0]
            finish_reason = choice.get('finish_reason', 'unknown')
            content = choice.get('message', {}).get('content', '').strip()
            if finish_reason == 'length':
                usage = res_json.get('usage', {})
                print(f"    ⚠️ finish_reason=length (tokens={usage.get('completion_tokens', '?')})")
            return content
    except Exception as e:
        print(f"    ❌ LLM 呼叫失敗 (Local LLM API error): {e}")
        return None

def build_prompt(clinic_name, dept, intro, latest_post):
    return f"""你是一位專業的醫療行銷顧問。請根據以下診所的資訊，為其推薦「醫師工具箱（AI SOAP 語音病歷生成工具）」生成一段專屬的行銷開發文案。

診所名稱：{clinic_name}
診療科別：{dept}
診所簡介：{intro if intro else '未取得簡介'}
最新貼文：{latest_post if latest_post else '未取得最新貼文'}

產品介紹：
「醫師工具箱」是一個 AI 輔助病歷記載工具：
1. 🎙️ 語音即時記錄：看診對話錄音，AI 自動轉換為符合健保格式的 SOAP 病歷，節省 80% 打字時間。
2. 📱 LINE 病史整合：串接 LINE OA，病患可以在 LINE 上預約、自動回覆，並整合病歷史。
3. HIS 系統橋接：支援任何現有 HIS 診所系統，完全不須更換既有設備。
4. 優惠資費：LINE + Voice Record 每月各 1000 人次，只要 1000 元/月。由徐永峰醫師監製。

請返回 JSON 格式的數據，格式如下：
{{
    "personalized_copy": "繁體中文開發文案，長度在 100-150 字之間，必須包含資費「1000元/月」",
    "specialty_tag": "識別出的診所科別（例如：小兒科、耳鼻喉科等）"
}}

文案生成要求：
1. 必須以繁體中文撰寫，字數控制在 100-150 字之間，簡潔有禮。
2. 必須精準結合該診所的特色。
3. 不要使用任何罐頭問候語，第一句直接切入「針對貴診所在...方面的特色，醫師工具箱能提供...協助」。
4. 必須明確包含資費「1000元/月」（高用量方案每月各 1000 人次只要 1000元/月）。
5. 結尾附上免費體驗連結：https://doctor-toolbox.com/ai-soap-generator。
6. 嚴禁包含醫療法禁用的誇大詞彙（如「最佳」、「最先進」、「保證療效」、「根治」、「全台第一」）。

請只輸出 JSON 格式的內容，不要有任何多餘的解釋或前言後語。"""

def generate_copy(clinic_name, dept, intro, latest_post):
    """Generate copy with retry. Returns copy string or GENERIC_COPY on failure."""
    if not intro and not latest_post:
        return GENERIC_COPY

    intro_trunc = intro[:400] if intro else ""
    post_trunc = latest_post[:400] if latest_post else ""
    prompt = build_prompt(clinic_name, dept, intro_trunc, post_trunc)

    for attempt in range(3):
        try:
            raw = call_local_llm(prompt)
            if not raw:
                raise ValueError("LLM 返回空字串")

            # Clean markdown wrapping
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()
            raw = raw.strip()
            if not raw.startswith("{"):
                s, e = raw.find("{"), raw.rfind("}")
                if s != -1 and e != -1:
                    raw = raw[s:e+1]

            data = json.loads(raw)
            copy = data.get("personalized_copy", "").strip()

            # Basic validation
            if len(copy) < 50:
                raise ValueError(f"文案太短 ({len(copy)} 字)")

            # Simplified Chinese check
            simplified = ["亲", "医", "这", "国", "诊", "体", "会", "电", "话", "设", "备", "进", "专", "优", "療"]
            # Exclude standard Chinese characters from check if they are false positives, 
            # but keep critical simplified tokens check
            critical_simplified = ["亲", "医", "这", "国", "诊", "体", "会", "电", "话", "设", "备", "无", "们", "来", "为"]
            for c in critical_simplified:
                if c in copy:
                    raise ValueError(f"檢測到簡體字：'{c}'")

            return copy

        except Exception as e:
            print(f"    ⚠️ [第 {attempt+1} 次] 文案驗證失敗: {e}")

    print("    ❌ 嘗試次數耗盡，使用通用文案")
    return GENERIC_COPY

# ═══════════════════════════════════════════════════════════════════
# Step 3: Send Messenger (simulating human typing)
# ═══════════════════════════════════════════════════════════════════

def send_messenger_message(page, messenger_url, copy_text, dry_run=False, image_path=None):
    """Open Messenger chat, type copy, send it. Returns (success, status)."""
    target_url = messenger_url
    if "facebook.com/messages/t/" not in messenger_url:
        parts = messenger_url.rstrip('/').split('/')
        if parts:
            username = parts[-1].split('?')[0]
            if username:
                target_url = f"https://www.facebook.com/messages/t/{username}"

    print(f"  📤 開啟 Messenger 私訊連結: {target_url}")
    page.goto(target_url)
    time.sleep(10)

    # Check login status
    is_login = page.evaluate("""() => {
        const text = document.body.innerText;
        return text.includes('登入 Facebook') || text.includes('Log In') || !!document.querySelector('#login_form');
    }""")
    if is_login:
        print("  ⚠️ 未登入！請先執行 python3 import_cookies.py 匯入 FB Cookie。")
        return False, "login_required"

    # Locate textbox and insert text
    print("  🔍 定位輸入框...")
    
    # 模擬真人滑鼠移動至輸入框並點擊 / Simulate human mouse movements
    try:
        locator = page.locator('div[contenteditable="true"][role="textbox"]').first
        if locator.is_visible():
            box = locator.bounding_box()
            if box:
                page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2, steps=15)
                time.sleep(0.4)
                page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
    except Exception as me:
        pass

    focused = page.evaluate("""() => {
        const tb = document.querySelector('div[contenteditable="true"][role="textbox"]');
        if (tb) {
            const style = window.getComputedStyle(tb);
            if (style.display !== 'none' && style.visibility !== 'hidden' && tb.offsetHeight > 0) {
                tb.focus();
                tb.click();
                document.execCommand('selectAll', false, null);
                document.execCommand('delete', false, null);
                return true;
            }
        }
        return false;
    }""")

    if not focused:
        page.screenshot(path="/tmp/pipeline_textbox_failed.png")
        print("  ❌ 找不到 Messenger 輸入框")
        return False, "textbox_not_found"

    # Upload image if provided and exists
    if image_path and Path(image_path).exists() and not dry_run:
        print(f"  📤 上傳配圖: {image_path}...")
        try:
            page.set_input_files('input[type="file"]', str(image_path))
            time.sleep(5)  # Wait for Messenger to process image upload
            print("  ✅ 配圖上傳成功")
        except Exception as e:
            print(f"  ⚠️ 配圖上傳失敗: {e}")

    print("  📝 聚焦成功，使用 page.keyboard.insert_text() 插入文字...")
    page.keyboard.insert_text(copy_text)
    time.sleep(2)

    if dry_run:
        page.screenshot(path="/tmp/pipeline_dryrun.png")
        print("  🧪 [DRY-RUN] 文案已貼上至輸入框，跳過發送")
        return True, "dry_run"

    # Send message
    print("  🚀 發送中...")
    page.keyboard.press("Enter")
    time.sleep(3)
    page.evaluate("""() => {
        const btns = Array.from(document.querySelectorAll('[aria-label="傳送"], [aria-label="Send"], [role="button"]'));
        for (const btn of btns) {
            const label = btn.getAttribute('aria-label') || '';
            if (label === '傳送' || label === 'Send') { btn.click(); break; }
        }
    }""")
    time.sleep(5)

    # Verify delivery outcome
    failed = page.evaluate("""() => {
        const text = document.body.innerText;
        const kws = ['無法傳送', '無法送出', '你目前無法使用此功能', '暫時被限制',
                      "You can't send messages", 'Could not send', 'Something went wrong', '限制', 'Blocked'];
        for (const kw of kws) { if (text.includes(kw)) return kw; }
        return null;
    }""")

    if failed:
        ss = f"/tmp/pipeline_failed_{int(time.time())}.png"
        page.screenshot(path=ss)
        print(f"  🛑 發送失敗: {failed} (詳細截圖已存至: {ss})")
        return False, "delivery_failed"

    ss = f"/tmp/pipeline_sent_{int(time.time())}.png"
    page.screenshot(path=ss)
    print(f"  ✅ 發送成功！截圖存至: {ss}")
    return True, "sent"

# ═══════════════════════════════════════════════════════════════════
# Main Pipeline Orchestrator (SQLite版)
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="逐診所完整流水線（SQLite版）：爬取→文案（A/B測試）→發送→資料庫標記")
    parser.add_argument("--city", required=True, help="目標城市 (如：台中, 台北, 高雄)")
    parser.add_argument("--limit", type=int, default=20, help="處理上限筆數 (預設 20)")
    parser.add_argument("--dry-run", action="store_true", help="測試模式，不實際送出 Messenger")
    parser.add_argument("--stats", action="store_true", help="僅顯示統計")
    parser.add_argument("--delay-min", type=int, default=300, help="訊息間最小延遲秒數 (預設 300)")
    parser.add_argument("--delay-max", type=int, default=600, help="訊息間最大延遲秒數 (預設 600)")
    parser.add_argument("--image", type=str, default="/home/hsuyungfeng/DevSoft/doctor-toolbox-post/assets/doctor-toolbox-post.png", help="廣告配圖路徑 (預設為 assets 下的圖)")
    parser.add_argument("--proxy", type=str, help="代理伺服器網址 (例如 http://127.0.0.1:8080)")
    args = parser.parse_args()

    city = args.city
    print("=" * 60)
    print(f"🏥 醫師工具箱 — {city} 逐診所流水線 (SQLite Database Backend)")
    print(f"   模式: {'🧪 DRY-RUN' if args.dry_run else '🚀 正式'} | 上限: {args.limit} 筆")
    print("=" * 60)

    # 1. 顯示該城市的統計狀態 / Display county stats
    show_stats(city)

    if args.stats:
        return

    # 2. 獲取待處理名單 / Query candidate list
    to_process = db.get_city_candidates(city, args.limit)
    print(f"\n📋 {city} 待處理候選: {len(to_process)} 筆")

    if not to_process:
        print("✅ 沒有待處理的診所候選名單 / No pending candidates.")
        return

    # 3. 啟動瀏覽器 / Launch CloakBrowser
    print(f"🚀 啟動 CloakBrowser (profile: {PROFILE_DIR})...")
    from cloakbrowser import launch_persistent_context
    
    chrome_args = ["--fingerprint=77889"]
    if getattr(args, 'proxy', None):
        chrome_args.append(f"--proxy-server={args.proxy}")
        print(f"  🔒 使用代理伺服器: {args.proxy}")
        
    try:
        browser = launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            humanize=True,
            timezone="Asia/Taipei",
            locale="zh-TW",
            args=chrome_args
        )
    except Exception as e:
        print(f"❌ 瀏覽器啟動失敗: {e}")
        sys.exit(1)

    page = browser.pages[0] if browser.pages else browser.new_page()

    success_count = 0
    fail_count = 0
    consecutive_failures = 0

    # 4. 逐診所執行 / Loop clinics
    for seq, row in enumerate(to_process):
        if interrupted:
            print("\n🛑 中斷訊號，安全退出...")
            break

        if consecutive_failures >= 3:
            print("\n🛑 連續 3 次發送失敗，觸發斷路器安全限制 (Halt Circuit Breaker)！終止執行。")
            break

        clinic_id = row['id']
        name = row['name']
        addr = row['address']
        dept = row['specialty'] or '一般科'
        fb_url = row['fb_url']
        email = row['email']
        messenger = row['messenger']
        intro = row['intro']
        post_text = row['latest_post']
        copy = row['personalized_copy']
        ab_variant = row['ab_variant']
        website_url = row.get('website_url')

        print(f"\n{'━'*60}")
        print(f"[{seq+1}/{len(to_process)}] 🏥 {name} ({dept})")
        print(f"  📍 {addr}")
        print(f"{'━'*60}")

        # ─── 步驟 1: 尋找與爬取 FB 專頁 / Scrape FB ───
        # 如果資料庫無 email 或無 fb_url，優先嘗試使用 Firecrawl 爬取官網補充
        if (not email or not fb_url or fb_url == 'not_found'):
            print("  🔍 步驟 1a: 嘗試搜尋診所官網進行 Firecrawl 結構化爬取...")
            website = website_url
            if not website:
                website = search_clinic_website(page, name)
                if website:
                    db.update_clinic_website(clinic_id, website)
                    print(f"    ✅ 搜尋到診所官網並已寫入資料庫快取: {website}")
                else:
                    db.update_clinic_website(clinic_id, 'not_found')
                    website = 'not_found'
                    print("    ⚠️ 未找到診所官網，已標記快取為 not_found")
            elif website == 'not_found':
                print("    ⚠️ 官網先前已標記為未找到，跳過搜尋。")
            else:
                print(f"    ✅ 讀取到資料庫快取官網: {website}")

            if website and website != 'not_found':
                try:
                    from firecrawl_scraper import scrape_url_local
                    scrape_res = scrape_url_local(website)
                    if scrape_res.get('success'):
                        # Found emails
                        emails = scrape_res.get('emails', [])
                        if emails:
                            email = emails[0]
                            print(f"    📧 Firecrawl 提取到 Email: {email}")
                        
                        # Found Facebook links
                        fb_links = scrape_res.get('facebook_links', [])
                        if fb_links and (not fb_url or fb_url == 'not_found'):
                            fb_url = fb_links[0]
                            print(f"    ✅ Firecrawl 提取到 FB: {fb_url}")
                        
                        db.update_clinic_fb(clinic_id, email, messenger, intro, post_text, fb_url=fb_url)
                    else:
                        print(f"    ⚠️ Firecrawl 爬取失敗: {scrape_res.get('error')}")
                except Exception as ex:
                    print(f"    ⚠️ Firecrawl 呼叫異常: {ex}")

        # 正常尋找或補全 Facebook/Messenger
        fb_valid = fb_url and fb_url != 'not_found'
        if not fb_valid:
            print("  🔍 步驟 1b: 搜尋 Facebook 頁面...")
            fb_url = search_clinic_facebook(page, name)

            if fb_url:
                print(f"  ✅ 找到 FB: {fb_url}")
                print("  🔍 步驟 1c: 爬取 FB 頁面詳情...")
                details = scrape_fb_page_details(page, fb_url, name)
                
                email = details.get('email', '') or email
                messenger = details.get('messenger', '')
                intro = details.get('intro', '')
                post_text = details.get('latest_post', '')
                
                db.update_clinic_fb(clinic_id, email, messenger, intro, post_text, fb_url=fb_url)
                print(f"    Messenger: {messenger}")
                print(f"    Intro: {intro[:60]}..." if intro else "    Intro: (空)")
            else:
                print("  ❌ 未找到 FB 頁面")
                db.update_clinic_status(clinic_id, 'no_fb', datetime.now().isoformat())
                db.update_clinic_fb_url(clinic_id, 'not_found')
                fail_count += 1
                continue
        else:
            print(f"  ✅ 步驟 1b: FB 已存在 ({fb_url})")
            # 補爬欄位 / Supplement missing info
            if (not messenger or messenger == 'not_found') or (not intro or intro == 'not_found'):
                print("  🔍 步驟 1c: 補充爬取 FB 頁面詳情...")
                details = scrape_fb_page_details(page, fb_url, name)
                
                email = details.get('email', '') or email
                if not messenger or messenger == 'not_found':
                    messenger = details.get('messenger', '')
                if not intro or intro == 'not_found':
                    intro = details.get('intro', '')
                    post_text = details.get('latest_post', '') or post_text
                
                db.update_clinic_fb(clinic_id, email, messenger, intro, post_text)

        # ─── 步驟 2: A/B 測試文案生成與管理 / A/B Copywriting ───
        if not copy:
            print("  ✍️ 步驟 2: 分流並生成行銷文案...")
            # 若無分組，隨機指派 A/B 組別 / Assign random A/B variant if empty
            if not ab_variant:
                ab_variant = random.choice(['generic-v1', 'personalized-v1'])
                
            if ab_variant == 'generic-v1':
                copy = GENERIC_COPY
                print("    [A/B 組別: generic-v1] 套用通用文案模板")
            else:
                print("    [A/B 組別: personalized-v1] 調用本地 LLM 生成個人化文案...")
                copy = generate_copy(name, dept, intro, post_text)
                
            db.update_clinic_copy(clinic_id, copy, ab_variant)
            print(f"    最終選定文案 ({len(copy)} 字): {copy[:80]}...")
        else:
            print(f"  ✅ 步驟 2: 文案已存在 (組別: {ab_variant}, {len(copy)} 字)")

        # ─── 步驟 3: 多管道發送決策鏈 / Multichannel Outreach Funnel ───
        # Prepend personalized greeting header if not already present
        greeting = f"{name} 醫療團隊您好！\n\n"
        send_copy = copy
        if not send_copy.strip().startswith(name) and "醫療團隊您好" not in send_copy:
            send_copy = greeting + send_copy

        ok = False
        status = 'failed'

        # 優先級 1: Email 發送 (若有 email 欄位)
        email_valid = email and '@' in email
        if email_valid and not args.dry_run:
            print(f"  ✉️ 優先級 1: 正在發送推廣郵件給 {email}...")
            try:
                from send_email import send_marketing_email, get_marketing_html_template
                email_html = get_marketing_html_template(send_copy)
                ok, status = send_marketing_email(email, f"【醫師工具箱】AI 語音病歷生成器 ── {name} 專屬體驗邀請", email_html, image_path=args.image)
                if ok:
                    status = 'email_sent'
                else:
                    print(f"    ⚠️ Email 發送失敗: {status}，準備嘗試 Messenger 私訊...")
            except Exception as ex:
                print(f"    ⚠️ Email 發送異常: {ex}，準備嘗試 Messenger 私訊...")

        # 優先級 2: Messenger 私訊 (若 Email 發送失敗或不存在)
        if not ok:
            msg_valid = messenger and messenger != 'not_found' and messenger.startswith('http')
            if msg_valid:
                print(f"  📤 優先級 2: {'DRY-RUN 測試' if args.dry_run else '正式發送'} Messenger 訊息...")
                ok, status = send_messenger_message(page, messenger, send_copy, dry_run=args.dry_run, image_path=args.image)
            else:
                print("  ⚠️ 無 Messenger 連結，直接嘗試 Facebook 貼文留言...")

        # 優先級 3: Facebook 貼文留言 (若私訊失敗或無私訊管道)
        if (not ok or status == 'delivery_failed' or status == 'no_messenger') and not args.dry_run:
            if fb_url and fb_url != 'not_found':
                print(f"  ⚠️ Messenger 無法發送 (狀態: {status})，嘗試在 Facebook 貼文留言...")
                from post_clinics import post_facebook_comment
                comment_success = post_facebook_comment(page, fb_url, send_copy)
                if comment_success:
                    print("  ✅ Facebook 貼文留言成功！")
                    ok = True
                    status = 'fb_commented'
                else:
                    print("  ❌ Facebook 貼文留言失敗！")
            else:
                print("  ❌ 無可用發送管道且無 FB 專頁，無法進行任何行銷")

        # ─── 步驟 4: 更新狀態標記與日誌 / Save Status ───
        db.update_clinic_status(clinic_id, status, datetime.now().isoformat())

        # 紀錄日誌 / Log outreach entry
        log_outreach({
            'clinic_id': clinic_id,
            'clinic_name': name,
            'city': city,
            'dept': dept,
            'messenger': messenger,
            'status': status,
            'ab_variant': ab_variant,
            'timestamp': datetime.now().isoformat(),
        })

        if ok:
            success_count += 1
            consecutive_failures = 0
            print(f"  ✅ 步驟 4: 資料庫更新成功 status={status}")
        else:
            fail_count += 1
            consecutive_failures += 1
            print(f"  ❌ 步驟 4: 資料庫發送失敗 status={status}")

        # 診所與診所之間的發送隨機延遲冷卻 / Random delay between clinics
        if seq < len(to_process) - 1 and not interrupted:
            delay = random.randint(args.delay_min, args.delay_max)
            print(f"\n  ⏳ 慢速冷卻中... {delay} 秒 ({delay/60:.1f} 分鐘) 後處理下一間...")
            for _ in range(delay):
                if interrupted:
                    break
                time.sleep(1)

    # 關閉瀏覽器 / Close browser
    try:
        browser.close()
    except:
        pass

    # 最終狀態回報 / Final stats
    print(f"\n{'='*60}")
    print(f"🏁 {city} 逐診所行銷流水線執行完畢！")
    print(f"  ✅ 成功: {success_count}")
    print(f"  ❌ 失敗: {fail_count}")
    print(f"{'='*60}")
    show_stats(city)

    # 自動同步 SQLite 變更回 CSV / Automatically sync SQLite back to CSV
    print("\n🔄 正在自動同步資料庫變更回 CSV 檔案...")
    try:
        import subprocess
        res = subprocess.run(["python3", "sync_db_to_csv.py"], capture_output=True, text=True)
        if res.returncode == 0:
            print("✅ 自動 CSV 同步完成！")
        else:
            print(f"⚠️ 自動 CSV 同步失敗: {res.stderr}")
    except Exception as e:
        print(f"⚠️ 自動 CSV 同步異常: {e}")

if __name__ == "__main__":
    main()
