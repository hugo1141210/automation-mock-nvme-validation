# 模組關係 / Module Relationships

# 中文版

## 1. 文件目的

本文件說明 **Automation Mock NVMe Validation（AMNV）** 中各 Python 模組之間的責任邊界、主要依賴方向、呼叫關係與資料流。

`02_System_Architecture.md` 說明的是整體系統分層；本文件則進一步回答：

- 哪個模組可以呼叫哪個模組；
- 哪個模組負責建立資料；
- 哪個模組只負責使用資料；
- 哪些模組屬於共用基礎元件；
- 哪些模組不應彼此直接依賴；
- Individual Test、Automation、GUI 與 Report 如何接起來。

本文件的重點不是列出所有 `import` statement，而是描述整體程式設計中的 **Dependency Direction** 與 **Responsibility Ownership**。

---

## 2. 模組關係總覽

AMNV 的主要呼叫方向可概括為：

```text
main.py
↓
ui/main_window.py
↓
┌───────────────────────────────┐
│ Individual Test               │
│ T01 ~ T09                     │
└───────────────────────────────┘
          或
┌───────────────────────────────┐
│ Automation                    │
│ A01 / A02                     │
└───────────────────────────────┘
↓
runner.py
↓
queue_model.py
↓
fake_nvme.py
↓
mock_controller.py
↓
storage.py / fault_injector.py
↓
logs/runtime_fw.log
```

另外有數個共用支援模組：

```text
config_loader.py
models.py
validator.py
log_parser.py
cancellation.py
reporting/*
```

這些模組會被不同層重複使用。

---

## 3. Dependency Direction 原則

AMNV 盡量遵守「高階模組依賴低階服務，但低階服務不回頭依賴 GUI / Automation」的方向。

主要關係：

```text
GUI
↓
Automation / Test Case
↓
Runner / Validator / Log Parser
↓
Queue / Mock Controller / Storage / Fault
```

不希望出現：

```text
storage.py
→ GUI

queue_model.py
→ A01

mock_controller.py
→ Report

validator.py
→ Qt Widget
```

這樣可以避免底層模組被特定 UI 或 Automation Flow 綁死。

---

# 4. Entry Point

## 4.1 `main.py`

### 角色

`main.py` 是 Application Entry Point。

主要責任：

```text
建立 QApplication
→ 建立 MainWindow
→ 顯示 MainWindow
→ 啟動 Qt Event Loop
```

### 依賴

主要依賴：

```text
PySide6
amnv/ui/main_window.py
```

### 不負責

`main.py` 不應處理：

- NVMe Command；
- Test Logic；
- Storage；
- Fault Injection；
- Report Generation。

因此 Entry Point 保持輕量。

---

# 5. GUI Layer

## 5.1 `amnv/ui/main_window.py`

### 角色

`main_window.py` 是使用者操作與 Backend Task 之間的協調者。

它知道：

- 哪個 Button 對應哪個 Test；
- 哪個 Button 對應 A01 / A02；
- 如何啟動 Background Worker；
- 如何接收 Result；
- 如何顯示 Console；
- 如何產生 / 開啟 Report；
- 如何管理 Stop Request。

### 主要依賴

概念上依賴：

```text
ui_main_window.py
test_worker.py

T01 ~ T09
A01
A02

a01_reporter.py
a02_report.py

config_loader.py
cancellation.py
```

### 呼叫方向

```text
User Click
↓
main_window.py
↓
TestWorker
↓
Test / Automation
```

Result 回來後：

```text
Test / Automation Result
↓
TestWorker Signal
↓
main_window.py
↓
Console / Report / UI State
```

### 設計限制

GUI 不應自己實作：

```text
READ
WRITE
Timeout
Queue State
Fault Validation
```

否則 Validation Logic 會被綁死在 Qt。

---

## 5.2 `amnv/ui/test_worker.py`

### 角色

`test_worker.py` 是一個通用 Task Wrapper。

主要工作：

```text
接收 callable
→ 執行 callable
→ emit result
→ 或 emit error
→ emit finished
```

### 重要特性

Worker 不知道：

- T01 是什麼；
- A02 是什麼；
- READ / WRITE 是什麼；
- Cancellation 如何實作。

