# 真實 NVMe / SSD 與 AMNV 對照 / Real NVMe / SSD vs AMNV

# 中文版

## 1. 文件目的

本文件說明真實 NVMe SSD 的主要 Host-to-Controller 執行流程，並逐階段對照 **Automation Mock NVMe Validation（AMNV）** 中使用的邏輯模擬機制與實際 Python 檔案。

本文件的目的不是將 AMNV 描述成完整的 SSD Emulator，而是明確回答：

1. 真實 NVMe / SSD 流程中每一個主要階段負責什麼；
2. AMNV 在哪些地方保留了相同的邏輯概念；
3. AMNV 使用哪些程式模組對應這些概念；
4. 哪些 PCIe、DMA、Firmware、FTL、NAND 行為並未被實際模擬；
5. AMNV 的驗證結果應該如何正確解讀。

AMNV 的定位始終是：

> **Host-side Logical NVMe Validation Simulation**

而不是：

> **Physical SSD / PCIe / NAND Emulator**

---

## 2. 對照原則

真實 NVMe SSD 與 AMNV 的對照，不應理解為「一個 Python 模組等於一個真實硬體模組」。

AMNV 採用的是 **Conceptual Mapping（概念映射）**。

也就是：

```text
真實 NVMe 行為
→ 抽取可驗證的邏輯概念
→ 在 Python 中建立可觀察、可控制、可重現的對應機制
```

例如：

```text
真實系統：
Host 在 Host Memory 中建立 SQ Entry
→ 更新 MMIO Doorbell
→ Controller 透過 PCIe / DMA 取得 Command

AMNV：
CommandRunner 建立 Command
→ QueueModel 更新 SQ State
→ 記錄 Logical Doorbell Event
→ 啟動 Mock Controller subprocess
```

兩者保留相同的「Command Submission Lifecycle」概念，但 AMNV 並未實作實際的 PCIe Transaction、MMIO Register 或 DMA。

---

## 3. 真實 NVMe SSD 的主要資料流

一筆典型 NVMe Command 的高階流程可以概括為：

```text
Application / Test Tool
→ Operating System / NVMe Driver
→ Build NVMe Command
→ Write Submission Queue Entry
→ Update SQ Tail Doorbell
→ SSD Controller Fetches Command
→ Controller Firmware Executes Command
→ Data Transfer / Media Operation
→ Write Completion Queue Entry
→ Interrupt or Polling
→ Host Consumes Completion
→ Update CQ Head Doorbell
```

實際 SSD 內部通常還會包含：

```text
Controller Firmware
→ FTL
→ DRAM / SRAM Metadata
→ NAND Flash
→ ECC / Media Management
```

AMNV 只選擇其中與 validation workflow 直接相關的部分進行邏輯建模。

---

## 4. 高階對照表

| 真實 NVMe / SSD 階段 | 真實系統主要機制 | AMNV 對應 | 主要檔案 | 模擬程度 |
| --- | --- | --- | --- | --- |
| Test / Workload | Application、Validation Tool | T01～T09、A01、A02 | `amnv/test_cases/*`, `amnv/automation/*` | 邏輯對應 |
| Command Build | NVMe Driver 建立 Command | CommandRunner 建立 Structured Command | `amnv/runner.py` | 邏輯模擬 |
| CID Allocation | Host 配置 Command Identifier | QueueModel 配置 `next_cid` | `amnv/queue_model.py` | 邏輯模擬 |
| SQ Entry | Host Memory Submission Queue | SQ State / Outstanding State | `amnv/queue_model.py` | 邏輯模擬 |
| SQ Doorbell | MMIO Register Write | Logical Doorbell Trace Event | `amnv/runner.py`, `amnv/queue_model.py` | 僅事件語意 |
| PCIe Transport | PCIe TLP | Python subprocess boundary | `amnv/runner.py`, `fake_nvme.py` | 不模擬 PCIe |
| DMA Command Fetch | Controller DMA 讀 SQ | Logical Controller Fetch | `amnv/queue_model.py`, `amnv/runner.py` | 邏輯模擬 |
| Controller Firmware | NVMe Firmware Command Handler | Mock Controller Logic | `fake_nvme.py`, `amnv/mock_controller.py` | 行為模擬 |
| FTL / Media | FTL、NAND、ECC、GC 等 | JSON Mock Storage | `amnv/storage.py`, `data/mock_storage*.json` | 高度簡化 |
| Fault Behavior | Media / FW / Timing Fault | Deterministic Fault Injection | `amnv/fault_injector.py` | Validation-oriented |
| Firmware Log | Firmware Debug / Error Log | Firmware-style Runtime Log | `logs/runtime_fw.log`, `amnv/log_parser.py` | 格式與關聯模擬 |
| CQ Entry | Completion Queue in Host Memory | Logical Completion / CQ State | `amnv/queue_model.py`, `amnv/runner.py` | 邏輯模擬 |
| Interrupt | MSI / MSI-X / Polling | Python Result Return | `amnv/runner.py` | 不模擬 Interrupt |
| Host Validation | Driver / Validation Tool 判斷結果 | Validator / Test Checks | `amnv/validator.py`, `amnv/test_cases/*` | 直接實作 |
| Reset / Recovery | Controller Reset / Queue Re-init | Logical Queue Reset | `amnv/runner.py`, `amnv/queue_model.py` | 邏輯模擬 |
| Report | Validation Tool / Test System | PDF Evidence | `amnv/reporting/*` | 專案功能 |

