# 自動化設計 / Automation Design

# 中文版

## 1. 文件目的

本文件說明 **Automation Mock NVMe Validation（AMNV）** 的 Automation Layer 設計，主要包含：

- **A01 — Full Validation**
- **A02 — Deterministic Fault Campaign**
- Suite / Campaign 的執行順序；
- Individual Test / Case Result 的聚合方式；
- Fault Profile 的資料驅動設計；
- Storage Baseline 與 Runtime Log 管理；
- Exception Handling；
- Cooperative Cancellation；
- `ABORTED` / `NOT_RUN` / `STOPPED` 語意；
- PDF Report Handoff。

T01～T09 的 Individual Test Logic 已在 `04_Test_Design.md` 中說明。

本文件的重點是：

> Individual Test / Fault Case 如何被組合成可重複執行、可統計、可中止、可產生 Evidence Report 的 Automation Workflow。

---

## 2. Automation Layer 的定位

AMNV 的 Automation Layer 位於 GUI 與 Individual Validation Logic 之間。

概念上：

```text
GUI
→ Automation Suite / Campaign
→ Individual Test or Fault Case
→ CommandRunner / Mock Controller
→ Result / Evidence
→ Suite Aggregation
→ PDF Report
```

Automation Layer 不應重新實作底層 Command Logic。

它的主要責任是：

1. 決定執行哪些 Test / Case；
2. 控制執行順序；
3. 建立一致的執行前置狀態；
4. 聚合 Individual Result；
5. 處理 Test / Case Exception；
6. 處理 User Stop；
7. 產生 Suite-level Result；
8. 將 Result 交給 Reporter。

因此 Automation 的角色是：

```text
Orchestration
+
Execution Control
+
Result Aggregation
+
Evidence Handoff
```

---

## 3. A01 與 A02 的設計差異

A01 與 A02 都是 Automation，但設計目的不同。

| 項目 | A01 | A02 |
| --- | --- | --- |
| 名稱 | Full Validation | Deterministic Fault Campaign |
| 執行單位 | T01～T09 | Fault Campaign Case |
| 主要目的 | Full Regression | Fault-oriented Validation |
| Scenario 來源 | Python Test Modules | `fault_campaign.json` + Python Profile Logic |
| Coverage | Baseline、Normal、Negative、Recovery、Log | Timeout、Read Fail、Program Fail、Miscompare |
| Result Unit | Test Result | Case Result |
| Grouping | T01～T09 | FP01～FP04 |
| Storage Baseline | Suite start reset | Campaign start reset |
| Stop | ABORTED + NOT_RUN | ABORTED + NOT_RUN |
| Final Result | PASS / FAIL / STOPPED | PASS / FAIL / STOPPED |
| Report | A01 PDF | A02 PDF |

A01 回答：

> 「整套 Individual Validation Tests 是否可以一次完整執行？」

A02 回答：

> 「指定 Fault Profiles 是否能被穩定注入、偵測、記錄並依 Scenario 完成 Recovery？」

---

# 4. A01 — Full Validation

## 4.1 設計目標

A01 將 T01～T09 組成完整 Regression Suite。

主要目的：

- 一次執行所有 Individual Validation Tests；
- 固定 Test Execution Order；
- 統一建立 Storage Baseline；
- 保存每個 Test 的完整 Result；
- 即使某 Test 發生功能性 FAIL，也能依設定決定是否繼續；
- 將 Unexpected Exception 轉換為 `ERROR` Result；
- 支援 Cooperative Stop；
- 為尚未執行的 Test 建立 `NOT_RUN` Result；
- 聚合 Suite Statistics；
- 產生 A01 PDF Report。

主要檔案：

```text
amnv/automation/a01_full_validation.py
amnv/test_cases/t01_device_baseline.py
...
amnv/test_cases/t09_write_failure_recovery.py
amnv/cancellation.py
amnv/reporting/a01_reporter.py
config/validation_config.json
```

---

## 4.2 Test Execution Order

A01 的執行順序為：

```text
T01 Device Baseline Check
↓
T02 Normal Write / Readback
↓
T03 Invalid Read Range
↓
T04 Unsupported Command
↓
T05 Read Timeout + Recovery
↓
T06 Data Integrity Failure
↓
T07 Firmware Log Parsing
↓
T08 Read Error Correlation
↓
T09 Write Failure + Recovery
```

此順序具有設計意義。

前半部先確認：

```text
Baseline
→ Normal I/O
→ Basic Negative Command Handling
```

再進入：

```text
Timeout / Recovery
→ Data Integrity
→ Log Parsing
→ Error Correlation
→ Write Failure Recovery
```

因此整套 Suite 從基本功能逐步進入較複雜的 Fault / Recovery Validation。

---

## 4.3 Storage Baseline

A01 在 Suite 開始時會建立可重現的 Storage Baseline。

概念為：

```text
mock_storage_seed.json
→ Reset
→ mock_storage.json
→ T01~T09 Execution
```

這項設計的目的，是避免前一次人工測試或前一次 Suite 執行留下的 Storage State 影響本次 Regression。

Suite Report 也會保存 Storage Baseline Reset 的資訊。

A01 因此具有：

```text
Same Initial State
+
Same Test Order
+
Same Expected Behavior
```

