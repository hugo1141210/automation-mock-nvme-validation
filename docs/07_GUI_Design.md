# GUI 設計 / GUI Design

# 中文版

## 1. 文件目的

本文件說明 **Automation Mock NVMe Validation（AMNV）** 的 PySide6 GUI 設計，包括：

- GUI 的設計目標；
- 視窗與功能區塊；
- T01～T09 Individual Test 操作；
- A01 / A02 Automation 操作；
- Background Worker / QThread 設計；
- Test Stop 與 Cancellation 的 GUI 整合；
- Console / Log Viewer；
- Mock Storage Utility；
- PDF Report 操作；
- GUI 與 Backend Validation Logic 的責任邊界。

AMNV GUI 的定位不是複雜的產品管理介面，而是一個 **Validation Control Panel**。

它的主要目的，是讓使用者可以：

```text
選擇 Scenario
→ 啟動 Validation
→ 觀察執行狀態
→ 必要時停止
→ 查看 Result / Evidence
→ 開啟 Report
```

---

## 2. GUI 設計目標

GUI 的設計遵循下列原則。

### 2.1 單一視窗完成主要操作

AMNV 不使用多層 Menu 或多個 Dialog 切換主要功能。

核心操作集中在同一個 Main Window：

- T01～T09；
- A01；
- A02；
- Test Stop；
- Storage Utility；
- Report Utility；
- Console。

這樣可以降低 Demo 與實際操作時的切換成本。

### 2.2 Test Selection 與 Evidence Observation 同時可見

畫面上方負責：

```text
選擇 Test / Automation
```

畫面下方則提供：

```text
Console / Log Viewer
```

因此使用者啟動 Test 後，不需要切換頁面即可看到執行結果。

### 2.3 GUI 不承擔 Validation Logic

GUI 負責：

```text
Dispatch
Display
Control
Report Integration
```

Backend 負責：

```text
Command Execution
Validation
Fault Injection
Recovery
Result Generation
```

這樣 Test Logic 不會被綁定在 Qt Widget 中。

### 2.4 長時間工作不可阻塞 Main Thread

像 T05 Timeout、A01、A02 等工作可能需要數秒甚至更久。

因此 Test / Automation 不直接在 Qt Main Thread 執行，而是放到 Background Worker。

這可避免：

- Window 顯示 Not Responding；
- Console 無法更新；
- Stop Button 無法操作。

### 2.5 Stop 必須是 Controlled Cancellation

GUI 不使用強制 `QThread.terminate()`。

Stop 的概念是：

```text
GUI 發出 Cancellation Request
→ Backend 自行在安全位置停止
→ 必要時終止 active Mock Controller subprocess
→ 保存 ABORTED Evidence
```

---

# 3. GUI 主要檔案

GUI 相關檔案：

```text
main.py

amnv/ui/
├── __init__.py
├── main_window.py
├── main_window.ui
├── test_worker.py
└── ui_main_window.py
```

責任分工：

| 檔案 | 主要責任 |
| --- | --- |
| `main.py` | 建立 QApplication 與 MainWindow |
| `main_window.ui` | Qt Designer Layout Source |
| `ui_main_window.py` | 由 UI Compiler 產生 Widget Code |
| `main_window.py` | GUI Business / Control Logic |
| `test_worker.py` | Generic Background Task Worker |

---

# 4. Main Window

AMNV Main Window 的設計尺寸為：

```text
800 x 700
```

同時設定 Minimum Size：

```text
800 x 700
```

主要分成三個區域：

```text
┌─────────────────────────────────────────────────────┐
│ Validation Tests                      │ Control      │
│ T01 T04 T07                           │ Storage      │
│ T02 T05 T08                           │ Stop         │
│ T03 T06 T09                           │ Report       │
│         A01            A02                          │
├─────────────────────────────────────────────────────┤
│                                                     │
│              Console / Log Viewer                   │
│                                                     │
│                                                     │
│                                              Clear  │
└─────────────────────────────────────────────────────┘
```

三個主要 Group 為：

1. `Validation Tests`
2. `Control`
3. `Console / Log Viewer`

---

# 5. Validation Tests 區域

## 5.1 T01～T09

Individual Test Button：

```text
T01 Device Baseline
T02 Write / Readback
T03 Invalid Range

T04 Unsupported Cmd
T05 Timeout / Recovery
T06 Data Integrity

T07 Log Parsing
T08 Read FW Error
T09 Write Failure
```

