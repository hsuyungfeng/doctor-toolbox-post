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
from pydantic import BaseModel, Field, field_validator, ValidationError

# === Config ===
WORKSPACE_DIR = Path(__file__).resolve().parent
CSV_PATH = "/home/hsuyungfeng/文件/doctor-toolbox-post/clinics西醫.csv"

# Local llama-qwen36 docker container endpoint
LLM_API_URL = os.environ.get("LLM_API_URL", "http://localhost:8080/v1/chat/completions")

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

csv_header = []
csv_rows = []
interrupted = False

class ClinicCopySchema(BaseModel):
    personalized_copy: str = Field(description="Outreach copy text in Traditional Chinese, 80-180 chars.")
    specialty_tag: str = Field(description="Identified clinic specialty (e.g., Pediatrics, ENT).")

    @field_validator("personalized_copy")
    @classmethod
    def validate_copy(cls, val: str) -> str:
        # 1. Length check
        if len(val) < 80 or len(val) > 180:
            raise ValueError(f"文案長度（{len(val)} 字）必須在 80 到 180 字之間。")
        
        # 2. Traditional Chinese check
        simplified_chars = [
            "亲", "医", "这", "国", "诊", "体", "会", "电", "话", "设", "备", "进", "专", 
            "优", "疗", "简", "贴", "时", "间", "样", "资", "费", "营", "药", 
            "无", "发", "们", "个", "来", "为", "对", "学", "东", "动", "车", "业", 
            "统", "广", "场", "应", "观", "规", "范", "卫", "总", "类", "确", "极"
        ]
        for char in simplified_chars:
            if char in val:
                raise ValueError(f"檢測到簡體字：'{char}'，文案必須為全繁體中文")
                
        # 3. Superlative blacklist check
        blacklist = ["最佳", "最先進", "保證療效", "根治", "全台第一"]
        for term in blacklist:
            if term in val:
                raise ValueError(f"違反醫療法禁用詞：'{term}'")
                
        return val

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
        ],
        "temperature": 0.2,
        "max_tokens": 300,
        "response_format": {"type": "json_object"}
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
            return res_json.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
    except Exception as e:
        print(f"    ❌ 呼叫 Local Qwen36 失敗 (請確認 llama.cpp docker 容器是否在 {LLM_API_URL} 啟動): {e}")
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
2. 必須精準結合該診所的特色（例如：如果是小兒科，強調記載小兒發展史與疫苗資訊；如果是眼科，強調記載近視控制與配鏡需求；如果是外科，強調記載傷口處置等）。
3. 不要使用任何罐頭問候語，第一句直接切入「針對貴診所在...方面的特色，醫師工具箱能提供...協助」。
4. 結尾附上免費體驗連結：https://doctor-toolbox.com/ai-soap-generator。
5. 嚴禁包含醫療法禁用的誇大詞彙（如「最佳」、「最先進」、「保證療效」、「根治」、「全台第一」）。

範例一（小兒科）：
{{
    "personalized_copy": "針對貴診所在小兒過敏與預防接種方面的專業特色，醫師工具箱能提供極大協助。我們的 AI 語音病歷系統能即時轉錄看診對話，自動生成符合小兒發展與疫苗紀錄的 SOAP 病歷，免去繁瑣的手動輸入。讓您可以更專注於與家長的溝通。歡迎點擊免費體驗：https://doctor-toolbox.com/ai-soap-generator",
    "specialty_tag": "小兒科"
}}

範例二（一般科/家醫科）：
{{
    "personalized_copy": "針對貴診所在慢性病長期追蹤與家庭照護的在地特色，醫師工具箱能提供絕佳協助。我們的 AI SOAP 語音病歷能即時記錄患者病情陳述，並整合 LINE OA 預約與自動問答，大幅節省行政與病歷整理時間。歡迎點擊免費體驗：https://doctor-toolbox.com/ai-soap-generator",
    "specialty_tag": "一般科"
}}

請只輸出 JSON 格式的內容，不要有任何多餘的解釋或前言後語。"""

def generate_with_retry(clinic_name, dept, intro, post, retries=2):
    # Truncate inputs to prevent context bloat
    intro_trunc = intro[:400] if intro else ""
    post_trunc = post[:400] if post else ""
    prompt = build_prompt(clinic_name, dept, intro_trunc, post_trunc)
    
    for attempt in range(retries + 1):
        try:
            raw_response = call_local_llm(prompt)
            if not raw_response:
                raise ValueError("LLM 返回空字串")
            
            # Extract JSON block if LLM returned markdown wrapping
            if "```json" in raw_response:
                raw_response = raw_response.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_response:
                raw_response = raw_response.split("```")[1].split("```")[0].strip()
            
            # Clean outer non-JSON chars if any (just in case)
            raw_response = raw_response.strip()
            if not raw_response.startswith("{"):
                start_idx = raw_response.find("{")
                end_idx = raw_response.rfind("}")
                if start_idx != -1 and end_idx != -1:
                    raw_response = raw_response[start_idx:end_idx+1]
            
            data = json.loads(raw_response)
            validated = ClinicCopySchema(**data)
            return validated.personalized_copy
            
        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            print(f"  ⚠️ [第 {attempt+1} 次嘗試] 驗證失敗: {e}")
            if attempt == retries:
                print("  ❌ 嘗試次數耗盡。使用預設通用開發文案。")
                return GENERIC_COPY

def main():
    load_data()
    
    # Map indices
    idx_name = csv_header.index('醫事機構名稱')
    idx_dept = csv_header.index('診療科別')
    idx_intro = csv_header.index('Intro')
    idx_post = csv_header.index('Latest_Post')
    idx_copy = csv_header.index('Personalized_Copy')
    
    # Filter clinics that need copying generated
    to_process = []
    for i, row in enumerate(csv_rows):
        copy = row[idx_copy].strip()
        if not copy:
            to_process.append(i)
            
    print(f"\n📊 待處理診所數量: {len(to_process)} 筆")
    if not to_process:
        print("  - 沒有需要生成文案的診所。")
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
        
        # Check if both fields are empty
        if not intro and not post:
            row[idx_copy] = GENERIC_COPY
            print(f"\n[{idx+1}/{len(to_process)}] {clinic_name} ({dept}) -> Intro 與 Latest_Post 皆為空。直接套用通用開發文案。")
            success_count += 1
            newly_saved += 1
        else:
            print(f"\n[{idx+1}/{len(to_process)}] 正在為 {clinic_name} ({dept}) 生成個人化開發文案...")
            response_copy = generate_with_retry(clinic_name, dept, intro, post)
            if response_copy:
                row[idx_copy] = response_copy
                print(f"    ✨ 最終文案:\n{response_copy}")
                success_count += 1
                newly_saved += 1
            else:
                print("    ❌ 生成失敗，跳過")
            
        if newly_saved >= 10:
            save_data()
            newly_saved = 0
            
    save_data()
    print(f"\n📊 執行完成：成功處理 {success_count} 筆診所開發信件。")

if __name__ == "__main__":
    main()