使 Regression 結果具有可重現性。

---

## 4.4 Individual Test Invocation

A01 不直接複製 T01～T09 的 Test Logic。

它呼叫各 Test Module 的 `run()`，並傳入同一個 Suite Execution Context 所使用的 Cancellation Token。

概念如下：

```text
A01
→ run T01
→ receive TestResult

A01
→ run T02
→ receive TestResult

...

A01
→ run T09
→ receive TestResult
```

每一個 Test Result 本身仍保留：

- Expected；
- Actual；
- Validation Checks；
- Duration；
- Command Evidence；
- Recovery Evidence；
- Abort Evidence。

A01 只負責聚合，不重新判斷各 Test 內部的 Expected / Actual Logic。

---

## 4.5 Result Preservation

A01 會保存每個 Test 的 Result，而不是只保存最後 Suite PASS / FAIL。

例如：

```text
T01 PASS
T02 PASS
T03 PASS
T04 PASS
T05 FAIL
T06 PASS
...
```

Suite Result 因此可以回答兩種問題：

### Suite Level

```text
整套 Validation 是否通過？
```

### Test Level

```text
哪一個 Test 發生問題？
該 Test 的 Expected / Actual / Evidence 是什麼？
```

這讓 Automation Report 可以保留可追查性。

---

## 4.6 Test Exception Handling

如果 Individual Test 發生非預期 Exception，A01 不應讓整個 Python Process 因 Exception 直接失去 Result。

Automation Layer 會將這種情況轉成：

```text
Test Result = ERROR
```

並保存可用的 Exception Information。

其目的為區分：

```text
FAIL
= Test 正常完成，但 Validation Check 不符合 Expected

ERROR
= Test Logic 無法正常完成
```

這兩種情況在 Validation Report 中具有不同意義。

---

## 4.7 Continue Behavior

A01 的 Automation Design 允許根據 Configuration 決定 Individual Test 不通過後是否繼續執行後續 Test。

概念為：

```text
Test PASS
→ Continue

Test FAIL / ERROR
→ Check automation policy
    ├─ Continue
    └─ Stop normal suite execution
```

這與 User Stop 不同。

功能性 Failure 造成的正常流程停止，不應被標記為 `STOPPED`。

`STOPPED` 專門代表 Cancellation Request。

---

## 4.8 Normal Completion

當 T01～T09 都已按照 Suite Policy 完成，而且沒有 User Stop 時，A01 會聚合 Result。

主要統計欄位為：

```text
Total
Executed
Passed
Failed
Error
Aborted
Not Run
```

其中：

```text
Executed
=
Passed + Failed + Error + Aborted
```

`NOT_RUN` 不算 Executed。

---

## 4.9 A01 PASS / FAIL

### PASS

正常執行完成，而且所有要求執行的 Test 都通過。

典型結果：

```text
Total      9
Executed   9
Passed     9
Failed     0
Error      0
Aborted    0
Not Run    0

Suite = PASS
```

### FAIL

沒有 User Stop，但一個或多個 Test 為：

```text
FAIL
或
ERROR
```

則 Suite 應反映 Functional Validation Failure。

---

# 5. A01 Cooperative Stop

## 5.1 Stop 的目的

A01 支援在 Suite 執行期間由使用者按下 GUI `Test Stop`。

設計要求：

- 不使用 `QThread.terminate()`；
- 不把 User Stop 當成 Test FAIL；
- 已完成的 Test Result 不得被改寫；
- Active Test 可以成為 `ABORTED`；
- Remaining Test 成為 `NOT_RUN`；
- Suite 成為 `STOPPED`；
- Partial Result 仍然必須產生 PDF。

---

## 5.2 Stop Before Next Test

A01 在啟動下一個 Test 前會確認 Cancellation State。

如果 Stop 已經提出：

```text
Completed Tests
→ Preserve Original Result

Current / Next Scheduled Test
→ Do Not Start

Remaining Tests
→ NOT_RUN

Suite
→ STOPPED
```

---

## 5.3 Stop During Active Test

如果 Stop 發生於正在執行的 Test：

```text
GUI Stop
→ CancellationToken
→ Active Test observes token
→ Test attempts cooperative cancellation
```

若正在執行 `fake_nvme.py` subprocess：

```text
terminate()
→ approximately 0.5 s grace period
→ kill() fallback if needed
→ logical controller reset
```

Active Test 最終回傳：

```text
ABORTED
```

而不是：

```text
FAIL
```

---

## 5.4 Completed Test 不回溯修改

Stop Request 與 Test Completion 可能非常接近。

因此 A01 遵守：

> 如果 Test 已經在 Cancellation 生效前正常完成，就保留原本 PASS / FAIL / ERROR。

例如：

```text
T04 已完成 PASS
使用者按 Stop
T05 尚未開始

T04 = PASS
T05~T09 = NOT_RUN
Suite = STOPPED
```

不會把 T04 改成 ABORTED。

---

## 5.5 Partial Suite Example

已完成驗證的 A01 Active-stop Case 可以形成：

```text
T01 PASS
T02 PASS
T03 PASS
T04 PASS
T05 ABORTED
T06 NOT_RUN
T07 NOT_RUN
T08 NOT_RUN
T09 NOT_RUN
```

