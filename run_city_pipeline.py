#!/usr/bin/env python3
"""
Per-Clinic Pipeline: Scrape → Generate Copy → Send → Mark (one clinic at a time)

For each clinic in the target city:
  1. Google search → find FB page
  2. Scrape FB page → Intro, Latest_Post, Messenger link
  3. Generate personalized copy via local LLM
  4. Send via Facebook Messenger
  5. Mark sent + timestamp in CSV, save immediately

Usage:
  python3 run_city_pipeline.py --city 台中 --limit 20
  python3 run_city_pipeline.py --city 台中 --limit 5 --dry-run
  python3 run_city_pipeline.py --city 台中 --stats
"""

import argparse
import csv
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

# === Config ===
WORKSPACE_DIR = Path(__file__).resolve().parent
CSV_PATH = str(WORKSPACE_DIR / "clinics西醫.csv")
CACHE_PATH = str(WORKSPACE_DIR / "clinic_links.json")
LOG_PATH = str(WORKSPACE_DIR / "outreach_sent_log.jsonl")
LLM_API_URL = os.environ.get("LLM_API_URL", "http://localhost:8080/v1/chat/completions")
PROFILE_DIR = WORKSPACE_DIR / "browser_profile"

# City aliases
CITY_ALIASES = {
    "台中": ["台中", "臺中"], "臺中": ["台中", "臺中"],
    "台北": ["台北", "臺北"], "臺北": ["台北", "臺北"],
    "新北": ["新北"], "桃園": ["桃園"],
    "台南": ["台南", "臺南"], "臺南": ["台南", "臺南"],
    "高雄": ["高雄"], "基隆": ["基隆"], "新竹": ["新竹"],
    "嘉義": ["嘉義"], "彰化": ["彰化"], "南投": ["南投"],
    "雲林": ["雲林"], "屏東": ["屏東"], "宜蘭": ["宜蘭"],
    "花蓮": ["花蓮"], "苗栗": ["苗栗"],
    "台東": ["台東", "臺東"], "臺東": ["台東", "臺東"],
    "澎湖": ["澎湖"], "金門": ["金門"], "連江": ["連江"],
}

GENERIC_COPY = """您好！我是醫師工具箱的開發團隊。

我們開發了一套 AI 語音病歷生成工具，可以幫診所：

🎙️ 語音即時轉錄 → AI 自動生成 SOAP 病歷
💬 LINE OA 整合 → 自動回覆患者常見問題
📋 病史整合 → 患者病史一鍵掌握

特點：
✅ 任何系統都能橋接，不須更換 HIS
✅ 符合健保規範的 SOAP 病歷格式
✅ 高用量方案（LINE + Voice Record 每月各 1000 人次）

歡迎免費試用，了解醫師工具箱如何節省您的病歷時間！

👉 https://doctor-toolbox.com/

如有興趣歡迎回覆，或留下您的聯絡方式，我們會安排示範。"""

interrupted = False

def handle_signal(sig, frame):
    global interrupted
    print("\n🛑 收到中斷訊號，完成目前診所後安全退出...")
    interrupted = True

signal.signal(signal.SIGINT, handle_signal)


# ═══════════════════════════════════════════════════════════════════
# CSV Helpers
# ═══════════════════════════════════════════════════════════════════

def load_csv():
    print(f"📂 載入 CSV: {CSV_PATH}")
    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = list(next(reader))
        rows = [list(row) for row in reader]

    required = ['FB_URL', 'Email', 'Messenger', 'Intro', 'Latest_Post',
                'Personalized_Copy', 'Messenger_Status', 'Outreach_Time']
    for col in required:
        if col not in header:
            header.append(col)
    for row in rows:
        while len(row) < len(header):
            row.append('')

    return header, rows