---

## 5. Command Build 與 Test Scenario

### 5.1 真實 NVMe

在真實系統中，Application 或 Validation Tool 不會直接對 NAND 發出操作。

Command 通常經過：

```text
Application / Test Tool
→ OS / NVMe Driver
→ NVMe Command Structure
```

NVMe Command 會包含 Opcode、Namespace Identifier、LBA、Length、Data Pointer 等資訊。

### 5.2 AMNV

AMNV 由 Test Case 或 Automation Scenario 決定要執行什麼行為。

主要來源：

```text
amnv/test_cases/
amnv/automation/
```

實際 Command 建立則由：

```text
amnv/runner.py
```

處理。

AMNV 目前會保留 Validation 所需要的主要欄位，例如：

- CID
- Opcode
- NSID
- LBA
- Length
- Data
- Fault

這些欄位的目的，是讓 Validation Result 可以清楚追蹤「哪一筆 Command 發生了什麼事情」。

---

## 6. Submission Queue 與 CID

### 6.1 真實 NVMe

NVMe Submission Queue（SQ）通常建立在 Host Memory。

Host Driver：

1. 取得可用的 SQ Entry；
2. 填入 NVMe Command；
3. 指派 CID；
4. 更新 SQ Tail；
5. 寫入 SQ Tail Doorbell。

Controller 之後透過 PCIe / DMA 取得新的 Command。

### 6.2 AMNV

AMNV 使用：

```text
amnv/queue_model.py
```

維護邏輯 Queue State。

主要欄位：

```text
sq_head
sq_tail
cq_head
cq_tail
outstanding_cids
next_cid
```

CommandRunner 透過 QueueModel 完成：

```text
CID Allocation
→ SQ Submit
→ Outstanding CID Tracking
```

AMNV 並沒有建立真實 Host Memory Queue，也沒有實際 DMA。

其目的是保留足夠的 Queue State，讓 Test 能驗證：

- SQ 是否有進展；
- CQ 是否完成；
- Timeout 後 CID 是否仍 Outstanding；
- Reset 是否清空 Queue；
- Retry 是否使用新的 CID。

---

## 7. Doorbell

### 7.1 真實 NVMe

NVMe Doorbell 是 Host 透過 MMIO 寫入 Controller Register 的機制。

典型用途：

- SQ Tail Doorbell：通知 Controller 有新的 Submission；
- CQ Head Doorbell：通知 Controller Host 已消費 Completion。

Doorbell 是 Host 與 Controller Queue Synchronization 的重要部分。

### 7.2 AMNV

AMNV 不實作 MMIO Register。

它只保存 Doorbell 的邏輯語意與執行順序。

例如 Execution Trace 中可看到：

```text
SQ_SUBMIT
SQ_TAIL_DOORBELL
...
CQ_CONSUME
CQ_HEAD_DOORBELL
```

主要涉及：

```text
amnv/runner.py
amnv/queue_model.py
```

因此 AMNV 驗證的是：

> Doorbell 在 Command Lifecycle 中應該發生的時機與 Queue State 關係。

而不是：

> 真實 PCIe BAR Register 寫入行為。

---

## 8. PCIe Transport 與 DMA

### 8.1 真實 NVMe

在真實 NVMe SSD 中，Host 與 Controller 之間透過 PCIe 通訊。

典型行為可能包含：

- PCIe Transaction Layer Packet（TLP）
- MMIO Register Access
- DMA Read / Write
- PRP / SGL Data Description

Controller 可以透過 DMA 讀取：

- Submission Queue
- Host Data Buffer

並將 Completion 寫回 Host Memory。

### 8.2 AMNV

AMNV **不實作 PCIe Transport 或 DMA**。

Host / Controller 的邏輯邊界改由：

```text
amnv/runner.py
→ fake_nvme.py subprocess
```