Summary：

```text
Total      9
Executed   5
Passed     4
Failed     0
Error      0
Aborted    1
Not Run    4

Suite = STOPPED
```

被中斷的 T05 仍可保存：

- Abort Stage；
- Stop Reason；
- Interrupted Command；
- Host Result；
- Process Termination；
- Queue State after abort；
- Outstanding CID；
- Next CID。

因此 STOP 並不代表 Evidence 消失。

---

# 6. A02 — Deterministic Fault Campaign

## 6.1 設計目標

A02 不直接重跑 T01～T09。

它是一套獨立的 Data-driven Fault Campaign，用來重複驗證指定 Fault Profile。

主要目的：

- 用固定 Case Definition 重現 Fault；
- 確認 Fault Detection；
- 確認 Host Result；
- 確認 Firmware-style Log；
- 確認 Storage Side Effect；
- 確認 Recovery；
- 形成 Fault Coverage Summary；
- 支援 Campaign Stop；
- 產生完整或 Partial PDF Report。

主要檔案：

```text
amnv/automation/a02_fault_campaign.py
data/fault_campaign.json
config/validation_config.json
amnv/runner.py
amnv/fault_injector.py
amnv/storage.py
amnv/log_parser.py
amnv/cancellation.py
amnv/reporting/a02_report.py
```

---

## 6.2 Data-driven Campaign

A02 將 Case Definition 與 Python Execution Logic 分開。

Case Definition 主要位於：

```text
data/fault_campaign.json
```

Python 負責：

```text
How to execute a fault profile
How to validate it
How to recover
```

JSON 負責：

```text
Which case
Which fault
Which operation
Which LBA
Expected detection
Expected recovery
Execution order
```

這種設計讓 Campaign 更接近 Validation Automation 常見的：

```text
Test Data
+
Reusable Execution Logic
```

而不是每個 Case 都複製一份 Python Script。

---

## 6.3 Campaign Configuration Validation

A02 啟動時會先檢查 Campaign Definition 是否符合 Automation Configuration。

其中包括：

```text
suite_id
execution_order / profile_order
```

如果：

```text
fault_campaign.json
```

與：

```text
validation_config.json
```

的 Profile Order 不一致，Automation 會視為 Configuration Error，而不是默默使用其中一份設定。

這可避免：

> 文件 / 設定以為按照 A 順序執行，但程式實際按照 B 順序執行。

---

## 6.4 Fault Profile Order

A02 的主要 Profile 為：

```text
FP01 — Command Timeout
FP02 — NAND Read Failure
FP03 — NAND Program Failure
FP04 — Data Miscompare
```

總 Case 數為：

```text
9 Cases
```

分布：

| Profile | Fault | Cases |
| --- | --- | ---: |
| FP01 | timeout | 3 |
| FP02 | NAND_READ_FAIL | 2 |
| FP03 | NAND_PROGRAM_FAIL | 2 |
| FP04 | miscompare | 2 |
| Total |  | 9 |

---

# 7. FP01 — Command Timeout

## 7.1 Coverage

FP01 包含：

```text
A02-FP01-C01
READ LBA 0
Recovery: Reset + Retry

A02-FP01-C02
READ LBA 100
Recovery: Reset + Retry

A02-FP01-C03
WRITE LBA 200
Recovery: Reset + Retry + Readback
```

## 7.2 Validation Focus

Timeout Profile 驗證：

```text
Fault Command
→ Host TIMEOUT
→ Outstanding CID
→ Controller Reset
→ Queue State Recovery
→ CID progression preserved
→ Retry
```

WRITE Timeout Case 另外增加 Final Readback。

## 7.3 Expected Detection

```text
TIMEOUT
```

這表示 Case 驗證的是 Host-side Timeout Detection，而不是 Controller Error Completion。

---

# 8. FP02 — NAND Read Failure

## 8.1 Coverage

FP02 包含：

```text
A02-FP02-C01
READ LBA 300

A02-FP02-C02
READ LBA 1500
```

Fault：

```text
NAND_READ_FAIL
```

## 8.2 Validation Focus

Expected Behavior：

```text
READ
→ FAILED Completion
→ Error = NAND_READ_FAIL
→ Runtime Firmware Log
→ Correlate Command and Log
```

Expected Detection：

```text
FAILED_CQ_AND_LOG
```

Recovery：

```text
Log correlation / No retry
```

FP02 的目的不是測 Recovery，而是集中測：

```text
Controller Failure
+
Host-visible Error
+
Firmware Evidence
```

---

# 9. FP03 — NAND Program Failure

## 9.1 Coverage

FP03 包含：

```text
A02-FP03-C01
WRITE LBA 400

A02-FP03-C02
WRITE LBA 2000
```

Fault：

```text
NAND_PROGRAM_FAIL
```

## 9.2 Validation Focus

Expected：

```text
Failed WRITE
→ FAILED / NAND_PROGRAM_FAIL
→ Firmware Log Correlation
→ Storage remains unchanged
→ Controller Reset
→ Retry WRITE
→ Final Readback
```

Expected Detection：

```text
FAILED_CQ_AND_LOG
```

Recovery：

