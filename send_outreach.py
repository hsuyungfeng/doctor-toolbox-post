#!/usr/bin/env python3
"""
Send personalized outreach messages slowly via Facebook Messenger.
Loads clinics西醫.csv, opens Messenger URLs in CloakBrowser, types the copy, and sends it.
Includes random delay of 5-10 minutes between messages.
"""
import csv
import json
import time
import os
import sys
import random
import argparse
import signal
from datetime import datetime
from pathlib import Path
from cloakbrowser import launch_persistent_context

# === Paths ===
WORKSPACE_DIR = Path(__file__).resolve().parent
PROFILE_DIR = WORKSPACE_DIR / "browser_profile"
CSV_PATH = "/home/hsuyungfeng/文件/doctor-toolbox-post/clinics西醫.csv"
if not os.path.exists(os.path.dirname(CSV_PATH)):
    CSV_PATH = str(WORKSPACE_DIR / "clinics西醫.csv")

OUTREACH_LOG_PATH = "/home/hsuyungfeng/文件/doctor-toolbox-post/outreach_sent_log.jsonl"
if not os.path.exists(os.path.dirname(OUTREACH_LOG_PATH)):
    OUTREACH_LOG_PATH = str(WORKSPACE_DIR / "outreach_sent_log.jsonl")

csv_header = []
csv_rows = []
interrupted = False

USE_SQLITE = False

def load_data():
    global csv_header, csv_rows, CSV_PATH, USE_SQLITE
    
    db_file = WORKSPACE_DIR / "clinics.db"
    if db_file.exists() and CSV_PATH != "dummy.csv" and not csv_rows:
        import sqlite3
        print(f"🗄️ [SQLite] 載入資料庫: {db_file}")
        conn = sqlite3.connect(str(db_file))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clinics")
        rows = cursor.fetchall()
        
        csv_header = [
            '醫事機構代碼', '醫事機構名稱', '醫事機構種類', '電話', '地址', 
            '分區業務組', '特約類別', '服務項目', '診療科別', '終止合約或歇業日期', 
            '固定看診時段', '備註', '縣市別代碼', '合約起日', 'FB_URL', 'Email', 
            'Messenger', 'Intro', 'Latest_Post', 'Personalized_Copy', 
            'Messenger_Status', 'Outreach_Time', 'ab_variant'
        ]
        
        col_map = {
            'id': '醫事機構代碼', 'name': '醫事機構名稱', 'category': '醫事機構種類',
            'phone': '電話', 'address': '地址', 'division': '分區業務組',
            'contract_type': '特約類別', 'services': '服務項目', 'specialty': '診療科別',
            'termination_date': '終止合約或歇業日期', 'hours': '固定看診時段',
            'notes': '備註', 'county_code': '縣市別代碼', 'start_date': '合約起日',
            'fb_url': 'FB_URL', 'email': 'Email', 'messenger': 'Messenger',
            'intro': 'Intro', 'latest_post': 'Latest_Post', 'personalized_copy': 'Personalized_Copy',
            'messenger_status': 'Messenger_Status', 'outreach_time': 'Outreach_Time',
            'ab_variant': 'ab_variant'
        }
        rev_map = {v: k for k, v in col_map.items()}
        
        csv_rows = []
        for r in rows:
            row_list = []
            for col in csv_header:
                db_col = rev_map.get(col)
                val = r[db_col] if db_col in r.keys() else ''
                row_list.append(str(val) if val is not None else '')
            csv_rows.append(row_list)
            
        conn.close()
        USE_SQLITE = True
        print(f"  - 成功載入 {len(csv_rows)} 筆診所資料")
        return

    print(f"📂 [CSV] 載入資料庫: {CSV_PATH}")
    if not os.path.exists(CSV_PATH):
        local_csv = WORKSPACE_DIR / "clinics西醫.csv"
        if local_csv.exists():
            CSV_PATH = str(local_csv)
        else:
            print("❌ 找不到 CSV 檔案")
            sys.exit(1)
            
    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        csv_header = list(next(reader))
        csv_rows = [list(row) for row in reader]

    # Filter out Traditional Chinese Medicine (中醫) and Dentists (牙醫/牙科)
    idx_name = csv_header.index('醫事機構名稱')
    idx_dept = csv_header.index('診療科別') if '診療科別' in csv_header else -1
    
    filtered_rows = []
    for row in csv_rows:
        if len(row) <= idx_name:
            continue
        name = row[idx_name].strip()
        dept = row[idx_dept].strip() if (idx_dept != -1 and len(row) > idx_dept) else ""
        
        is_forbidden = False
        for term in ["中醫", "牙醫", "牙科"]:
            if term in name or term in dept:
                is_forbidden = True
                break
        
        if not is_forbidden:
            filtered_rows.append(row)
        else:
            print(f"  [Filter] 排除 中醫/牙醫 診所: {name} ({dept})")
            
    csv_rows = filtered_rows
        
    # Ensure Messenger_Status and Outreach_Time columns exist
    if 'Messenger_Status' not in csv_header:
        csv_header.append('Messenger_Status')
    if 'Outreach_Time' not in csv_header:
        csv_header.append('Outreach_Time')
        
    # Pad rows
    for row in csv_rows:
        while len(row) < len(csv_header):
            row.append('')

