#!/usr/bin/env python3
"""
City-Based Campaign Orchestrator (run_city_campaign.py)

Unified workflow:
  1. Filter clinics by city/county from CSV
  2. Scrape FB info for unscraped clinics (Google → FB page → Intro/Posts)
  3. Generate personalized copy via local LLM
  4. Send outreach via Facebook Messenger
  5. Mark sent clinics in CSV

Usage:
  python3 run_city_campaign.py --city 台中 --limit 20
  python3 run_city_campaign.py --city 台中 --limit 20 --dry-run
  python3 run_city_campaign.py --city 台中 --scrape-only     # Only scrape, don't send
  python3 run_city_campaign.py --city 台中 --generate-only   # Only generate copy
  python3 run_city_campaign.py --city 台中 --send-only       # Only send (skip scrape/generate)
  python3 run_city_campaign.py --city 台中 --stats           # Show stats only
"""

import argparse
import csv
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

# === Config ===
WORKSPACE_DIR = Path(__file__).resolve().parent
CSV_PATH = str(WORKSPACE_DIR / "clinics西醫.csv")
LLM_API_URL = os.environ.get("LLM_API_URL", "http://localhost:8080/v1/chat/completions")
VENV_PYTHON = str(WORKSPACE_DIR / ".venv" / "bin" / "python3")
if not os.path.exists(VENV_PYTHON):
    VENV_PYTHON = sys.executable

# City name aliases (common variants)
CITY_ALIASES = {
    "台中": ["台中", "臺中"],
    "臺中": ["台中", "臺中"],
    "台北": ["台北", "臺北"],
    "臺北": ["台北", "臺北"],
    "新北": ["新北"],
    "桃園": ["桃園"],
    "台南": ["台南", "臺南"],
    "臺南": ["台南", "臺南"],
    "高雄": ["高雄"],
    "基隆": ["基隆"],
    "新竹": ["新竹"],
    "嘉義": ["嘉義"],
    "彰化": ["彰化"],
    "南投": ["南投"],
    "雲林": ["雲林"],
    "屏東": ["屏東"],
    "宜蘭": ["宜蘭"],
    "花蓮": ["花蓮"],
    "台東": ["台東", "臺東"],
    "臺東": ["台東", "臺東"],
    "苗栗": ["苗栗"],
    "澎湖": ["澎湖"],
    "金門": ["金門"],
    "連江": ["連江"],
}

interrupted = False

def handle_signal(sig, frame):
    global interrupted
    print("\n🛑 收到中斷訊號，正在安全儲存...")
    interrupted = True

signal.signal(signal.SIGINT, handle_signal)


# ─── CSV Helpers ──────────────────────────────────────────────────

def load_csv():
    """Load CSV and return (header, rows)."""
    print(f"📂 載入 CSV: {CSV_PATH}")
    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = list(next(reader))
        rows = [list(row) for row in reader]

    # Ensure required columns exist
    required_cols = ['FB_URL', 'Email', 'Messenger', 'Intro', 'Latest_Post',
                     'Personalized_Copy', 'Messenger_Status', 'Outreach_Time']
    for col in required_cols:
        if col not in header:
            header.append(col)

    # Pad rows
    for row in rows:
        while len(row) < len(header):
            row.append('')

    return header, rows