```text
Correlate
+
Reset
+
Retry
+
Readback
```

這個 Profile 同時驗證：

- Failure Detection；
- Evidence Correlation；
- Data Protection；
- Recovery。

---

# 10. FP04 — Data Miscompare

## 10.1 Coverage

FP04 包含：

```text
A02-FP04-C01
READ LBA 500

A02-FP04-C02
READ LBA 2500
```

Fault：

```text
miscompare
```

## 10.2 Validation Focus

Expected Behavior：

```text
READ
→ CQ SUCCESS
→ Returned Data Corrupted
→ Validator detects mismatch
→ Underlying Storage remains intact
```

Expected Detection：

```text
DATA_MISCOMPARE
```

Recovery：

```text
None
```

這個 Profile 刻意驗證：

> Transport / Command Completion 成功，不代表 Data Integrity 正確。

---

# 11. A02 Case Setup

## 11.1 Setup 的目的

在 Fault Case 真正執行前，A02 可能需要先建立 Case 所需的 Baseline Data。

例如：

- 確認指定 LBA 有已知 Data；
- 為 WRITE Failure Case 建立 Old Data；
- 確認 Setup Command 本身成功。

Setup Failure 與 Fault Detection Failure 必須區分。

如果 Setup 就不符合預期，Case 不應繼續假裝 Fault Validation 有效。

---

## 11.2 Runtime Log Isolation

Case Setup 可能產生正常 Firmware-style Log。

因此 A02 在真正 Fault Command 前會清除 Setup Log，使 Case 的 Runtime Log Evidence 只屬於實際 Fault Execution。

概念：

```text
Case Setup
→ Setup may generate normal log
→ Clear Runtime Log
→ Execute Fault Command
→ Fault Log belongs to this Case
```

這可避免 Correlation 被前置 Command 汙染。

---

# 12. A02 Case Dispatch

A02 根據 `fault_profile` 選擇對應執行邏輯。

概念如下：

```text
timeout
→ Timeout Handler

NAND_READ_FAIL
→ Read Failure Handler

NAND_PROGRAM_FAIL
→ Program Failure Handler

miscompare
→ Miscompare Handler
```

如果 `fault_profile` 不在支援範圍：

```text
Configuration / Execution Error
```

而不是默默跳過。

---

# 13. A02 Case Result

每個 Case 都保存至少以下類型資訊：

```text
case_id
profile_id
fault_profile
operation
lba
result
duration
expected_detection
recovery
checks
setup
evidence
exception
```

因此 A02 Report 不只是列出：

```text
PASS / FAIL
```

還可以回答：

- 哪個 Fault Profile；
- 哪個 Command；
- 哪個 LBA；
- 預期如何偵測；
- 預期 Recovery；
- 實際 Evidence；
- 是否發生 Exception。

---

# 14. A02 Exception Handling

如果 Case 執行期間發生 Unexpected Exception：

```text
Case = ERROR
```

並保存：

- Exception Type；
- Exception Message；
- Traceback。

這與：

```text
Case FAIL
```

不同。

`FAIL` 表示 Fault Case 有正常完成，但 Validation Check 不符合 Expected。

`ERROR` 表示 Case Execution 本身出現非預期問題。

---

# 15. A02 Continue Behavior

A02 可以根據 Automation Configuration 決定：

```text
Case 不為 PASS
```

後是否繼續執行 Campaign。

概念：

```text
Case PASS
→ Next Case

Case FAIL / ERROR
→ Check continue policy
    ├─ Continue
    └─ End normal campaign execution
```

這和 User Stop 一樣需要分開定義。

正常 Failure Policy 導致的 Campaign 結束：

```text
Suite = FAIL
```

而不是：

```text
Suite = STOPPED
```

---

# 16. Profile Summary

A02 不只建立整體 Summary，也依 Fault Profile 聚合 Result。

例如：

```text
FP01
Total / Executed / Passed / Failed / Error / Aborted / Not Run

FP02
...

FP03
...

FP04
...
```

這讓 Report 可以回答：

> 是哪一種 Fault Coverage 出問題？

而不是只知道：

```text
A02 FAIL
```

---

# 17. A02 Normal Completion

正常完整 Campaign：

```text
FP01 Cases
→ FP02 Cases
→ FP03 Cases
→ FP04 Cases
→ Profile Summary
→ Campaign Summary
→ PDF
```

若 9 個 Case 都符合預期：

```text
Total       9
Executed    9
Passed      9
Failed      0
Error       0
Aborted     0
Not Run     0

A02 = PASS
```

如果沒有 User Stop，但一個或多個 Case FAIL / ERROR：

```text
A02 = FAIL
```

---

# 18. A02 Cooperative Stop

## 18.1 Stop Semantics

A02 和 A01 共用相同的核心 Cancellation 原則：

```text
Completed Case
→ Preserve PASS / FAIL / ERROR

Interrupted Active Case
→ ABORTED

Never-started Cases
→ NOT_RUN

Campaign
→ STOPPED
```

---

## 18.2 Stop During Fault Command

如果 Stop 發生在 active Fault Command：

```text
GUI Stop
→ CancellationToken
→ CommandRunner sees cancellation
→ terminate active fake_nvme.py
→ grace period
→ kill fallback if required
→ logical reset
→ Current Case = ABORTED
```

