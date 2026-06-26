#!/usr/bin/env python3
"""
Import Facebook/Messenger session cookies from JSON to bypass login bot checks.
Reads fb_cookies.json, injects them into CloakBrowser persistent profile.
"""
import os
import sys
import json
from pathlib import Path
from cloakbrowser import launch_persistent_context

WORKSPACE_DIR = Path(__file__).resolve().parent
PROFILE_DIR = WORKSPACE_DIR / "browser_profile"
COOKIES_JSON_PATH = WORKSPACE_DIR / "fb_cookies.json"

def main():
    print("=" * 60)
    print("醫師工具箱 - 匯入臉書 Cookie 工作階段")
    print("=" * 60)

    if not COOKIES_JSON_PATH.exists():
        print(f"❌ 找不到 {COOKIES_JSON_PATH.name} 檔案！")
        print("請先使用瀏覽器擴充功能（如 Cookie-Editor）匯出臉書與 Messenger 的 JSON Cookie，")
        print(f"並將其貼上儲存為：{COOKIES_JSON_PATH}")
        sys.exit(1)

    try:
        with open(COOKIES_JSON_PATH, "r", encoding="utf-8") as f:
            cookies = json.load(f)
    except Exception as e:
        print(f"❌ 讀取或解析 {COOKIES_JSON_PATH.name} 失敗: {e}")
        sys.exit(1)

    if not isinstance(cookies, list):
        print("❌ Cookie JSON 格式不正確，必須是 Cookie 物件的陣列 (list)。")
        sys.exit(1)

    # Clean up sameSite values to match Playwright requirements
    cleaned_cookies = []
    for c in cookies:
        if not isinstance(c, dict) or "name" not in c or "value" not in c or "domain" not in c:
            continue
            
        cookie_item = {
            "name": c["name"],
            "value": c["value"],
            "domain": c["domain"],
            "path": c.get("path", "/"),
            "secure": c.get("secure", True),
        }
        
        # sameSite mapping
        if "sameSite" in c and c["sameSite"]:
            s_val = str(c["sameSite"]).lower()
            if "lax" in s_val:
                cookie_item["sameSite"] = "Lax"
            elif "strict" in s_val:
                cookie_item["sameSite"] = "Strict"
            elif "none" in s_val or "no_restriction" in s_val:
                cookie_item["sameSite"] = "None"
                
        # expiration/expires mapping (Playwright expects float epoch, some export expirationDate)
        if "expires" in c:
            cookie_item["expires"] = float(c["expires"])
        elif "expirationDate" in c:
            cookie_item["expires"] = float(c["expirationDate"])
            
        cleaned_cookies.append(cookie_item)
        
        # Duplicate for messenger.com domains to ensure messenger session works
        if "facebook.com" in c["domain"]:
            msg_cookie_1 = cookie_item.copy()
            msg_cookie_1["domain"] = ".messenger.com"
            cleaned_cookies.append(msg_cookie_1)
            
            msg_cookie_2 = cookie_item.copy()
            msg_cookie_2["domain"] = "www.messenger.com"
            cleaned_cookies.append(msg_cookie_2)

    print(f"  載入並整理了 {len(cleaned_cookies)} 筆 Cookie 項。")

    # Create profile dir if missing
    if not PROFILE_DIR.exists():
        PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    print("\n🚀 啟動 CloakBrowser 寫入 Cookie...")
    try:
        context = launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=True,
            humanize=True,
            timezone="Asia/Taipei",
            locale="zh-TW",
            args=["--fingerprint=77889"]
        )
        
        # Inject cookies
        context.add_cookies(cleaned_cookies)
        print(f"  [Debug] 注入 Cookie 完成。當前 Context 中的 Cookie 總數: {len(context.cookies())}")
        
        # Test navigation to verify login
        page = context.pages[0] if context.pages else context.new_page()
        print("  正在載入 Facebook 以啟用 Cookie 工作階段...")
        page.goto("https://www.facebook.com")
        import time
        time.sleep(5)
        
        fb_screenshot_path = str(WORKSPACE_DIR / "facebook_check.png")
        page.screenshot(path=fb_screenshot_path)
        print(f"  [Debug] Facebook 頁面標題: '{page.title()}', 網址: '{page.url}', 截圖已存至: {fb_screenshot_path}")
        
        print("  正在進入 Messenger 驗證...")
        page.goto("https://www.messenger.com")
        time.sleep(5)
        
        is_login_page = page.evaluate("""() => {
            const text = document.body.innerText;
            return text.includes('登入 Facebook') || text.includes('Log In') || !!document.querySelector('#login_form') || text.includes('註冊');
        }""")
        
        # Load facebook page to confirm login
        page.goto("https://www.facebook.com")
        time.sleep(5)
        
        is_fb_logged_in = page.evaluate("""() => {
            const text = document.body.innerText;
            return text.includes('建立限制動態') || text.includes('在想些什麼') || !text.includes('登入');
        }""")
        
        print(f"  [Debug] 目前頁面標題: '{page.title()}'")
        print(f"  [Debug] 目前頁面網址: '{page.url}'")
        print(f"  [Debug] Facebook 登入成功狀態: {is_fb_logged_in}")
        
        if not is_fb_logged_in:
            screenshot_path = str(WORKSPACE_DIR / "messenger_login_check.png")
            page.screenshot(path=screenshot_path)
            print(f"  [Debug] 驗證失敗截圖已存至: {screenshot_path}")
            context.close()
            print("\n⚠️ 驗證失敗：匯入 Cookie 後，臉書仍顯示未登入狀態。")
            print("請確保您在匯出 Cookie 時，瀏覽器上的臉書與 Messenger 處於已登入狀態，且匯出的是該頁面的完整 Cookie。")
            sys.exit(1)
            
        context.close()
        print("\n✅ 成功！Cookie 匯入成功且登入驗證通過！")
        print("您現在可以直接執行 run_campaign.py 進行外展。")
        
    except Exception as e:
        print(f"❌ 執行過程中發生錯誤: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
