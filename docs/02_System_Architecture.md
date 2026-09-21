# 系統架構 / System Architecture

# 中文版

## 1. 文件目的

本文件說明 **Automation Mock NVMe Validation（AMNV）** 的整體軟體架構、主要模組責任、模組之間的資料流，以及各層如何共同完成 NVMe Host-side 邏輯驗證。

AMNV 採用分層式設計，將 GUI、Automation、Test Case、Command Execution、Mock Controller、Storage、Fault Injection、Validation、Reporting 與 Cancellation 分開處理。

這樣的設計主要有三個目的：

1. **降低模組耦合**：Test Case 不需要直接處理 GUI 或 PDF；
2. **讓驗證流程可觀察**：Command、Queue、Fault、Recovery 與 Result 都有明確責任邊界；
3. **方便擴充**：新增 Test Case、Fault Profile 或 Report 時，不需要大幅修改其他模組。

---

## 2. 專案目錄結構

AMNV 的主要目錄與檔案如下：

```text
automation-mock-nvme-validation/
├── main.py
├── fake_nvme.py
├── config/
│   └── validation_config.json
├── data/
│   ├── fault_campaign.json
│   ├── mock_device.json
│   ├── mock_storage.json
│   ├── mock_storage_seed.json
│   └── sample_fw.log
├── logs/
│   └── runtime_fw.log
├── reports/
│   ├── A01/
│   └── A02/
├── docs/
│   └── ...
└── amnv/
    ├── cancellation.py
    ├── config_loader.py
    ├── fault_injector.py
    ├── log_parser.py
    ├── mock_controller.py
    ├── models.py
    ├── queue_model.py
    ├── runner.py
    ├── storage.py
    ├── validator.py
    ├── automation/
    │   ├── a01_full_validation.py
    │   └── a02_fault_campaign.py
    ├── reporting/
    │   ├── a01_reporter.py
    │   └── a02_report.py
    ├── test_cases/
    │   ├── t01_device_baseline.py
    │   ├── t02_write_readback.py
    │   ├── t03_invalid_read_range.py
    │   ├── t04_unsupported_command.py
    │   ├── t05_read_timeout_recovery.py
    │   ├── t06_data_integrity_failure.py
    │   ├── t07_firmware_log_parsing.py
    │   ├── t08_read_error_correlation.py
    │   └── t09_write_failure_recovery.py
    └── ui/
        ├── main_window.py
        ├── main_window.ui
        ├── test_worker.py
        └── ui_main_window.py
```

此結構反映了 AMNV 的主要責任分層。

---

## 3. 架構分層

AMNV 可概分為八個主要層級：

1. **Presentation Layer**
2. **Automation Layer**
3. **Validation Scenario Layer**
4. **Host Command Execution Layer**
5. **Mock Controller Layer**
6. **Storage / Fault / Log Layer**
7. **Validation Result Layer**
8. **Reporting Layer**

另外，`CancellationToken` 作為跨層的 Execution Control Mechanism，在 GUI、Automation、Test Case 與 Runner 之間傳遞 Stop 狀態。

---

## 4. Presentation Layer

### 4.1 `main.py`

`main.py` 是 GUI Application 的啟動入口。

主要責任為：

- 建立 Qt Application；
- 建立 Main Window；
- 啟動 GUI Event Loop。

它不負責 Test Logic、Command Execution 或 Validation。

這讓 Application Entry Point 保持單純，只負責啟動系統。

### 4.2 `amnv/ui/main_window.py`

`main_window.py` 是 GUI 的主要控制層。

主要責任包含：

- 綁定 T01～T09 按鈕；
- 綁定 A01 / A02 Automation；
- 啟動 Background Worker；
- 建立每次執行使用的 `CancellationToken`；
- 接收 Test / Automation Result；
- 顯示 Console 訊息；
- 管理 Stop Button；
- 呼叫 A01 / A02 Reporter；
- 管理 Mock Storage Utility；
- 視設定開啟產生的 PDF Report。

GUI 不直接實作 NVMe Command Logic。

它主要負責：

```text
User Action
→ Task Dispatch
→ Progress Display
→ Result Display
→ Report Integration
```

### 4.3 `amnv/ui/test_worker.py`

`test_worker.py` 提供通用 Background Worker。

其目的為將較長時間的 Test 或 Automation Task 放入 `QThread` 執行，避免 GUI Main Thread 被阻塞。

Worker 本身不實作 STOP Logic。

這是一個刻意的設計選擇：

- Stop Request 由 GUI Thread 直接設定共享的 `CancellationToken`；
- Worker 正在執行 Test 時，不需要等待 Qt queued slot；
- Test / Runner 會自行觀察 Token。

因此本專案不使用 `QThread.terminate()` 強制終止執行緒。

### 4.4 `main_window.ui` 與 `ui_main_window.py`

`main_window.ui` 為 Qt Designer 的 UI Definition。

`ui_main_window.py` 則由 Qt UI Tool 產生，用來建立實際的 Widget Structure。

設計原則是：

