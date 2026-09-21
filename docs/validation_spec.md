# Automation Mock NVMe Validation — Validation Specification

## 1. Purpose

This document defines the validation rules, Mock Device behavior, logical NVMe queue model,
fault injection behavior, Test Situations, Automation Suites, recovery policies, storage model,
logging rules, and report requirements for the `automation-mock-nvme-validation` project.

The project is designed as an interview/demo validation framework that demonstrates:

- Python automated validation
- Mock device control
- Logical NVMe command execution
- SQ / CQ / Doorbell concepts
- Fault injection
- Failure analysis
- Recovery
- Data integrity validation
- Automated test execution
- PDF report generation

> The NVMe SQ / CQ / Doorbell implementation in this project is a logical simulation.
> It does not emulate real PCIe MMIO, DMA, PRP/SGL, MSI/MSI-X, SSD Controller Firmware,
> FTL, or physical NAND behavior.

---

# 2. Project Scope

The project covers:

- Mock NVMe device information
- Firmware Revision validation
- SMART / Health validation
- Logical Submission Queue (SQ)
- Logical Completion Queue (CQ)
- Logical Doorbell operation
- Read Command
- Write Command
- Sparse persistent storage
- Invalid I/O range handling
- Unsupported Command handling
- Command Timeout detection
- Data Miscompare detection
- Firmware-like error injection
- Firmware-like log parsing
- CID / LBA failure correlation
- Reset / Recovery / Retry
- Automated Full Validation Suite
- Automated Fault Injection Campaign
- PDF report generation

---

# 3. Mock Device Definition

Device definition file:

`data/mock_device.json`

Baseline device configuration:

| Item | Definition |
|---|---|
| Model | `MockNVMe-01` |
| Firmware Revision | `1.0.3` |
| Namespace ID | `1` |
| Capacity | `4096 Logical Blocks` |
| Logical Block Size | `512 Bytes` |
| Valid LBA Range | `0 ~ 4095` |
| Temperature | `35°C` |
| Maximum Temperature Threshold | `70°C` |
| Critical Warning Expected | `0` |
| Media Errors Expected | `0` |
| Percentage Used | `5%` |

The health thresholds defined by this project are Mock Validation thresholds and must not
be represented as mandatory NVMe specification requirements.

---

# 4. Mock Storage Model

Runtime storage:

`data/mock_storage.json`

Initial storage baseline:

`data/mock_storage_seed.json`

The storage model uses a sparse LBA representation.

Only LBAs containing explicit test data need to exist in the JSON file.

Example:

```text
LBA 100  → TEST_PATTERN_A
LBA 200  → OLD_PATTERN
LBA 400  → OLD_PATTERN
```

---

## 4.1 Unwritten LBA

A valid LBA that has not been explicitly written is defined as an **Unwritten LBA**.

Project-defined behavior:

```text
Valid LBA
+
No stored data
        ↓
Read
        ↓
Return 512 Bytes of 0x00
```

This is a Mock Project rule and does not represent guaranteed behavior of a real SSD.

---

## 4.2 Data Representation

Human-readable patterns are stored in JSON, for example:

```text
TEST_PATTERN_A
OLD_PATTERN
NEW_PATTERN
```

During implementation, the pattern may be encoded and zero-padded to one logical 512-byte block.

---

## 4.3 Storage Persistence

Successful Write operations update:

`data/mock_storage.json`

A subsequent independent Read must observe the written data.

Validation must be performed through the Read interface.

Tests must not directly inspect `mock_storage.json` and use that internal file access as the
final Readback validation result.

---

## 4.4 Reset Data

`Reset Data` performs:

```text
mock_storage_seed.json
        ↓
Copy
        ↓
mock_storage.json
```

This restores the entire Runtime Storage to the predefined baseline.

Storage Reset and Controller Reset are separate operations.

---

# 5. Logical NVMe Queue Model

The project implements a logical NVMe Queue Model.

---

## 5.1 SQ Entry

A Submission Queue Entry may contain:

- CID
- Opcode / Operation
- NSID
- LBA
- Length
- Data

---

## 5.2 CQ Entry

A Completion Queue Entry may contain:

- CID
- Status
- Error
- Returned Data when applicable

---

## 5.3 Queue Depth

| Queue | Depth |
|---|---:|
| Submission Queue | 4 |
| Completion Queue | 4 |

