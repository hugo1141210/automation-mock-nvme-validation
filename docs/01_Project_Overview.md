# 專案總覽 / Project Overview

# 中文版

## 1. 專案目的

**Automation Mock NVMe Validation（AMNV）** 是一套以 Python 實作的 Host-side 邏輯型 NVMe 驗證自動化框架。

本專案的目的，是在缺乏實體 SSD、Controller Firmware 開發環境，或 PCIe / NVMe 硬體驗證平台的情況下，以可重現、可控制的 Mock Environment 重建並驗證重要的 NVMe 驗證概念。

AMNV 的重點放在「驗證流程本身」，包含：

- Command submission 與 completion handling
- Submission Queue（SQ）/ Completion Queue（CQ）邏輯狀態追蹤
- Command Identifier（CID）配置與遞增
- Timeout detection
- Controller reset 與 retry
- Deterministic fault injection
- Firmware-style runtime log correlation
- Data-integrity validation
- Automated test execution
- PDF evidence generation
- Cooperative stop / cancellation behavior

本專案並不是要以電氣層、協議層或硬體層精確模擬一顆真正的 SSD，而是建立一個可重現的邏輯驗證環境，用來展示 Host-side validation design、failure handling、recovery logic、automation structure 與 evidence collection。

---

## 2. 專案定位

AMNV 的定位介於「單純 Command Mock」與「真實 NVMe SSD 驗證平台」之間。

真正的 NVMe 驗證環境通常包含下列硬體與協議行為：

- PCIe transport
- Memory-Mapped I/O（MMIO）
- 真實 NVMe Submission / Completion Queues
- Direct Memory Access（DMA）
- Physical Region Page（PRP）/ Scatter-Gather List（SGL）
- MSI / MSI-X 等 interrupt mechanisms
- Controller firmware
- Flash Translation Layer（FTL）
- NAND media behavior

AMNV 不嘗試在實體層重建這些機制。

本專案選擇以 Python 重建部分「邏輯行為」，讓 validation scenario 可以被重複執行，並驗證 Host-side 預期結果是否正確。

因此，本框架適合用於：

- Validation workflow 練習
- Test case design
- Automation design
- Fault-handling analysis
- Recovery-flow verification
- Queue-state reasoning
- Firmware-log correlation
- SSD / Firmware Validation 相關職缺的面試展示

---

## 3. 主要設計目標

### 3.1 可重現且具決定性的執行

相同的測試條件應該產生相同的預期結果。

Fault 由設定刻意注入，而不是依賴隨機硬體行為，因此 Timeout、NAND Read Failure、NAND Program Failure、Data Miscompare 等異常狀況都可以穩定重現。

### 3.2 可觀察的 Command Lifecycle

每一筆 Command 都應保留足夠資訊，方便進行驗證與除錯，包括：

- Opcode
- CID
- LBA
- Length
- Host-side status
- Completion status
- Timeout state
- Queue state
- Outstanding CID state
- Execution trace

這讓整個 validation flow 可以被觀察與分析，而不是把 Command execution 當成無法追蹤的 black box。

### 3.3 明確驗證 Recovery 行為

Recovery 本身也是 validation target，而不是單純的 cleanup。

例如在 Timeout scenario 中，需要驗證：

1. Command timeout 後可以維持在 outstanding state；
2. Controller reset 可以清除 logical SQ / CQ 與 outstanding command state；
3. CID progression 不會因 reset 被重設；
4. Retry 會使用新的 CID；
5. Fault 移除後，Retry 可以正常完成。

### 3.4 區分 Test Result 與 Execution State

本專案將「測試正確性」與「執行狀態」分開處理。

Test / Case result states：

- `PASS`
- `FAIL`
- `ERROR`
- `ABORTED`
- `NOT_RUN`

Suite result states：

- `PASS`
- `FAIL`
- `STOPPED`

這樣可以避免 User Stop 被錯誤解讀成 Functional Failure。

### 3.5 以 Evidence 為核心的輸出

本框架不只顯示最終 PASS / FAIL，而是盡可能保留驗證證據。

Evidence 可包含：

- Validation checks
- Command result data
- Queue state
- Reset state
- Retry state
- Firmware-style log entries
- Abort stage
- Stop reason
- Report summary

A01 與 A02 在正常執行或被 Stop 的情況下，都可以產生對應 PDF Report。

---

## 4. 驗證 Scenario

### 4.1 Individual Validation Tests — T01 to T09

T01～T09 分別用來驗證特定的 Command、Failure、Recovery 或 Evidence-handling 行為。