版面採三欄配置，讓九個 Test 可以在同一個區域快速辨識。

每個 Button 對應一個 Test Module：

```text
T01 → t01_device_baseline.py
T02 → t02_write_readback.py
T03 → t03_invalid_read_range.py
T04 → t04_unsupported_command.py
T05 → t05_read_timeout_recovery.py
T06 → t06_data_integrity_failure.py
T07 → t07_firmware_log_parsing.py
T08 → t08_read_error_correlation.py
T09 → t09_write_failure_recovery.py
```

---

## 5.2 Individual Test 操作流程

使用者點選 Test：

```text
Button Click
→ main_window.py
→ _start_test()
→ _start_background_task()
→ QThread + TestWorker
→ Test run()
→ TestResult
→ GUI Result Handler
→ Console
```

GUI 不需要知道 Test 內部執行了幾筆 READ / WRITE。

它只負責：

- 啟動正確 Task；
- 接收 Result；
- 顯示 Summary。

---

# 6. A01 / A02 Automation Button

Validation Test 區域底部另外提供：

```text
A01 Full Validation
A02 Fault Campaign
```

它們和 Individual Test 分開，是因為執行粒度不同。

### A01

```text
A01
→ T01 ~ T09
→ Suite Result
→ A01 PDF
```

### A02

```text
A02
→ Fault Campaign Cases
→ Profile / Campaign Result
→ A02 PDF
```

因此 GUI 讓使用者可以選擇：

```text
單獨測某一項
```

或：

```text
執行完整 Automation
```

---

# 7. Control 區域

Control Group 提供四個操作：

```text
Read Current Data
Reset Data
Test Stop
Open Last Report
```

這四個按鈕分成三種用途：

### Storage Utility

```text
Read Current Data
Reset Data
```

### Execution Control

```text
Test Stop
```

### Evidence Utility

```text
Open Last Report
```

---

# 8. Read Current Data

`Read Current Data` 用來讀取目前：

```text
data/mock_storage.json
```

並把目前 Mock Storage State 顯示到 Console。

用途包括：

- 確認 WRITE 是否改變資料；
- 檢查 Fault 後 Storage 是否保持不變；
- Demo 時直接觀察 Runtime Storage。

這是 Debug / Inspection Utility，不會改變 Storage。

---

# 9. Reset Data

`Reset Data` 用來將：

```text
data/mock_storage_seed.json
```

恢復成：

```text
data/mock_storage.json
```

概念：

```text
Seed Baseline
→ Reset
→ Runtime Storage
```

用途：

- 清除之前 Test 的寫入結果；
- 回到 deterministic baseline；
- 手動準備下一次 Demo / Test。

Automation 自己也具有對應的 Baseline Reset Policy，因此 GUI Reset 是額外提供給使用者的人工控制工具。

---

# 10. Console / Log Viewer

畫面下半部是：

```text
QPlainTextEdit
```

並設定：

```text
Read Only = true
Line Wrap = NoWrap
Maximum Block Count = 5000
```

這個區域是 GUI 的主要 Runtime Observation Interface。

---

## 10.1 Timestamp

GUI Log 使用時間戳：

```text
HH:MM:SS.mmm
```

概念輸出：

```text
[18:20:10.125] [TEST] T05 - Read Timeout + Recovery started.
[18:20:12.180] [TEST] T05 Result: PASS
```

時間戳的目的不是進行高精度 Performance Measurement，而是讓使用者可以觀察：

- Task Start；
- Result；
- Stop；
- Error；
- Report Generation；

之間的事件順序。

---

## 10.2 Console 顯示內容

Individual Test 完成後，GUI 可顯示：

```text
Test ID
Result
Expected
Actual
Duration
Validation Check Count
```

A01 / A02 完成後則主要顯示：

```text
Suite Result
Executed
Passed
Failed
Duration
Report Path
```

A02 另外可以顯示 Fault Profile / Case Summary。

---

## 10.3 Clear

Console 提供：

```text
Clear
```

只清除畫面上的文字。

它不會：

- Reset Storage；
- 刪除 PDF；
- 清除 Test Result；
- 中止執行中的 Test。

---

# 11. Background Execution

## 11.1 為什麼使用 QThread

Test 若直接在 Main Thread 執行：

```text
Button Click
→ Test runs for several seconds
```

Qt Event Loop 會被阻塞。