def save_csv(header, rows):
    """Atomically save CSV."""
    print("💾 儲存 CSV...")
    temp = CSV_PATH + ".tmp"
    with open(temp, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    if os.path.exists(CSV_PATH):
        os.remove(CSV_PATH)
    os.rename(temp, CSV_PATH)
    print("  ✅ CSV 已儲存")


def filter_city(header, rows, city):
    """Return indices of rows matching the given city."""
    aliases = CITY_ALIASES.get(city, [city])
    idx_addr = header.index('地址')
    idx_name = header.index('醫事機構名稱')
    idx_dept = header.index('診療科別') if '診療科別' in header else -1

    city_indices = []
    for i, row in enumerate(rows):
        addr = row[idx_addr] if len(row) > idx_addr else ''
        name = row[idx_name] if len(row) > idx_name else ''
        dept = row[idx_dept] if idx_dept >= 0 and len(row) > idx_dept else ''

        # Skip TCM / dentist
        is_forbidden = any(t in name or t in dept for t in ["中醫", "牙醫", "牙科"])
        if is_forbidden:
            continue

        if any(alias in addr for alias in aliases):
            city_indices.append(i)

    return city_indices


def show_stats(header, rows, city_indices, city):
    """Print statistics for the filtered city."""
    idx_fb = header.index('FB_URL') if 'FB_URL' in header else -1
    idx_msg = header.index('Messenger') if 'Messenger' in header else -1
    idx_copy = header.index('Personalized_Copy') if 'Personalized_Copy' in header else -1
    idx_status = header.index('Messenger_Status') if 'Messenger_Status' in header else -1
    idx_intro = header.index('Intro') if 'Intro' in header else -1

    total = len(city_indices)
    has_fb = 0
    has_msg = 0
    has_copy = 0
    has_intro = 0
    sent = 0
    need_scrape = 0
    need_copy = 0
    need_send = 0

    for i in city_indices:
        row = rows[i]
        fb = row[idx_fb].strip() if idx_fb >= 0 else ''
        msg = row[idx_msg].strip() if idx_msg >= 0 else ''
        copy = row[idx_copy].strip() if idx_copy >= 0 else ''
        intro = row[idx_intro].strip() if idx_intro >= 0 else ''
        status = row[idx_status].strip() if idx_status >= 0 else ''

        fb_valid = fb and fb != 'not_found'
        msg_valid = msg and msg != 'not_found' and msg.startswith('http')

        if fb_valid:
            has_fb += 1
        if msg_valid:
            has_msg += 1
        if copy:
            has_copy += 1
        if intro and intro != 'not_found':
            has_intro += 1
        if status in ('sent', 'dry_run'):
            sent += 1

        # Needs
        if not fb_valid:
            need_scrape += 1
        if fb_valid and not copy:
            need_copy += 1
        if msg_valid and copy and status not in ('sent', 'dry_run'):
            need_send += 1

    print(f"\n{'='*60}")
    print(f"📊 {city} 診所統計")
    print(f"{'='*60}")
    print(f"  診所總數:          {total}")
    print(f"  有 FB 頁面:        {has_fb}")
    print(f"  有 Messenger:      {has_msg}")
    print(f"  有 Intro:          {has_intro}")
    print(f"  有個人化文案:       {has_copy}")
    print(f"  已發送:            {sent}")
    print(f"{'─'*60}")
    print(f"  🔍 待爬取 FB:      {need_scrape}")
    print(f"  ✍️  待生成文案:     {need_copy}")
    print(f"  📤 待發送:         {need_send}")
    print(f"{'='*60}")

    return {
        'total': total, 'has_fb': has_fb, 'has_msg': has_msg,
        'has_copy': has_copy, 'sent': sent,
        'need_scrape': need_scrape, 'need_copy': need_copy, 'need_send': need_send,
    }


# ─── Step 1: Scrape FB Info ──────────────────────────────────────

def scrape_fb_for_city(header, rows, city_indices, limit=50):
    """Run scrape_fb_info.py for clinics in the target city that lack FB data."""
    idx_fb = header.index('FB_URL')
    idx_name = header.index('醫事機構名稱')
    idx_addr = header.index('地址')

    to_scrape = []
    for i in city_indices:
        fb = rows[i][idx_fb].strip()
        if not fb or fb == '':
            to_scrape.append(i)

    if not to_scrape:
        print("\n✅ 此城市所有診所已有 FB 資料，跳過爬取。")
        return 0

    to_scrape = to_scrape[:limit]
    print(f"\n🔍 準備爬取 {len(to_scrape)} 筆診所的 FB 資訊...")

    # Call scrape_fb_info.py with city filter
    scrape_script = str(WORKSPACE_DIR / "scrape_fb_info.py")
    if os.path.exists(scrape_script):
        cmd = [VENV_PYTHON, scrape_script, "--limit", str(len(to_scrape))]
        print(f"  執行: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=str(WORKSPACE_DIR))
        return result.returncode
    else:
        print(f"  ⚠️ 找不到 {scrape_script}")
        return 1


# ─── Step 2: Generate Copy ───────────────────────────────────────

def generate_copy_for_city(header, rows, city_indices, limit=50):
    """Generate personalized copy for city clinics that have FB data but no copy yet."""
    idx_fb = header.index('FB_URL')
    idx_copy = header.index('Personalized_Copy')
    idx_name = header.index('醫事機構名稱')
    idx_dept = header.index('診療科別') if '診療科別' in header else -1
    idx_intro = header.index('Intro') if 'Intro' in header else -1
    idx_post = header.index('Latest_Post') if 'Latest_Post' in header else -1

    to_generate = []
    for i in city_indices:
        row = rows[i]
        copy = row[idx_copy].strip()
        if not copy:
            to_generate.append(i)

    if not to_generate:
        print("\n✅ 此城市所有診所已有文案，跳過生成。")
        return

    to_generate = to_generate[:limit]
    print(f"\n✍️ 準備為 {len(to_generate)} 筆診所生成文案...")

    # Import the LLM generation logic
    from generate_copy_llm import (
        build_prompt, generate_with_retry, GENERIC_COPY
    )

    success = 0
    newly_saved = 0

    for count, row_idx in enumerate(to_generate):
        if interrupted:
            break

        row = rows[row_idx]
        clinic_name = row[idx_name].strip()
        dept = row[idx_dept].strip() if idx_dept >= 0 else ''
        intro = row[idx_intro].strip() if idx_intro >= 0 else ''
        post = row[idx_post].strip() if idx_post >= 0 else ''

        if not intro and not post:
            row[idx_copy] = GENERIC_COPY
            print(f"  [{count+1}/{len(to_generate)}] {clinic_name} ({dept}) → 套用通用文案")
            success += 1
        else:
            print(f"  [{count+1}/{len(to_generate)}] 正在為 {clinic_name} ({dept}) 生成個人化文案...")
            copy = generate_with_retry(clinic_name, dept, intro, post)
            if copy:
                row[idx_copy] = copy
                print(f"    ✨ 文案已生成 ({len(copy)} 字)")
                success += 1
            else:
                print(f"    ❌ 生成失敗")

        newly_saved += 1
        if newly_saved >= 10:
            save_csv(header, rows)
            newly_saved = 0

    if newly_saved > 0:
        save_csv(header, rows)

    print(f"\n📊 文案生成完成：成功 {success}/{len(to_generate)} 筆")


# ─── Step 3: Send Outreach ───────────────────────────────────────

def send_outreach_for_city(header, rows, city_indices, limit=10, dry_run=False, delay_min=300, delay_max=600):
    """Send Messenger outreach for city clinics that have copy + Messenger link."""
    idx_msg = header.index('Messenger')
    idx_copy = header.index('Personalized_Copy')
    idx_status = header.index('Messenger_Status')
    idx_name = header.index('醫事機構名稱')
    idx_time = header.index('Outreach_Time') if 'Outreach_Time' in header else -1

    to_send = []
    for i in city_indices:
        row = rows[i]
        msg = row[idx_msg].strip()
        copy = row[idx_copy].strip()
        status = row[idx_status].strip()

        msg_valid = msg and msg != 'not_found' and msg.startswith('http')

        if msg_valid and copy and status not in ('sent', 'dry_run'):
            to_send.append(i)

    if not to_send:
        print("\n✅ 此城市沒有待發送的診所（需要先爬取 FB + 生成文案）。")
        return

    to_send = to_send[:limit]
    mode_str = "🧪 DRY-RUN" if dry_run else "🚀 正式發送"
    print(f"\n{mode_str} {len(to_send)} 筆診所...")

    send_script = str(WORKSPACE_DIR / "send_outreach.py")
    cmd = [VENV_PYTHON, send_script, "--limit", str(len(to_send)),
           "--delay-min", str(delay_min), "--delay-max", str(delay_max)]
    if dry_run:
        cmd.append("--dry-run")

    print(f"  執行: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(WORKSPACE_DIR))
    return result.returncode


# ─── Main ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="City-based campaign orchestrator")
    parser.add_argument("--city", required=True, help="Target city name (e.g., 台中, 台北, 高雄)")
    parser.add_argument("--limit", type=int, default=20, help="Max clinics to process per step (default: 20)")
    parser.add_argument("--dry-run", action="store_true", help="Dry-run mode (don't actually send)")
    parser.add_argument("--scrape-only", action="store_true", help="Only run FB scraping step")
    parser.add_argument("--generate-only", action="store_true", help="Only run copy generation step")
    parser.add_argument("--send-only", action="store_true", help="Only run sending step")
    parser.add_argument("--stats", action="store_true", help="Show stats only, don't execute")
    parser.add_argument("--delay-min", type=int, default=300, help="Min delay between sends (seconds)")
    parser.add_argument("--delay-max", type=int, default=600, help="Max delay between sends (seconds)")
    args = parser.parse_args()

    city = args.city
    print("=" * 60)
    print(f"醫師工具箱 — {city} 城市行銷活動")
    print(f"模式: {'DRY-RUN' if args.dry_run else '正式'}")
    print("=" * 60)

    # Load data
    header, rows = load_csv()
    city_indices = filter_city(header, rows, city)
    print(f"  {city} 診所 (排除中醫/牙醫): {len(city_indices)} 筆")

    if not city_indices:
        print(f"❌ 找不到 {city} 的診所資料")
        return

    # Stats
    stats = show_stats(header, rows, city_indices, city)

    if args.stats:
        return

    # Determine which steps to run
    run_all = not (args.scrape_only or args.generate_only or args.send_only)

    # Step 1: Scrape
    if run_all or args.scrape_only:
        if interrupted:
            return
        print(f"\n{'='*60}")
        print("步驟 1/3：爬取 FB 資訊")
        print(f"{'='*60}")
        if stats['need_scrape'] > 0:
            scrape_fb_for_city(header, rows, city_indices, limit=args.limit)
            # Reload CSV after scraping (scrape_fb_info.py modifies it directly)
            header, rows = load_csv()
            city_indices = filter_city(header, rows, city)
        else:
            print("  ⏭️ 無需爬取，跳過")

    # Step 2: Generate copy
    if run_all or args.generate_only:
        if interrupted:
            return
        print(f"\n{'='*60}")
        print("步驟 2/3：生成個人化文案")
        print(f"{'='*60}")
        generate_copy_for_city(header, rows, city_indices, limit=args.limit)
        # Reload
        header, rows = load_csv()
        city_indices = filter_city(header, rows, city)

    # Step 3: Send
    if run_all or args.send_only:
        if interrupted:
            return
        print(f"\n{'='*60}")
        print("步驟 3/3：發送 Messenger 開發訊息")
        print(f"{'='*60}")
        send_outreach_for_city(header, rows, city_indices,
                               limit=args.limit, dry_run=args.dry_run,
                               delay_min=args.delay_min, delay_max=args.delay_max)

    # Final stats
    header, rows = load_csv()
    city_indices = filter_city(header, rows, city)
    show_stats(header, rows, city_indices, city)

    print(f"\n🏁 {city} 行銷活動流程完成！")


if __name__ == "__main__":
    main()