- `.ui` 負責 Layout；
- `ui_main_window.py` 視為 Generated File；
- Business Logic 集中於 `main_window.py`。

因此不直接將 Test Logic 寫入 Generated UI Code。

---

## 5. Automation Layer

Automation Layer 負責把 Individual Test / Case 組合成可重複執行的 Suite。

### 5.1 `amnv/automation/a01_full_validation.py`

A01 是 Full Validation Suite。

主要責任：

- 依序執行 T01～T09；
- 保存每個 Test Result；
- 接收 `CancellationToken`；
- 發送 Progress Event；
- 判斷 `PASS / FAIL / ERROR / ABORTED / NOT_RUN`；
- 統計 Executed / Passed / Failed / Error / Aborted / Not Run；
- 產生 Suite-level Result；
- Stop 發生時將 Suite 標記為 `STOPPED`。

A01 本身不重新實作 T01～T09 的 Test Logic，而是負責 orchestration。

### 5.2 `amnv/automation/a02_fault_campaign.py`

A02 是 Deterministic Fault Campaign。

其 Case 定義主要由 `data/fault_campaign.json` 提供。

主要責任：

- 載入 Campaign；
- 檢查 Profile Order 與 Configuration；
- 建立執行順序；
- 執行各 Fault Case；
- 呼叫 `CommandRunner`；
- 驗證 Setup、Fault、Recovery 與 Evidence；
- 產生 Profile Summary；
- 支援 cooperative cancellation；
- Stop 後保留 `ABORTED / NOT_RUN`；
- 產生 Suite-level `PASS / FAIL / STOPPED`。

目前主要 Fault Profile 包含：

- Command Timeout
- NAND Read Failure
- NAND Program Failure
- Data Miscompare

A02 和 A01 的差異是：

- **A01** 以 Test Case 為單位做完整 Regression；
- **A02** 以 Fault Profile / Campaign Case 為中心做 Fault-oriented Validation。

---

## 6. Validation Scenario Layer

### 6.1 `amnv/test_cases/`

T01～T09 是 Individual Validation Scenario。

每一個 Test Case 都負責：

1. 定義自己的測試目標；
2. 呼叫需要的 Command；
3. 建立 Validation Check；
4. 判定 Test Result；
5. 保存 Evidence；
6. 在適當位置檢查 Cancellation。

Test Case 不直接處理：

- GUI；
- PDF Layout；
- Qt Thread；
- Campaign Orchestration。

這讓 Test Case 可以單獨從 CLI、GUI 或 Automation Layer 被呼叫。

### 6.2 T01～T09 的角色

| Test | 主要角色 |
| --- | --- |
| T01 | Device Baseline / Identify / SMART-style baseline |
| T02 | Normal WRITE / READ Readback |
| T03 | Invalid Range Validation |
| T04 | Unsupported Command Validation |
| T05 | Timeout / Reset / Retry Recovery |
| T06 | Data Miscompare Detection |
| T07 | Firmware-style Log Parsing |
| T08 | READ Failure / Log Correlation |
| T09 | WRITE Failure / Storage Protection / Reset / Retry / Readback |

各 Test 的完整流程與驗證條件會在 Test Design 文件中分別說明。

---

## 7. Host Command Execution Layer

### 7.1 `amnv/runner.py`

`CommandRunner` 是 AMNV Host-side Command Lifecycle 的核心協調元件。

它負責：

- 建立 Command；
- 配置 CID；
- 呼叫 Queue Model；
- 啟動 `fake_nvme.py` subprocess；
- 等待 Controller Result；
- 處理 Timeout；
- 處理 User Abort；
- 建立 logical Completion；
- 更新 Queue State；
- 保存 Execution Trace；
- 執行 Controller Reset。

正常 Command 的概念流程為：

```text
Command Build
→ SQ Submit
→ SQ Tail Doorbell
→ Controller Fetch
→ Subprocess Execution
→ Controller Result
→ CQ Post
→ CQ Consume
→ CQ Head Doorbell
→ Final Result
```

Runner 回傳的結果會保留 Host、Command、Controller、Completion、Queue State、Trace 等資訊，供 Test Case 做後續 Validation。

### 7.2 Timeout 行為

Timeout 不視為一般 Command Failure。

當 Controller subprocess 未在預期時間內完成時：

- Host Result 標記為 `TIMEOUT`；
- 不產生正常 Completion；
- Outstanding CID 保留；
- Queue State 保留 Timeout 當下狀態。

之後由 Test / Campaign 決定是否執行 Controller Reset 與 Retry。

### 7.3 User Abort 行為

User Abort 與 Timeout 為兩個不同 Lifecycle。

當 `CancellationToken` 被設定且 active subprocess 尚未完成：

1. Runner 發現 Cancellation；
2. 呼叫 `terminate()`；
3. 等待約 0.5 秒 Grace Period；
4. 必要時使用 `kill()`；
5. 執行 logical Controller Reset；
6. 清除 SQ / CQ / outstanding state；
7. 保留 CID progression；
8. 回傳 `ABORTED` Evidence。

此機制用於 STOP v1。

