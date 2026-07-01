# 醫師工具箱 (Doctor Toolbox) - 診所推廣與自動化行銷系統

本專案是一套專為 **醫師工具箱 (Doctor Toolbox)** 設計的自動化診所資訊收集、推廣與多管道行銷外展系統。主要針對台灣西醫診所進行自動化開發，結合 AI 技術客製化文案，並模擬真人行為進行慢速推廣以防止帳號被 Facebook 與郵件伺服器限制。

## 📋 功能特色

1. **多管道行銷決策鏈 (`run_city_pipeline.py`)** ⭐ 推薦
   - 按照 **Email 信件推廣 ──> Messenger 私訊（上傳配圖） ──> Facebook 貼文留言（保底）** 的三層管道漏斗進行自動發送。
   - 遇到前一管道不可用或發送失敗時，會自動嘗試下一管道，保障觸及成功率。

2. **本地自託管 Firecrawl 結構化爬網 (`firecrawl_scraper.py`)**
   - 整合本地 Docker 自託管的 **Firecrawl** 服務，自動爬取診所官方網站，將網頁內容轉為 Markdown。
   - 自動從官網中提取 **Email 聯絡信箱** 與 **Facebook 粉絲專頁/Messenger 連結**，無須付費或依賴雲端 API。

3. **AI 客製化文案生成 (`generate_copy_llm.py`)**
   - 串接本地大型語言模型（Qwen/Llama 容器，`http://localhost:8080`）。
   - 根據 Firecrawl 爬取到的官網特色、診療科別（如兒科、眼科、外科）及粉專貼文，自動生成高度客製化、語意通順的行銷文案，並在發送前自動過濾所有簡體字與醫療法違禁詞。

4. **HTML 郵件行銷與配圖內嵌 (`send_email.py`)**
   - 支援通過 SMTP 自動發送精美的 HTML 電子郵件。
   - 採用 **CID 內嵌圖片技術**，將 `doctor-toolbox-post.png` 廣告海報直接嵌入郵件正文中，收件人打開信件即可直接看到，免點擊下載。

5. **智慧慢速 Messenger 發送**
   - 模擬真人輸入與發送，自動將 Messenger 網址轉換為 Facebook 訊息頁面 (`https://www.facebook.com/messages/t/`)，支援廣告配圖（`assets/doctor-toolbox-post.png`）自動上傳，並配合 **5~10 分鐘的隨機冷卻時間** 模擬真人行為。
   - 內建斷路器（Halt Circuit Breaker），連續 3 次失敗自動停止，保護帳號。

6. **追蹤與統計儀表板 (`outreach_dashboard.html`)**
   - 提供直觀的網頁儀表板，可載入 `clinics西醫.csv` 並即時統計已處理、待發送、發送失敗等進度。

---

## ⚙️ 專案路徑與配置

| 項目 | 本地路徑 / 設定值 |
|------|------|
| 資料庫 CSV | `./clinics西醫.csv` |
| SQLite 資料庫 | `./clinics.db` |
| 發送日誌 | `./outreach_sent_log.jsonl` |
| 瀏覽器 Profile | `./browser_profile` |
| 瀏覽器指紋 | `--fingerprint=77889` |
| Local LLM | `http://localhost:8080/v1/chat/completions` |
| Local Firecrawl | `http://localhost:3002` (Self-hosted via Docker) |
| Python 環境 | `python3` (系統環境) |

---

## 🚀 快速開始 & 本地部署

### 第一步：環境初始化
```bash
# 安裝 Python 依賴
pip3 install -r requirements.txt
playwright install chromium
```

### 第二步：本地自託管啟動 Firecrawl
本專案已將 Firecrawl 作為 Git Submodule 整合在專案中，您可以使用 Docker 進行一鍵本地部署：
```bash
# 進入子模組目錄
cd firecrawl

# 啟動自託管服務（耗時數分鐘，啟動後可至 http://localhost:3002 驗證）
docker compose up -d
cd ..
```

