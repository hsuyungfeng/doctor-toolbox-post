# Phase 2 - Plan 03 Summary: Master Campaign Orchestrator

**日期:** 2026-06-26
**狀態:** 完成 (Completed)

## 實作內容

我們已完成可靠性強化階段的第三個計畫 (02-03)，實作了主控協調腳本 `run_campaign.py` 並搭配單元測試。

### 1. 主控協調流程 (Orchestration Pipeline)
建立一個統一的入口腳本 `run_campaign.py`，它以順序性的、非並行的安全方式串聯整個推廣管道的所有核心組件：
1. **釋放瀏覽器鎖定 (release_browser_locks):** 呼叫 `pkill -f browser_profile` 以確保任何殘留的瀏覽器程序皆已被強制終止，解鎖 profile 資源以防止啟動崩潰。
2. **工作階段驗證門鎖 (verify_facebook_session):** 在爬取和發送前，以無頭模式 (headless) 載入 Messenger 以驗證使用者的 Facebook 登入工作階段是否有效。如果尚未登入或 Cookie 已失效，則自動中斷並提示操作者重新執行 `setup_session.py`。
3. **診所爬取 (scrape_fb_info):** 爬取尚未取得 Intro/Posts 的診所，可透過 `--skip-scrape` 參數跳過。
4. **AI 客製化文案生成 (generate_copy_llm):** 自動檢查資料庫，對有 Intro/Posts 的診所調用 Qwen36 產生合規文案，對無資料診所自動指派通用備用文案，並提供 Pydantic 驗證及重試熔斷。
5. **發送沙盒測試 (send_outreach dry-run):** 正式發送前，會固定執行 limit=2 的 dry-run，驗證瀏覽器對定位器、文字寫入的定位準確度並儲存測試截圖。
6. **正式行銷外展發送 (send_outreach campaign):** 調用發送腳本，正式對候選名單發送文案，內建隨機冷卻間隔、動態退避延遲以及警告熔斷保護。支援使用 `--dry-run-only` 參數跳過此步驟。

### 2. 安全防護與命令防禦
- **避免權限提升 (STRIDE 減輕):** 子進程調用不使用 `shell=True`，而是以完整的 Python 解譯器路徑（`sys.executable`）及硬編碼的腳本路徑作為引數陣列，徹底防止任何 Shell 注入攻擊與意外程序執行。
- **無縫參數傳遞:** 允許操作者在外部直接傳遞 `--limit`、`--delay-min`、`--delay-max`、`--dry-run-only` 和 `--skip-scrape` 參數，自動路由與覆蓋子進程的核心設定。

### 3. 單元測試驗證 (`tests/test_campaign.py`)
撰寫了 4 個測試案例：
- `test_campaign_orchestrator_expired_session`: 驗證當 `verify_facebook_session` 檢測到未登入時，程序立即終止並拋出 `SystemExit(1)`。
- `test_campaign_orchestrator_success`: 驗證在正常工作階段下，系統按正確順序發起 4 個子進程（爬取、文案生成、沙盒發送、正式發送），且 CLI 覆蓋參數正常路由到子進程。
- `test_campaign_orchestrator_dry_run_only`: 驗證若帶入 `--dry-run-only` 標籤，程序只發起 3 個子進程，不執行正式發送。
- `test_campaign_orchestrator_skip_scrape`: 驗證帶入 `--skip-scrape` 標籤時，正確跳過爬取步驟。

單元測試執行結果：**4 passed**。

## 產出檔案

1. 新增檔案: [run_campaign.py](file:///home/hsu/doctor-toolbox-post/run_campaign.py)
2. 測試檔案: [tests/test_campaign.py](file:///home/hsu/doctor-toolbox-post/tests/test_campaign.py)

---
*GSD 執行進度: Phase 2 所有計畫 (02-01, 02-02, 02-03) 皆已實作並通過 100% 的測試驗證！*