因此它是一個純粹的 Thread Execution Adapter。

### 關係

```text
main_window.py
→ TestWorker
→ callable task
```

而不是：

```text
TestWorker
→ T01
→ T02
→ A01
```

Worker 不直接綁定任何 Test。

---

## 5.3 `amnv/ui/main_window.ui`

這是 Qt Designer 的 Layout Definition。

主要描述：

- Button；
- Group Box；
- Console；
- Window Layout。

不含 Business Logic。

---

## 5.4 `amnv/ui/ui_main_window.py`

這是由 `.ui` 轉換而來的 Generated Python File。

責任是建立 Qt Widget Object。

它不應被當作主要 Business Logic 檔案修改。

關係：

```text
main_window.ui
→ generated
→ ui_main_window.py
→ imported by main_window.py
```

---

# 6. Test Case Layer

## 6.1 `amnv/test_cases/t01...t09`

每一個 Test Case 都是獨立的 Validation Scenario。

共同責任：

```text
準備 Scenario
→ 呼叫 Runner / Parser
→ 建立 Checks
→ 判定 Result
→ 回傳 TestResult
```

### 主要共用依賴

不同 Test 會視需要使用：

```text
config_loader.py
models.py
runner.py
validator.py
log_parser.py
storage.py
cancellation.py
```

---

## 6.2 Test Case 不依賴 GUI

Test Case 應該可以直接執行：

```text
python
→ import run()
→ execute
→ get TestResult
```

因此：

```text
T01 ~ T09
```

不需要知道：

- GUI Button；
- QThread；
- QPlainTextEdit；
- PDF Layout。

這讓同一份 Test Logic 可以同時被：

```text
Individual GUI Execution
A01 Automation
CLI Verification
```

重用。

---

## 6.3 T01 的關係

```text
t01_device_baseline.py
├─ config_loader.py
├─ runner.py
├─ validator.py
└─ models.py
```

流程：

```text
Load Expected Device Config
→ CommandRunner.execute(IDENTIFY)
→ CommandRunner.execute(SMART)
→ Validator
→ TestResult
```

---

## 6.4 T02 的關係

```text
t02_write_readback.py
├─ runner.py
├─ validator.py
├─ models.py
└─ cancellation.py
```

底層實際資料會經：

```text
runner.py
→ fake_nvme.py
→ mock_controller.py
→ storage.py
```

Test 本身不直接負責 JSON Storage I/O。

---

## 6.5 T03 / T04 的關係

T03 / T04 主要驗證 Error Completion。

```text
Test
→ runner.py
→ fake_nvme.py
→ mock_controller.py
→ Error Result
→ validator.py
```

T03 的 Invalid Range 最終會涉及 Storage Range Validation。

T04 則主要由 Controller Opcode Handling 判斷 Unsupported Command。

---

## 6.6 T05 的關係

T05 同時依賴：

```text
runner.py
queue_model.py
validator.py
cancellation.py
models.py
```

實際 Recovery State 由 Runner / QueueModel 提供。

Test Case 只驗證：

```text
Timeout Result
Reset Result
Retry Result
```

是否符合 Expected。

T05 不自己實作 Queue Counter。

---

## 6.7 T06 的關係

T06 使用：

```text
runner.py
fault_injector.py（間接）
storage.py（間接）
validator.py
```

主要路徑：

```text
T06
→ Runner
→ Mock Controller
→ Fault Injector
→ Miscompare Response
→ T06 Validator detects mismatch
```

Fault Injector 建立異常資料，但真正決定 Test PASS / FAIL 的是 Validation Layer。

---

## 6.8 T07 的關係

T07 和一般 I/O Test 不同。

主要關係：

```text
t07_firmware_log_parsing.py
→ log_parser.py
→ data/sample_fw.log
→ validator.py
→ TestResult
```

T07 不需要經過：

```text
runner.py
fake_nvme.py
queue_model.py
```

這表示 Test Layer 不被強迫全部走同一條 Command Path。

---

## 6.9 T08 的關係

T08 同時使用 Host Result 與 Runtime Log。

```text
T08
→ runner.py
→ NAND_READ_FAIL

T08
→ log_parser.py
→ runtime_fw.log

Command Result
+
Firmware Log
→ validator.py
→ TestResult
```