### 第三步：Facebook 登入工作階段 (Cookie 匯入)
1. 在您的主要瀏覽器中登入 Facebook 帳號。
2. 安裝 **Cookie-Editor** 擴充功能，選擇 **Export → JSON** 複製 Cookie 內容。
3. 將其儲存為專案根目錄下的 `./fb_cookies.json`。
4. 執行匯入以持久化瀏覽器會話：
   ```bash
   python3 import_cookies.py
   ```

### 第四步：執行測試與多管道發送
```bash
# 測試本地 Firecrawl 爬取官網與提取 Email
python3 firecrawl_scraper.py https://example.com

# 查看某城市診所統計
python3 run_city_pipeline.py --city 台中 --stats

# 正式執行慢速多管道行銷（限 5 筆，每筆隨機等待 5-10 分鐘）
xvfb-run python3 run_city_pipeline.py --city 台中 --limit 5 --delay-min 300 --delay-max 600
```

---

## 🤖 如何使用 Hermes / Antigravity Agent 進行自動化操作

專案內建了 `.agents/skills/doctor-toolbox-poster/` 技能，您可以直接命令 AI 代理（Hermes/Antigravity）以全自主方式替您維護與推廣：

### 1. 使用 `/goal` 指令委託長效任務
當您需要讓 Agent 在背景完全自主執行慢速外展時，推薦使用 `/goal` 指令。例如：
> **「/goal 幫我跑台中市的診所行銷，限制 5 筆，並以 5~10 分鐘的隨機冷卻間隔慢速發送。」**

Agent 接收到命令後，會自動：
1. 確認本地 Firecrawl 容器（`3002` 埠）與 LLM 容器（`8080` 埠）皆已運行。
2. 背景啟動 `xvfb-run python3 run_city_pipeline.py --city 台中 --limit 5 --delay-min 300 --delay-max 600`。
3. 每完成一個步驟即更新資料庫與 `clinics西醫.csv`。
4. 任務完成後自動向您彙報成功統計與發送狀態。

### 2. 數據同步 (Sync SQLite back to CSV)
如果您在資料庫中對發送失敗的診所進行了手動重設（例如重設為 `NULL` 準備重新發送），您可以使用以下命令要求 Agent 同步 CSV：
> **「幫我將 SQLite 的發送狀態同步回 `clinics西醫.csv` 檔案，並把失敗紀錄改為未送。」**

這會自動觸發並執行 `sync_db_to_csv.py` 以確保資料一致。

---

## 🛠️ 常見問題與排錯

- **Email 發送失敗或未發送**：
  - 請檢查 `send_email.py` 中預設的 Gmail `SMTP_USER` 與 `SMTP_PASSWORD`（應用程式密碼）是否正確。
  - 如需更改，可直接設定環境變數 `export SMTP_USER="xxxx"` 再執行。
- **FB 私訊被限制**：
  - 如果截圖（存放在 `/tmp/pipeline_failed_*.png`）中出現「無法傳送」或紅色驚嘆號，代表帳號暫時被臉書限制發信。系統會自動調用 **FB 貼文留言** 作為保底備用方案，在診所粉專最新貼文下留言。
- **釋放瀏覽器鎖定**：
  - 若提示瀏覽器被鎖定，請執行 `pkill -f browser_profile` 釋放背景進程。

---

## 📝 開發與討論紀錄 (Development & Discussion Records)

### 📅 2026-07-01 更新：Firecrawl 本地化、多管道決策鏈與 SMTP 整合
- **多管道行銷決策鏈**：實作 `Email -> Messenger (附圖) -> FB 留言 (保底)` 決策。Email 發信採用 CID 內嵌技術展示海報，Messenger 與留言定位器均已優化，對應臉書動態彈出框以防寫入失敗。
- **Firecrawl 本地自託管**：將 Firecrawl 作為子模組引入，支持本地 Docker 一鍵部署。提供 `firecrawl_scraper.py` 客戶端，自動解析官網並擷取 Email 與臉書連結，不再依賴第三方 API。
- **數據互通同步**：提供 `sync_db_to_csv.py` 確保資料庫與 `clinics西醫.csv` 隨時保持同步，方便利用儀表板進行進度追踪。