表示。

也就是：

```text
真實系統：
Host ↔ PCIe ↔ Controller

AMNV：
CommandRunner ↔ Python subprocess ↔ Mock Controller
```

這個 subprocess boundary 的目的，是讓 AMNV 可以建立：

- 獨立 Controller Execution；
- Timeout；
- Process Termination；
- Host / Controller Responsibility Boundary。

它不代表 PCIe Packet 或 DMA Engine。

---

## 9. Mock Controller 與真實 Controller Firmware

### 9.1 真實 SSD Controller

真實 SSD Controller Firmware 通常需要處理：

- NVMe Command Parsing
- Queue Management
- Buffer Management
- FTL Request
- NAND Scheduling
- Error Handling
- Completion Generation
- Background Tasks

### 9.2 AMNV

AMNV 使用：

```text
fake_nvme.py
amnv/mock_controller.py
```

建立簡化的 Controller Behavior。

`fake_nvme.py` 是 subprocess entry point。

`mock_controller.py` 負責實際 Command Logic。

目前只處理專案 Validation 所需要的操作，例如：

- IDENTIFY
- SMART-style data
- READ
- WRITE
- Unsupported Command

因此 AMNV Mock Controller 主要回答的是：

> 「如果這個 Command 在這個 Scenario 下被執行，Validation 所需要的 Result 應該是什麼？」

它並不模擬真實 Controller Firmware Scheduler 或所有 NVMe Admin / I/O Command。

---

## 10. FTL、NAND 與 Mock Storage

### 10.1 真實 SSD

真實 WRITE 通常並不是：

```text
LBA → 直接寫 NAND 固定位置
```

Controller 會經過 FTL（Flash Translation Layer），並可能處理：

- LBA → Physical Page Mapping
- Garbage Collection
- Wear Leveling
- Bad Block Management
- ECC
- Write Amplification
- NAND Program / Read / Erase
- DRAM / SRAM Metadata

### 10.2 AMNV

AMNV 不實作 FTL。

Storage 使用：

```text
amnv/storage.py
data/mock_storage.json
data/mock_storage_seed.json
```

以 JSON 建立簡化的 Logical Block State。

概念為：

```text
LBA
→ MockStorage
→ Stored Pattern / Data
```

因此 AMNV 可以驗證：

- WRITE 是否更新指定 LBA；
- READ 是否取得預期 Data；
- Failed WRITE 是否保持 Storage Unchanged；
- Retry WRITE 是否成功；
- Reset Storage 是否恢復 deterministic baseline。

但 AMNV 不驗證：

- Physical Page Allocation
- NAND Timing
- Program / Erase Cycle
- ECC
- Garbage Collection
- Wear Leveling
- Real NAND Failure Mechanism

---

## 11. Fault Injection 對照

AMNV 的 Fault Injection 是 Validation-oriented。

主要由：

```text
amnv/fault_injector.py
```

提供。

### 11.1 Timeout

真實環境可能因：

- Controller Hang
- Firmware Deadlock
- PCIe Issue
- Long-running Operation
- Device Failure

造成 Host Timeout。

AMNV 不模擬實際原因。

它直接建立「Command 不在 Timeout Window 內正常完成」的情境，讓 Host-side Validation 驗證：

```text
TIMEOUT
→ Outstanding CID
→ Reset
→ Retry
```

### 11.2 NAND_READ_FAIL

真實 SSD 中可能來自：

- NAND Read Error
- ECC Uncorrectable
- Media Failure
- Internal Firmware Error

AMNV 將其抽象為：

```text
FAILED Completion
Error = NAND_READ_FAIL
```

並搭配 Firmware-style Log，讓 Test 驗證 Error Correlation。

### 11.3 NAND_PROGRAM_FAIL

真實 SSD 中可能與：

- NAND Program Failure
- Media Defect
- Internal Write Path Error

相關。

AMNV 的核心驗證重點是：

```text
WRITE fails
→ Storage remains unchanged
→ Error evidence exists
→ Reset
→ Retry WRITE
→ Readback verifies recovery
```

### 11.4 Miscompare

真實 Data Integrity Issue 可能來自多種來源。

AMNV 的 Miscompare Scenario 刻意建立：

```text
CQ Status = SUCCESS
Returned Data != Stored Data
```

用來驗證：

> Command-level SUCCESS 不代表 Data Integrity 一定正確。

因此 Validation Layer 必須另外比較 Data Content。

---

## 12. Completion Queue

### 12.1 真實 NVMe

Controller 完成 Command 後，會將 Completion Queue Entry 寫入 Host Memory。

CQE 通常包含：