因此 T08 是多來源 Evidence Correlation Test。

---

## 6.10 T09 的關係

T09 是依賴關係最完整的 Test 之一：

```text
T09
├─ runner.py
├─ queue_model.py（透過 Runner）
├─ mock_controller.py（透過 subprocess）
├─ storage.py
├─ fault_injector.py
├─ log_parser.py
├─ validator.py
├─ models.py
└─ cancellation.py
```

它串接：

```text
Fault
→ Error Completion
→ Log
→ Storage Verification
→ Reset
→ Retry
→ Readback
```

因此是多模組整合型 Validation Scenario。

---

# 7. Automation Layer

## 7.1 `amnv/automation/a01_full_validation.py`

A01 的主要依賴方向：

```text
A01
→ T01
→ T02
→ ...
→ T09
```

另外使用：

```text
config_loader.py
storage.py
cancellation.py
models.py / TestResult
```

### A01 不直接控制底層 Command

A01 不應直接：

```text
runner.execute("READ")
runner.execute("WRITE")
```

來重建 Individual Test。

A01 的主要責任是：

```text
orchestrate tests
```

而不是：

```text
implement tests
```

---

## 7.2 `amnv/automation/a02_fault_campaign.py`

A02 與 A01 不同。

A02 的 Fault Case 不是 T01～T09 Wrapper，而是自己的 Campaign Logic。

主要依賴：

```text
config_loader.py
runner.py
storage.py
log_parser.py
validator.py
cancellation.py
data/fault_campaign.json
```

Fault 行為則經 Runner 進入：

```text
fake_nvme.py
→ fault_injector.py
→ mock_controller.py
```

---

# 8. Runner Layer

## 8.1 `amnv/runner.py`

`runner.py` 是 Host-side Command Execution 的中心。

主要依賴：

```text
config_loader.py
models.py
queue_model.py
fake_nvme.py（subprocess）
cancellation.py
```

CommandRunner 建立：

```text
SQEntry
CQEntry
Trace
Queue State
Host Result
Controller Result
```

---

## 8.2 Runner 與 QueueModel

關係：

```text
CommandRunner
→ QueueModel
```

Runner 告訴 QueueModel：

```text
Host submit command
Controller fetch command
Controller post completion
Host consume completion
Reset controller
```

QueueModel 則保存狀態。

因此：

```text
Runner = Lifecycle Coordinator
QueueModel = Logical Queue State Owner
```

這兩個責任不可混在一起。

---

## 8.3 Runner 與 `fake_nvme.py`

Runner 不直接呼叫 `MockController` Python Object。

而是建立 subprocess：

```text
CommandRunner
→ subprocess
→ fake_nvme.py
```

這建立 Host / Controller 的 Execution Boundary。

好處：

- 可模擬 Timeout；
- 可終止 Controller Process；
- Host PID / Controller PID 分離；
- Controller Error 不直接污染 Host Process State。

---

# 9. Queue Model

## 9.1 `amnv/queue_model.py`

QueueModel 是：

```text
SQ / CQ / CID State Owner
```

主要管理：

```text
sq_head
sq_tail
cq_head
cq_tail
outstanding_cids
next_cid
```

其他模組不應自行另外維護一份平行 Queue Counter。

否則會產生：

```text
Runner Queue State
!=
Test Queue State
```

因此 Test 只讀取 Runner 回傳的 Queue Evidence。

---

# 10. Controller Boundary

## 10.1 `fake_nvme.py`

`fake_nvme.py` 是 Host 與 Mock Controller 的 Process Entry Boundary。

主要工作：

```text
Parse Arguments
→ Build Controller-side Request
→ Apply Fault Path
→ Execute Command
→ Emit Structured Result
```

它不是：

```text
GUI
Test Suite
Report Generator
```

---

## 10.2 `amnv/mock_controller.py`

MockController 是簡化的 Controller Command Handler。

主要依賴：

```text
storage.py
data/mock_device.json
runtime firmware log
```

以及 Fault Injection Path。

它負責：

```text
IDENTIFY
SMART
READ
WRITE
Unsupported Opcode
```

---

# 11. Storage Layer

## 11.1 `amnv/storage.py`

Storage 是 Runtime Data State Owner。

