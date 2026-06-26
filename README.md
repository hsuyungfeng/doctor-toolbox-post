# 醫師工具箱 (Doctor Toolbox) - 診所推廣與自動化行銷系統

本專案是一套專為 **醫師工具箱 (Doctor Toolbox)** 設計的自動化診所推廣、資訊收集與 Messenger 開發系統。主要針對台灣西醫診所進行自動化行銷，結合 AI 技術客製化文案，並模擬真人行為進行慢速推廣以防止帳號被 Facebook 限制。

## 📋 功能特色

1. **診所資訊自動爬取 (`scrape_fb_info.py`)**
   - 自動搜尋並收集診所的 Facebook 粉絲專頁、公開 Email 以及 Messenger 連結。
   - 提取專頁的「簡介」與「最新貼文」，做為後續 AI 分析與文案生成的基礎資料。
   - 優先爬取台中市診所，支援中斷與隨時存檔。

2. **AI 客製化文案生成 (`generate_copy_llm.py`)**
   - 串接本地大型語言模型（預設為啟動於 `http://localhost:8080` 的 `llama-qwen36` 容器）。
   - 根據診所名稱、診療科別（如兒科、眼科、外科）以及簡介與貼文，自動生成**高度客製化**的行銷文案。
   - 內建 Pydantic 驗證與黑名單過濾，排除違反台灣醫療法之誇大不實詞彙（如「最佳」、「全台第一」）及簡體中文洩漏，失敗時提供重試與通用文案備用。

3. **智慧慢速開發發送 (`send_outreach.py`)**
   - 模擬真人輸入與發送，智慧定位輸入框並填入個人化文案。
   - **防封鎖動態退避 (Adaptive Backoff)**：偵測到臉書限制關鍵字時，自動將隨機冷卻延遲乘數加倍，拉長間隔；成功發送後逐步降速恢復。
   - **硬熔斷機制 (Halt Circuit Breaker)**：連續 3 次遭遇發送失敗或臉書限制時，自動終止任務並進行硬熔斷，避免帳號遭受永久停權。

4. **主控協調 CLI (`run_campaign.py`)**
   - 提供一鍵式協調整個 Pipeline 的入口。自動釋放鎖定、驗證臉書工作階段、執行爬取、AI 文案生成、沙盒測試與正式發送。

5. **追蹤與統計儀表板 (`outreach_dashboard.html`)**
   - 提供直觀的網頁儀表板，可載入 `clinics西醫.csv` 並即時統計已處理、待發送、發送失敗等進度。

## ⚙️ 專案路徑與配置

- **資料庫 CSV**：`/home/hsuyungfeng/文件/doctor-toolbox-post/clinics西醫.csv` (支援本地專案目錄 `clinics西醫.csv` 備用載入)
- **JSON 快取**：`/home/hsuyungfeng/文件/doctor-toolbox-post/clinic_links.json`
- **發送日誌**：`/home/hsuyungfeng/文件/doctor-toolbox-post/outreach_sent_log.jsonl`
- **瀏覽器 Profile**：`./browser_profile` (用於保持 FB 登入狀態與指紋)
- **瀏覽器指紋設定**：固定使用 `--fingerprint=77889` 以確保指紋一致性。

---

## 🚀 快速開始步驟

### 第一步：環境初始化 (使用 uv)
專案已提供 `requirements.txt` 以供一鍵設定。請在專案目錄下執行：
```bash
# 建立虛擬環境
uv venv

# 安裝所有相依套件 (cloakbrowser, pydantic, pytest)
uv pip install -r requirements.txt

# 下載 Playwright 的 Chromium 瀏覽器核心
uv run playwright install chromium
```

### 第二步：建立 Facebook 登入工作階段 (Session)
為了解鎖防爬蟲機制，必須讓自動化瀏覽器取得已登入的 Session 狀態。我們提供以下兩種方式：

#### 方式 A（推薦，Cookie 匯入防封鎖）：
當直接在自動化瀏覽器中輸入密碼登入被臉書無條件攔截時，請使用此方式：
1. 在您日常使用的瀏覽器（如 Chrome/Edge/Firefox）上安裝擴充功能：**Cookie-Editor**。
2. 於日常瀏覽器中登入您的 Facebook。
3. 登入成功後，點擊 `Cookie-Editor` 圖示，選擇 **Export -> JSON** 格式複製 Cookie。
4. 於本專案目錄下建立名為 **`fb_cookies.json`** 的檔案，並將複製的 JSON 內容貼上存檔。
5. 執行匯入腳本：
   ```bash
   uv run python3 import_cookies.py
   ```
   *腳本會自動將 Session 寫入 Profile 並進行登入功能驗證。*

#### 方式 B（手動登入）：
1. 執行以下指令：
   ```bash
   uv run python3 setup_session.py
   ```
2. 程式會以視窗模式開啟三個分頁：Facebook、Messenger 和 Google Maps。
3. 請在開啟的視窗中完成登入並勾選「保持登入」，完成後回到終端機按下 `Enter` 鍵關閉瀏覽器。

### 第三步：一鍵執行行銷外展 (run_campaign)
我們提供了一個主控協調 CLI，可以自動順序性地為您跑完所有流程：

* **僅執行沙盒測試與文案生成 (Dry-Run)**：
  如果您想確認爬取狀態、生成文案與測試瀏覽器定位，可先執行：
  ```bash
  uv run python3 run_campaign.py --dry-run-only
  ```
  *可在 `/home/hsu/doctor-toolbox-post/facebook_check.png` 與 `/tmp/outreach_dryrun.png` 查看驗證截圖。*

* **正式開始慢速發送行銷外展：**
  這會執行爬取、AI 生成，並開始向診所的 Messenger 發送行銷開發訊息：
  ```bash
  uv run python3 run_campaign.py --limit 10 --delay-min 300 --delay-max 600
  ```
  *(參數 `--limit` 為本次發送上限；`--delay-min` 與 `--delay-max` 為兩封訊息間的隨機冷卻秒數)*

---

## 🛠️ 開發與測試

- **單元測試**：本專案附帶 12 個完整的測試案例。您可執行以下指令以驗證文案審查驗證、退避熔斷和主控協調邏輯：
  ```bash
  PYTHONPATH=. pytest tests/test_fallback.py tests/test_backoff.py tests/test_campaign.py
  ```
- **排錯提示**：若發送失敗，可至 `/tmp` 目錄下尋找 `outreach_failed_block_*.png` 或 `outreach_textbox_failed.png` 查看當下瀏覽器截圖。
