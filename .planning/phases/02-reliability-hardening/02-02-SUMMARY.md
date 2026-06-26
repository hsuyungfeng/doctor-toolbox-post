# Phase 2 - Plan 02 Summary: Adaptive backoff & halt

**日期:** 2026-06-26
**狀態:** 完成 (Completed)

## 實作內容

我們已完成可靠性強化階段的第二個計畫 (02-02)，針對 `send_outreach.py` 實作了動態延遲退避 (Adaptive Backoff) 與熔斷機制 (Halt Circuit Breaker)。

### 1. 智慧型防封鎖動態延遲退避 (Adaptive Delay Backoff)
- **延遲乘數 (Delay Multiplier):** 於發送流程中維護一個動態 `delay_multiplier`（初始值為 1.0）。
- **限制偵測與乘數加倍:** 當偵測到 Facebook 限制或發送失敗關鍵字（如 `無法傳送`、`暫時被限制` 等）時，會將狀態標記為 `backoff`，並將 `delay_multiplier` 加倍（乘以 2.0）。後續發送的隨機等待時間（`delay_min` 到 `delay_max`）也會乘以該倍數，拉長間隔以降低對臉書系統的衝擊。
- **逐步降速恢復:** 當成功發送一封郵件後，`delay_multiplier` 會乘以 0.9 逐漸收斂，直到恢復最底線的 1.0x 正常速度。

### 2. 連續警告計數與硬熔斷機制 (Halt Circuit Breaker)
- **連續限制計數:** 維護 `warning_count` 計數器，記錄連續遭遇 `delivery_failed` 的次數。
- **成功重置:** 任何一筆成功發送都會將 `warning_count` 重置為 0。
- **熔斷終止:** 當 `warning_count` 連續達到 3 次時，代表帳號極有可能已被軟封鎖或暫時禁言。此時程式會：
  - 在 CSV 中將最後一筆狀態記錄為 `session_halted`。
  - 將日誌寫入 `outreach_sent_log.jsonl`，記錄 `status="session_halted"`。
  - 印出高亮警告，並關閉瀏覽器，呼叫 `sys.exit(1)` 立即退出，避免帳號遭受永久停權的處罰。

### 3. 單元測試驗證 (`tests/test_backoff.py`)
撰寫了完整的 mock 測試案例：
- `test_backoff_and_circuit_breaker`: 
  - 模擬 Clinic A 發送成功 -> 狀態變更為 `sent`，`warning_count` 保持為 0，倍數為 1.0。
  - 模擬 Clinic B 遭遇限制 -> 狀態變更為 `backoff`，`warning_count` 增至 1，倍數變為 2.0x。
  - 模擬 Clinic C 遭遇限制 -> 狀態變更為 `backoff`，`warning_count` 增至 2，倍數變為 4.0x。
  - 模擬 Clinic D 遭遇限制 -> `warning_count` 達到 3，倍數變為 8.0x，觸發熔斷。確認拋出 `SystemExit(1)`，且 Clinic D 在 CSV 狀態欄寫入 `session_halted`。
- `test_backoff_recovery`: 
  - 驗證 Clinic A 與 Clinic B 發送成功時，乘數安全收斂且程序順利執行完成。

單元測試執行結果：**2 passed**。

## 產出檔案

1. 修正檔案: [send_outreach.py](file:///home/hsu/doctor-toolbox-post/send_outreach.py)
2. 測試檔案: [tests/test_backoff.py](file:///home/hsu/doctor-toolbox-post/tests/test_backoff.py)

---
*GSD 執行進度: Plan 02-02 已就緒，準備執行 Plan 02-03 (Master Campaign Orchestration CLI)*