結果可能是：

- GUI 無法 redraw；
- Button 無法操作；
- Stop Request 無法送出；
- Window 顯示沒有回應。

因此 AMNV 使用：

```text
QThread
+
TestWorker
```

執行 Backend Task。

---

## 11.2 TestWorker

`TestWorker` 是 Generic Worker。

它接收：

```text
Callable[[], Any]
```

主要 Signal：

```text
result
error
finished
```

執行概念：

```text
try:
    result = task()
    emit result

except:
    emit error

finally:
    emit finished
```

Worker 不需要知道目前執行的是：

```text
T05
A01
A02
```

因此同一個 Worker 可以重用。

---

# 12. Background Task Lifecycle

GUI 啟動 Task 時會建立：

```text
QThread
TestWorker
Active Task Metadata
CancellationToken
```

概念流程：

```text
Start Task
↓
Create New CancellationToken
↓
Create QThread
↓
Create TestWorker
↓
Move Worker to Thread
↓
Thread Started
↓
Worker.run()
↓
Result / Error
↓
Worker Finished
↓
Thread Quit
↓
deleteLater()
↓
GUI State Cleanup
```

這確保每次 Test 執行都具有自己的 Thread Lifecycle。

---

# 13. Single Active Task

GUI 不允許同時啟動兩個 Validation Task。

如果：

```text
T05 正在執行
```

此時又要求：

```text
A01
```

GUI 應拒絕第二個 Task，並在 Console 顯示：

```text
Another test is already running.
```

原因是多個 Test 同時執行會共同競爭：

- `mock_storage.json`
- `runtime_fw.log`
- Report / Runtime State

也會破壞 deterministic validation。

因此 GUI 採：

```text
One Active Validation Task at a Time
```

---

# 14. Active Button / Execution State

Task 開始後，GUI 會記錄：

```text
active_test_id
active_test_name
active_test_button
```

這些資訊用來：

- 顯示目前執行項目；
- 管理 Result Handler；
- 在 Task 結束後恢復 UI State。

至少 Active Task Button 在執行期間會被停用，避免同一個 Task 被連續重複啟動。

即使其他 Button 仍存在，Single Active Task Guard 仍會阻止平行 Validation。

---

# 15. Test Stop

## 15.1 GUI Stop 的設計目標

`Test Stop` 必須能處理：

- T01～T09 Individual Test；
- A01；
- A02。

但 Stop 不等於：

```text
Kill QThread
```

真正流程是：

```text
Test Stop
→ CancellationToken.request()
→ Backend observes token
→ Controlled Cancellation
```

---

## 15.2 為什麼不使用 QThread.terminate()

`QThread.terminate()` 可能在任意程式位置強制停止 Thread。

如果當下正在：

- 修改 Queue；
- 寫 Storage；
- 產生 Log；
- 更新 Evidence；

可能留下不一致狀態。

因此 STOP v1 不採強制 Thread Kill。

---

## 15.3 CancellationToken

每次新的 Test / A01 / A02 都使用新的：

```text
CancellationToken
```

Token 底層使用 thread-safe Event。

GUI Thread 可以直接執行：

```text
token.request()
```

而不需要等待 Worker Event Loop 處理 Qt Slot。

這一點很重要，因為 Worker 執行長時間 Python Function 時，本身不一定有機會即時處理 queued Qt event。

---

# 16. Individual Test Stop

Individual Test 在預定 cancellation point 檢查 Token。

如果尚未開始主要 Command：

```text
Stop
→ Test returns ABORTED
```

如果正在執行 active `fake_nvme.py` subprocess：

```text
Stop
↓
Runner observes cancellation
↓
terminate()
↓
0.5 s grace period
↓
kill() fallback if required
↓
logical controller reset
↓
Result = ABORTED
```

GUI 最後顯示的是 Test Result，而不是將它當成 GUI Error。

---

# 17. A01 Stop

A01 Stop 的 GUI 行為需要保留 Partial Suite Result。

例如：

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

GUI 最終可顯示：

```text
A01 Result: STOPPED
```

同時 Reporter 仍產生 Partial PDF。

因此 Stop 不是：

```text
丟棄整次執行結果
```

而是：

```text
結束執行並保存目前 Evidence
```

---

# 18. A02 Stop

A02 使用相同原則。

例如：

```text
Case 1 PASS
Case 2 ABORTED
Remaining 7 Cases NOT_RUN

A02 = STOPPED
```

