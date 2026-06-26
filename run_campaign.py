#!/usr/bin/env python3
"""
Master Campaign Orchestrator for Doctor Toolbox outreach pipeline.
Sequentially runs browser lock release, session validation, scraping,
copywriting generation, dry-run validation, and adaptive campaign sending.
"""
import os
import sys
import subprocess
import argparse
import time
from pathlib import Path

WORKSPACE_DIR = Path(__file__).resolve().parent
PROFILE_DIR = WORKSPACE_DIR / "browser_profile"

def release_browser_locks():
    print("\n🧹 正在清除未釋放的瀏覽器鎖定進程...")
    try:
        # Run pkill to terminate any lingering cloakbrowser/profile locks
        subprocess.run(["pkill", "-f", "browser_profile"], capture_output=True)
        time.sleep(2)
        print("  ✅ 鎖定進程已清除。")
    except Exception as e:
        print(f"  ⚠️ 清除鎖定進程時出現錯誤 (可忽略): {e}")

def verify_facebook_session():
    print("\n🔍 正在驗證 Facebook/Messenger 登入工作階段...")
    if not PROFILE_DIR.exists():
        print("  ❌ 找不到 browser_profile 目錄。請先執行 'python3 setup_session.py'。")
        return False

    try:
        from cloakbrowser import launch_persistent_context
        context = launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=True,
            humanize=True,
            timezone="Asia/Taipei",
            locale="zh-TW",
            args=["--fingerprint=88888"]
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://www.messenger.com")
        time.sleep(4)
        
        is_login_page = page.evaluate("""() => {
            const text = document.body.innerText;
            return text.includes('登入 Facebook') || text.includes('Log In') || !!document.querySelector('#login_form');
        }""")
        
        context.close()
        
        if is_login_page:
            print("  ❌ Facebook 登入工作階段已逾期或無效！")
            return False
            
        print("  ✅ 工作階段驗證成功！")
        return True
    except Exception as e:
        print(f"  ❌ 驗證工作階段時發生異常錯誤: {e}")
        return False

def run_step(name, command_args):
    print(f"\n⚙️ 正在執行步驟：{name}...")
    print(f"  指令: {' '.join(command_args)}")
    
    result = subprocess.run(command_args)
    if result.returncode != 0:
        print(f"  ❌ 步驟 {name} 執行失敗，退出碼: {result.returncode}")
        sys.exit(result.returncode)
    print(f"  ✅ 步驟 {name} 執行成功。")

def main():
    parser = argparse.ArgumentParser(description="醫師工具箱自動化外展主控協調 CLI")
    parser.add_argument("--limit", type=int, default=10, help="本次 campaign 發送訊息上限")
    parser.add_argument("--delay-min", type=int, default=300, help="發送最小等待延遲 (秒，預設 300秒)")
    parser.add_argument("--delay-max", type=int, default=600, help="發送最大等待延遲 (秒，預設 600秒)")
    parser.add_argument("--dry-run-only", action="store_true", help="僅執行沙盒測試 (Dry-Run)，不進行正式發送")
    parser.add_argument("--skip-scrape", action="store_true", help="跳過 FB 資訊爬取步驟")
    args = parser.parse_args()

    print("=" * 60)
    print("醫師工具箱 - 主控協調行銷外展 (Master Campaign Orchestrator)")
    print("=" * 60)
    print(f"工作目錄: {WORKSPACE_DIR}")
    print(f"配置參數: limit={args.limit}, delay_min={args.delay_min}, delay_max={args.delay_max}")
    print("=" * 60)

    # 1. Kill profile locks
    release_browser_locks()

    # 2. Verify Session
    if not verify_facebook_session():
        print("\n❌ Facebook 工作階段無效！請執行 'python3 setup_session.py' 以重新登入驗證。")
        sys.exit(1)

    # Resolve script paths
    python_bin = sys.executable
    scrape_script = str(WORKSPACE_DIR / "scrape_fb_info.py")
    copy_script = str(WORKSPACE_DIR / "generate_copy_llm.py")
    outreach_script = str(WORKSPACE_DIR / "send_outreach.py")

    # 3. Scraping Step
    if not args.skip_scrape:
        run_step("1. 診所資訊爬取 (scrape_fb_info)", [python_bin, scrape_script])
    else:
        print("\n⏭️ 跳過診所資訊爬取步驟。")

    # 4. Copywriting Step
    run_step("2. AI 客製化文案生成 (generate_copy_llm)", [python_bin, copy_script])

    # 5. Dry-Run Verification
    run_step("3. 發送沙盒測試 (send_outreach dry-run)", [
        python_bin, outreach_script, 
        "--dry-run", 
        "--limit", "2"
    ])

    # 6. Outreach Campaign Sending
    if not args.dry_run_only:
        run_step("4. 正式行銷外展 (send_outreach campaign)", [
            python_bin, outreach_script, 
            "--limit", str(args.limit),
            "--delay-min", str(args.delay_min),
            "--delay-max", str(args.delay_max)
        ])
    else:
        print("\n⏭️ 已設定 --dry-run-only，跳過正式行銷外展發送步驟。")

    print("\n🎉 醫師工具箱行銷外展流程全部順利執行完成！")

if __name__ == "__main__":
    main()