- CID
- Status
- SQ Head
- Phase Tag
- 其他 Completion Metadata

Host 之後消費 Completion，更新 CQ Head。

### 12.2 AMNV

AMNV 使用：

```text
amnv/queue_model.py
amnv/runner.py
```

建立 logical Completion State。

正常流程包含：

```text
CONTROLLER_RESULT
→ CQ_POST
→ CQ_CONSUME
→ CQ_HEAD_DOORBELL
```

這讓 AMNV 可以驗證：

- Completion 是否對應正確 CID；
- Queue head / tail 是否合理；
- Outstanding CID 是否在 Completion 後被移除。

但 CQ 本身不是 Host Memory 中的真實 Ring Buffer。

---

## 13. Interrupt / Polling

### 13.1 真實 NVMe

Controller 完成 Command 後，Host 可能透過：

- MSI
- MSI-X
- Polling

得知 Completion 已產生。

### 13.2 AMNV

AMNV 不模擬 Interrupt Controller、MSI 或 MSI-X。

Controller Result 透過 Python subprocess result 回到 `CommandRunner`。

因此此處的對照是：

```text
真實：
CQ Completion
→ Interrupt / Polling
→ Host Handler

AMNV：
Mock Controller Result
→ CommandRunner
→ Logical Completion Processing
```

AMNV 保留的是 Completion Handling 的邏輯，不是 Interrupt Mechanism。

---

## 14. Firmware Log 對照

### 14.1 真實 SSD

Firmware Validation 常會搭配：

- Debug Log
- Error Log
- Trace
- Internal Event Record

協助判斷 Command Failure 的內部原因。

### 14.2 AMNV

AMNV 使用：

```text
logs/runtime_fw.log
amnv/log_parser.py
data/sample_fw.log
```

建立 Firmware-style Log Validation。

主要 Correlation Field：

- CID
- Opcode
- LBA
- Status
- Error

T07 主要驗證 Log Parsing。

T08、T09、A02 則把 Runtime Log 當作 Fault Evidence。

這部分的目的不是模擬某家 SSD Vendor 的 Firmware Log Format，而是展示：

> Validation Framework 如何將 Command Result 與 Firmware Evidence 做 Correlation。

---

## 15. Reset 與 Recovery

### 15.1 真實 NVMe

真實 Controller Reset 可能涉及：

- Controller Disable / Enable
- Queue Reinitialization
- Outstanding Command Cleanup
- Driver Recovery
- Namespace / Controller Re-discovery
- Firmware State Recovery

實際行為依 Controller、Driver 與 Reset 類型而不同。

### 15.2 AMNV

AMNV 使用：

```text
amnv/runner.py
amnv/queue_model.py
```

提供 logical controller reset。

Reset 會清除：

```text
sq_head
sq_tail
cq_head
cq_tail
outstanding_cids
```

但保留：

```text
next_cid
```

因此可以驗證：

```text
CID 1 timeout
→ reset
→ outstanding cleared
→ next_cid = 2
→ retry uses CID 2
```

這是 Validation-oriented Recovery Model。

不能將其解讀為完整模擬 NVMe Controller Reset Specification。

---

## 16. Host Validation

真實 Validation Tool 的工作不是只看 Controller 回傳 SUCCESS。

它還需要根據 Scenario 驗證：

- Status
- Error Code
- Data
- Timing
- Queue State
- Recovery
- Log Evidence

AMNV 使用：

```text
amnv/validator.py
amnv/test_cases/*
amnv/automation/*
```

完成這一層。

因此 AMNV 的真正核心價值不是「Mock Controller 能回資料」，而是：

```text
Scenario
→ Execute
→ Observe
→ Validate
→ Recover
→ Preserve Evidence
```

---

## 17. AMNV 有實作的概念

AMNV 實作或邏輯重建的主要概念包括：

- Host-side Command Construction
- CID Allocation
- Logical SQ / CQ State
- Outstanding Command Tracking
- Logical Doorbell Event
- Controller Execution Boundary
- Command Timeout
- Controller Error Completion
- Reset / Retry
- CID Progression
- Data Read / Write Validation
- Data Miscompare Detection
- Deterministic Fault Injection
- Firmware-style Log Correlation
- Structured Test Result
- Suite Automation
- Cooperative Cancellation
- PDF Evidence Generation

---

## 18. AMNV 未實作的真實 SSD 機制

以下項目不在 AMNV Implementation Scope：