GUI 接收到完整 Campaign Result 後，一樣可以：

- 顯示 Summary；
- 顯示 Report Path；
- 開啟 Partial Report。

---

# 19. STOP Button 的狀態語意

Stop Request 只在有 Active Task 時有意義。

如果沒有執行中的 Task，GUI 不應製造假的：

```text
ABORTED
```

Result。

如果使用者重複按 Stop：

```text
CancellationToken
```

仍維持第一次 Stop Reason。

目的在於：

- Stop Request idempotent；
- 不覆寫原始原因；
- 不重複改變 Result。

---

# 20. Error Handling

`TestWorker` 捕捉未處理 Exception，並透過：

```text
error signal
```

把 traceback 送回 GUI。

GUI Error Handler 負責把錯誤顯示到 Console。

無論 Task 成功或 Exception：

```text
finished
```

都會送出，讓 Thread 正常清理。

因此 Worker Lifecycle 不依賴 Task 一定成功。

---

# 21. A01 Report Integration

GUI 的 A01 Wrapper 概念為：

```text
Run A01
↓
Suite Result
↓
Generate A01 Report
↓
Return:
    suite_result
    report_path
```

GUI 接收後主要顯示：

- A01 Result；
- Test Summary；
- Duration；
- PDF Path。

STOPPED Suite 也使用相同流程，因此可以產生 Partial Report。

---

# 22. A02 Report Integration

A02：

```text
Run A02
↓
Campaign Result
↓
Generate A02 Report
↓
Return:
    suite_result
    report_path
```

GUI 可顯示：

- Campaign Result；
- Passed / Executed；
- Failed / Error / Aborted；
- Fault Profiles；
- Duration；
- PDF Path。

---

# 23. Report Auto Open

設定檔可以提供：

```text
report.auto_open
```

如果：

```text
true
```

GUI 在 Report 產生完成後，可以使用 Qt Desktop Service 要求系統開啟 PDF。

如果：

```text
false
```

則只在 Console 顯示 Report Path。

這讓 Automated Run 不一定每次都彈出 PDF Viewer。

---

# 24. Open Last Report

`Open Last Report` 會在 Report Root 下搜尋：

```text
reports/**/*.pdf
```

並依檔案修改時間選擇最新 PDF。

用途：

- 不需要知道最新 Report 的確切檔名；
- Demo 後可以快速重新開啟剛產生的 Evidence。

如果沒有 Report：

```text
No PDF report found.
```

會顯示在 Console。

---

# 25. GUI 與 Report 的責任邊界

GUI 只負責：

```text
要求產生 Report
取得 report_path
開啟 PDF
```

實際 PDF Layout 與 Evidence Rendering 由：

```text
amnv/reporting/a01_reporter.py
amnv/reporting/a02_report.py
```

負責。

因此修改 PDF Layout 不需要修改 Qt UI Layout。

---

# 26. UI Source 與 Generated Code

GUI Layout 的正式 Source 是：

```text
main_window.ui
```

`ui_main_window.py` 是由 Qt User Interface Compiler 產生。

Generated File 本身也明確標示：

```text
All changes made in this file will be lost when recompiling UI file.
```

因此設計規則為：

```text
修改 Layout
→ main_window.ui

重新產生
→ ui_main_window.py

功能邏輯
→ main_window.py
```

不直接手動維護 `ui_main_window.py`。

---

# 27. GUI 與 Backend 邊界

## GUI 負責

- User Input；
- Test Selection；
- Task Start；
- Stop Request；
- Thread Management；
- Console Display；
- Storage Utility；
- Report Opening。

## Backend 負責

- Command Lifecycle；
- SQ / CQ；
- Fault Injection；
- Timeout；
- Reset；
- Retry；
- Validation；
- Test Result；
- Suite Result；
- Evidence。

GUI 不應根據畫面邏輯重新判定：

```text
PASS
FAIL
ABORTED
STOPPED
```

這些 Result 必須由 Backend Structured Result 提供。

---

# 28. GUI Design Boundary

目前 GUI 的主要目的為：

```text
Validation Control
+
Runtime Observation
+
Evidence Access
```

不是建立完整的 Test Management System。

因此目前刻意沒有加入：

- User Account；
- Database-backed Test History；
- Multi-device Lab Management；
- Remote Host Control；
- Dashboard Analytics；
- Real-time Chart；
- Test Scheduler；
- Parallel Test Execution。