| ID | Scenario | 主要驗證目的 |
| --- | --- | --- |
| T01 | Device Baseline Check | 驗證 Mock Device identity 與 SMART-style baseline data |
| T02 | Normal Write / Readback | 驗證正常 WRITE 後 READ back 的資料一致性 |
| T03 | Invalid Read Range | 驗證 Invalid LBA / Length 的拒絕行為 |
| T04 | Unsupported Command | 驗證 Unsupported Opcode 的處理 |
| T05 | Read Timeout + Recovery | 驗證 Timeout、Reset、CID progression、Retry 與 Recovery |
| T06 | Data Integrity Failure | 驗證 Returned Data Miscompare 的偵測 |
| T07 | Firmware Log Parsing | 驗證 Firmware-style Log Parsing |
| T08 | Read Error Correlation | 驗證 failed READ completion 與 Firmware Log Correlation |
| T09 | Write Failure + Recovery | 驗證 failed WRITE、Storage Protection、Reset、Retry 與 Readback |

每一個 Test 都可以透過 GUI 單獨執行。

### 4.2 A01 — Full Validation

A01 會依序執行 T01～T09，形成完整的 Validation Suite。

主要目的：

- 提供 one-click full regression
- 保留每個 Test 的執行結果
- 產生 Suite-level statistics
- 支援 cooperative stop
- 被中斷的 active test 記為 `ABORTED`
- 尚未執行的 test 記為 `NOT_RUN`
- 產生完整或 Partial PDF Report

A01 用來展示如何把 Individual Test Cases 編排成可重複執行的 Regression Suite。

### 4.3 A02 — Deterministic Fault Campaign

A02 以 Fault Profile 分組執行 Fault-oriented Validation Cases。

目前包含：

- `FP01` — Command Timeout
- `FP02` — NAND Read Failure
- `FP03` — NAND Program Failure
- `FP04` — Data Miscompare

A02 不只驗證 Fault 是否發生，也驗證 Host-side Framework 是否能依預期完成 Detection、Record、Correlation 與 Recovery。

A02 支援：

- Ordered Case execution
- Deterministic fault configuration
- Per-profile summary
- Cooperative stop
- `ABORTED` / `NOT_RUN` state preservation
- Partial Report generation after stop

---

## 5. 使用者操作方式

本專案提供 PySide6 GUI，讓使用者可以執行與觀察驗證流程。

GUI 功能包含：

- Individual T01～T09 execution
- A01 execution
- A02 execution
- Test Stop
- Runtime Console / Log Viewer
- Mock Storage Utilities
- Automatic PDF Report Generation
- Optional Report Opening

Long-running Test 透過 Worker Thread 執行，避免 GUI 在驗證期間失去回應。

Stop 功能採用 Cooperative Cancellation，而不是強制終止 Qt Worker Thread。

---

## 6. STOP v1

STOP v1 提供 Individual Test 與 Automation Suite 的 Controlled Cancellation。

主要行為：

- GUI 透過共享 `CancellationToken` 發出 cancellation request；
- Test 與 Automation Code 在定義好的 cancellation point 檢查 Token；
- Active `fake_nvme.py` subprocess 可以被 terminate；
- 透過 controller reset 回復 logical queue / outstanding state；
- 被中斷的 active unit 記為 `ABORTED`；
- 尚未開始的 unit 記為 `NOT_RUN`；
- Suite 記為 `STOPPED`；
- 已完成的 PASS / FAIL / ERROR 結果會被保留。

STOP v1 是 Cooperative Cancellation。

它不保證能處理 arbitrary Python deadlock 或 non-cooperative infinite loop。

---

## 7. 專案輸出

本專案主要產出以下幾類結果。

### Runtime Result

在 Console 中即時顯示 Test、Case 與 Suite 的執行狀態。

### Validation Evidence

以 Structured Python Result Object 保存：

- Validation checks
- Command details
- Recovery state
- Log entries
- Execution metadata

### PDF Reports

A01 與 A02 可以產生包含下列資訊的 PDF：

- Overall status
- Execution summary
- Per-test / per-case result
- Recovery evidence
- Fault evidence
- Stop evidence
- Technical scope

### Demonstration Assets

最終展示預計包含：

- Architecture / Workflow Diagrams
- Representative PASS Reports
- Representative STOPPED Reports
- GUI Screenshots
- Short Operation / Demo Video

---

## 8. 範圍與限制

AMNV 是一套 **Host-side Logical NVMe Validation Simulation**。

本專案不宣稱具備：

- Real PCIe Transaction Layer Packet behavior
- Real MMIO register access
- Real DMA behavior
- Real PRP / SGL handling
- Real MSI / MSI-X interrupt behavior
- Actual SSD Controller Firmware execution
- Flash Translation Layer behavior
- NAND electrical characteristics
- NAND timing / wear / ECC / media physics
- Real SSD performance measurement