Abort Evidence 可包含：

- Abort Stage；
- Stop Reason；
- Interrupted CID；
- Opcode；
- LBA；
- Host Result；
- Timed Out；
- Process Termination Method；
- Queue State after abort；
- Outstanding CID；
- Next CID。

---

## 18.3 Partial Campaign Example

已完成驗證的 A02 Active-stop Scenario 可以形成：

```text
A02-FP01-C01 PASS
A02-FP01-C02 ABORTED
Remaining 7 Cases NOT_RUN
```

Summary：

```text
Total       9
Executed    2
Passed      1
Failed      0
Error       0
Aborted     1
Not Run     7

A02 = STOPPED
```

這代表：

- 第一個 Case 已正常完成；
- 第二個 Case 被使用者中止；
- 後面七個 Case 根本沒有開始。

它們不能全部被算成 FAIL。

---

# 19. STOPPED 與 FAIL 的區別

這是 Automation Design 的重要語意。

## FAIL

代表：

```text
Automation 正常執行
但
Validation Result 不符合 Expected
```

例如：

```text
Expected NAND_READ_FAIL
Actual SUCCESS
```

## STOPPED

代表：

```text
使用者主動要求停止執行
```

它不表示產品、Test Logic 或 Fault Scenario 發生 Functional Failure。

因此：

```text
FAIL != STOPPED
```

同樣：

```text
ABORTED != FAIL
NOT_RUN != FAIL
```

---

# 20. Summary Counting Rules

A01 / A02 共用的核心統計概念為：

```text
Total
Executed
Passed
Failed
Error
Aborted
Not Run
```

其中：

```text
Executed
=
Passed
+
Failed
+
Error
+
Aborted
```

而：

```text
Total
=
Executed
+
Not Run
```

這個定義讓 Partial Execution 可以被正確表示。

例如：

```text
Total     9
Executed  5
Not Run   4
```

不會錯誤顯示成：

```text
5 Failed
```

---

# 21. Storage Reset Strategy

## 21.1 A01

A01 在 Full Validation 開始前 Reset Storage Baseline。

目的是確保整套 Regression 從固定狀態開始。

## 21.2 A02

A02 的設定支援：

```text
reset_storage_before_campaign
reset_storage_after_campaign
```

Campaign Start Reset 的目的，是讓 Fault Case 從 deterministic storage state 開始。

Campaign End 是否 Reset 則可以依 Configuration 控制。

這種設計讓：

```text
Reproducibility
```

與：

```text
Post-run Evidence Inspection
```

可以分開考量。

---

# 22. Report Handoff

Automation 本身負責產生 Structured Result。

PDF Reporter 負責將 Result 轉換成展示與驗收 Evidence。

概念：

```text
A01
→ Suite Result
→ a01_reporter.py
→ A01 PDF

A02
→ Campaign Result
→ a02_report.py
→ A02 PDF
```

Reporter 不重新執行 Test / Case。

因此：

```text
Execution Logic
```

與：

```text
Presentation Logic
```

保持分離。

---

# 23. GUI Integration

GUI 透過 Background Worker 啟動 A01 / A02。

概念：

```text
A01 Button
→ Background Task
→ A01 run
→ Generate A01 PDF
→ Return:
   suite_result
   report_path
→ GUI Console
```

A02 同樣：

```text
A02 Button
→ Background Task
→ A02 run
→ Generate A02 PDF
→ Return:
   suite_result
   report_path
→ GUI Console
```

GUI 接收到 Result 後顯示：

- Suite Result；
- Passed / Failed；
- Executed；
- Duration；
- Report Path；
- A02 Fault Profile Summary 等資訊。

如果設定：

```text
report.auto_open = true
```

GUI 可以在 Automation 完成後要求系統開啟產生的 PDF。

---

# 24. Automation Design 的 Evidence 原則

Automation Result 必須盡可能保留執行事實，而不是只提供最終 Verdict。

例如 A01 STOPPED Report 必須能回答：

```text
哪些 Test 已執行？
哪些 PASS？
哪個被 Abort？
哪些完全沒執行？
Stop 發生在哪一個 Stage？
Abort 後 Queue 是否恢復？
```

A02 Report 則必須能回答：

```text
哪些 Fault Profile 被執行？
哪個 Case 發生 Fault？
Fault 如何被偵測？
是否有 Firmware Log Evidence？
是否 Recovery？
哪個 Case 被 Abort？
哪些 Case NOT_RUN？
```

這就是 AMNV 將 Automation 與 Reporting 綁定設計，但又把 Execution / Presentation Code 分離的原因。

---

# 25. Automation Boundary

A01 / A02 的 Automation 結果代表：

> 在 AMNV 的 deterministic Host-side logical model 中，指定 Regression / Fault Campaign 是否依定義完成 Detection、Validation、Recovery、Cancellation 與 Evidence Collection。

它不代表：

- 真實 SSD Qualification；
- 真實 PCIe Compliance；
- 真實 NVMe Protocol Certification；
- 真實 NAND Reliability Campaign；
- 真實 Controller Firmware Regression。

Automation Layer 的價值在於展示：