- PCIe PHY
- PCIe Data Link Layer
- PCIe Transaction Layer Packet
- BAR / MMIO Register Behavior
- Real DMA
- PRP / SGL Data Movement
- MSI / MSI-X
- Real Host Driver
- Real NVMe Controller Registers
- Hardware Arbitration
- Real Firmware Scheduler
- FTL
- NAND Protocol
- NAND Page / Block Geometry
- ECC
- Wear Leveling
- Garbage Collection
- Bad Block Management
- Power Loss Protection
- Thermal / Performance Behavior
- Real Latency / Throughput Measurement

因此 AMNV 測試通過不能代表真實 SSD 在上述硬體或 Firmware Path 上也會通過。

---

## 19. 如何正確解讀 AMNV 的驗證結果

AMNV Result 應解讀為：

> 「在本專案建立的 deterministic Host-side logical model 中，指定 Scenario 的 Detection、Validation、Recovery 與 Evidence Handling 是否符合預期。」

不應解讀為：

> 「實際 NVMe SSD Firmware 已經被驗證完成。」

例如 T05 PASS 表示：

- Timeout 被正確辨識；
- Outstanding CID State 符合模型；
- Reset 清除 Queue State；
- CID progression 保留；
- Retry 使用新 CID；
- Retry 成功。

但它不代表：

- 真實 PCIe Device Reset 已驗證；
- 真實 Controller Firmware Reset Flow 已驗證；
- 真實 NVMe Driver Recovery 已驗證。

---

## 20. 專案展示時的定位

在 Demo 或面試時，AMNV 應被描述為：

> 一套用 Python 建立的 Host-side Logical NVMe Validation Automation Framework，透過 Mock Controller、Logical Queue Model、Deterministic Fault Injection 與 Structured Evidence，練習並展示 NVMe Validation Scenario Design、Automation、Failure Detection、Recovery 與 Reporting。

建議避免使用：

- Full NVMe Emulator
- SSD Firmware Emulator
- Real NAND Simulator
- PCIe Simulator

因為這些名稱會暗示本專案已實作實際不存在的硬體或 Firmware Layer。

---

# English Version

## 1. Document Purpose

This document explains the major Host-to-Controller execution flow of a real NVMe SSD and maps each stage to the logical simulation mechanism and Python files used by **Automation Mock NVMe Validation (AMNV)**.

The purpose is not to describe AMNV as a complete SSD emulator. Instead, the document clarifies:

1. the responsibility of each major stage in a real NVMe / SSD flow;
2. which logical concepts are preserved by AMNV;
3. which AMNV modules correspond to those concepts;
4. which PCIe, DMA, firmware, FTL, and NAND behaviors are not implemented;
5. how AMNV validation results should be interpreted.

AMNV is positioned as a:

> **Host-side Logical NVMe Validation Simulation**

and not as a:

> **Physical SSD / PCIe / NAND Emulator**

---

## 2. Mapping Principle

The comparison between a real NVMe SSD and AMNV should not be interpreted as a one-to-one mapping between a Python module and a physical hardware component.

AMNV uses **conceptual mapping**.

```text
Real NVMe behavior
→ Extract validation-relevant logical concept
→ Reconstruct an observable, controllable, deterministic Python mechanism
```

For example:

```text
Real system:
Host creates an SQ entry in Host Memory
→ updates an MMIO doorbell
→ controller fetches the command through PCIe / DMA

AMNV:
CommandRunner builds a command
→ QueueModel updates logical SQ state
→ records a logical doorbell event
→ starts a Mock Controller subprocess
```

The command-submission lifecycle is preserved conceptually, while PCIe transactions, MMIO registers, and DMA are not physically implemented.

---

## 3. Major Real NVMe SSD Data Flow

A typical high-level NVMe command flow can be summarized as:

```text
Application / Test Tool
→ Operating System / NVMe Driver
→ Build NVMe Command
→ Write Submission Queue Entry
→ Update SQ Tail Doorbell
→ SSD Controller Fetches Command
→ Controller Firmware Executes Command
→ Data Transfer / Media Operation
→ Write Completion Queue Entry
→ Interrupt or Polling
→ Host Consumes Completion
→ Update CQ Head Doorbell
```

Inside an SSD, additional paths may include:

```text
Controller Firmware
→ FTL
→ DRAM / SRAM Metadata
→ NAND Flash
→ ECC / Media Management
```

AMNV only models the portions that directly support its validation workflow.

---

## 4. High-Level Mapping Table