---

## 8. Queue Model

### 8.1 `amnv/queue_model.py`

Queue Model 用來邏輯化表示 NVMe Submission Queue / Completion Queue Lifecycle。

它追蹤：

- `sq_head`
- `sq_tail`
- `cq_head`
- `cq_tail`
- `outstanding_cids`
- `next_cid`

它不是真實 DMA-backed NVMe Queue，也沒有實作 PCIe MMIO。

它的用途是：

- 讓 Test 可以觀察 Queue State；
- 模擬 SQ Submit / Controller Fetch / CQ Post / Host Consume；
- 驗證 Timeout 後 Outstanding CID；
- 驗證 Reset 清除 Queue State；
- 驗證 Retry 使用新的 CID。

### 8.2 CID Progression

CID 由 Host-side Queue Model 管理。

Controller Reset 會清除：

- SQ head / tail；
- CQ head / tail；
- outstanding CID。

但不將 `next_cid` 回復成 1。

因此可以驗證：

```text
CID 1 Timeout
→ Reset
→ next_cid remains 2
→ Retry uses CID 2
```

這是 AMNV Recovery Validation 的重要設計之一。

---

## 9. Mock Controller Layer

### 9.1 `fake_nvme.py`

`fake_nvme.py` 是由 Host Runner 啟動的獨立 Python subprocess。

它提供 Mock NVMe Command Execution Entry Point。

主要責任：

- 接收 Host 傳入的 Command / CID / LBA / Length / Data / Fault；
- 呼叫 Mock Controller；
- 執行指定操作；
- 回傳 structured result；
- 將結果輸出給 Host Runner。

將 Controller 放在獨立 process 的目的，是讓 Host 可以模擬：

- Controller execution；
- command timeout；
- active subprocess termination；
- Host / Controller process boundary。

這並不代表真實 PCIe Controller Firmware Process，而是用 subprocess 建立邏輯執行邊界。

### 9.2 `amnv/mock_controller.py`

`mock_controller.py` 負責 Mock Controller 的 Command Behavior。

主要處理的 Command 類型包含專案目前需要的：

- IDENTIFY
- SMART-style data access
- READ
- WRITE
- Unsupported Command path

Controller 會使用：

- Mock Storage；
- Fault Injector；
- Mock Device Data；
- Runtime Firmware-style Log。

Controller Result 再交回 `fake_nvme.py`，由 Runner 轉換成 Host-side logical completion。

---

## 10. Storage Layer

### 10.1 `amnv/storage.py`

`MockStorage` 提供邏輯 Block Storage。

主要責任：

- 讀取目前 Storage State；
- WRITE 更新指定 LBA；
- READ 取得指定 LBA Data；
- 驗證 Range；
- Reset Storage Baseline。

它以 JSON File 作為 Mock Storage Backend，而不是 NAND Media。

### 10.2 `data/mock_storage_seed.json`

此檔案保存初始 Storage Baseline。

用途：

- 提供 deterministic initial state；
- A01 / A02 或 GUI reset 時重新建立測試基準；
- 避免前一次測試留下的資料影響下一輪驗證。

### 10.3 `data/mock_storage.json`

此檔案是 Runtime Storage State。

WRITE / READ Test 會在此狀態上運作。

因此：

```text
mock_storage_seed.json
= baseline

mock_storage.json
= runtime state
```

兩者分離可以同時支援測試資料變化與可重現的 reset。

---

## 11. Fault Injection Layer

### 11.1 `amnv/fault_injector.py`

Fault Injector 負責 deterministic fault behavior。

目前主要 Fault 包含：

- `timeout`
- `NAND_READ_FAIL`
- `NAND_PROGRAM_FAIL`
- `miscompare`

Fault Injector 同時驗證 Fault 與 Command 是否合理配對。

例如：

- `NAND_READ_FAIL` 只能用在 READ；
- `NAND_PROGRAM_FAIL` 應對應 WRITE。

這樣可以避免測試設定本身建立不合理的情境。

### 11.2 Fault Injection 的定位

Fault Injection 不等於真實 NAND Failure。

其目的為在可控制的時間點建立預期異常，使 Test 可以驗證：

```text
Injection
→ Detection
→ Evidence
→ Recovery
```

因此 AMNV 的 Fault Model 是 Validation-oriented，而不是 NAND Physics Simulation。

---

## 12. Log Layer

### 12.1 `amnv/log_parser.py`

`log_parser.py` 將 Firmware-style text log 解析為 structured fields。

主要欄位包含：

- Timestamp
- CID
- Opcode
- LBA
- Status
- Error

T07 使用靜態 `data/sample_fw.log` 驗證 Parser。

T08、T09 與 A02 Fault Case 則可使用 Runtime Log 進行 Command / Error Correlation。

### 12.2 `logs/runtime_fw.log`

此檔案保存 Mock Controller 執行期間產生的 Runtime Firmware-style Log。

它用來模擬 Firmware Debug / Error Log 在 Validation Workflow 中提供的 Evidence。

Log Correlation 主要比對：