因此，本專案應被視為 **Validation Design + Automation Project**，而不是 Physical SSD Emulator。

---

## 9. 預期展示價值

本專案希望展示以下能力：

- 理解基本 NVMe Command 與 Queue Concept
- 將 Protocol / Firmware Concept 轉換成 Test Scenario
- 設計 Positive / Negative Validation Cases
- 自動化重複驗證
- 區分 Timeout、Command Failure、Data Integrity Failure 與 User Cancellation
- 分析 Reset / Retry Behavior
- 將 Command Result 與 Firmware-style Log 進行 Correlation
- 保存 Validation Evidence
- 產出 Structured Validation Report
- 設計可操作的 Validation GUI
- 清楚定義 System Scope 與 Limitations

專案重點放在 Validation Engineering Methodology 與 Automation Design，而不是 Hardware Emulation.

---

# English Version

## 1. Project Purpose

**Automation Mock NVMe Validation (AMNV)** is a Host-side logical NVMe validation automation framework implemented in Python.

The project was created to reproduce and validate key NVMe validation concepts in a deterministic mock environment when a real SSD, controller firmware development environment, or PCIe/NVMe hardware validation platform is not available.

AMNV focuses on the validation workflow itself:

- command submission and completion handling
- Submission Queue (SQ) / Completion Queue (CQ) logical state tracking
- Command Identifier (CID) allocation and progression
- timeout detection
- controller reset and retry
- deterministic fault injection
- firmware-style runtime log correlation
- data-integrity validation
- automated test execution
- PDF evidence generation
- cooperative stop / cancellation behavior

The goal is not to emulate an SSD at electrical or protocol-accurate hardware level. The goal is to provide a reproducible environment for demonstrating Host-side validation design, failure handling, recovery logic, automation structure, and evidence collection.

---

## 2. Project Positioning

AMNV is positioned between a simple command mock and a real NVMe SSD validation platform.

A real NVMe validation environment normally contains hardware and protocol behavior such as:

- PCIe transport
- Memory-Mapped I/O (MMIO)
- real NVMe Submission / Completion Queues
- Direct Memory Access (DMA)
- Physical Region Page (PRP) / Scatter-Gather List (SGL)
- interrupt mechanisms such as MSI / MSI-X
- controller firmware
- Flash Translation Layer (FTL)
- NAND media behavior

AMNV does not attempt to reproduce these mechanisms physically.

Instead, the project reconstructs selected logical behaviors in Python so that validation scenarios can be executed repeatedly and the expected Host-side result can be verified.

This makes the framework suitable for:

- validation workflow practice
- test-case design
- automation design
- fault-handling analysis
- recovery-flow verification
- queue-state reasoning
- firmware-log correlation
- interview demonstration for SSD / firmware validation related roles

---

## 3. Main Design Goals

### 3.1 Deterministic Execution

The same test condition should produce the same expected result.

Faults are intentionally injected by configuration rather than depending on random hardware behavior. This allows failures such as timeout, NAND read failure, NAND program failure, and data miscompare to be reproduced consistently.

### 3.2 Observable Command Lifecycle

Each command should expose enough information for validation and debugging, including:

- opcode
- CID
- LBA
- length
- Host-side status
- completion status
- timeout state
- queue state
- outstanding CID state
- execution trace

This allows the validation flow to be inspected instead of treating each command as a black box.

### 3.3 Explicit Recovery Validation

Recovery is treated as part of the validation target, not only as cleanup.

For example, timeout scenarios verify that:

1. a command can remain outstanding after timeout;
2. controller reset clears logical SQ / CQ and outstanding command state;
3. CID progression is preserved;
4. retry uses a new CID;
5. the retry can complete successfully when the fault is removed.

### 3.4 Separation of Validation Results

The project distinguishes execution state from test correctness.

Test / Case result states:

- `PASS`
- `FAIL`
- `ERROR`
- `ABORTED`
- `NOT_RUN`

Suite result states:

- `PASS`
- `FAIL`
- `STOPPED`

This prevents a user-requested stop from being incorrectly reported as a functional test failure.

### 3.5 Evidence-Oriented Output

The framework is designed to preserve validation evidence rather than only display a final result.

Evidence can include:

- validation checks
- command result data
- queue state
- reset state
- retry state
- firmware-style log entries
- abort stage
- stop reason
- report summary

A01 and A02 can generate PDF reports for both normal completion and stopped execution.

---

## 4. Validation Scenarios

### 4.1 Individual Validation Tests — T01 to T09

The individual tests are designed to validate specific command, failure, recovery, or evidence-handling behaviors.