Queue Full / Queue Saturation testing is not included in the first project version.

---

## 5.4 Doorbell Model

Logical command flow:

```text
Host
 ↓
Create SQ Entry
 ↓
Update SQ Tail
 ↓
SQ Tail Doorbell
 ↓
Mock Controller Fetch
 ↓
Command Execution
 ↓
Create CQ Entry
 ↓
Host Consume CQ
 ↓
Update CQ Head
 ↓
CQ Head Doorbell
```

This is a logical model only.

No actual PCIe MMIO Doorbell registers are implemented.

---

# 6. Command Identifier (CID)

CID is local to an individual Test Situation or Automation Case.

Rules:

- CID starts at `1`.
- CID increments by `1` for each new command.
- Every independent Test starts from CID `1`.
- Every independent A02 Campaign Case starts from CID `1`.
- Controller Reset does not reset CID during the same Test.
- Retry must use a new CID.
- Re-running the same Test starts from CID `1` again.

Example T09:

```text
CID 001 → Initial Write → FAILED
CID 002 → Retry Write   → SUCCESS
CID 003 → Readback      → SUCCESS
```

For log and report identification:

```text
T09-CID001
T09-CID002

A02-FP03-C01-CID001
```

---

# 7. Supported Commands

Initial supported operations:

- Identify
- SMART / Health
- Read
- Write

Unsupported Commands may still be submitted as valid logical SQ Entries.

Example Unsupported Command:

`FORMAT`

The Mock Controller must reject the command and produce:

`UNSUPPORTED_COMMAND`

CLI syntax errors such as:

- Invalid numeric text
- Missing arguments
- Unknown option

are basic defensive input handling and are not formal Test Scenarios.

---

# 8. I/O Range Validation

Device capacity:

```text
4096 Logical Blocks
```

Valid LBA:

```text
0 ~ 4095
```

The Controller validates the requested LBA range before accessing storage.

Example:

```text
LBA    = 4095
Length = 2
```

The request exceeds the available capacity and must return:

`INVALID_RANGE`

An expected negative response is considered Test PASS when Actual matches Expected.

---

# 9. Command Timeout Definition

Command Completion Timeout:

`2.0 seconds`

Definition:

After the Host submits a command, if the corresponding CQ Entry is not available within
2 seconds, the command is classified as:

`TIMEOUT`

Timeout Fault behavior:

```text
SQ Submit
 ↓
Controller Fetch Command
 ↓
Fault Injection = Timeout
 ↓
No CQ Generated
 ↓
Host Wait
 ↓
Elapsed >= 2 sec
 ↓
TIMEOUT
```

Recommended timing source:

`time.monotonic()`

The 2-second timeout is a project/demo threshold and is not claimed as an NVMe Specification requirement.

---

# 10. Recovery Policy

Maximum Retry:

`1`

Controller Reset behavior:

- Clear outstanding commands
- Reinitialize SQ
- Reinitialize CQ
- Restore Controller state to READY
- Preserve Runtime Storage
- Preserve current Test CID progression

Controller Reset does not perform Storage Reset.

---

# 11. Fault Injection Rules

Fault Injection must be deterministic.

Random Fault Injection is not used.

Supported Faults:

- `timeout`
- `miscompare`
- `NAND_READ_FAIL`
- `NAND_PROGRAM_FAIL`

---

## 11.1 Timeout

Behavior:

```text
Command enters SQ
 ↓
Controller receives Command
 ↓
No CQ generated
 ↓
Host reaches timeout threshold
 ↓
TIMEOUT detected
```

---

## 11.2 Data Miscompare

Behavior:

```text
Storage contains correct data
 ↓
Controller reads correct data
 ↓
Fault Injection modifies Response Data
 ↓
CQ Status = SUCCESS
 ↓
Expected Data != Actual Data
 ↓
DATA_MISCOMPARE
```

The underlying Runtime Storage must remain unchanged.

---

## 11.3 NAND_READ_FAIL

Behavior:

- Read Command is accepted.
- CQ returns `FAILED`.
- Firmware-like Log is generated.
- Error is `NAND_READ_FAIL`.
- Storage is unchanged.

---

## 11.4 NAND_PROGRAM_FAIL

Behavior:

- Write Command is accepted.
- CQ returns `FAILED`.
- Firmware-like Log is generated.
- Error is `NAND_PROGRAM_FAIL`.
- Failed Write must not update Runtime Storage.
- Recovery may Reset and Retry once.