```text
Repeatable Scenario Execution
+
Deterministic Fault Reproduction
+
Result Aggregation
+
Failure Classification
+
Recovery Validation
+
Evidence Reporting
```

---

# English Version

## 1. Document Purpose

This document describes the Automation Layer design of **Automation Mock NVMe Validation (AMNV)**, primarily covering:

- **A01 — Full Validation**
- **A02 — Deterministic Fault Campaign**
- suite / campaign execution order;
- aggregation of individual test / case results;
- data-driven fault-profile design;
- storage baseline and runtime-log management;
- exception handling;
- cooperative cancellation;
- `ABORTED`, `NOT_RUN`, and `STOPPED` semantics;
- PDF report handoff.

The T01–T09 individual test logic is documented in `04_Test_Design.md`.

The main purpose of this document is to explain how individual tests and fault cases are organized into repeatable, measurable, cancellable automation workflows with preserved validation evidence.

---

## 2. Automation Layer Positioning

The AMNV Automation Layer sits between the GUI and the individual validation logic.

Conceptually:

```text
GUI
→ Automation Suite / Campaign
→ Individual Test or Fault Case
→ CommandRunner / Mock Controller
→ Result / Evidence
→ Suite Aggregation
→ PDF Report
```

The Automation Layer does not reimplement low-level command logic.

Its responsibilities are:

1. select tests / cases;
2. control execution order;
3. establish deterministic preconditions;
4. aggregate individual results;
5. handle test / case exceptions;
6. handle user cancellation;
7. generate suite-level results;
8. hand structured results to the reporting layer.

---

## 3. A01 vs A02

| Item | A01 | A02 |
| --- | --- | --- |
| Name | Full Validation | Deterministic Fault Campaign |
| Execution Unit | T01–T09 | Fault Campaign Case |
| Main Purpose | Full Regression | Fault-oriented Validation |
| Scenario Source | Python Test Modules | `fault_campaign.json` + Python Profile Logic |
| Coverage | Baseline, Normal, Negative, Recovery, Log | Timeout, Read Fail, Program Fail, Miscompare |
| Result Unit | Test Result | Case Result |
| Grouping | T01–T09 | FP01–FP04 |
| Storage Baseline | Reset at suite start | Reset at campaign start |
| Stop | ABORTED + NOT_RUN | ABORTED + NOT_RUN |
| Final Result | PASS / FAIL / STOPPED | PASS / FAIL / STOPPED |
| Report | A01 PDF | A02 PDF |

A01 answers:

> Can the complete set of individual validation tests be executed as a repeatable regression suite?

A02 answers:

> Can defined fault profiles be reproduced, detected, recorded, and recovered from according to the campaign design?

---

# 4. A01 — Full Validation

## 4.1 Design Objective

A01 organizes T01 through T09 into a complete regression suite.

Its primary responsibilities are:

- execute all individual validation tests;
- preserve a fixed execution order;
- establish a deterministic storage baseline;
- preserve complete per-test results;
- apply configured continuation behavior after functional failures;
- convert unexpected test exceptions into `ERROR` results;
- support cooperative cancellation;
- create `NOT_RUN` results for tests that never start;
- aggregate suite statistics;
- produce an A01 PDF report.

Main files:

```text
amnv/automation/a01_full_validation.py
amnv/test_cases/t01_device_baseline.py
...
amnv/test_cases/t09_write_failure_recovery.py
amnv/cancellation.py
amnv/reporting/a01_reporter.py
config/validation_config.json
```

---

## 4.2 Test Execution Order

```text
T01 Device Baseline Check
↓
T02 Normal Write / Readback
↓
T03 Invalid Read Range
↓
T04 Unsupported Command
↓
T05 Read Timeout + Recovery
↓
T06 Data Integrity Failure
↓
T07 Firmware Log Parsing
↓
T08 Read Error Correlation
↓
T09 Write Failure + Recovery
```

The sequence progresses from baseline and normal I/O validation into negative, fault, recovery, integrity, and evidence-oriented scenarios.

---

## 4.3 Storage Baseline

A01 begins from a deterministic storage state:

```text
mock_storage_seed.json
→ Reset
→ mock_storage.json
→ T01~T09 Execution
```

This prevents data left by previous manual or automated runs from affecting the regression result.

---

## 4.4 Individual Test Invocation

A01 calls each individual test rather than reimplementing its validation logic.

```text
A01
→ run T01
→ receive TestResult
→ run T02
→ receive TestResult
...
```

Each result preserves its own checks, command evidence, recovery state, and cancellation evidence.

---

## 4.5 Result Preservation

A01 keeps every individual test result so both suite-level and test-level questions can be answered.

The suite result identifies overall regression status.

The individual result explains the exact expected behavior, actual behavior, and evidence for each test.

---

## 4.6 Exception Handling

Unexpected exceptions are represented as:

```text
ERROR
```

rather than silently treated as functional validation failures.

The distinction is:

```text
FAIL
= validation completed but one or more checks did not match expectations

ERROR
= validation could not complete normally because of an unexpected execution problem
```

---

## 4.7 Continue Behavior

A01 can use automation configuration to determine whether later tests should continue after a non-passing test.

This is separate from user cancellation.