| Real NVMe / SSD Stage | Real-System Mechanism | AMNV Mapping | Main Files | Simulation Level |
| --- | --- | --- | --- | --- |
| Test / Workload | Application, Validation Tool | T01–T09, A01, A02 | `amnv/test_cases/*`, `amnv/automation/*` | Logical mapping |
| Command Build | NVMe Driver builds command | CommandRunner builds structured command | `amnv/runner.py` | Logical simulation |
| CID Allocation | Host assigns Command Identifier | QueueModel allocates `next_cid` | `amnv/queue_model.py` | Logical simulation |
| SQ Entry | Host-memory Submission Queue | SQ state / outstanding state | `amnv/queue_model.py` | Logical simulation |
| SQ Doorbell | MMIO register write | Logical doorbell trace event | `amnv/runner.py`, `amnv/queue_model.py` | Semantic only |
| PCIe Transport | PCIe TLP | Python subprocess boundary | `amnv/runner.py`, `fake_nvme.py` | PCIe not simulated |
| DMA Command Fetch | Controller DMA reads SQ | Logical controller fetch | `amnv/queue_model.py`, `amnv/runner.py` | Logical simulation |
| Controller Firmware | NVMe firmware command handler | Mock Controller logic | `fake_nvme.py`, `amnv/mock_controller.py` | Behavioral simulation |
| FTL / Media | FTL, NAND, ECC, GC | JSON mock storage | `amnv/storage.py`, `data/mock_storage*.json` | Highly simplified |
| Fault Behavior | Media / FW / timing fault | Deterministic fault injection | `amnv/fault_injector.py` | Validation-oriented |
| Firmware Log | Firmware debug / error log | Firmware-style runtime log | `logs/runtime_fw.log`, `amnv/log_parser.py` | Format/correlation simulation |
| CQ Entry | Completion Queue in Host Memory | Logical completion / CQ state | `amnv/queue_model.py`, `amnv/runner.py` | Logical simulation |
| Interrupt | MSI / MSI-X / Polling | Python result return | `amnv/runner.py` | Interrupt not simulated |
| Host Validation | Driver / validation tool evaluates result | Validator / test checks | `amnv/validator.py`, `amnv/test_cases/*` | Direct implementation |
| Reset / Recovery | Controller reset / queue re-init | Logical queue reset | `amnv/runner.py`, `amnv/queue_model.py` | Logical simulation |
| Report | Validation system | PDF evidence | `amnv/reporting/*` | Project function |

---

## 5. Command Build and Test Scenario

### 5.1 Real NVMe

In a real system, an application or validation tool does not directly operate NAND.

The command typically passes through:

```text
Application / Test Tool
→ OS / NVMe Driver
→ NVMe Command Structure
```

An NVMe command may contain opcode, namespace identifier, LBA, length, and data-pointer information.

### 5.2 AMNV

In AMNV, the test case or automation scenario determines the requested behavior.

Primary sources include:

```text
amnv/test_cases/
amnv/automation/
```

Actual command construction is coordinated by:

```text
amnv/runner.py
```

AMNV preserves validation-relevant fields such as:

- CID
- Opcode
- NSID
- LBA
- Length
- Data
- Fault

These fields allow the framework to trace what happened to a specific command.

---

## 6. Submission Queue and CID

### 6.1 Real NVMe

An NVMe Submission Queue is normally located in Host Memory.

The Host driver:

1. obtains an available SQ entry;
2. fills the NVMe command;
3. assigns a CID;
4. updates SQ Tail;
5. writes the SQ Tail Doorbell.

The controller later obtains the command through PCIe / DMA.

### 6.2 AMNV

AMNV uses:

```text
amnv/queue_model.py
```

to maintain logical queue state.

Tracked fields include:

```text
sq_head
sq_tail
cq_head
cq_tail
outstanding_cids
next_cid
```

The CommandRunner uses the queue model for:

```text
CID Allocation
→ SQ Submit
→ Outstanding CID Tracking
```

AMNV does not create a real Host Memory queue and does not perform DMA.

The model exists so tests can verify:

- SQ progression;
- CQ completion;
- outstanding CID after timeout;
- queue clearing after reset;
- retry using a new CID.

---

## 7. Doorbell

### 7.1 Real NVMe

NVMe doorbells are MMIO registers written by the Host.

Typical purposes include:

- SQ Tail Doorbell: notify the controller of new submissions;
- CQ Head Doorbell: notify the controller that completions have been consumed.

### 7.2 AMNV

AMNV does not implement MMIO registers.

It preserves only the logical event order and queue-state semantics.

Execution traces can include:

```text
SQ_SUBMIT
SQ_TAIL_DOORBELL
...
CQ_CONSUME
CQ_HEAD_DOORBELL
```

The main files are:

```text
amnv/runner.py
amnv/queue_model.py
```

AMNV therefore validates when the logical doorbell event occurs relative to queue state, not an actual PCIe BAR register write.

---

## 8. PCIe Transport and DMA

### 8.1 Real NVMe

