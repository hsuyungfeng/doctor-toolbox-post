# Phase 2 - Plan 01 Summary: Metadata check & fallbacks

**日期:** 2026-06-26
**狀態:** 完成 (Completed)

## 實作內容

我們已完成可靠性強化階段的第一個計畫 (02-01)，主要對 `generate_copy_llm.py` 進行了強化，並新增了單元測試。

### 1. 新增 Pydantic 驗證機制與通用備用文案
- 引入 `pydantic` 進行結構化 JSON 輸出驗證。
- 定義 `ClinicCopySchema` 驗證 schema：
  - **長度限制:** 文案字數必須在 80 到 180 字之間。
  - **全繁體中文檢測:** 定義了簡體字特徵黑名單，包含常見的 AI 簡體字洩漏（如 `医`、`国`、`诊`、`极` 等），只要檢測到即拒絕並拋出驗證錯誤。
  - **醫療廣告禁用詞過濾:** 排除違反台灣醫療法之誇大不實詞彙（如 `最佳`、`最先進`、`保證療效`、`根治`、`全台第一`）。
- 定義 `GENERIC_COPY` 常數，做為備用通用開發信。

### 2. 優化診所處理與重試路由機制
- **無資料診所自動路由:** 在 `main()` 中，若診所的 `Intro` 與 `Latest_Post` 皆為空，直接將 `Personalized_Copy` 寫入為 `GENERIC_COPY`，不呼叫 LLM，節省 Token 並提高速度。
- **LLM 呼叫 JSON 模式:** 強制傳遞 `"response_format": {"type": "json_object"}` 與降低 `temperature: 0.2` 以確保輸出穩定性。
- **重試與熔斷:** 若 LLM 輸出的文案無法通過 Pydantic 驗證（包含 JSON 格式錯亂、長度超標、含簡體字或禁用詞），自動重試最多 2 次（共 3 次嘗試）。若 3 次皆驗證失敗，則自動套用 `GENERIC_COPY`，確保整批任務不因單一診所生成錯誤而中斷。

### 3. 單元測試驗證 (`tests/test_fallback.py`)
撰寫了 6 個完整的測試案例：
- `test_clinic_copy_schema_valid`: 驗證合規的繁體中文文案能正常通過。
- `test_clinic_copy_schema_invalid_length`: 驗證文案過短 (<80 字) 或過長 (>180 字) 會被拒絕。
- `test_clinic_copy_schema_simplified_chinese`: 驗證含有簡體字 (如 `极`) 會被阻擋。
- `test_clinic_copy_schema_blacklist`: 驗證含有 `最佳` 等誇大詞會被阻擋。
- `test_generate_with_retry_success`: 驗證 LLM 正常回傳時的生成邏輯。
- `test_generate_with_retry_fallback_after_failures`: 驗證 LLM 失敗/不合規時，重試 3 次並最終套用 `GENERIC_COPY` 的機制。

單元測試執行結果：**6 passed**。

## 產出檔案

1. 修正檔案: [generate_copy_llm.py](file:///home/hsu/doctor-toolbox-post/generate_copy_llm.py)
2. 測試檔案: [tests/test_fallback.py](file:///home/hsu/doctor-toolbox-post/tests/test_fallback.py)
3. 測試用資料庫: [clinics西醫.csv](file:///home/hsu/doctor-toolbox-post/clinics西醫.csv) (建立 Mock 資料庫用於本地開發)

---
*GSD 執行進度: Plan 02-01 已就緒，準備執行 Plan 02-02 (Adaptive backoff & halt)*