| ID | Scenario | Main Validation Purpose |
| --- | --- | --- |
| T01 | Device Baseline Check | Verify mock device identity and SMART-style baseline data |
| T02 | Normal Write / Readback | Verify normal WRITE followed by READ data validation |
| T03 | Invalid Read Range | Verify invalid LBA / length rejection |
| T04 | Unsupported Command | Verify unsupported opcode handling |
| T05 | Read Timeout + Recovery | Verify timeout, reset, CID progression, retry, and recovery |
| T06 | Data Integrity Failure | Verify detection of returned-data mismatch |
| T07 | Firmware Log Parsing | Verify firmware-style log parsing behavior |
| T08 | Read Error Correlation | Verify failed READ completion and firmware-log correlation |
| T09 | Write Failure + Recovery | Verify failed WRITE, storage protection, reset, retry, and readback |

Each test can be executed individually from the GUI.

### 4.2 A01 — Full Validation

A01 executes T01 through T09 as a complete validation suite.

Its main purposes are:

- provide one-click full regression execution
- preserve per-test results
- produce suite-level statistics
- support cooperative stop
- mark the active interrupted test as `ABORTED`
- mark remaining tests as `NOT_RUN`
- generate a complete or partial PDF validation report

A01 is intended to demonstrate how individual validation cases can be orchestrated into a repeatable regression suite.

### 4.3 A02 — Deterministic Fault Campaign

A02 executes fault-oriented validation cases grouped by fault profile.

Current fault profiles include:

- `FP01` — Command Timeout
- `FP02` — NAND Read Failure
- `FP03` — NAND Program Failure
- `FP04` — Data Miscompare

The campaign validates not only whether a fault occurs, but also whether the Host-side framework detects, records, correlates, and recovers from the fault as expected.

A02 supports:

- ordered Case execution
- deterministic fault configuration
- per-profile summary
- cooperative stop
- `ABORTED` / `NOT_RUN` state preservation
- partial report generation after stop

---

## 5. User Interaction

The project provides a PySide6 graphical interface for execution and observation.

The GUI provides:

- individual T01–T09 execution
- A01 execution
- A02 execution
- Test Stop
- runtime console / log viewing
- mock storage utilities
- automatic PDF report generation
- optional report opening after suite completion

Long-running test execution is placed in a worker thread so that the GUI can remain responsive while validation is running.

The Stop function uses cooperative cancellation rather than forcefully terminating the Qt worker thread.

---

## 6. STOP v1

STOP v1 provides controlled cancellation for individual tests and automation suites.

The main behavior is:

- the GUI requests cancellation through a shared `CancellationToken`;
- tests and automation code check the token at defined cancellation points;
- an active `fake_nvme.py` subprocess can be terminated;
- controller reset is used to recover logical queue / outstanding state;
- an interrupted active unit becomes `ABORTED`;
- units that were never started become `NOT_RUN`;
- the suite becomes `STOPPED`;
- completed PASS / FAIL / ERROR results are preserved.

STOP v1 is cooperative by design.

It does not guarantee recovery from arbitrary Python deadlocks or non-cooperative infinite loops.

---

## 7. Project Outputs

The project produces several types of output.

### Runtime Result

Console-visible test, Case, and suite status.

### Validation Evidence

Structured Python result objects containing:

- validation checks
- command details
- recovery state
- log entries
- execution metadata

### PDF Reports

A01 and A02 generate PDF reports containing:

- overall status
- execution summary
- per-test or per-case results
- recovery evidence
- fault evidence
- stop evidence when applicable
- technical scope information

### Demonstration Assets

The final project presentation is planned to include:

- architecture and workflow diagrams
- representative PASS reports
- representative STOPPED reports
- GUI screenshots
- a short operation / demonstration video

---

## 8. Scope and Limitations

AMNV is a **Host-side logical NVMe validation simulation**.

It does not claim to provide:

- real PCIe Transaction Layer Packet behavior
- real MMIO register access
- real DMA behavior
- real PRP / SGL handling
- real MSI / MSI-X interrupts
- actual SSD controller firmware execution
- Flash Translation Layer behavior
- NAND electrical characteristics
- NAND timing, wear, ECC, or media physics
- real SSD performance measurement

The framework should therefore be evaluated as a validation-design and automation project, not as a physical SSD emulator.

---

## 9. Expected Demonstration Value

The project is intended to demonstrate the ability to:

- understand basic NVMe command and queue concepts
- convert protocol / firmware concepts into test scenarios
- design positive and negative validation cases
- automate repeated validation
- distinguish timeout, command failure, data-integrity failure, and user cancellation
- reason about reset and retry behavior
- correlate command results with firmware-style logs
- preserve test evidence
- produce structured validation reports
- design a usable validation GUI
- define clear system scope and limitations

The emphasis is on validation engineering methodology and automation design rather than hardware emulation.