- CID
- Opcode
- LBA
- Status
- Error

---

## 13. Validation Result Layer

### 13.1 `amnv/models.py`

`models.py` 定義共用的 Test Result Data Model。

Individual Test 使用共通 Result 結構保存：

- Test ID
- Test Name
- Status
- Expected
- Actual
- Duration
- Details / Evidence

支援的 Test Result State：

- `PASS`
- `FAIL`
- `ERROR`
- `ABORTED`
- `NOT_RUN`

統一 Result Model 的目的，是讓 GUI、A01 與 Reporter 可以用一致方式處理不同 Test。

### 13.2 `amnv/validator.py`

`validator.py` 提供共用 Validation Helper。

其責任為：

- 建立 Check；
- 比較 Expected / Actual；
- 集中判斷 Checks 是否全部通過；
- 避免每個 Test Case 重複建立同類型判斷程式。

---

## 14. Configuration Layer

### 14.1 `amnv/config_loader.py`

`config_loader.py` 提供統一 Configuration Loading。

主要來源為：

```text
config/validation_config.json
```

Test Case 與 Automation 不應各自硬編碼所有設定，而是透過 Configuration Layer 取得需要的參數。

### 14.2 `config/validation_config.json`

此檔案保存全域 Validation Configuration。

用途包括：

- Test parameter；
- Automation behavior；
- A01 / A02 setting；
- Report-related setting；
- Execution behavior。

### 14.3 `data/fault_campaign.json`

此檔案保存 A02 Fault Campaign 的 Case Definition。

內容包含：

- Suite ID；
- Profile；
- Execution Order；
- Fault Type；
- Operation；
- LBA；
- Expected Detection；
- Recovery Behavior。

將 Campaign Case 與 Python Code 分離，可以讓 Fault Campaign 更接近 data-driven validation。

---

## 15. Cancellation / Execution Control

### 15.1 `amnv/cancellation.py`

`CancellationToken` 是一個以 `threading.Event` 為核心的 thread-safe cancellation object。

主要行為：

- `request()`：提出 Stop Request；
- `is_requested()`：查詢 Cancellation 狀態；
- `wait()`：允許 blocking operation 等待 cancellation；
- `reason`：保存第一次 Stop Reason。

第一次 reason 會被保留，重複 Stop 不會覆寫原始原因。

### 15.2 Token Lifecycle

每一次 Individual Test、A01 或 A02 執行，都建立新的 Token。

Token 不重用，也不提供 reset。

概念如下：

```text
Run Start
→ New CancellationToken
→ Task Execution
→ Optional Stop Request
→ Task Finish
→ Token Discard
```

這避免前一次 Stop State 汙染下一次 Test。

---

## 16. Reporting Layer

### 16.1 `amnv/reporting/a01_reporter.py`

A01 Reporter 將 A01 Suite Result 轉換成 PDF Validation Report。

內容可包含：

- Suite Result；
- Total / Executed / Passed / Failed / Error / Aborted / Not Run；
- T01～T09 Summary；
- Individual Test Evidence；
- Timeout / Recovery Evidence；
- STOP Evidence；
- Technical Scope。

正常執行與 STOPPED 執行都可以產生 Report。

### 16.2 `amnv/reporting/a02_report.py`

A02 Reporter 負責 Fault Campaign Report。

內容可包含：

- Campaign Result；
- Campaign Matrix；
- Fault Profile Summary；
- Individual Case Evidence；
- Fault Detection Evidence；
- Recovery Evidence；
- ABORTED / NOT_RUN；
- STOP Reason；
- Technical Scope。

Reporter 只負責「把已經產生的 Result / Evidence 呈現出來」，不重新執行 Test Logic。

---

## 17. 主要資料流

### 17.1 Individual Test

Individual Test 的主要資料流為：

```text
GUI
→ TestWorker
→ T01~T09
→ CommandRunner
→ QueueModel
→ fake_nvme.py
→ MockController
→ Storage / Fault Injector / Log
→ Controller Result
→ CommandRunner
→ Validator
→ TestResult
→ GUI
```

如果 Test 不需要 Command，例如 Log Parsing Test，則可以直接使用對應 Helper / Data，不必經過 Runner。

### 17.2 A01

```text
GUI
→ A01
→ T01
→ T02
→ ...
→ T09
→ Suite Summary
→ A01 Reporter
→ PDF
```

A01 將 Individual Test Result 聚合成 Suite Result。

### 17.3 A02

```text
GUI
→ A02
→ fault_campaign.json
→ Ordered Cases
→ CommandRunner
→ Fault Injection
→ Validation / Recovery
→ Profile Summary
→ A02 Reporter
→ PDF
```

A02 是 Data-driven Fault Campaign，而不是單純呼叫 T01～T09。

### 17.4 STOP

```text
GUI Stop
→ CancellationToken.request()
→ Active Test / Automation observes token
→ CommandRunner terminates active subprocess if required
→ Logical Controller Reset
→ Active unit = ABORTED
→ Remaining units = NOT_RUN
→ Suite = STOPPED
→ Partial PDF
```