A normal policy-based stop caused by a functional failure results in a failed suite, not a `STOPPED` suite.

---

## 4.8 Normal Completion and Counting

A01 summarizes:

```text
Total
Executed
Passed
Failed
Error
Aborted
Not Run
```

The counting rule is:

```text
Executed
=
Passed + Failed + Error + Aborted
```

`NOT_RUN` is not counted as executed.

---

## 4.9 A01 PASS / FAIL

A normal all-pass run is:

```text
Total      9
Executed   9
Passed     9
Failed     0
Error      0
Aborted    0
Not Run    0

Suite = PASS
```

If one or more tests fail or error without a user stop:

```text
Suite = FAIL
```

---

# 5. A01 Cooperative Stop

A01 supports a user-requested Stop without forcefully terminating the Qt worker thread.

The design rules are:

- preserve completed PASS / FAIL / ERROR results;
- mark the interrupted active test `ABORTED`;
- mark never-started tests `NOT_RUN`;
- mark the suite `STOPPED`;
- still generate a partial PDF report.

If cancellation interrupts an active mock-controller subprocess:

```text
terminate()
→ approximately 0.5 s grace period
→ kill() fallback if necessary
→ logical controller reset
```

A verified partial result can take the form:

```text
T01 PASS
T02 PASS
T03 PASS
T04 PASS
T05 ABORTED
T06 NOT_RUN
T07 NOT_RUN
T08 NOT_RUN
T09 NOT_RUN

Total      9
Executed   5
Passed     4
Failed     0
Error      0
Aborted    1
Not Run    4

Suite = STOPPED
```

---

# 6. A02 — Deterministic Fault Campaign

## 6.1 Design Objective

A02 is a separate data-driven fault campaign rather than a rerun of T01–T09.

It is designed to:

- reproduce fault conditions from fixed case definitions;
- validate detection;
- validate Host-visible results;
- validate firmware-style evidence;
- validate storage side effects;
- validate recovery;
- generate fault-profile coverage summaries;
- support campaign cancellation;
- generate full or partial PDF reports.

Main files:

```text
amnv/automation/a02_fault_campaign.py
data/fault_campaign.json
config/validation_config.json
amnv/runner.py
amnv/fault_injector.py
amnv/storage.py
amnv/log_parser.py
amnv/cancellation.py
amnv/reporting/a02_report.py
```

---

## 6.2 Data-driven Campaign

A02 separates case data from reusable execution logic.

`fault_campaign.json` defines which cases to run, while Python defines how each supported fault profile is executed, validated, and recovered.

This avoids duplicating an entire Python script for every LBA / fault combination.

---

## 6.3 Configuration Validation

A02 validates campaign identity and profile order before execution.

If `fault_campaign.json` and `validation_config.json` disagree on the configured campaign order, the mismatch is treated as a configuration error instead of being silently ignored.

---

## 6.4 Fault Profile Order and Coverage

```text
FP01 — Command Timeout
FP02 — NAND Read Failure
FP03 — NAND Program Failure
FP04 — Data Miscompare
```

Case distribution:

| Profile | Fault | Cases |
| --- | --- | ---: |
| FP01 | timeout | 3 |
| FP02 | NAND_READ_FAIL | 2 |
| FP03 | NAND_PROGRAM_FAIL | 2 |
| FP04 | miscompare | 2 |
| Total |  | 9 |

---

# 7. FP01 — Command Timeout

Cases:

```text
A02-FP01-C01
READ LBA 0
Recovery: Reset + Retry

A02-FP01-C02
READ LBA 100
Recovery: Reset + Retry

A02-FP01-C03
WRITE LBA 200
Recovery: Reset + Retry + Readback
```

The profile validates Host timeout detection, outstanding CID state, reset, CID progression, retry, and final readback where applicable.

Expected detection:

```text
TIMEOUT
```

---

# 8. FP02 — NAND Read Failure

Cases:

```text
A02-FP02-C01
READ LBA 300

A02-FP02-C02
READ LBA 1500
```

Fault:

```text
NAND_READ_FAIL
```

Expected behavior:

```text
READ
→ FAILED Completion
→ NAND_READ_FAIL
→ Runtime Firmware Log
→ Command / Log Correlation
```

Expected detection:

```text
FAILED_CQ_AND_LOG
```

No retry is required by this profile.

---

# 9. FP03 — NAND Program Failure

Cases:

```text
A02-FP03-C01
WRITE LBA 400

A02-FP03-C02
WRITE LBA 2000
```

Fault:

```text
NAND_PROGRAM_FAIL
```

Expected behavior:

```text
Failed WRITE
→ Firmware Log Correlation
→ Storage remains unchanged
→ Reset
→ Retry WRITE
→ Readback
```

This profile validates failure detection, evidence correlation, data protection, and recovery.

---

# 10. FP04 — Data Miscompare

Cases:

```text
A02-FP04-C01
READ LBA 500

A02-FP04-C02
READ LBA 2500
```

Fault:

```text
miscompare
```

Expected behavior:

```text
CQ SUCCESS
→ Returned Data Corrupted
→ Validator Detects Mismatch
→ Storage Remains Intact
```

Expected detection:

```text
DATA_MISCOMPARE
```

No recovery action is required.

---