def save_data():
    global csv_header, csv_rows, CSV_PATH, USE_SQLITE
    if USE_SQLITE:
        import sqlite3
        db_file = WORKSPACE_DIR / "clinics.db"
        print(f"💾 [SQLite] 儲存資料庫...")
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        
        idx_id = csv_header.index('醫事機構代碼')
        idx_status = csv_header.index('Messenger_Status')
        idx_time = csv_header.index('Outreach_Time')
        
        for row in csv_rows:
            clinic_id = row[idx_id]
            status_text = row[idx_status]
            time_text = row[idx_time]
            
            cursor.execute("""
            UPDATE clinics SET 
                messenger_status = ?, outreach_time = ?
            WHERE id = ?
            """, (status_text, time_text, clinic_id))
            
        conn.commit()
        conn.close()
        print("  ✅ 資料庫更新完成 / Database updated.")
        return

    print(f"\n💾 [CSV] 正在儲存 CSV 資料庫...")
    try:
        temp_csv = CSV_PATH + ".tmp"
        with open(temp_csv, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(csv_header)
            writer.writerows(csv_rows)
        if os.path.exists(CSV_PATH):
            os.remove(CSV_PATH)
        os.rename(temp_csv, CSV_PATH)
        print("  ✅ 成功存檔！")
    except Exception as e:
        print(f"  ❌ 存檔失敗: {e}")

def log_outreach(entry):
    try:
        with open(OUTREACH_LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    except Exception as e:
        print(f"  ⚠️ 寫入日誌失敗: {e}")

def handle_signal(sig, frame):
    global interrupted
    print("\n🛑 偵測到中斷訊號 (Ctrl+C)... 正在儲存進度並關閉...")
    interrupted = True

signal.signal(signal.SIGINT, handle_signal)

def send_messenger_message(page, messenger_url, copy_text, dry_run=False):
    """Open Messenger chat, type the personalized copy, and send it."""
    # Convert m.me or messenger.com links to facebook.com/messages/t/ to bypass domain authentication issues
    target_url = messenger_url
    if "facebook.com/messages/t/" not in messenger_url:
        parts = messenger_url.rstrip('/').split('/')
        if parts:
            username = parts[-1].split('?')[0]
            if username:
                target_url = f"https://www.facebook.com/messages/t/{username}"

    print(f"  🌐 開啟 FB 訊息對話框: {target_url} (原網址: {messenger_url})")
    page.goto(target_url)
    time.sleep(10) # Wait for page load and redirections
    
    # Check if Messenger is blocked or redirecting
    is_login_page = page.evaluate("""() => {
        const text = document.body.innerText;
        return text.includes('登入 Facebook') || text.includes('Log In') || !!document.querySelector('#login_form');
    }""")
    if is_login_page:
        print("  ⚠️ 偵測到未登入或需要登入狀態！請先執行 python3 setup_session.py 登入臉書。")
        return False, "login_required"
        
    # Locate textbox
    print("  🔍 定位輸入框...")
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
        page.screenshot(path="/tmp/outreach_textbox_failed.png")
        print("  ❌ 找不到可寫入的 Messenger 輸入框。")
        return False, "textbox_not_found"
        
    print("  📝 聚焦成功，使用 page.keyboard.insert_text() 插入文字...")
    page.keyboard.insert_text(copy_text)
    time.sleep(2)
    
    if dry_run:
        page.screenshot(path="/tmp/outreach_dryrun.png")
        print("  🚀 [Dry Run] 已成功定位輸入框並貼上文案，跳過發送動作。")
        return True, "dry_run"
        
    # Press Enter or Click Send button
    print("  🚀 正在發送訊息...")
    page.keyboard.press("Enter")
    time.sleep(3)
    
    # Click fallback Send button
    page.evaluate("""() => {
        const sendBtns = Array.from(document.querySelectorAll('[aria-label="傳送"], [aria-label="Send"], [role="button"]'));
        for (const btn of sendBtns) {
            const label = btn.getAttribute('aria-label') || '';
            if (label === '傳送' || label === 'Send') {
                btn.click();
                break;
            }
        }
    }""")
    
    time.sleep(5)
    
    # Verify by checking page text for delivery failure / block
    failed_delivery = page.evaluate("""() => {
        const text = document.body.innerText;
        const blockKeywords = [
            '無法傳送',
            '無法送出',
            '你目前無法使用此功能',
            '暫時被限制',
            "You can't send messages",
            'Could not send',
            'Something went wrong',
            '限制',
            'Blocked'
        ];
        for (const kw of blockKeywords) {
            if (text.includes(kw)) {
                return kw;
            }
        }
        return null;
    }""")
    
    if failed_delivery:
        screenshot_path = f"/tmp/outreach_failed_block_{int(time.time())}.png"
        page.screenshot(path=screenshot_path)
        print(f"  🛑 警告：偵測到發送失敗或帳號限制！關鍵字: {failed_delivery}")
        print(f"  截圖已儲存至: {screenshot_path}")
        return False, "delivery_failed"

    # Verify by taking screenshot
    screenshot_path = f"/tmp/outreach_sent_{int(time.time())}.png"
    page.screenshot(path=screenshot_path)
    print(f"  ✅ 發送完畢。截圖已儲存至: {screenshot_path}")
    return True, "sent"

def main():
    parser = argparse.ArgumentParser(description="醫師工具箱慢速自動化 Messenger 開發程式")
    parser.add_argument("--dry-run", action="store_true", help="測試定位與輸入而不實際送出")
    parser.add_argument("--delay-min", type=int, default=300, help="最小間隔延遲 (秒，預設 300秒/5分鐘)")
    parser.add_argument("--delay-max", type=int, default=600, help="最大間隔延遲 (秒，預設 600秒/10分鐘)")
    parser.add_argument("--limit", type=int, default=10, help="本次執行最大發送筆數")
    args = parser.parse_args()
    
    load_data()
    
    idx_name = csv_header.index('醫事機構名稱')
    idx_msg = csv_header.index('Messenger')
    idx_copy = csv_header.index('Personalized_Copy')
    idx_status = csv_header.index('Messenger_Status')
    idx_time = csv_header.index('Outreach_Time')
    
    # Find candidates
    candidates = []
    for i, row in enumerate(csv_rows):
        name = row[idx_name].strip()
        msg_url = row[idx_msg].strip()
        copy = row[idx_copy].strip()
        status = row[idx_status].strip()
        
        # We need a valid Messenger link and a personalized copy.
        # Dry-run: allow both empty status and 'sent' status (for re-testing).
        # Normal mode: only empty status.
        if msg_url and msg_url != 'not_found' and msg_url.startswith('http') and copy:
            if args.dry_run:
                if status in ('', 'sent'):
                    candidates.append(i)
            else:
                if not status:
                    candidates.append(i)
            
    print(f"\n📊 待發送的 Messenger 開發候選名單: {len(candidates)} 筆")
    if not candidates:
        if args.dry_run:
            print("  - 沒有符合條件的診所（含已發送）。請確認 CSV 中是否有 Messenger 連結與 Personalized_Copy。")
        else:
            print("  - 沒有符合條件且尚未發送的診所。請確認 CSV 中是否有 Messenger 連結與 Personalized_Copy。")
        return
        
    # Limit number of sends in one run
    to_send = candidates[:args.limit]
    print(f"🎬 本次預計處理前 {len(to_send)} 筆診所。")
    
    # Launch browser
    print(f"\n🚀 啟動 CloakBrowser 載入 Profile: {PROFILE_DIR}")
    try:
        browser_context = launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=True,
            humanize=True,
            timezone="Asia/Taipei",
            locale="zh-TW",
            args=["--fingerprint=77889"]
        )
    except Exception as e:
        print(f"❌ 瀏覽器啟動失敗: {e}")
        sys.exit(1)
        
    page = browser_context.pages[0] if browser_context.pages else browser_context.new_page()
    
    success_count = 0
    warning_count = 0
    delay_multiplier = 1.0
    
    try:
        for index, row_idx in enumerate(to_send):
            if interrupted:
                break
                
            row = csv_rows[row_idx]
            clinic_name = row[idx_name].strip()
            msg_url = row[idx_msg].strip()
            copy_text = row[idx_copy].strip()
            
            print(f"\n[{index+1}/{len(to_send)}] 正在向 {clinic_name} 發送個人化開發訊息...")
            
            success, result_status = send_messenger_message(page, msg_url, copy_text, dry_run=args.dry_run)
            
            if success:
                warning_count = 0
                delay_multiplier = max(1.0, delay_multiplier * 0.9)
                
                # If it's a dry run, we don't save the status to CSV to prevent
                # consuming the candidate before the actual outreach campaign.
                if not args.dry_run:
                    row[idx_status] = result_status
                    row[idx_time] = datetime.now().isoformat()
                    save_data()
                else:
                    print(f"    [Dry Run] 跳過更新 CSV 中的狀態，保留候選資格。")
                
                # Log progress
                log_entry = {
                    "clinic_name": clinic_name,
                    "messenger_url": msg_url,
                    "status": result_status,
                    "timestamp": datetime.now().isoformat() if args.dry_run else row[idx_time],
                    "delay_multiplier": delay_multiplier
                }
                log_outreach(log_entry)
                success_count += 1
            else:
                print(f"    ❌ 向 {clinic_name} 發送失敗，錯誤代碼: {result_status}")
                if result_status == "login_required":
                    print("🛑 偵測到需要登入，終止後續發送。")
                    break
                elif result_status == "delivery_failed":
                    warning_count += 1
                    delay_multiplier *= 2.0
                    print(f"  ⚠️ 偵測到 Facebook 限制/發送失敗。警告次數: {warning_count}/3，延遲乘數加倍至: {delay_multiplier:.1f}x")
                    
                    row[idx_status] = "backoff"
                    row[idx_time] = datetime.now().isoformat()
                    log_entry = {
                        "clinic_name": clinic_name,
                        "messenger_url": msg_url,
                        "status": "backoff",
                        "timestamp": row[idx_time],
                        "delay_multiplier": delay_multiplier
                    }
                    log_outreach(log_entry)
                    save_data()
                    
                    if warning_count >= 3:
                        row[idx_status] = "session_halted"
                        save_data()
                        log_entry["status"] = "session_halted"
                        log_outreach(log_entry)
                        print("\n🛑🛑🛑 錯誤：連續偵測到 3 次發送限制！啟動熔斷保護機制，停止所有外展活動！ 🛑🛑🛑")
                        try:
                            browser_context.close()
                        except:
                            pass
                        sys.exit(1)
                else:
                    row[idx_status] = result_status
                    row[idx_time] = datetime.now().isoformat()
                    log_entry = {
                        "clinic_name": clinic_name,
                        "messenger_url": msg_url,
                        "status": result_status,
                        "timestamp": row[idx_time]
                    }
                    log_outreach(log_entry)
                    save_data()
                    
            # Wait between sends to avoid bot detection
            if index < len(to_send) - 1 and not interrupted:
                if args.dry_run:
                    delay = random.randint(5, 10)  # Short delay for dry-run
                else:
                    min_delay = int(args.delay_min * delay_multiplier)
                    max_delay = int(args.delay_max * delay_multiplier)
                    delay = random.randint(min_delay, max_delay)
                print(f"⏳ 防封鎖冷卻：將隨機等待 {delay} 秒 (約 {delay/60:.1f} 分鐘，延遲乘數 {delay_multiplier:.1f}x) 後再進行下一筆...")
                
                # Sleep in small steps so we can interrupt quickly
                for _ in range(delay):
                    if interrupted:
                        break
                    time.sleep(1)
                    
    except Exception as e:
        print(f"\n❌ 發送程序異常中斷: {e}")
    finally:
        print("\n💾 正在儲存資料並關閉瀏覽器...")
        try:
            browser_context.close()
        except:
            pass
        save_data()
        
    print(f"\n📊 執行完成：成功發送/模擬 {success_count} 筆 Messenger 開發信。")

if __name__ == "__main__":
    main()
