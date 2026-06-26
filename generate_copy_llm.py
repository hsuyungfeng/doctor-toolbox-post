#!/usr/bin/env python3
"""
Generate personalized Doctor Toolbox copy for clinics using a local LLM (Ollama).
Reads clinics西醫.csv, calls local LLM, and writes copies back to CSV.
Supports resuming and handles interrupts gracefully.
"""
import csv
import json
import os
import sys
import signal
import urllib.request
import urllib.parse
from pathlib import Path

# === Config ===
WORKSPACE_DIR = Path(__file__).resolve().parent
CSV_PATH = "/home/hsuyungfeng/文件/doctor-toolbox-post/clinics西醫.csv"

# Local llama-qwen36 docker container endpoint
LLM_API_URL = os.environ.get("LLM_API_URL", "http://localhost:8080/v1/chat/completions")

csv_header = []
csv_rows = []
interrupted = False

def load_data():
    global csv_header, csv_rows, CSV_PATH
    print(f"📂 載入 CSV 資料庫: {CSV_PATH}")
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
        
    # Ensure Personalized_Copy column exists
    if 'Personalized_Copy' not in csv_header:
        csv_header.append('Personalized_Copy')
        
    # Ensure Intro and Latest_Post columns exist (if they weren't created by scraper)
    for col in ['Intro', 'Latest_Post']:
        if col not in csv_header:
            csv_header.append(col)
            
    # Pad rows
    for row in csv_rows:
        while len(row) < len(csv_header):
            row.append('')

def save_data():
    print(f"\n💾 正在儲存 CSV 資料庫...")
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

def handle_signal(sig, frame):
    global interrupted
    print("\n🛑 偵測到中斷訊號 (Ctrl+C)... 正在儲存資料並退出...")
    interrupted = True

signal.signal(signal.SIGINT, handle_signal)

def call_local_llm(prompt):
    """Call local llama-qwen36 API synchronously using urllib (OpenAI compatible format)."""
    data = {
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    json_data = json.dumps(data).encode('utf-8')
    
    req = urllib.request.Request(
        LLM_API_URL,
        data=json_data,
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            res_body = response.read().decode('utf-8')
            res_json = json.loads(res_body)
            # choices[0].message.content
            return res_json.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
    except Exception as e:
        print(f"    ❌ 呼叫 Local Qwen36 失敗 (請確認 llama.cpp docker 容器是否在 http://localhost:8080 啟動): {e}")
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

文案生成要求：
1. 必須以繁體中文撰寫，字數控制在 100-150 字之間，簡潔有禮。
2. 必須精準結合該診所的特色（例如：如果是小兒科，強調記載小兒發展史與疫苗資訊；如果是眼科，強調記載近視控制與配鏡需求；如果是外科，強調記載傷口處置等）。
3. 不要使用任何罐頭問候語，第一句直接切入「針對貴診所在...方面的特色，醫師工具箱能提供...協助」。
4. 結尾附上免費體驗連結：https://doctor-toolbox.com/ai-soap-generator。

請直接輸出文案內容，不要有任何多餘的解釋或前言後語。"""

def main():
    load_data()
    
    # Map indices
    idx_name = csv_header.index('醫事機構名稱')
    idx_dept = csv_header.index('診療科別')
    idx_intro = csv_header.index('Intro')
    idx_post = csv_header.index('Latest_Post')
    idx_copy = csv_header.index('Personalized_Copy')
    
    # Filter clinics that have scraped data but no personalized copy
    to_process = []
    for i, row in enumerate(csv_rows):
        name = row[idx_name].strip()
        intro = row[idx_intro].strip()
        post = row[idx_post].strip()
        copy = row[idx_copy].strip()
        
        # We need at least intro or post to personalize
        if (intro or post) and not copy:
            to_process.append(i)
            
    print(f"\n📊 待生成個人化文案診所數量: {len(to_process)} 筆")
    if not to_process:
        print("  - 沒有符合條件且尚未生成文案的診所。請先啟動爬蟲收集 Intro 與 Posts。")
        return
        
    print(f"🤖 使用 Local LLM 模型: llama-qwen36 ({LLM_API_URL})")
    
    newly_saved = 0
    success_count = 0
    
    for idx, row_idx in enumerate(to_process):
        if interrupted:
            break
            
        row = csv_rows[row_idx]
        clinic_name = row[idx_name].strip()
        dept = row[idx_dept].strip()
        intro = row[idx_intro].strip()
        post = row[idx_post].strip()
        
        print(f"\n[{idx+1}/{len(to_process)}] 正在為 {clinic_name} ({dept}) 生成個人化開發文案...")
        
        prompt = build_prompt(clinic_name, dept, intro, post)
        response_copy = call_local_llm(prompt)
        
        if response_copy:
            row[idx_copy] = response_copy
            print(f"    ✨ 生成文案:\n{response_copy}")
            success_count += 1
            newly_saved += 1
        else:
            print("    ❌ 生成失敗，跳過")
            
        if newly_saved >= 10:
            save_data()
            newly_saved = 0
            
    save_data()
    print(f"\n📊 執行完成：成功生成 {success_count} 筆個人化開發信件。")

if __name__ == "__main__":
    main()