---

# 12. Firmware-like Log Definition

Sample log:

`data/sample_fw.log`

Required fields:

- Timestamp
- CID
- Opcode
- LBA
- Status
- Error

Example:

```text
2026-09-18 10:20:05 CID=005 OPCODE=READ LBA=300 STATUS=FAILED ERROR=NAND_READ_FAIL
```

Dynamic Firmware-like Logs used by T08 / T09 must follow the same field format.

---

# 13. Validation Result Principle

Test PASS / FAIL is based on:

```text
Expected Behavior
       vs
Actual Behavior
```

An operation-level error does not automatically mean Test FAIL.

Examples:

```text
Expected INVALID_RANGE
Actual   INVALID_RANGE
→ Test PASS
```

```text
Expected TIMEOUT
Actual   TIMEOUT
→ Test PASS
```

```text
Expected DATA_MISCOMPARE
Actual   DATA_MISCOMPARE
→ Test PASS
```

---

# 14. Scenario Catalog

| ID | Scenario | 類型 | Mock 行為 / 資料來源 | 核心驗證 |
|---|---|---|---|---|
| **S01** | Identify Command | Operation | 從 `mock_device.json` 回傳 Model、FW Revision、Namespace、Capacity | 能正確取得 Device 基本資訊 |
| **S02** | Firmware Revision Check | Validation | 比較 Identify 回傳 FW 與 Expected FW | Firmware Revision 是否符合預期 |
| **S03** | SMART / Health Check | Operation + Validation | 從 Mock Device Health Data 回傳健康資訊 | Health / Warning / Threshold 等欄位是否符合預期 |
| **S04** | Read Command | Operation | 依 LBA / Length 從 `mock_storage.json` 讀取資料；合法但未寫入區域回傳預設 `0x00` Data | Read Status、LBA、Length、Data 是否正確 |
| **S05** | Write Command | Operation | 依 LBA / Length 寫入 `mock_storage.json` 並保持跨 Process Persistence | Write 是否成功、資料是否真正保存 |
| **S06** | Invalid Range | Negative Condition | 根據 Capacity / Length Rule 判斷 LBA Range 是否超出有效範圍 | 合法格式但超界的 I/O 是否回傳 `INVALID_RANGE` |
| **S07** | Unsupported Command | Negative Condition | Command 正常建立 SQ Entry；Mock Controller 判定 Opcode 不支援，產生 CQ `UNSUPPORTED_COMMAND` | Controller 是否正確拒絕 Unsupported Command |
| **S08** | Command Timeout | Fault Condition | 明確注入 Timeout；Controller 取得 Command 後故意不產生對應 CQ | Host 是否在 2 秒後正確偵測 Command Timeout |
| **S09** | Data Miscompare | Fault Condition + Data Validation | Storage 原始資料不修改，但在 Read Response 注入錯誤 Data；CQ 仍可為 SUCCESS | CQ SUCCESS 情況下，Expected / Actual Data 不一致是否仍能被偵測 |
| **S10** | Firmware Error Injection | Fault Condition | 明確注入 Firmware-like Error，例如 `NAND_READ_FAIL`、`NAND_PROGRAM_FAIL` | 建立 deterministic、可重現的 Firmware Failure Condition |
| **S11** | Firmware Log Parsing | Analysis | 解析固定格式的 Firmware-like Log | 擷取 Timestamp、CID、Opcode、LBA、Status、Error |
| **S12** | CID / LBA Correlation | Failure Analysis | 使用 CID / LBA 關聯 SQ Command、CQ Completion 與 Firmware Log | 找出哪個 Command / LBA 對應該次 Failure |
| **S13** | Reset / Recovery | Recovery | Failure 後清除 Queue、Outstanding Command 與 Controller State；不清 Storage，必要時 Retry | Reset 後 Queue / Controller 是否恢復，Retry 是否能正常完成 |

---

# 15. Test Situation Matrix