---

## 18. 架構設計原則

AMNV 的架構遵循以下原則。

### 18.1 Test Logic 與 GUI 分離

Test 不依賴 Qt Widget，因此可從 GUI 或 CLI 執行。

### 18.2 Execution 與 Validation 分離

Runner 負責執行 Command Lifecycle。

Test Case 負責判斷該結果是否符合 Scenario Expected Behavior。

### 18.3 Runtime 與 Configuration 分離

Validation parameter 與 Fault Campaign Definition 以 JSON 保存，避免所有 Scenario 都硬編碼在 Python 中。

### 18.4 Evidence 與 Presentation 分離

Test / Automation 先產生 Structured Evidence。

Reporter 再將 Evidence 轉換成 PDF。

### 18.5 Timeout 與 User Abort 分離

Timeout 是 Test Scenario。

User Abort 是 Execution Control。

兩者即使都可能中斷 Command，也必須有不同的 Result、Evidence 與 Recovery 語意。

---

## 19. 架構邊界

AMNV 的 Software Architecture 是為了支援 Host-side Logical Validation，而不是建立完整 NVMe Stack。

本架構有意省略：

- PCIe Physical / Data Link / Transaction Layer；
- Real MMIO register；
- DMA engine；
- PRP / SGL data movement；
- MSI / MSI-X interrupt；
- Real Controller Firmware Scheduler；
- FTL；
- NAND protocol；
- ECC / wear leveling / garbage collection 等 media behavior。

這些項目可作為真實 NVMe / SSD 系統的概念對照，但不屬於 AMNV 的 implementation boundary。

---

# English Version

## 1. Document Purpose

This document describes the overall software architecture of **Automation Mock NVMe Validation (AMNV)**, the responsibilities of its major modules, the data flow between layers, and how the components work together to perform Host-side logical NVMe validation.

AMNV uses a layered design that separates the GUI, automation, test cases, command execution, mock controller, storage, fault injection, validation, reporting, and cancellation mechanisms.

The design has three main goals:

1. **Reduce module coupling**: test cases do not directly manage the GUI or PDF layout;
2. **Keep validation flows observable**: command, queue, fault, recovery, and result responsibilities are clearly separated;
3. **Support extension**: new test cases, fault profiles, or reports can be added without major changes to unrelated modules.

---

## 2. Project Directory Structure

The main project structure is:

```text
automation-mock-nvme-validation/
├── main.py
├── fake_nvme.py
├── config/
│   └── validation_config.json
├── data/
│   ├── fault_campaign.json
│   ├── mock_device.json
│   ├── mock_storage.json
│   ├── mock_storage_seed.json
│   └── sample_fw.log
├── logs/
│   └── runtime_fw.log
├── reports/
│   ├── A01/
│   └── A02/
├── docs/
│   └── ...
└── amnv/
    ├── cancellation.py
    ├── config_loader.py
    ├── fault_injector.py
    ├── log_parser.py
    ├── mock_controller.py
    ├── models.py
    ├── queue_model.py
    ├── runner.py
    ├── storage.py
    ├── validator.py
    ├── automation/
    │   ├── a01_full_validation.py
    │   └── a02_fault_campaign.py
    ├── reporting/
    │   ├── a01_reporter.py
    │   └── a02_report.py
    ├── test_cases/
    │   ├── t01_device_baseline.py
    │   ├── t02_write_readback.py
    │   ├── t03_invalid_read_range.py
    │   ├── t04_unsupported_command.py
    │   ├── t05_read_timeout_recovery.py
    │   ├── t06_data_integrity_failure.py
    │   ├── t07_firmware_log_parsing.py
    │   ├── t08_read_error_correlation.py
    │   └── t09_write_failure_recovery.py
    └── ui/
        ├── main_window.py
        ├── main_window.ui
        ├── test_worker.py
        └── ui_main_window.py
```

This structure reflects the major responsibility layers in AMNV.

---

## 3. Architecture Layers

AMNV can be divided into eight major layers:

1. **Presentation Layer**
2. **Automation Layer**
3. **Validation Scenario Layer**
4. **Host Command Execution Layer**
5. **Mock Controller Layer**
6. **Storage / Fault / Log Layer**
7. **Validation Result Layer**
8. **Reporting Layer**

In addition, `CancellationToken` acts as a cross-layer execution-control mechanism shared by the GUI, automation, test cases, and runner.

---

## 4. Presentation Layer

### 4.1 `main.py`

`main.py` is the GUI application entry point.

Its responsibilities are limited to:

- creating the Qt application;
- creating the main window;
- starting the GUI event loop.

It does not implement test logic, command execution, or validation.

### 4.2 `amnv/ui/main_window.py`

`main_window.py` is the primary GUI control layer.

Its responsibilities include:

- binding T01–T09 buttons;
- binding A01 / A02 automation;
- starting background workers;
- creating a `CancellationToken` for each execution;
- receiving test / automation results;
- displaying console messages;
- managing the Stop button;
- invoking A01 / A02 reporters;
- managing mock-storage utilities;
- optionally opening generated PDF reports.