主要資料：

```text
data/mock_storage.json
data/mock_storage_seed.json
```

責任：

```text
Read
Write
Range Check
Reset
```

### 不負責

Storage 不判斷：

```text
T02 PASS / FAIL
A01 PASS / FAIL
```

它只提供 Data Behavior。

---

# 12. Fault Injection Layer

## 12.1 `amnv/fault_injector.py`

Fault Injector 是 Fault Behavior Owner。

主要 Fault：

```text
timeout
NAND_READ_FAIL
NAND_PROGRAM_FAIL
miscompare
```

它會驗證 Fault 與 Operation 是否合理配對。

例如：

```text
NAND_READ_FAIL
只能對 READ 使用
```

### 關係

主要由 Controller Execution Path 使用：

```text
Runner
→ fake_nvme.py
→ FaultInjector
→ MockController / Response
```

Test Case 不應直接偽造 Completion Result 來假裝 Fault 發生。

---

# 13. Configuration Layer

## 13.1 `amnv/config_loader.py`

這是 Configuration Access 的共用入口。

主要資料：

```text
config/validation_config.json
```

其他模組透過 Config Loader 取得：

- Device Expected Data；
- Timeout；
- Automation Policy；
- A01 / A02 Setting；
- Report Setting。

好處是避免各模組自己硬編碼相同設定。

---

## 13.2 `data/fault_campaign.json`

這不是通用 Config，而是 A02 的 Campaign Data。

關係：

```text
a02_fault_campaign.py
→ fault_campaign.json
```

它定義 Case Data。

A02 Python Code 定義 Execution Mechanism。

因此：

```text
JSON = What to test
Python = How to test
```

---

# 14. Validation Layer

## 14.1 `amnv/validator.py`

Validator 提供共用 Check Function。

例如概念上：

```text
check_equal()
check_completion_status()
check_maximum()
all_checks_passed()
```

Test Case 呼叫 Validator 產生一致格式的 Check。

### 關係

```text
Test Case
→ validator.py
→ Check List
→ models.py / TestResult
```

Validator 不應直接：

- 執行 Command；
- Reset Storage；
- 產 PDF。

---

# 15. Result Model

## 15.1 `amnv/models.py`

Models 定義跨模組共用資料結構。

例如：

```text
SQEntry
CQEntry
TestResult
```

作用是讓：

```text
Runner
QueueModel
Test Case
Automation
Reporter
GUI
```

對資料格式有共同理解。

---

## 15.2 Result Ownership

Individual Test 的 Result Owner 是：

```text
Test Case
```

Suite Result Owner 是：

```text
A01 / A02
```

PDF 只是：

```text
Result Presentation
```

Reporter 不應重新決定 Test 是否 PASS。

---

# 16. Log Layer

## 16.1 `amnv/log_parser.py`

Log Parser 的責任：

```text
Text Log
→ Structured Entry
```

主要資料來源：

```text
data/sample_fw.log
logs/runtime_fw.log
```

它不負責判斷：

```text
T08 PASS
```

而是提供 T08 所需的 Structured Evidence。

---

# 17. Cancellation Layer

## 17.1 `amnv/cancellation.py`

CancellationToken 是跨層控制元件。

使用方向：

```text
GUI
→ Token.request()

Automation
→ Token check / pass through

Test
→ Token check / pass through

Runner
→ Token check during active subprocess
```

### 重要關係

Token 不是由 Worker Thread 擁有。

它是一個共享的 thread-safe execution-control object。

因此 GUI 可以在 Worker 正忙時直接提出 Stop Request。

---

# 18. Reporting Layer

## 18.1 `amnv/reporting/a01_reporter.py`

輸入：

```text
A01 Suite Result
```

輸出：

```text
reports/A01/*.pdf
```

主要依賴：

```text
A01 Result Structure
ReportLab
```

不執行 Test。

---

## 18.2 `amnv/reporting/a02_report.py`

輸入：

```text
A02 Campaign Result
```

輸出：

```text
reports/A02/*.pdf
```

主要呈現：

- Campaign Matrix；
- Fault Coverage；
- Case Evidence；
- Recovery；
- Stop Evidence。

---

# 19. 完整正常 I/O 呼叫鏈