| Test ID | Test Situation | 涵蓋 Scenario | 主要流程 / Condition | 驗證目標 |
|---|---|---|---|---|
| **T01** | **Device Baseline Check** | S01 + S02 + S03 | Identify → FW Revision Check → SMART / Health Check | Device Info、FW Revision、Health Data 是否符合 Expected / Threshold |
| **T02** | **Normal Write / Readback** | S05 + S04 | Write → SQ Submit → Controller → CQ SUCCESS → Storage Persist → Read → SQ/CQ → Data Compare | Write 後能透過獨立 Readback 取得相同資料，驗證 Mock Storage Persistence 與正常 I/O Flow |
| **T03** | **Invalid Read Range** | S04 + S06 | 提交格式合法的 Read，但 `LBA + Length` 超出 Capacity → Controller Range Check → CQ `INVALID_RANGE` | Controller 是否正確拒絕超界 I/O；Actual Error 是否符合 Expected |
| **T04** | **Unsupported Command** | S07 | Unsupported Opcode 建立 SQ Entry → Controller 判定不支援 → CQ `UNSUPPORTED_COMMAND` | Unsupported Command 是否在 Controller Layer 被正確拒絕並回傳預期 Completion Status |
| **T05** | **Read Timeout + Recovery** | S04 + S08 + S13 | Read → SQ Submit → Controller 不產 CQ → 2 秒 Timeout → Detect → Reset → Retry with New CID → CQ SUCCESS | Timeout 是否能被正確偵測；Reset 後 Queue / Controller 恢復，Retry Read 是否成功 |
| **T06** | **Data Integrity Failure** | S05 + S04 + S09 | Write Known Data → Read → Inject Miscompare into Response → CQ SUCCESS → Expected / Actual Compare | 即使 Command Completion 為 SUCCESS，Data Miscompare 是否仍能被 Validator 偵測 |
| **T07** | **Firmware Log Parsing** | S11 | 載入固定 `sample_fw.log` → Parse → Structured Result | 是否能正確擷取 Timestamp、CID、Opcode、LBA、Status、Error |
| **T08** | **Read Firmware Error + Correlation** | S04 + S10 + S11 + S12 | Read → Inject `NAND_READ_FAIL` → CQ FAILED → Firmware-like Log → Parse → CID / LBA Correlation | 能否將 Failed Read、SQ Command、CQ Completion、Firmware Log 正確關聯 |
| **T09** | **Write Failure + Recovery + Verification** | S05 + S10 + S11 + S12 + S13 | Precondition → Write → Inject `NAND_PROGRAM_FAIL` → CQ FAILED → Verify Storage Unchanged → Log Parse / Correlation → Reset → Retry Write → Readback | Failed Write 是否不污染 Storage；Failure 是否能正確分析；Reset / Retry 後 Write 與 Readback 是否恢復正常 |

---

# 16. Automation Suite A01 — Automated Full Validation Suite

Purpose:

Execute T01 through T09 sequentially as a complete Functional / Regression Validation Suite.

| Case ID | Execution Order | 執行 Test | Automation 行為 | Expected Result |
|---|---:|---|---|---|
| **A01-C01** | 1 | **T01 Device Baseline Check** | 執行 Identify、FW Revision、SMART / Health Validation | Device Info、FW Revision、Health 均符合 Expected / Threshold → PASS |
| **A01-C02** | 2 | **T02 Normal Write / Readback** | 執行正常 Write → Readback → Data Compare | Readback Data 與 Write Data 相同 → PASS |
| **A01-C03** | 3 | **T03 Invalid Read Range** | 提交超出 Capacity 的合法 Read Command | Actual = `INVALID_RANGE` → PASS |
| **A01-C04** | 4 | **T04 Unsupported Command** | 提交 Unsupported Opcode，由 Mock Controller 處理 | Actual = `UNSUPPORTED_COMMAND` → PASS |
| **A01-C05** | 5 | **T05 Read Timeout + Recovery** | 注入 Timeout → Detect → Reset → Retry | Timeout 正確偵測且 Retry Read 成功 → PASS |
| **A01-C06** | 6 | **T06 Data Integrity Failure** | Read Response 注入 Miscompare，執行 Data Validation | CQ SUCCESS，但 Miscompare 被正確偵測 → PASS |
| **A01-C07** | 7 | **T07 Firmware Log Parsing** | 載入固定 `sample_fw.log` 並執行 Parser | Required Fields 均正確解析 → PASS |
| **A01-C08** | 8 | **T08 Read Firmware Error + Correlation** | 注入 `NAND_READ_FAIL` → CQ FAILED → Parse → Correlation | SQ、CQ、Firmware Log 正確關聯 → PASS |
| **A01-C09** | 9 | **T09 Write Failure + Recovery + Verification** | 注入 `NAND_PROGRAM_FAIL` → Storage Verify → Correlation → Reset → Retry → Readback | Failed Write 未污染 Storage，Recovery 後正常 → PASS |

