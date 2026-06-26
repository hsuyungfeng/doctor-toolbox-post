#!/usr/bin/env python3
"""
為台中診所生成通用開發文案（沒有 Personalized_Copy 的診所）。
"""
import csv
import json
import sys

CSV_PATH = "/home/hsuyungfeng/文件/doctor-toolbox-post/clinics西醫.csv"

# Generic outreach copy template for doctor toolbox
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

def main():
    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = [list(row) for row in reader]
    
    idx_name = header.index('醫事機構名稱')
    idx_msg = header.index('Messenger')
    idx_copy = header.index('Personalized_Copy')
    idx_status = header.index('Messenger_Status')
    
    updated = 0
    skipped = 0
    
    for i, row in enumerate(rows):
        name = row[idx_name].strip()
        msg_url = row[idx_msg].strip()
        copy = row[idx_copy].strip()
        status = row[idx_status].strip()
        
        # Skip if already has copy or already sent
        if copy and status not in ('sent', 'dry_run'):
            skipped += 1
            continue
        if status in ('sent', 'dry_run'):
            skipped += 1
            continue
        
        # Only process Taichung clinics with valid messenger link
        # We need to check city code - read it from column 12
        idx_city = header.index('縣市別代碼')
        city_code = row[idx_city].strip()
        address = row[4].strip() if len(row) > 4 else ''
        
        is_taichung = (city_code in ('65000', '66000')) or '台中' in name or '台中' in address
        if not is_taichung:
            skipped += 1
            continue
        if not msg_url or msg_url == 'not_found' or not msg_url.startswith('http'):
            skipped += 1
            continue
        
        # Generate generic copy
        row[idx_copy] = GENERIC_COPY
        updated += 1
        print(f"  [{i}] {name} -> 已生成通用文案")
    
    # Save back
    with open(CSV_PATH, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    
    print(f"\n✅ 完成！更新了 {updated} 筆台中診所的 Personalized_Copy，跳過 {skipped} 筆。")
    print(f"📂 檔案已儲存至: {CSV_PATH}")

if __name__ == '__main__':
    main()