def save_csv(header, rows):
    temp = CSV_PATH + ".tmp"
    with open(temp, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    if os.path.exists(CSV_PATH):
        os.remove(CSV_PATH)
    os.rename(temp, CSV_PATH)


def log_outreach(entry):
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')


def filter_city_candidates(header, rows, city):
    """Return row indices for clinics in the city that haven't been sent yet."""
    aliases = CITY_ALIASES.get(city, [city])
    idx_addr = header.index('地址')
    idx_name = header.index('醫事機構名稱')
    idx_dept = header.index('診療科別') if '診療科別' in header else -1
    idx_status = header.index('Messenger_Status')

    candidates = []
    for i, row in enumerate(rows):
        addr = row[idx_addr] if len(row) > idx_addr else ''
        name = row[idx_name] if len(row) > idx_name else ''
        dept = row[idx_dept] if idx_dept >= 0 and len(row) > idx_dept else ''
        status = row[idx_status].strip()

        # Skip TCM / dentist
        if any(t in name or t in dept for t in ["中醫", "牙醫", "牙科"]):
            continue
        # Skip already sent
        if status in ('sent', 'dry_run'):
            continue
        # Must be in target city
        if any(alias in addr for alias in aliases):
            candidates.append(i)

    return candidates


def show_stats(header, rows, city):
    aliases = CITY_ALIASES.get(city, [city])
    idx_addr = header.index('地址')
    idx_name = header.index('醫事機構名稱')
    idx_dept = header.index('診療科別') if '診療科別' in header else -1
    idx_fb = header.index('FB_URL')
    idx_msg = header.index('Messenger')
    idx_copy = header.index('Personalized_Copy')
    idx_status = header.index('Messenger_Status')

    total = has_fb = has_msg = has_copy = sent = 0

    for row in rows:
        addr = row[idx_addr]
        name = row[idx_name]
        dept = row[idx_dept] if idx_dept >= 0 else ''
        if any(t in name or t in dept for t in ["中醫", "牙醫", "牙科"]):
            continue
        if not any(a in addr for a in aliases):
            continue

        total += 1
        fb = row[idx_fb].strip()
        if fb and fb != 'not_found': has_fb += 1
        msg = row[idx_msg].strip()
        if msg and msg != 'not_found' and msg.startswith('http'): has_msg += 1
        if row[idx_copy].strip(): has_copy += 1
        if row[idx_status].strip() in ('sent', 'dry_run'): sent += 1

    print(f"\n{'='*60}")
    print(f"📊 {city} 診所統計")
    print(f"{'='*60}")
    print(f"  診所總數 (排除中醫/牙醫):  {total}")
    print(f"  已有 FB 頁面:              {has_fb}")
    print(f"  已有 Messenger:            {has_msg}")
    print(f"  已有文案:                  {has_copy}")
    print(f"  已發送:                    {sent}")
    print(f"  待處理:                    {total - sent}")
    print(f"{'='*60}")


# ═══════════════════════════════════════════════════════════════════
# Step 1: Scrape FB (reuse logic from scrape_fb_info.py)
# ═══════════════════════════════════════════════════════════════════

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
        print(f"    ❌ LLM 呼叫失敗: {e}")
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
4. 優惠資費：LINE + Voice Record 每月各 1000 人次，只要 1000 元。由徐永峰醫師監製。

請返回 JSON 格式的數據，格式如下：
{{
    "personalized_copy": "繁體中文開發文案，長度在 100-150 字之間",
    "specialty_tag": "識別出的診所科別（例如：小兒科、耳鼻喉科等）"
}}

文案生成要求：
1. 必須以繁體中文撰寫，字數控制在 100-150 字之間，簡潔有禮。
2. 必須精準結合該診所的特色。
3. 不要使用任何罐頭問候語，第一句直接切入「針對貴診所在...方面的特色，醫師工具箱能提供...協助」。
4. 結尾附上免費體驗連結：https://doctor-toolbox.com/ai-soap-generator。
5. 嚴禁包含醫療法禁用的誇大詞彙（如「最佳」、「最先進」、「保證療效」、「根治」、「全台第一」）。

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
            simplified = ["亲", "医", "这", "国", "诊", "体", "会", "电", "话", "设", "备", "进", "专", "优", "疗"]
            for c in simplified:
                if c in copy:
                    raise ValueError(f"檢測到簡體字：'{c}'")

            return copy

        except Exception as e:
            print(f"    ⚠️ [第 {attempt+1} 次] 文案驗證失敗: {e}")

    print("    ❌ 嘗試次數耗盡，使用通用文案")
    return GENERIC_COPY


# ═══════════════════════════════════════════════════════════════════
# Step 3: Send Messenger
# ═══════════════════════════════════════════════════════════════════

def send_messenger_message(page, messenger_url, copy_text, dry_run=False):
    """Open Messenger chat, type copy, send it. Returns (success, status)."""
    # Convert m.me → facebook.com/messages/t/
    target_url = messenger_url
    if "facebook.com/messages/t/" not in messenger_url:
        parts = messenger_url.rstrip('/').split('/')
        if parts:
            username = parts[-1].split('?')[0]
            if username:
                target_url = f"https://www.facebook.com/messages/t/{username}"

    print(f"  📤 開啟: {target_url}")
    page.goto(target_url)
    time.sleep(10)

    # Check login
    is_login = page.evaluate("""() => {
        const text = document.body.innerText;
        return text.includes('登入 Facebook') || text.includes('Log In') || !!document.querySelector('#login_form');
    }""")
    if is_login:
        print("  ⚠️ 未登入！請先執行 import_cookies.py")
        return False, "login_required"

    # Locate textbox and insert text
    print("  🔍 定位輸入框...")
    inserted = page.evaluate("""(textToInsert) => {
        const boxes = Array.from(document.querySelectorAll(
            "div[contenteditable='true'], [role='textbox'], [aria-label*='訊息'], [aria-label*='Message']"
        ));
        const tb = boxes.find(el => {
            const s = window.getComputedStyle(el);
            return s.display !== 'none' && s.visibility !== 'hidden' && el.offsetHeight > 0;
        });
        if (tb) {
            tb.focus(); tb.click();
            document.execCommand('selectAll', false, null);
            document.execCommand('delete', false, null);
            document.execCommand('insertText', false, textToInsert);
            return true;
        }
        return false;
    }""", copy_text)

    if not inserted:
        page.screenshot(path="/tmp/pipeline_textbox_failed.png")
        print("  ❌ 找不到輸入框")
        return False, "textbox_not_found"

    time.sleep(2)

    if dry_run:
        page.screenshot(path="/tmp/pipeline_dryrun.png")
        print("  🧪 [DRY-RUN] 文案已貼上，跳過發送")
        return True, "dry_run"

    # Send
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

    # Verify delivery
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
        print(f"  🛑 發送失敗: {failed} (截圖: {ss})")
        return False, "delivery_failed"

    ss = f"/tmp/pipeline_sent_{int(time.time())}.png"
    page.screenshot(path=ss)
    print(f"  ✅ 發送成功！截圖: {ss}")
    return True, "sent"


# ═══════════════════════════════════════════════════════════════════
# Main Pipeline
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="逐診所完整流水線：爬取→文案→貼文→標記")
    parser.add_argument("--city", required=True, help="目標城市 (如：台中, 台北, 高雄)")
    parser.add_argument("--limit", type=int, default=20, help="處理上限筆數 (預設 20)")
    parser.add_argument("--dry-run", action="store_true", help="測試模式，不實際發送")
    parser.add_argument("--stats", action="store_true", help="僅顯示統計")
    parser.add_argument("--delay-min", type=int, default=300, help="訊息間最小延遲秒數 (預設 300)")
    parser.add_argument("--delay-max", type=int, default=600, help="訊息間最大延遲秒數 (預設 600)")
    args = parser.parse_args()

    city = args.city
    print("=" * 60)
    print(f"🏥 醫師工具箱 — {city} 逐診所流水線")
    print(f"   模式: {'🧪 DRY-RUN' if args.dry_run else '🚀 正式'} | 上限: {args.limit} 筆")
    print("=" * 60)

    header, rows = load_csv()
    print(f"  CSV 共 {len(rows)} 筆")

    show_stats(header, rows, city)

    if args.stats:
        return

    candidates = filter_city_candidates(header, rows, city)
    print(f"\n📋 {city} 待處理候選: {len(candidates)} 筆")

    if not candidates:
        print("✅ 沒有待處理的診所")
        return

    to_process = candidates[:args.limit]
    print(f"🎬 本次處理: {len(to_process)} 筆\n")

    # Column indices
    idx_name = header.index('醫事機構名稱')
    idx_addr = header.index('地址')
    idx_dept = header.index('診療科別') if '診療科別' in header else -1
    idx_fb = header.index('FB_URL')
    idx_email = header.index('Email')
    idx_msg = header.index('Messenger')
    idx_intro = header.index('Intro')
    idx_post = header.index('Latest_Post')
    idx_copy = header.index('Personalized_Copy')
    idx_status = header.index('Messenger_Status')
    idx_time = header.index('Outreach_Time')

    # Launch browser
    print(f"🚀 啟動 CloakBrowser (profile: {PROFILE_DIR})...")
    from cloakbrowser import launch_persistent_context
    try:
        browser = launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            humanize=True,
            timezone="Asia/Taipei",
            locale="zh-TW",
            args=["--fingerprint=77889"]
        )
    except Exception as e:
        print(f"❌ 瀏覽器啟動失敗: {e}")
        sys.exit(1)

    page = browser.pages[0] if browser.pages else browser.new_page()

    success_count = 0
    fail_count = 0
    consecutive_failures = 0

    for seq, row_idx in enumerate(to_process):
        if interrupted:
            print("\n🛑 中斷訊號，安全退出...")
            break

        if consecutive_failures >= 3:
            print("\n🛑 連續 3 次失敗，觸發安全斷路器，停止執行")
            break

        row = rows[row_idx]
        name = row[idx_name].strip()
        addr = row[idx_addr].strip()
        dept = row[idx_dept].strip() if idx_dept >= 0 else ''

        print(f"\n{'━'*60}")
        print(f"[{seq+1}/{len(to_process)}] 🏥 {name} ({dept})")
        print(f"  📍 {addr}")
        print(f"{'━'*60}")

        # ─── 1. Scrape FB ───
        fb_url = row[idx_fb].strip()
        messenger = row[idx_msg].strip()
        intro = row[idx_intro].strip()

        if not fb_url or fb_url == 'not_found':
            print("  🔍 步驟 1: 搜尋 Facebook 頁面...")
            fb_url = search_clinic_facebook(page, name)

            if fb_url:
                print(f"  ✅ 找到 FB: {fb_url}")
                row[idx_fb] = fb_url

                print("  🔍 步驟 1b: 爬取 FB 頁面詳情...")
                details = scrape_fb_page_details(page, fb_url, name)
                row[idx_email] = details.get('email', '')
                messenger = details.get('messenger', '')
                row[idx_msg] = messenger
                intro = details.get('intro', '')
                row[idx_intro] = intro
                row[idx_post] = details.get('latest_post', '')
                print(f"    Messenger: {messenger}")
                print(f"    Intro: {intro[:60]}..." if intro else "    Intro: (空)")
            else:
                print("  ❌ 未找到 FB 頁面")
                row[idx_fb] = 'not_found'
                row[idx_status] = 'no_fb'
                row[idx_time] = datetime.now().isoformat()
                save_csv(header, rows)
                fail_count += 1
                continue
        else:
            print(f"  ✅ 步驟 1: FB 已存在 ({fb_url})")
            # Still scrape if missing messenger/intro
            if (not messenger or messenger == 'not_found') or (not intro or intro == 'not_found'):
                print("  🔍 步驟 1b: 補充爬取 FB 頁面詳情...")
                details = scrape_fb_page_details(page, fb_url, name)
                if not messenger or messenger == 'not_found':
                    messenger = details.get('messenger', '')
                    row[idx_msg] = messenger
                if not intro or intro == 'not_found':
                    intro = details.get('intro', '')
                    row[idx_intro] = intro
                    row[idx_post] = details.get('latest_post', '') or row[idx_post]

        # Check Messenger link
        msg_valid = messenger and messenger != 'not_found' and messenger.startswith('http')
        if not msg_valid:
            print("  ⚠️ 無 Messenger 連結，跳過此診所")
            row[idx_status] = 'no_messenger'
            row[idx_time] = datetime.now().isoformat()
            save_csv(header, rows)
            fail_count += 1
            continue

        # ─── 2. Generate Copy ───
        copy = row[idx_copy].strip()
        if not copy:
            print("  ✍️ 步驟 2: 生成個人化文案...")
            post_text = row[idx_post].strip()
            copy = generate_copy(name, dept, intro, post_text)
            row[idx_copy] = copy
            print(f"    文案 ({len(copy)} 字): {copy[:80]}...")
        else:
            print(f"  ✅ 步驟 2: 文案已存在 ({len(copy)} 字)")

        # ─── 3. Send ───
        print(f"  📤 步驟 3: {'DRY-RUN' if args.dry_run else '發送'} Messenger 訊息...")
        ok, status = send_messenger_message(page, messenger, copy, dry_run=args.dry_run)

        # ─── 4. Mark ───
        row[idx_status] = status
        row[idx_time] = datetime.now().isoformat()

        # Save immediately after each clinic
        save_csv(header, rows)

        # Log
        log_outreach({
            'clinic_name': name,
            'city': city,
            'dept': dept,
            'messenger': messenger,
            'status': status,
            'timestamp': datetime.now().isoformat(),
        })

        if ok:
            success_count += 1
            consecutive_failures = 0
            print(f"  ✅ 步驟 4: 已標記 status={status}, time={row[idx_time]}")
        else:
            fail_count += 1
            consecutive_failures += 1
            print(f"  ❌ 步驟 4: 已標記 status={status}")

            if status == "delivery_failed":
                print("  🛑 FB 發送被限制，進入加倍冷卻期...")

        # Delay before next clinic (skip if last one)
        if seq < len(to_process) - 1 and not interrupted:
            delay = random.randint(args.delay_min, args.delay_max)
            print(f"\n  ⏳ 冷卻 {delay} 秒 ({delay/60:.1f} 分鐘) 後處理下一間...")
            for _ in range(delay):
                if interrupted:
                    break
                time.sleep(1)

    # Cleanup
    try:
        browser.close()
    except:
        pass

    # Final stats
    print(f"\n{'='*60}")
    print(f"🏁 {city} 流水線完成！")
    print(f"  ✅ 成功: {success_count}")
    print(f"  ❌ 失敗: {fail_count}")
    print(f"{'='*60}")

    header, rows = load_csv()
    show_stats(header, rows, city)


if __name__ == "__main__":
    main()
