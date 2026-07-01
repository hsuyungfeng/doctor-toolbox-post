#!/usr/bin/env python3
"""
Quick send to a specific clinic - 文星外科診所
"""
import time
import sys
from pathlib import Path
from cloakbrowser import launch_persistent_context

# Configuration
PROFILE_DIR = Path("/home/hsuyungfeng/DevSoft/doctor-toolbox-post/browser_profile")
CLINIC_NAME = "文星外科診所"
MESSENGER_URL = "https://www.facebook.com/messages/t/wenxin22636645"
DEFAULT_IMAGE_PATH = "/home/hsuyungfeng/DevSoft/doctor-toolbox-post/assets/doctor-toolbox-post.png"
COPY_TEXT = """🩺 看診對話，自動變成 SOAP 病歷

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

def send_to_clinic(clinic_name=CLINIC_NAME, messenger_url=MESSENGER_URL, copy_text=COPY_TEXT, image_path=DEFAULT_IMAGE_PATH):
    # Prepend personalized greeting header if not already present
    greeting = f"{clinic_name} 醫療團隊您好！\n\n"
    if not copy_text.strip().startswith(clinic_name) and "醫療團隊您好" not in copy_text:
        copy_text = greeting + copy_text

    # Convert m.me or messenger.com links to facebook.com/messages/t/ to bypass domain issues
    target_url = messenger_url
    if "facebook.com/messages/t/" not in messenger_url:
        parts = messenger_url.rstrip('/').split('/')
        if parts:
            username = parts[-1].split('?')[0]
            if username:
                target_url = f"https://www.facebook.com/messages/t/{username}"

    print(f"🎯 目標診所：{clinic_name}")
    print(f"📧 Messenger: {target_url} (原網址: {messenger_url})")
    if image_path and Path(image_path).exists():
        print(f"🖼️ 配圖路徑：{image_path}")
    else:
        print("🖼️ 配圖路徑：無")
    
    # Launch browser
    print(f"\n🚀 啟動 CloakBrowser (profile: {PROFILE_DIR})...")
    try:
        browser_context = launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            humanize=True,
            timezone="Asia/Taipei",
            locale="zh-TW",
            args=["--fingerprint=77889"]
        )
    except Exception as e:
        print(f"❌ 瀏覽器啟動失敗：{e}")
        sys.exit(1)
    
    page = browser_context.pages[0] if browser_context.pages else browser_context.new_page()
    
    # Open Messenger
    print(f"\n🌐 開啟 FB 訊息對話框...")
    page.goto(target_url)
    time.sleep(10)
    
    # Check if login is required
    is_login_page = page.evaluate("""() => {
        const text = document.body.innerText;
        return text.includes('登入 Facebook') || text.includes('Log In') || !!document.querySelector('#login_form');
    }""")
    
    if is_login_page:
        print("⚠️ 偵測到未登入或需要登入狀態！請先登入 Facebook。")
        browser_context.close()
        sys.exit(1)
    
    # Locate and focus textbox
    print("🔍 定位輸入框...")
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
        print("❌ 找不到可寫入的 Messenger 輸入框。")
        page.screenshot(path="/tmp/quick_send_textbox_failed.png")
        browser_context.close()
        sys.exit(1)
    
    # Upload image if provided and exists
    if image_path and Path(image_path).exists():
        print(f"📤 上傳配圖: {image_path}...")
        try:
            page.set_input_files('input[type="file"]', str(image_path))
            time.sleep(5)  # Wait for Messenger to process image upload
            print("✅ 配圖上傳成功")
        except Exception as e:
            print(f"⚠️ 配圖上傳失敗: {e}")

    print("📝 聚焦成功，使用 page.keyboard.insert_text() 插入文字...")
    page.keyboard.insert_text(copy_text)
    time.sleep(2)
    
    # Verify message text is in the input box
    print("🔍 驗證訊息內容...")
    message_verified = page.evaluate("""() => {
        const tb = document.querySelector('div[contenteditable="true"][role="textbox"]');
        if (tb) {
            const text = tb.innerText || tb.textContent || '';
            return text.length > 50 && (text.includes('醫師工具箱') || text.includes('SOAP'));
        }
        return false;
    }""")
    
    if not message_verified:
        print("⚠️ 警告：訊息內容似乎沒有正確填入！")
        print("   請檢查 Facebook 頁面是否有特殊限制或輸入框結構變更。")
        page.screenshot(path="/tmp/quick_send_verify_failed.png")
        # Continue anyway, but warn user
    
    # Send message
    print("🚀 發送訊息...")
    page.keyboard.press("Enter")
    time.sleep(2)
    
    # Try clicking Send button if Enter didn't work
    send_clicked = page.evaluate("""() => {
        const sendBtns = Array.from(document.querySelectorAll('[aria-label="傳送"], [aria-label="Send"], [role="button"]'));
        for (const btn of sendBtns) {
            const label = btn.getAttribute('aria-label') || '';
            const text = btn.innerText || '';
            if (label === '傳送' || label === 'Send' || text.includes('傳送') || text.includes('Send')) {
                btn.click();
                return true;
            }
        }
        return false;
    }""")
    
    if send_clicked:
        print("✅ 已點擊傳送按鈕")
    else:
        print("⚠️ 未找到傳送按鈕，使用 Enter 鍵發送")
    
    time.sleep(3)
    
    # Verify message was sent
    print("🔍 驗證訊息是否發送成功...")
    message_sent = page.evaluate("""() => {
        const sentMessages = Array.from(document.querySelectorAll('[aria-label*="由你傳送"], [aria-label*="Sent by you"]'));
        for (const msg of sentMessages) {
            const label = msg.getAttribute('aria-label') || '';
            if (label.includes('醫師工具箱') || label.includes('SOAP') || label.includes('LINE')) {
                return true;
            }
        }
        return false;
    }""")
    
    if not message_sent:
        print("🛑 警告：無法驗證訊息是否發送成功！")
        print("   可能原因：")
        print("   1. Facebook 頁面限制了陌生人訊息")
        print("   2. 帳號被限制發送訊息")
        print("   3. 訊息被分類到「請求」夾層")
        page.screenshot(path="/tmp/quick_send_verify_failed.png")
        # Continue but don't update DB as 'sent'
        update_status = 'failed'
    else:
        print("✅ 確認訊息已成功發送")
        update_status = 'sent'
    
    # Check for errors
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
        print(f"🛑 警告：偵測到發送失敗或帳號限制！關鍵字：{failed_delivery}")
        screenshot_path = f"/tmp/quick_send_failed_{int(time.time())}.png"
        page.screenshot(path=screenshot_path)
        print(f"截圖已儲存至：{screenshot_path}")
        browser_context.close()
        sys.exit(1)
    
    # Success
    screenshot_path = f"/tmp/quick_send_{int(time.time())}.png"
    page.screenshot(path=screenshot_path)
    print(f"✅ 發送成功！截圖已儲存至：{screenshot_path}")
    
     # Update database
    print("\n💾 更新資料庫...")
    import sqlite3
    conn = sqlite3.connect('clinics.db')
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE clinics 
    SET messenger_status = ?, outreach_time = ? 
    WHERE messenger = ?
    """, (update_status, time.strftime('%Y-%m-%dT%H:%M:%S'), messenger_url))
    conn.commit()
    conn.close()
    print(f"✅ 資料庫更新完成 (狀態：{update_status})")
    
    browser_context.close()
    print("\n🎉 完成！")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Quick send to a specific clinic")
    parser.add_argument("--name", type=str, default=CLINIC_NAME, help="Clinic name")
    parser.add_argument("--messenger", type=str, default=MESSENGER_URL, help="Messenger URL")
    parser.add_argument("--image", type=str, default=DEFAULT_IMAGE_PATH, help="Image attachment path")
    args = parser.parse_args()
    send_to_clinic(args.name, args.messenger, COPY_TEXT, args.image)