以 T02 為例：

```text
GUI
↓
main_window.py
↓
TestWorker
↓
t02_write_readback.py
↓
CommandRunner
↓
QueueModel
↓
fake_nvme.py subprocess
↓
FaultInjector（本案例無 Fault）
↓
MockController
↓
MockStorage
↓
Controller Result
↓
CommandRunner
↓
QueueModel Completion
↓
T02 Validator
↓
TestResult
↓
TestWorker
↓
GUI
```

這條鏈清楚區分：

```text
UI
Test Intent
Execution
Controller Behavior
Data
Validation
Presentation
```

---

# 20. Timeout 呼叫鏈

以 T05 為例：

```text
T05
↓
CommandRunner
↓
QueueModel submit CID 1
↓
fake_nvme.py
↓
Timeout
↓
Runner returns TIMEOUT
↓
T05 validates outstanding CID
↓
Runner controller_reset()
↓
QueueModel reset
↓
T05 retries
↓
CID 2
↓
SUCCESS
↓
T05 validates recovery
```

責任分工：

```text
Timeout Detection
= Runner

Outstanding State
= QueueModel

Recovery Decision
= T05

PASS / FAIL
= T05 + Validator
```

---

# 21. Firmware Error Correlation 呼叫鏈

以 T08 為例：

```text
T08
↓
Runner
↓
fake_nvme.py
↓
FaultInjector
↓
NAND_READ_FAIL
↓
Mock Controller Error Completion
↓
runtime_fw.log

同時：

T08
↓
log_parser.py
↓
Structured Log Entry

最後：

Command Evidence
+
Log Evidence
↓
Validator
↓
TestResult
```

---

# 22. A01 呼叫鏈

```text
GUI
↓
main_window.py
↓
TestWorker
↓
A01
├─ T01
├─ T02
├─ T03
├─ T04
├─ T05
├─ T06
├─ T07
├─ T08
└─ T09
↓
Suite Aggregation
↓
a01_reporter.py
↓
PDF
↓
GUI Result Display
```

A01 本身不取代 Individual Test。

---

# 23. A02 呼叫鏈

```text
GUI
↓
main_window.py
↓
TestWorker
↓
A02
↓
fault_campaign.json
↓
Case Setup
↓
Fault Profile Handler
↓
CommandRunner
↓
Fault / Controller / Storage
↓
Validation
↓
Case Result
↓
Profile Summary
↓
Campaign Result
↓
a02_report.py
↓
PDF
```

---

# 24. STOP 呼叫鏈

```text
User clicks Test Stop
↓
main_window.py
↓
CancellationToken.request()
↓
Active Automation / Test / Runner observes token
↓
If subprocess active:
    terminate
    → grace period
    → kill fallback
↓
logical controller reset
↓
Active Unit = ABORTED
↓
Remaining Unit = NOT_RUN
↓
Suite = STOPPED
↓
Reporter
↓
Partial PDF
```

---

# 25. 模組責任矩陣

| 模組 | Execution | State | Validation | Orchestration | UI | Reporting |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `main.py` | No | No | No | No | Entry | No |
| `ui/main_window.py` | Dispatch | UI State | No | Trigger | Yes | Trigger |
| `ui/test_worker.py` | Task wrapper | Thread | No | No | Support | No |
| `test_cases/*` | Scenario | Local | Yes | No | No | No |
| `automation/a01_*` | Calls Tests | Suite | Aggregate | Yes | No | No |
| `automation/a02_*` | Calls Cases | Campaign | Aggregate | Yes | No | No |
| `runner.py` | Yes | Command | No | Command | No | No |
| `queue_model.py` | No | SQ/CQ/CID | No | No | No | No |
| `fake_nvme.py` | Controller boundary | Process | No | No | No | No |
| `mock_controller.py` | Command behavior | Controller-side | No | No | No | No |
| `storage.py` | Data operation | Storage | No | No | No | No |
| `fault_injector.py` | Fault behavior | Fault | No | No | No | No |
| `validator.py` | No | Check | Yes | No | No | No |
| `models.py` | No | Data Model | No | No | No | No |
| `log_parser.py` | Parse | Log Entry | Support | No | No | No |
| `cancellation.py` | Control | Stop State | No | Support | No | No |
| `reporting/*` | No | No | No | No | No | Yes |