The GUI does not implement NVMe command behavior directly.

Its main flow is:

```text
User Action
→ Task Dispatch
→ Progress Display
→ Result Display
→ Report Integration
```

### 4.3 `amnv/ui/test_worker.py`

`test_worker.py` provides a generic background worker.

Long-running test or automation tasks are executed in a `QThread` so that the GUI main thread remains responsive.

The worker does not implement STOP logic itself.

Stop requests are written directly from the GUI thread into a shared `CancellationToken`, allowing the active test or runner to observe cancellation without depending on a queued worker slot.

The project therefore does not use `QThread.terminate()` for execution control.

### 4.4 `main_window.ui` and `ui_main_window.py`

`main_window.ui` contains the Qt Designer UI definition.

`ui_main_window.py` is generated from the UI definition and constructs the widget structure.

The design principle is:

- `.ui` defines layout;
- `ui_main_window.py` is treated as generated code;
- business logic remains in `main_window.py`.

---

## 5. Automation Layer

The automation layer combines individual tests or campaign cases into repeatable suites.

### 5.1 `amnv/automation/a01_full_validation.py`

A01 is the Full Validation Suite.

Its responsibilities include:

- executing T01 through T09 in order;
- preserving each test result;
- receiving a `CancellationToken`;
- emitting progress events;
- handling `PASS / FAIL / ERROR / ABORTED / NOT_RUN`;
- calculating Executed / Passed / Failed / Error / Aborted / Not Run;
- producing the suite-level result;
- returning `STOPPED` when execution is cancelled.

A01 does not reimplement T01–T09 test logic. It acts as the orchestration layer.

### 5.2 `amnv/automation/a02_fault_campaign.py`

A02 is the Deterministic Fault Campaign.

Campaign definitions are primarily provided through `data/fault_campaign.json`.

Its responsibilities include:

- loading campaign definitions;
- checking profile order and configuration;
- creating the execution order;
- executing fault cases;
- calling `CommandRunner`;
- validating setup, fault, recovery, and evidence;
- producing profile summaries;
- supporting cooperative cancellation;
- preserving `ABORTED / NOT_RUN` states after stop;
- producing a suite-level `PASS / FAIL / STOPPED` result.

The current fault profiles include:

- Command Timeout
- NAND Read Failure
- NAND Program Failure
- Data Miscompare

The major distinction is:

- **A01** is a complete regression organized around individual tests;
- **A02** is a fault-oriented validation campaign organized around fault profiles and campaign cases.

---

## 6. Validation Scenario Layer

### 6.1 `amnv/test_cases/`

T01–T09 are individual validation scenarios.

Each test is responsible for:

1. defining its validation objective;
2. executing required commands;
3. building validation checks;
4. determining the test result;
5. preserving evidence;
6. checking cancellation at appropriate points.

Test cases do not directly manage the GUI, PDF layout, Qt threads, or campaign orchestration.

This allows them to be executed individually from the CLI, GUI, or automation layer.

### 6.2 Roles of T01–T09

| Test | Primary Role |
| --- | --- |
| T01 | Device Baseline / Identify / SMART-style baseline |
| T02 | Normal WRITE / READ Readback |
| T03 | Invalid Range Validation |
| T04 | Unsupported Command Validation |
| T05 | Timeout / Reset / Retry Recovery |
| T06 | Data Miscompare Detection |
| T07 | Firmware-style Log Parsing |
| T08 | READ Failure / Log Correlation |
| T09 | WRITE Failure / Storage Protection / Reset / Retry / Readback |

The complete flow and validation criteria for each test are described separately in the Test Design documentation.

---

## 7. Host Command Execution Layer

### 7.1 `amnv/runner.py`

`CommandRunner` is the central coordinator of the AMNV Host-side command lifecycle.

It is responsible for:

- building commands;
- allocating CIDs;
- interacting with the queue model;
- starting the `fake_nvme.py` subprocess;
- waiting for controller results;
- handling timeout;
- handling user abort;
- creating logical completions;
- updating queue state;
- preserving execution traces;
- performing controller reset.

A normal command follows the conceptual flow:

```text
Command Build
→ SQ Submit
→ SQ Tail Doorbell
→ Controller Fetch
→ Subprocess Execution
→ Controller Result
→ CQ Post
→ CQ Consume
→ CQ Head Doorbell
→ Final Result
```

The runner returns Host, command, controller, completion, queue-state, and trace information for later validation.

### 7.2 Timeout Behavior

Timeout is not treated as a normal command failure.

When the controller subprocess does not complete within the expected time:

- the Host result becomes `TIMEOUT`;
- no normal completion is generated;
- the outstanding CID remains;
- queue state remains at the timeout condition.

The test or campaign then decides whether controller reset and retry are required.

### 7.3 User Abort Behavior

User Abort and Timeout are distinct lifecycles.

When cancellation is requested while an active subprocess is still running:

