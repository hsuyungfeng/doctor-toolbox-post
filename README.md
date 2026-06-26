# 醫師工具箱 (Doctor Toolbox) - 診所推廣與自動化行銷系統

本專案是一套專為 **醫師工具箱 (Doctor Toolbox)** 設計的自動化診所推廣、資訊收集與 Messenger 開發系統。主要針對台灣西醫診所進行自動化行銷，結合 AI 技術客製化文案，並模擬真人行為進行慢速推廣以防止帳號被 Facebook 限制。

## 📋 功能特色

1. **診所資訊自動爬取 (`scrape_fb_info.py`)**
   - 自動搜尋並收集診所的 Facebook 粉絲專頁、公開 Email 以及 Messenger 連結。
   - 提取專頁的「簡介」與「最新貼文」，做為後續 AI 分析與文案生成的基礎資料。
   - 優先爬取台中市診所，支援中斷與隨時存檔。

2. **AI 客製化文案生成 (`generate_copy_llm.py`)**
   - 串接本地大型語言模型（預設為啟動於 `http://localhost:8080` 的 `llama-qwen36` 容器）。
   - 根據診所名稱、診療科別（如兒科、眼科、外科）以及爬取到的簡介與貼文內容，自動生成**高度客製化**的行銷文案。
   - 例如：小兒科強調疫苗與兒童發展史、眼科強調近視控制與配鏡需求、外科強調傷口處置，杜絕罐頭開發信。

3. **智慧慢速開發發送 (`send_outreach.py`)**
   - 模擬真人輸入與發送，開啟診所的 Messenger 連結，智慧定位輸入框並填入個人化文案。
   - **冷卻機制**：預設每次發送間隔 5~10 分鐘的隨機冷卻時間，保護行銷帳號避免被臉書系統識別為機器人。
   - **自動熔斷機制**：發送訊息後自動偵測頁面，若發現「無法傳送」、「暫時被限制」、「無法送出」等 Facebook 限制關鍵字，會**立即終止**發送任務以防帳號被封鎖。
   - **沙盒測試 (Dry-Run)**：支援 `--dry-run` 參數，僅執行定位、貼上與截圖驗證，不實際送出訊息。

4. **留言與 Google Maps 評論推廣 (`post_clinics.py`)**
   - 自動在診所的 FB 貼文下方留言，或是在 Google Maps 上自動評分五星並貼上推廣評論。

5. **追蹤與統計儀表板 (`outreach_dashboard.html`)**
   - 提供直觀的網頁儀表板，可載入 `clinics西醫.csv` 並即時統計已處理、待發送、發送失敗等進度。

## ⚙️ 專案路徑與配置

- **資料庫 CSV**：`/home/hsuyungfeng/文件/doctor-toolbox-post/clinics西醫.csv`
- **JSON 快取**：`/home/hsuyungfeng/文件/doctor-toolbox-post/clinic_links.json`
- **發送日誌**：`/home/hsuyungfeng/文件/doctor-toolbox-post/outreach_sent_log.jsonl`
- **瀏覽器 Profile**：`./browser_profile` (用於保持 FB 登入狀態與指紋)
- **瀏覽器指紋設定**：固定使用 `--fingerprint=88888` 以確保指紋一致性。

## 🚀 快速開始步驟

### 第一步：初始化瀏覽器 Session
為了繞過登入驗證，必須先手動登入一次並儲存 Session：
```bash
python3 setup_session.py
```
此指令會以視窗模式開啟三個分頁：Facebook、Messenger、Google Maps。請在開啟的瀏覽器中手動完成登入並勾選「保持登入」，完成後在終端機按下 `Enter` 關閉瀏覽器。

### 第二步：執行診所資訊爬取
收集診所 FB 粉專資訊、簡介及貼文：
```bash
python3 scrape_fb_info.py
```

### 第三步：生成 AI 行銷文案
請確保本地 `llama-qwen36` 容器已在 `http://localhost:8080` 啟動，然後執行：
```bash
python3 generate_copy_llm.py
```

### 第四步：測試發送 (Dry-Run)
在實際發送前，建議先執行 1~2 筆測試，確認定位器與輸入是否正常，並查看截圖：
```bash
python3 send_outreach.py --dry-run --limit 2
```
*可在 `/tmp/outreach_dryrun.png` 查看輸入框貼上文案的結果。*

### 第五步：開始正式慢速發送
```bash
python3 send_outreach.py --limit 10 --delay-min 300 --delay-max 600
```

---

## 🛠️ 開發與測試
- 專案使用 [pytest](file:///home/hsuyungfeng/DevSoft/doctor-toolbox-post/pytest.ini) 配置忽略了 `tests` 目錄下的實體自動化指令碼，避免自動化邏輯干擾測試收集。
- **排錯提示**：若發送失敗，可至 `/tmp` 目錄下尋找 `outreach_failed_block_*.png` 或 `outreach_textbox_failed.png` 查看當下瀏覽器截圖。