Real NVMe Host/Controller communication uses PCIe.

Relevant mechanisms may include:

- PCIe Transaction Layer Packets
- MMIO register access
- DMA Read / Write
- PRP / SGL data descriptions

### 8.2 AMNV

AMNV does **not** implement PCIe transport or DMA.

The logical Host / Controller boundary is represented by:

```text
amnv/runner.py
→ fake_nvme.py subprocess
```

Conceptually:

```text
Real:
Host ↔ PCIe ↔ Controller

AMNV:
CommandRunner ↔ Python subprocess ↔ Mock Controller
```

The subprocess boundary enables:

- independent controller execution;
- timeout;
- process termination;
- separation of Host and Controller responsibilities.

It does not represent PCIe packets or a DMA engine.

---

## 9. Mock Controller and Real Controller Firmware

### 9.1 Real SSD Controller

Real SSD controller firmware may handle:

- NVMe command parsing
- queue management
- buffer management
- FTL requests
- NAND scheduling
- error handling
- completion generation
- background tasks

### 9.2 AMNV

AMNV uses:

```text
fake_nvme.py
amnv/mock_controller.py
```

to provide simplified controller behavior.

`fake_nvme.py` is the subprocess entry point.

`mock_controller.py` implements the command logic required by the project, including:

- IDENTIFY
- SMART-style data
- READ
- WRITE
- unsupported-command paths

The Mock Controller answers the validation-oriented question:

> Given this command and this scenario, what result should the validation framework observe?

It does not implement a real controller firmware scheduler or the complete NVMe command set.

---

## 10. FTL, NAND, and Mock Storage

### 10.1 Real SSD

A real WRITE is not simply:

```text
LBA → fixed NAND location
```

The controller may involve:

- LBA-to-physical-page mapping
- garbage collection
- wear leveling
- bad-block management
- ECC
- NAND program / read / erase
- DRAM / SRAM metadata

### 10.2 AMNV

AMNV does not implement an FTL.

Storage is modeled by:

```text
amnv/storage.py
data/mock_storage.json
data/mock_storage_seed.json
```

The simplified concept is:

```text
LBA
→ MockStorage
→ Stored Pattern / Data
```

AMNV can therefore validate:

- WRITE updates an LBA;
- READ returns expected data;
- failed WRITE preserves storage;
- retry WRITE succeeds;
- storage reset returns to a deterministic baseline.

It does not validate physical NAND behavior.

---

## 11. Fault Injection Mapping

AMNV fault injection is validation-oriented and is primarily implemented by:

```text
amnv/fault_injector.py
```

### 11.1 Timeout

A real timeout may be caused by controller hang, firmware deadlock, PCIe issues, long-running operations, or device failure.

AMNV does not simulate the physical cause.

It creates a condition in which the command does not complete normally within the timeout window so Host-side validation can verify:

```text
TIMEOUT
→ Outstanding CID
→ Reset
→ Retry
```

### 11.2 NAND_READ_FAIL

A real read failure may originate from media errors, ECC failure, or internal firmware issues.

AMNV abstracts this as:

```text
FAILED Completion
Error = NAND_READ_FAIL
```

and combines it with firmware-style log evidence.

### 11.3 NAND_PROGRAM_FAIL

AMNV focuses on validating:

```text
WRITE fails
→ Storage remains unchanged
→ Error evidence exists
→ Reset
→ Retry WRITE
→ Readback verifies recovery
```

### 11.4 Miscompare

AMNV deliberately creates:

```text
CQ Status = SUCCESS
Returned Data != Stored Data
```

to demonstrate that command-level SUCCESS does not guarantee data integrity.

The validation layer must independently compare returned data.

---

## 12. Completion Queue

### 12.1 Real NVMe

After a command completes, the controller writes a Completion Queue Entry into Host Memory.

A CQE normally contains information such as:

- CID
- Status
- SQ Head
- Phase Tag
- other completion metadata

### 12.2 AMNV

AMNV uses:

```text
amnv/queue_model.py
amnv/runner.py
```

to provide logical completion state.

A normal path includes:

```text
CONTROLLER_RESULT
→ CQ_POST
→ CQ_CONSUME
→ CQ_HEAD_DOORBELL
```

The model allows validation of:

- CID correspondence;
- queue head / tail progression;
- removal of completed CIDs from outstanding state.

The CQ is not a real Host Memory ring buffer.

---

## 13. Interrupt / Polling

### 13.1 Real NVMe

The Host may discover completion through:

- MSI
- MSI-X
- Polling

### 13.2 AMNV

AMNV does not simulate an interrupt controller, MSI, or MSI-X.