這些功能若未來需要，可以在不改變 Core Validation Logic 的前提下另外擴充。

---

# 29. GUI 設計總結

AMNV GUI 的核心設計可以概括為：

```text
Simple Test Selection
+
One Active Task
+
Background Execution
+
Cooperative Stop
+
Observable Console
+
Storage Inspection
+
PDF Evidence Access
```

GUI 並不是專案的 Validation Engine。

它是一個把既有 Test / Automation / Reporting 模組整合成可操作工具的 Presentation / Control Layer。

---

# English Version

## 1. Document Purpose

This document describes the PySide6 GUI design of **Automation Mock NVMe Validation (AMNV)**, including:

- GUI objectives;
- window layout;
- T01–T09 execution;
- A01 / A02 execution;
- background worker and QThread design;
- Test Stop and cancellation integration;
- console/log viewer;
- mock-storage utilities;
- PDF report handling;
- GUI/backend responsibility boundaries.

The GUI is positioned as a **validation control panel**, not as a full test-management product.

Its primary workflow is:

```text
Select Scenario
→ Start Validation
→ Observe Execution
→ Stop if Required
→ Review Result / Evidence
→ Open Report
```

---

## 2. GUI Design Goals

The GUI follows these principles:

1. keep all major operations in one main window;
2. keep test selection and runtime observation visible together;
3. keep validation logic outside Qt widgets;
4. execute long-running work outside the main GUI thread;
5. use cooperative cancellation instead of forcibly terminating worker threads.

---

# 3. GUI Files

```text
main.py

amnv/ui/
├── __init__.py
├── main_window.py
├── main_window.ui
├── test_worker.py
└── ui_main_window.py
```

| File | Responsibility |
| --- | --- |
| `main.py` | QApplication and MainWindow entry point |
| `main_window.ui` | Qt Designer layout source |
| `ui_main_window.py` | generated widget code |
| `main_window.py` | GUI control/business integration |
| `test_worker.py` | generic background task worker |

---

# 4. Main Window Layout

The main window uses:

```text
800 x 700
```

as both the initial and minimum size.

The interface contains three main sections:

1. `Validation Tests`
2. `Control`
3. `Console / Log Viewer`

The layout keeps validation controls above the runtime console so execution can be observed without changing views.

---

# 5. Validation Test Controls

Individual buttons are provided for:

```text
T01 Device Baseline
T02 Write / Readback
T03 Invalid Range
T04 Unsupported Cmd
T05 Timeout / Recovery
T06 Data Integrity
T07 Log Parsing
T08 Read FW Error
T09 Write Failure
```

Each button dispatches the corresponding individual test module.

The GUI does not reproduce the internal command logic of those tests.

---

# 6. Automation Controls

Two automation buttons are provided:

```text
A01 Full Validation
A02 Fault Campaign
```

A01 runs the full T01–T09 regression suite.

A02 runs the deterministic fault campaign.

This allows the same GUI to support both focused validation and complete automation runs.

---

# 7. Control Section

The Control group provides:

```text
Read Current Data
Reset Data
Test Stop
Open Last Report
```

These represent:

- storage inspection;
- baseline reset;
- execution cancellation;
- report access.

---

# 8. Storage Utilities

`Read Current Data` reads the current runtime mock storage and displays it in the console.

`Reset Data` restores the runtime storage from the seed baseline.

These utilities support debugging and demonstration without embedding storage logic in the GUI itself.

---

# 9. Console / Log Viewer

The console uses a read-only `QPlainTextEdit`.

It is configured with:

```text
Read Only = true
Line Wrap = NoWrap
Maximum Block Count = 5000
```

GUI log entries use timestamps in:

```text
HH:MM:SS.mmm
```

format.

The console can display test starts, results, expected/actual values, validation counts, suite summaries, errors, stop events, and report paths.

The `Clear` button only clears visible console text.

---

# 10. Background Execution

Long-running validation is executed through:

```text
QThread
+
TestWorker
```

so the Qt main event loop remains responsive.

This is required so the window can continue to repaint and accept a Stop request while validation is active.

---

# 11. TestWorker

`TestWorker` is generic.

It accepts a callable and emits:

```text
result
error
finished
```

Conceptually:

```text
run task
→ emit result

on exception
→ emit error

always
→ emit finished
```

The worker does not contain test-specific logic.

---

# 12. Task Lifecycle

