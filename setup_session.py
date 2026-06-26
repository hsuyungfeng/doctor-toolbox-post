#!/usr/bin/env python3
"""
Initialize persistent browser session.
Allows manual login to Google and Facebook, saving session data in './browser_profile'.
"""
import os
import sys
from pathlib import Path
from cloakbrowser import launch_persistent_context

# Resolve profile path in workspace
WORKSPACE_DIR = Path(__file__).resolve().parent
PROFILE_DIR = WORKSPACE_DIR / "browser_profile"

def main():
    print("=" * 60)
    print("醫師工具箱 - 初始化瀏覽器登入 Session")
    print("=" * 60)
    print(f"📁 儲存路徑: {PROFILE_DIR}")
    
    if not PROFILE_DIR.exists():
        PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        print("已建立 profile 目錄。")

    print("\n🚀 啟動 CloakBrowser (視窗模式)...")
    try:
        context = launch_persistent_context(
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

    page = context.new_page()
    
    print("\n🔑 步驟說明:")
    print("1. 請在開啟的瀏覽器中手動登入您的 Facebook、Messenger 與 Google 帳號。")
    print("2. 確保登入成功並勾選「記住我」或保持登入狀態。")
    print("3. 完成後，在終端機（此視窗）按下 [Enter] 鍵來關閉瀏覽器並儲存 Session。")
    print("-" * 60)

    # Open Facebook, Messenger, and Google Maps in separate tabs/steps
    print("正在導航至 Facebook 登入頁面...")
    page.goto("https://www.facebook.com")
    
    print("正在開啟新分頁至 Messenger 登入頁面...")
    page_msg = context.new_page()
    page_msg.goto("https://www.messenger.com")
    
    print("正在開啟新分頁至 Google Maps...")
    page2 = context.new_page()
    page2.goto("https://www.google.com/maps")

    # Wait for user input to close
    input("\n👉 完成登入後，請在此處按下 [Enter] 關閉瀏覽器: ")

    print("\n💾 正在儲存 Session 並關閉瀏覽器...")
    context.close()
    print("✅ 儲存完成！您現在可以執行自動貼文腳本。")

if __name__ == "__main__":
    main()