The Mock Controller result returns to `CommandRunner` through the Python subprocess result path.

The conceptual mapping is:

```text
Real:
CQ Completion
→ Interrupt / Polling
→ Host Handler

AMNV:
Mock Controller Result
→ CommandRunner
→ Logical Completion Processing
```

---

## 14. Firmware Log Mapping

### 14.1 Real SSD

Firmware validation frequently uses debug logs, error logs, traces, and internal event records to understand command failures.

### 14.2 AMNV

AMNV uses:

```text
logs/runtime_fw.log
amnv/log_parser.py
data/sample_fw.log
```

to provide firmware-style log validation.

Primary correlation fields are:

- CID
- Opcode
- LBA
- Status
- Error

T07 validates parsing.

T08, T09, and A02 use runtime logs as fault evidence.

The purpose is not to reproduce a vendor-specific firmware log format, but to demonstrate how a validation framework correlates command results with firmware evidence.

---

## 15. Reset and Recovery

### 15.1 Real NVMe

A real controller reset may involve:

- controller disable / enable;
- queue reinitialization;
- outstanding-command cleanup;
- driver recovery;
- controller / namespace rediscovery;
- firmware state recovery.

Actual behavior depends on the reset type, controller, and driver.

### 15.2 AMNV

AMNV uses:

```text
amnv/runner.py
amnv/queue_model.py
```

to provide a logical controller reset.

Reset clears:

```text
sq_head
sq_tail
cq_head
cq_tail
outstanding_cids
```

while preserving:

```text
next_cid
```

This enables validation of:

```text
CID 1 timeout
→ reset
→ outstanding cleared
→ next_cid = 2
→ retry uses CID 2
```

This is a validation-oriented recovery model rather than a complete implementation of NVMe reset semantics.

---

## 16. Host Validation

A real validation tool must inspect more than a controller SUCCESS status.

It may need to validate:

- status
- error code
- data
- timing
- queue state
- recovery
- log evidence

AMNV implements this layer through:

```text
amnv/validator.py
amnv/test_cases/*
amnv/automation/*
```

The central value of AMNV is therefore not simply that the Mock Controller can return data.

The validation workflow is:

```text
Scenario
→ Execute
→ Observe
→ Validate
→ Recover
→ Preserve Evidence
```

---

## 17. Concepts Implemented by AMNV

AMNV logically implements or reconstructs:

- Host-side command construction
- CID allocation
- logical SQ / CQ state
- outstanding-command tracking
- logical doorbell events
- controller execution boundary
- command timeout
- controller error completion
- reset / retry
- CID progression
- data read / write validation
- data-miscompare detection
- deterministic fault injection
- firmware-style log correlation
- structured test results
- suite automation
- cooperative cancellation
- PDF evidence generation

---

## 18. Real SSD Mechanisms Not Implemented by AMNV

The following are outside the AMNV implementation scope:

- PCIe PHY
- PCIe Data Link Layer
- PCIe Transaction Layer Packets
- BAR / MMIO register behavior
- real DMA
- PRP / SGL data movement
- MSI / MSI-X
- real Host driver
- real NVMe controller registers
- hardware arbitration
- real firmware scheduler
- FTL
- NAND protocol
- NAND page / block geometry
- ECC
- wear leveling
- garbage collection
- bad-block management
- power-loss protection
- thermal / performance behavior
- real latency / throughput measurement

A passing AMNV result therefore does not imply that a real SSD has passed validation on these hardware or firmware paths.

---

## 19. Correct Interpretation of AMNV Results

An AMNV result should be interpreted as:

> Within the deterministic Host-side logical model implemented by this project, did the specified scenario produce the expected detection, validation, recovery, and evidence-handling behavior?

It should not be interpreted as:

> Real NVMe SSD firmware has been fully validated.

For example, T05 PASS means that within the model:

- timeout was detected;
- outstanding CID state matched expectations;
- reset cleared logical queue state;
- CID progression was preserved;
- retry used a new CID;
- retry completed successfully.

It does not mean that a real PCIe device reset, controller firmware reset flow, or NVMe driver recovery path has been physically validated.

---

## 20. Recommended Project Positioning

During a demo or interview, AMNV should be described as:

> A Python-based Host-side Logical NVMe Validation Automation Framework that uses a Mock Controller, logical queue model, deterministic fault injection, and structured evidence to demonstrate NVMe validation scenario design, automation, failure detection, recovery, and reporting.

Terms such as the following should be avoided:

- Full NVMe Emulator
- SSD Firmware Emulator
- Real NAND Simulator
- PCIe Simulator

These names would imply hardware or firmware layers that the project does not implement.