A01 rules:

- Fixed execution order: T01 → T09
- Individual Test FAIL does not stop the Suite
- All results must still be collected
- Suite PASS requires all Cases PASS
- PDF Report must always be generated after completion

---

# 17. Automation Suite A02 — Automated Fault Injection Campaign

Purpose:

Use a deterministic Data-driven Fault Matrix to validate:

- Fault Detection
- Failure Analysis
- Recovery
- Correlation
- Storage Integrity

across multiple Commands / LBAs.

| Case ID | Fault Profile | I/O Parameter | Test Condition / Expected Detection | Recovery Policy | Expected Result |
|---|---|---|---|---|---|
| **A02-FP01-C01** | Timeout | READ / LBA 0 / Len 1 | Valid unwritten LBA；注入 Timeout；2 秒內無 CQ，應判定 `TIMEOUT` | Reset + Retry once | Retry Read 成功，回傳 512 Bytes `0x00`；Storage 不變 |
| **A02-FP01-C02** | Timeout | READ / LBA 100 / Len 1 | LBA 100 = `TEST_PATTERN_A`；注入 Timeout；2 秒內無 CQ，應判定 `TIMEOUT` | Reset + Retry once | Retry Read 成功，Data = `TEST_PATTERN_A`；Storage 不變 |
| **A02-FP01-C03** | Timeout | WRITE / LBA 200 / Len 1 | LBA 200 = `OLD_PATTERN`，Target = `NEW_PATTERN`；注入 Timeout；第一次 Write 不得落盤 | Reset + Retry once + Readback | Timeout 後仍為 `OLD_PATTERN`；Retry 成功後 Readback = `NEW_PATTERN` |
| **A02-FP02-C01** | NAND Read Failure | READ / LBA 300 / Len 1 | Valid Known Data；注入 `NAND_READ_FAIL`；預期 CQ `FAILED` 並產生 Firmware-like Log | Log Parse + CID/LBA Correlation；No Retry | Error、CID、Opcode、LBA、CQ、Log 正確關聯；Storage 不變 |
| **A02-FP02-C02** | NAND Read Failure | READ / LBA 1500 / Len 1 | Valid Known Data；注入 `NAND_READ_FAIL`；預期 CQ `FAILED` 並產生 Firmware-like Log | Log Parse + CID/LBA Correlation；No Retry | 不同 LBA 下仍能正確完成 Failure Correlation；Storage 不變 |
| **A02-FP03-C01** | NAND Program Failure | WRITE / LBA 400 / Len 1 | LBA 400 = `OLD_PATTERN`，Target = `NEW_PATTERN`；注入 `NAND_PROGRAM_FAIL`；預期 CQ `FAILED` | Correlation → Reset → Retry once → Readback | Failed Write 後仍為 `OLD_PATTERN`；Retry 後 Readback = `NEW_PATTERN` |
| **A02-FP03-C02** | NAND Program Failure | WRITE / LBA 2000 / Len 1 | LBA 2000 = `OLD_PATTERN`，Target = `NEW_PATTERN`；注入 `NAND_PROGRAM_FAIL`；預期 CQ `FAILED` | Correlation → Reset → Retry once → Readback | 不同 LBA 下 Failure Protection、Recovery、Readback 均正確 |
| **A02-FP04-C01** | Data Miscompare | READ / LBA 500 / Len 1 | LBA 500 = `TEST_PATTERN_A`；注入 Miscompare；CQ 仍為 `SUCCESS`，但 Response Data 錯誤 | No Reset / No Retry | Validator 正確判定 `DATA_MISCOMPARE`；Storage 本身不變 |
| **A02-FP04-C02** | Data Miscompare | READ / LBA 2500 / Len 1 | LBA 2500 = `TEST_PATTERN_A`；注入 Miscompare；CQ 仍為 `SUCCESS`，但 Response Data 錯誤 | No Reset / No Retry | 不同 LBA 下均能偵測 Miscompare；Storage 本身不變 |

A02 rules:

```text
Execution Order:
FP01 → FP02 → FP03 → FP04
```