---

# 26. 為什麼這樣拆模組

## 26.1 可測試性

Test Case 不依賴 GUI，因此可以獨立執行。

## 26.2 可重用性

Runner 可被：

```text
T01~T09
A02
```

共用。

## 26.3 可觀察性

QueueModel、Result、Log、Checks 都能保存 Evidence。

## 26.4 可維護性

修改 PDF Layout 不需要修改 CommandRunner。

修改 GUI Layout 不需要修改 Storage。

新增 Test Case 不需要改 Mock Storage 架構。

## 26.5 Failure Isolation

Host Process 與 Mock Controller Process 分離，可讓 Timeout / Abort 更容易被模擬與控制。

---

# 27. 模組邊界原則

後續若擴充 AMNV，建議維持下列規則：

### Rule 1

GUI 不實作 Test Logic。

### Rule 2

Test Case 不直接控制 Qt。

### Rule 3

Queue State 只由 QueueModel 管理。

### Rule 4

Command Lifecycle 由 Runner 管理。

### Rule 5

Storage 不決定 Test PASS / FAIL。

### Rule 6

Fault Injector 不決定 Suite Result。

### Rule 7

Reporter 只呈現 Evidence，不重新執行 Validation。

### Rule 8

Automation 負責編排，不重寫 Individual Test。

### Rule 9

Cancellation 與 Timeout 保持不同語意。

---

# English Version

## 1. Document Purpose

This document describes the responsibility boundaries, dependency direction, call relationships, and data flow between Python modules in **Automation Mock NVMe Validation (AMNV)**.

While `02_System_Architecture.md` describes the overall layered architecture, this document focuses on how modules depend on and call one another.

The goal is not to enumerate every Python import statement, but to describe the intended **dependency direction** and **responsibility ownership**.

---

## 2. Module Relationship Overview

The main call direction is:

```text
main.py
↓
ui/main_window.py
↓
Individual Test T01~T09
or
Automation A01 / A02
↓
runner.py
↓
queue_model.py
↓
fake_nvme.py
↓
mock_controller.py
↓
storage.py / fault_injector.py
↓
runtime firmware log
```

Shared support modules include:

```text
config_loader.py
models.py
validator.py
log_parser.py
cancellation.py
reporting/*
```

---

## 3. Dependency Direction

AMNV follows a general high-level-to-low-level dependency direction:

```text
GUI
↓
Automation / Test Case
↓
Runner / Validator / Log Parser
↓
Queue / Mock Controller / Storage / Fault
```

Low-level modules should not depend back on GUI or automation-specific behavior.

---

# 4. Entry Point

## `main.py`

`main.py` creates the Qt application, creates the main window, and starts the event loop.

It does not implement NVMe commands, test logic, storage behavior, fault injection, or reporting.

---

# 5. GUI Layer

## `amnv/ui/main_window.py`

The main window coordinates user actions and backend tasks.

It connects buttons to:

- T01–T09;
- A01;
- A02;
- stop;
- storage utilities;
- report utilities.

Its main flow is:

```text
User Action
→ Dispatch Task
→ Receive Result
→ Display Console State
→ Trigger Report Handling
```

It does not implement NVMe command behavior directly.

## `amnv/ui/test_worker.py`

`TestWorker` is a generic callable executor used inside a `QThread`.

It only knows how to:

```text
run task
emit result
emit error
emit finished
```

It does not know specific test semantics.

## `main_window.ui` / `ui_main_window.py`

The `.ui` file defines layout.

`ui_main_window.py` is generated code used by `main_window.py`.

Business logic remains outside the generated file.

---

# 6. Test Case Layer

Each file under:

```text
amnv/test_cases/
```

represents an independent validation scenario.

The common flow is:

```text
Prepare Scenario
→ Execute Command / Parse Evidence
→ Build Checks
→ Determine Result
→ Return TestResult
```

Tests can use:

```text
config_loader.py
models.py
runner.py
validator.py
log_parser.py
storage.py
cancellation.py
```

depending on the scenario.

Tests do not depend on Qt widgets or PDF layout.

---

# 7. Test-specific Relationships

## T01