A validation run follows the general lifecycle:

```text
Start Task
→ Create New CancellationToken
→ Create QThread
→ Create TestWorker
→ Move Worker to Thread
→ Execute Task
→ Receive Result / Error
→ Worker Finished
→ Thread Quit
→ Cleanup GUI State
```

A fresh cancellation token is used for each run.

---

# 13. Single Active Task

AMNV intentionally allows only one active validation task at a time.

If another test or suite is requested while one is already running, the second request is rejected.

This protects shared runtime resources such as:

```text
mock_storage.json
runtime_fw.log
```

and preserves deterministic behavior.

---

# 14. Test Stop

The `Test Stop` button requests cancellation through a shared `CancellationToken`.

It does not call:

```text
QThread.terminate()
```

The cancellation request is observed by the active automation, test, or runner.

If a mock-controller subprocess is active:

```text
terminate
→ approximately 0.5 s grace period
→ kill fallback if required
→ logical reset
```

The interrupted unit becomes `ABORTED`.

---

# 15. Individual Test Stop

Individual T01–T09 tests support cooperative cancellation.

A stop before a major operation can abort the test before the command starts.

A stop during active controller execution causes controlled subprocess termination and logical recovery.

The GUI receives a normal structured `ABORTED` TestResult rather than treating user cancellation as an application error.

---

# 16. A01 Stop

A01 preserves completed test results.

An interrupted current test becomes:

```text
ABORTED
```

Remaining tests become:

```text
NOT_RUN
```

The suite becomes:

```text
STOPPED
```

A partial A01 PDF report is still generated.

---

# 17. A02 Stop

A02 uses the same execution-control semantics:

```text
Completed Case
→ preserve result

Active Interrupted Case
→ ABORTED

Remaining Case
→ NOT_RUN

Campaign
→ STOPPED
```

A partial fault-campaign report is still generated.

---

# 18. Error Handling

Unhandled task exceptions are caught by `TestWorker` and returned to the GUI through the error signal.

The worker still emits `finished`, allowing thread cleanup to occur even after an exception.

This separates:

```text
GUI / Worker Exception
```

from:

```text
Validation FAIL
```

---

# 19. Report Integration

A01 and A02 GUI wrappers follow the pattern:

```text
Run Automation
→ Structured Suite Result
→ Generate PDF
→ Return:
    suite_result
    report_path
```

The GUI displays the summary and report path.

The reporting modules own PDF layout and evidence rendering.

---

# 20. Report Auto-open

The configuration can control:

```text
report.auto_open
```

When enabled, the GUI asks the operating system to open the generated PDF.

When disabled, the report remains available through its path and the `Open Last Report` function.

---

# 21. Open Last Report

The GUI searches the report directory recursively for PDF files and selects the most recently modified report.

This provides quick access to the latest validation evidence without requiring the user to know the timestamp-based filename.

---

# 22. UI Source and Generated Code

`main_window.ui` is the editable layout source.

`ui_main_window.py` is generated by the Qt UI compiler and explicitly warns that manual changes will be lost when the file is regenerated.

The intended workflow is:

```text
Layout Changes
→ main_window.ui

Generate
→ ui_main_window.py

Behavior / Integration
→ main_window.py
```

---

# 23. GUI / Backend Boundary

The GUI owns:

- user interaction;
- task dispatch;
- thread lifecycle;
- stop requests;
- console presentation;
- storage utilities;
- report opening.

The backend owns:

- command execution;
- queue state;
- fault injection;
- timeout;
- reset / retry;
- validation;
- test and suite result semantics;
- evidence generation.

The GUI does not independently decide whether a test is `PASS`, `FAIL`, `ABORTED`, or whether a suite is `STOPPED`.

---

# 24. GUI Scope Boundary

The current GUI intentionally does not implement:

- user accounts;
- database-backed test history;
- remote lab management;
- dashboard analytics;
- real-time performance charts;
- test scheduling;
- parallel validation;
- multi-device control.

Its focus is:

```text
Validation Control
+
Runtime Observation
+
Evidence Access
```

---

# 25. GUI Design Summary

The final GUI design can be summarized as:

```text
Simple Test Selection
+
One Active Task
+
Background Execution
+
Cooperative Stop
+
Observable Console
+
Storage Inspection
+
PDF Evidence Access
```

The GUI is a presentation and control layer built around the validation framework rather than the validation engine itself.