Additional rules:

- Case FAIL does not stop the Campaign.
- Every Case establishes its own Precondition.
- Fault Injection is deterministic.
- Random Fault Injection is not used.
- Campaign completion does not automatically Reset Storage.
- Runtime Storage final state remains available for `Read Current Data`.

---

# 18. PDF Report Definition

PDF Library:

`ReportLab`

Reports are generated only by:

- A01
- A02

Individual T01 ~ T09 executions do not automatically generate PDF Reports.

---

## 18.1 Report Directory

```text
reports/
├─ A01/
└─ A02/
```

---

## 18.2 Filename Rule

Format:

```text
<SuiteID>_<YYYYMMDD>_<HHMMSS>.pdf
```

Examples:

```text
A01_20260918_133600.pdf
A02_20260918_134215.pdf
```

Old Reports must not be overwritten.

---

## 18.3 Automatic Open

After A01 / A02 completes:

```text
Generate PDF
 ↓
Save PDF
 ↓
Console shows saved path
 ↓
Automatically open PDF
```

PySide6 may use:

`QDesktopServices.openUrl(...)`

---

## 18.4 Open Last Report

The GUI provides:

`Open Last Report`

This opens the most recently generated A01 or A02 report.

---

## 18.5 Report Contents

Suggested PDF sections:

1. Project / Environment
2. Mock Device Information
3. Validation Configuration
4. Suite Summary
5. Individual Case Results
6. SQ / CQ Statistics
7. Fault Injection Summary
8. Recovery Summary
9. Failure / Correlation Details
10. Final Suite Result

---

# 19. GUI Requirements

Framework:

`PySide6`

UI layout source:

`amnv/ui/main_window.ui`

Generated UI Python:

`amnv/ui/ui_main_window.py`

Application logic:

`amnv/ui/main_window.py`

---

## 19.1 Test Execution

The GUI provides individual Buttons for:

- T01
- T02
- T03
- T04
- T05
- T06
- T07
- T08
- T09
- A01
- A02

---

## 19.2 Control Functions

The GUI provides:

- Test Stop
- Read Current Data
- Reset Data
- Open Last Report

`Test Stop` applies to the currently executing Txx, A01, or A02 operation.

---

## 19.3 Console / Log Viewer

Console widget:

`QPlainTextEdit`

Requirements:

- Read Only
- No Wrap
- Vertical Scroll
- New Logs append downward
- Auto-scroll to latest output
- Maximum approximately 5000 lines
- User can manually scroll upward
- User can select and copy Log text

Console displays:

- System Status
- Host activity
- Subprocess activity
- Mock CLI output
- SQ
- CQ
- Controller behavior
- Fault Injection
- Recovery
- Validation
- PASS / FAIL
- Duration
- A01 / A02 progress
- Report output path
- Storage Query results

No separate Status Panel or Result Table is required.

---

## 19.4 Clear Console

`Clear Console` is located in the Console / Log Viewer Group.

It clears the GUI Console display only.

It does not delete Runtime Log files or Report files.

---

# 20. Mock CLI / Process Boundary

The project may expose:

`fake_nvme.py`

as an independently executable Mock NVMe CLI.

Main GUI execution concept:

```text
main.py / GUI
      ↓
runner.py
      ↓
subprocess
      ↓
fake_nvme.py
      ↓
Mock Controller
      ↓
Queue / Storage / Fault
```

Console may explicitly display process boundaries such as:

```text
[HOST]
[SUBPROCESS]
[MOCK-CLI]
[SQ]
[CTRL]
[CQ]
[FAULT]
[RECOVERY]
[VALIDATE]
[TEST]
```

This allows the demo to clearly show that the validation framework and the Mock CLI are
separate execution components.

---

# 21. Known Limitations

The project intentionally does not emulate:

- Real PCIe transport
- Real PCIe Endpoint behavior
- Real MMIO Doorbell registers
- DMA
- PRP
- SGL
- MSI
- MSI-X
- Real NVMe Controller Firmware
- Real NAND Flash
- NAND timing
- ECC
- Wear Leveling
- Garbage Collection
- Flash Translation Layer (FTL)
- Real SSD Firmware Qualification environment
- Queue Saturation / Queue Full behavior in the first version

The project demonstrates host-side automated validation concepts using a controlled logical
NVMe model and deterministic Fault Injection.