```text
t01_device_baseline.py
→ config_loader.py
→ runner.py
→ validator.py
→ models.py
```

## T02

```text
t02_write_readback.py
→ runner.py
→ validator.py
→ models.py
```

The lower-level data path continues through the Mock Controller and Storage.

## T03 / T04

These tests use Runner results to validate negative command behavior.

T03 reaches storage-range validation through the controller path.

T04 validates unsupported-opcode handling.

## T05

T05 depends heavily on:

```text
runner.py
queue_model.py
validator.py
cancellation.py
```

The runner and queue model own timeout and recovery state; T05 validates that state.

## T06

T06 uses the normal command path with a miscompare fault.

The fault mechanism produces incorrect returned data, while the test validator detects the mismatch.

## T07

T07 directly uses:

```text
log_parser.py
data/sample_fw.log
validator.py
```

It does not require the command runner.

## T08

T08 combines:

```text
Host Command Result
+
Runtime Firmware Log
```

and validates correlation.

## T09

T09 integrates the largest number of modules:

```text
runner
queue state
fault injection
storage
log parsing
validation
cancellation
```

to validate complete write-failure recovery.

---

# 8. Automation Layer

## `a01_full_validation.py`

A01 orchestrates T01 through T09.

Its responsibility is orchestration and aggregation, not reimplementation of individual test logic.

## `a02_fault_campaign.py`

A02 uses:

```text
fault_campaign.json
config_loader.py
runner.py
storage.py
log_parser.py
validator.py
cancellation.py
```

to execute its own data-driven fault cases.

A02 does not simply wrap T01–T09.

---

# 9. Runner Layer

## `amnv/runner.py`

`CommandRunner` coordinates the Host-side command lifecycle.

Its main dependencies are:

```text
config_loader.py
models.py
queue_model.py
fake_nvme.py
cancellation.py
```

Conceptually:

```text
Runner = Lifecycle Coordinator
QueueModel = Queue State Owner
```

---

# 10. Queue Model

## `amnv/queue_model.py`

QueueModel owns:

```text
sq_head
sq_tail
cq_head
cq_tail
outstanding_cids
next_cid
```

Other modules should consume queue evidence rather than maintaining independent queue counters.

---

# 11. Controller Boundary

## `fake_nvme.py`

This file is the subprocess boundary between Host-side Runner execution and Mock Controller execution.

## `amnv/mock_controller.py`

The mock controller implements simplified command behavior for:

- IDENTIFY;
- SMART-style data;
- READ;
- WRITE;
- unsupported opcodes.

---

# 12. Storage Layer

## `amnv/storage.py`

Storage owns runtime logical block data.

It handles:

```text
Read
Write
Range Validation
Reset
```

It does not determine test PASS / FAIL.

---

# 13. Fault Injection Layer

## `amnv/fault_injector.py`

The fault injector owns deterministic fault behavior such as:

```text
timeout
NAND_READ_FAIL
NAND_PROGRAM_FAIL
miscompare
```

The controller execution path applies faults; tests validate their effects.

---

# 14. Configuration Layer

## `amnv/config_loader.py`

Provides centralized access to:

```text
config/validation_config.json
```

## `data/fault_campaign.json`

Defines A02 case data.

Conceptually:

```text
JSON = What to test
Python = How to test
```

---

# 15. Validation Layer

## `amnv/validator.py`

Provides reusable validation checks.

It does not execute commands or generate reports.

---

# 16. Result Model

## `amnv/models.py`

Defines shared structures such as:

```text
SQEntry
CQEntry
TestResult
```

The test case owns the individual result.

A01 / A02 own suite-level aggregation.

The reporter only presents those results.

---

# 17. Log Layer

## `amnv/log_parser.py`

Converts firmware-style text logs into structured entries.

It supplies evidence to tests such as T07, T08, and T09.

---

# 18. Cancellation Layer

## `amnv/cancellation.py`

`CancellationToken` is shared across:

```text
GUI
Automation
Test
Runner
```

The GUI requests cancellation.

Active execution layers observe the token.

The token is not owned by the worker thread itself.

---

# 19. Reporting Layer

## `amnv/reporting/a01_reporter.py`

Consumes A01 suite results and generates A01 PDF reports.