1. the runner detects cancellation;
2. `terminate()` is requested;
3. a grace period of approximately 0.5 seconds is provided;
4. `kill()` is used if required;
5. logical controller reset is performed;
6. SQ / CQ / outstanding state is cleared;
7. CID progression is preserved;
8. `ABORTED` evidence is returned.

This mechanism is used by STOP v1.

---

## 8. Queue Model

### 8.1 `amnv/queue_model.py`

The queue model represents the logical NVMe Submission Queue / Completion Queue lifecycle.

It tracks:

- `sq_head`
- `sq_tail`
- `cq_head`
- `cq_tail`
- `outstanding_cids`
- `next_cid`

It is not a real DMA-backed NVMe queue and does not implement PCIe MMIO.

Its purpose is to:

- expose queue state to tests;
- model SQ submission, controller fetch, CQ posting, and Host consumption;
- validate outstanding CIDs after timeout;
- validate queue clearing after reset;
- validate retry using a new CID.

### 8.2 CID Progression

CID allocation is managed by the Host-side queue model.

Controller reset clears:

- SQ head / tail;
- CQ head / tail;
- outstanding CIDs.

However, it does not reset `next_cid` to 1.

This enables validation of:

```text
CID 1 Timeout
→ Reset
→ next_cid remains 2
→ Retry uses CID 2
```

---

## 9. Mock Controller Layer

### 9.1 `fake_nvme.py`

`fake_nvme.py` is an independent Python subprocess started by the Host runner.

It provides the mock NVMe command execution entry point.

Its responsibilities include:

- receiving command / CID / LBA / length / data / fault information;
- invoking the mock controller;
- executing the requested operation;
- returning a structured controller result;
- writing the result back to the Host runner.

Using a separate process allows AMNV to model:

- controller execution;
- command timeout;
- active subprocess termination;
- a logical Host / Controller execution boundary.

It is not intended to represent a real PCIe controller firmware process.

### 9.2 `amnv/mock_controller.py`

`mock_controller.py` implements the mock controller command behavior.

It handles the command types required by the project, including:

- IDENTIFY
- SMART-style data access
- READ
- WRITE
- unsupported-command paths

The controller interacts with:

- mock storage;
- fault injector;
- mock device data;
- runtime firmware-style logs.

---

## 10. Storage Layer

### 10.1 `amnv/storage.py`

`MockStorage` provides logical block storage.

Its responsibilities include:

- reading runtime storage state;
- updating data for WRITE;
- returning data for READ;
- validating range;
- resetting storage to its baseline.

It uses JSON as its mock backend instead of NAND media.

### 10.2 `data/mock_storage_seed.json`

This file stores the initial storage baseline.

It provides:

- deterministic initial state;
- a reset source for A01, A02, or GUI utilities;
- protection against previous test data contaminating the next validation run.

### 10.3 `data/mock_storage.json`

This file stores runtime storage state.

WRITE / READ tests operate on this state.

Therefore:

```text
mock_storage_seed.json
= baseline

mock_storage.json
= runtime state
```

---

## 11. Fault Injection Layer

### 11.1 `amnv/fault_injector.py`

The fault injector provides deterministic fault behavior.

The main fault types are:

- `timeout`
- `NAND_READ_FAIL`
- `NAND_PROGRAM_FAIL`
- `miscompare`

The fault injector also validates whether a fault is compatible with the requested command.

For example:

- `NAND_READ_FAIL` is only valid for READ;
- `NAND_PROGRAM_FAIL` is associated with WRITE.

### 11.2 Fault Injection Positioning

Fault injection does not represent physical NAND failure behavior.

Its purpose is to create controlled failure conditions so validation logic can verify:

```text
Injection
→ Detection
→ Evidence
→ Recovery
```

The AMNV fault model is therefore validation-oriented rather than a NAND-physics simulation.

---

## 12. Log Layer

### 12.1 `amnv/log_parser.py`

`log_parser.py` converts firmware-style text logs into structured fields.

The main fields include:

- Timestamp
- CID
- Opcode
- LBA
- Status
- Error

T07 uses the static `data/sample_fw.log` file to validate parser behavior.

T08, T09, and A02 fault cases can use runtime logs for command/error correlation.

### 12.2 `logs/runtime_fw.log`

This file stores runtime firmware-style logs produced during mock-controller execution.

It is intended to simulate firmware debug/error evidence used in validation workflows.

Correlation primarily compares:

- CID
- Opcode
- LBA
- Status
- Error

---

## 13. Validation Result Layer

### 13.1 `amnv/models.py`

`models.py` defines the shared test-result data model.

Individual tests preserve:

- Test ID
- Test Name
- Status
- Expected
- Actual
- Duration
- Details / Evidence

Supported test-result states are:

- `PASS`
- `FAIL`
- `ERROR`
- `ABORTED`
- `NOT_RUN`

A common result model allows the GUI, A01, and reporting layers to handle different tests consistently.

### 13.2 `amnv/validator.py`

`validator.py` provides shared validation helpers.

Its responsibilities include:

- building checks;
- comparing expected and actual values;
- determining whether all checks passed;
- reducing repeated validation code across test cases.

---

## 14. Configuration Layer