# 11. Case Setup and Runtime Log Isolation

A02 cases may establish known data before fault injection.

Setup failure is treated separately from fault-detection failure.

Because setup commands may produce normal firmware-style log entries, A02 clears the runtime log before the actual fault command so that the case owns isolated fault evidence.

```text
Setup
→ Clear Runtime Log
→ Fault Execution
→ Correlate Fault Evidence
```

---

# 12. Fault Profile Dispatch

A02 dispatches reusable handlers based on `fault_profile`:

```text
timeout
→ Timeout Handler

NAND_READ_FAIL
→ Read Failure Handler

NAND_PROGRAM_FAIL
→ Program Failure Handler

miscompare
→ Miscompare Handler
```

Unsupported profiles are treated as errors rather than silently skipped.

---

# 13. Case Result Model

A case preserves information such as:

```text
case_id
profile_id
fault_profile
operation
lba
result
duration
expected_detection
recovery
checks
setup
evidence
exception
```

This allows the report to explain not only whether a case passed, but what was executed, what was expected, what was detected, and what evidence was collected.

---

# 14. Exception and Continue Behavior

Unexpected case exceptions become:

```text
ERROR
```

A functional validation mismatch becomes:

```text
FAIL
```

Automation configuration can control whether campaign execution continues after a non-passing case.

A normal failure-policy stop results in `FAIL`, not `STOPPED`.

---

# 15. Profile Summary

A02 aggregates results by FP01 through FP04 so fault coverage can be evaluated by fault class rather than only by a single campaign-level result.

The summary can distinguish:

```text
Total
Executed
Passed
Failed
Error
Aborted
Not Run
```

for each profile.

---

# 16. A02 Normal Completion

A normal campaign executes:

```text
FP01
→ FP02
→ FP03
→ FP04
→ Profile Summary
→ Campaign Summary
→ PDF
```

A complete all-pass run is:

```text
Total       9
Executed    9
Passed      9
Failed      0
Error       0
Aborted     0
Not Run     0

A02 = PASS
```

Functional failures or errors without cancellation produce:

```text
A02 = FAIL
```

---

# 17. A02 Cooperative Stop

The core cancellation semantics match A01:

```text
Completed Case
→ preserve PASS / FAIL / ERROR

Interrupted Active Case
→ ABORTED

Never-started Case
→ NOT_RUN

Campaign
→ STOPPED
```

A verified active-stop result can take the form:

```text
A02-FP01-C01 PASS
A02-FP01-C02 ABORTED
Remaining 7 Cases NOT_RUN

Total       9
Executed    2
Passed      1
Failed      0
Error       0
Aborted     1
Not Run     7

A02 = STOPPED
```

Abort evidence can preserve the interrupted command, abort stage, stop reason, process termination method, queue recovery state, outstanding CID state, and next CID.

---

# 18. STOPPED vs FAIL

`FAIL` means:

```text
The validation executed normally,
but actual behavior did not match expected behavior.
```

`STOPPED` means:

```text
The user explicitly requested execution to stop.
```

Therefore:

```text
FAIL != STOPPED
ABORTED != FAIL
NOT_RUN != FAIL
```

This distinction is required for accurate automation evidence.

---

# 19. Summary Counting Rules

The common counting rules are:

```text
Executed
=
Passed + Failed + Error + Aborted
```

and:

```text
Total
=
Executed + Not Run
```

These rules allow partial executions to be represented without misclassifying unexecuted units as failures.

---

# 20. Storage Reset Strategy

A01 resets the storage baseline before the full regression suite.

A02 supports campaign reset behavior through configuration, including reset before the campaign and optional reset after the campaign.

The goal is to balance deterministic test setup with the ability to inspect post-run state.

---

# 21. Report Handoff

Automation produces structured results.

Reporting converts those results into evidence documents.

```text
A01
→ Suite Result
→ a01_reporter.py
→ A01 PDF

A02
→ Campaign Result
→ a02_report.py
→ A02 PDF
```

The reporting layer does not execute validation logic again.

---

# 22. GUI Integration

The GUI launches A01 and A02 as background tasks.

Each automation wrapper returns:

```text
suite_result
report_path
```

The GUI then displays summary information and the generated PDF path.

If configured, the generated report can be opened automatically after completion.

---

# 23. Evidence-Oriented Automation

Automation results are designed to preserve execution facts rather than only a final verdict.

A01 evidence should make it possible to identify:

- executed tests;
- passed / failed / errored tests;
- aborted active test;
- never-started tests;
- cancellation stage;
- recovery state.

A02 evidence should additionally identify:

- executed fault profiles;
- case-level fault behavior;
- detection method;
- firmware-log evidence;
- recovery action;
- aborted and not-run cases.

---

# 24. Automation Boundary

A01 and A02 demonstrate deterministic automation inside the AMNV Host-side logical model.

They do not represent real SSD qualification, PCIe compliance testing, NVMe certification, NAND reliability testing, or real controller-firmware regression.

The Automation Layer demonstrates:

```text
Repeatable Scenario Execution
+
Deterministic Fault Reproduction
+
Result Aggregation
+
Failure Classification
+
Recovery Validation
+
Cancellation Handling
+
Evidence Reporting
```