## `amnv/reporting/a02_report.py`

Consumes A02 campaign results and generates A02 PDF reports.

Neither reporter re-executes validation logic.

---

# 20. Normal I/O Call Chain

Using T02 as an example:

```text
GUI
↓
main_window.py
↓
TestWorker
↓
T02
↓
CommandRunner
↓
QueueModel
↓
fake_nvme.py
↓
FaultInjector
↓
MockController
↓
MockStorage
↓
Controller Result
↓
CommandRunner
↓
Queue Completion
↓
Validator
↓
TestResult
↓
GUI
```

---

# 21. Timeout Call Chain

Using T05:

```text
T05
↓
CommandRunner
↓
QueueModel submits CID 1
↓
Controller subprocess
↓
Timeout
↓
Runner reports TIMEOUT
↓
T05 validates outstanding state
↓
Runner reset
↓
QueueModel clears queue state
↓
Retry CID 2
↓
SUCCESS
↓
T05 validates recovery
```

Responsibilities:

```text
Timeout Detection = Runner
Queue State = QueueModel
Recovery Decision = T05
PASS / FAIL = T05 + Validator
```

---

# 22. Firmware Error Correlation Chain

Using T08:

```text
T08
→ Runner
→ Faulted Controller Execution
→ Error Completion
→ runtime_fw.log

T08
→ Log Parser
→ Structured Log Evidence

Command Evidence
+
Log Evidence
→ Validator
→ TestResult
```

---

# 23. A01 Call Chain

```text
GUI
→ TestWorker
→ A01
→ T01 ... T09
→ Suite Aggregation
→ A01 Reporter
→ PDF
→ GUI
```

---

# 24. A02 Call Chain

```text
GUI
→ TestWorker
→ A02
→ fault_campaign.json
→ Case Setup
→ Fault Profile Handler
→ CommandRunner
→ Fault / Controller / Storage
→ Validation
→ Case Result
→ Profile Summary
→ Campaign Result
→ A02 Reporter
→ PDF
```

---

# 25. STOP Call Chain

```text
User Stop
→ main_window.py
→ CancellationToken.request()
→ Active Automation / Test / Runner observes token
→ terminate active subprocess if required
→ logical reset
→ Active Unit = ABORTED
→ Remaining Unit = NOT_RUN
→ Suite = STOPPED
→ Partial Report
```

---

# 26. Responsibility Matrix

| Module | Execution | State | Validation | Orchestration | UI | Reporting |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `main.py` | No | No | No | No | Entry | No |
| `ui/main_window.py` | Dispatch | UI State | No | Trigger | Yes | Trigger |
| `ui/test_worker.py` | Task wrapper | Thread | No | No | Support | No |
| `test_cases/*` | Scenario | Local | Yes | No | No | No |
| `automation/a01_*` | Calls Tests | Suite | Aggregate | Yes | No | No |
| `automation/a02_*` | Calls Cases | Campaign | Aggregate | Yes | No | No |
| `runner.py` | Yes | Command | No | Command | No | No |
| `queue_model.py` | No | SQ/CQ/CID | No | No | No | No |
| `fake_nvme.py` | Controller boundary | Process | No | No | No | No |
| `mock_controller.py` | Command behavior | Controller | No | No | No | No |
| `storage.py` | Data operation | Storage | No | No | No | No |
| `fault_injector.py` | Fault behavior | Fault | No | No | No | No |
| `validator.py` | No | Checks | Yes | No | No | No |
| `models.py` | No | Data Model | No | No | No | No |
| `log_parser.py` | Parse | Log Entry | Support | No | No | No |
| `cancellation.py` | Control | Stop State | No | Support | No | No |
| `reporting/*` | No | No | No | No | No | Yes |

---

# 27. Module Boundary Rules

The following rules should remain true if AMNV is extended:

1. GUI does not implement validation logic.
2. Test cases do not depend on Qt.
3. Queue state is owned by QueueModel.
4. Command lifecycle is owned by CommandRunner.
5. Storage does not decide test PASS / FAIL.
6. Fault Injector does not decide suite status.
7. Reporter presents evidence but does not re-run validation.
8. Automation orchestrates tests instead of rewriting them.
9. Timeout and user cancellation remain semantically distinct.