### 14.1 `amnv/config_loader.py`

`config_loader.py` provides centralized configuration loading.

Its primary source is:

```text
config/validation_config.json
```

Tests and automation retrieve required parameters through the configuration layer instead of independently hardcoding all settings.

### 14.2 `config/validation_config.json`

This file stores global validation configuration.

It is used for items such as:

- test parameters;
- automation behavior;
- A01 / A02 settings;
- report-related settings;
- execution behavior.

### 14.3 `data/fault_campaign.json`

This file defines A02 fault-campaign cases.

Its data includes:

- suite ID;
- profile;
- execution order;
- fault type;
- operation;
- LBA;
- expected detection;
- recovery behavior.

Separating campaign cases from Python code makes A02 closer to a data-driven validation design.

---

## 15. Cancellation / Execution Control

### 15.1 `amnv/cancellation.py`

`CancellationToken` is a thread-safe cancellation object based on `threading.Event`.

Its main behavior includes:

- `request()` to request stop;
- `is_requested()` to query cancellation state;
- `wait()` to allow blocking operations to observe cancellation;
- `reason` to preserve the first stop reason.

The first stop reason is preserved and repeated stop requests do not overwrite it.

### 15.2 Token Lifecycle

A new token is created for every individual test, A01 run, or A02 run.

Tokens are not reused or reset.

```text
Run Start
→ New CancellationToken
→ Task Execution
→ Optional Stop Request
→ Task Finish
→ Token Discard
```

This prevents cancellation state from one run from contaminating the next.

---

## 16. Reporting Layer

### 16.1 `amnv/reporting/a01_reporter.py`

The A01 reporter converts A01 suite results into a PDF validation report.

The report can include:

- suite result;
- Total / Executed / Passed / Failed / Error / Aborted / Not Run;
- T01–T09 summary;
- individual test evidence;
- timeout/recovery evidence;
- STOP evidence;
- technical scope.

Reports can be generated for both normal and STOPPED runs.

### 16.2 `amnv/reporting/a02_report.py`

The A02 reporter produces fault-campaign reports.

Its output can include:

- campaign result;
- campaign matrix;
- fault-profile summary;
- individual case evidence;
- fault-detection evidence;
- recovery evidence;
- ABORTED / NOT_RUN state;
- stop reason;
- technical scope.

The reporting layer renders already-produced results and evidence. It does not re-execute validation logic.

---

## 17. Main Data Flows

### 17.1 Individual Test

```text
GUI
→ TestWorker
→ T01~T09
→ CommandRunner
→ QueueModel
→ fake_nvme.py
→ MockController
→ Storage / Fault Injector / Log
→ Controller Result
→ CommandRunner
→ Validator
→ TestResult
→ GUI
```

Tests that do not require a command, such as log-parsing validation, can directly use the corresponding helper/data path without passing through the runner.

### 17.2 A01

```text
GUI
→ A01
→ T01
→ T02
→ ...
→ T09
→ Suite Summary
→ A01 Reporter
→ PDF
```

A01 aggregates individual test results into a suite result.

### 17.3 A02

```text
GUI
→ A02
→ fault_campaign.json
→ Ordered Cases
→ CommandRunner
→ Fault Injection
→ Validation / Recovery
→ Profile Summary
→ A02 Reporter
→ PDF
```

A02 is a data-driven fault campaign rather than a simple sequence of T01–T09.

### 17.4 STOP

```text
GUI Stop
→ CancellationToken.request()
→ Active Test / Automation observes token
→ CommandRunner terminates active subprocess if required
→ Logical Controller Reset
→ Active unit = ABORTED
→ Remaining units = NOT_RUN
→ Suite = STOPPED
→ Partial PDF
```

---

## 18. Architecture Design Principles

### 18.1 Separate Test Logic from the GUI

Tests do not depend on Qt widgets and can be executed from the GUI or CLI.

### 18.2 Separate Execution from Validation

The runner manages command lifecycle execution.

The test case determines whether the result satisfies the expected scenario behavior.

### 18.3 Separate Runtime from Configuration

Validation parameters and fault-campaign definitions are stored in JSON rather than hardcoded entirely in Python.

### 18.4 Separate Evidence from Presentation

Tests and automation first produce structured evidence.

Reporters then convert that evidence into PDF output.

### 18.5 Separate Timeout from User Abort

Timeout is a test scenario.

User Abort is execution control.

Even though both may interrupt a command, they use different result, evidence, and recovery semantics.

---

## 19. Architecture Boundary

The AMNV software architecture is designed for Host-side logical validation rather than implementation of a complete NVMe stack.

The following are intentionally outside the implementation boundary:

- PCIe Physical / Data Link / Transaction Layer;
- real MMIO registers;
- DMA engine;
- PRP / SGL data movement;
- MSI / MSI-X interrupts;
- real controller firmware scheduler;
- FTL;
- NAND protocol;
- ECC / wear leveling / garbage collection and other media behavior.

These mechanisms can be used as conceptual references when comparing AMNV with a real SSD system, but they are not implemented by AMNV.
