# 測試設計 / Test Design

# 中文版

## 1. 文件目的

本文件說明 **Automation Mock NVMe Validation（AMNV）** 中 T01～T09 的 Individual Validation Test 設計。

每個 Test Case 都以特定的 NVMe Host-side 驗證情境為中心，測試內容包含：

- 測試目標；
- 使用的 Command / Data / Fault；
- 前置條件；
- 執行流程；
- 主要 Validation Check；
- PASS 判定方式；
- 驗證機制與設計意義；
- 對應程式檔案。

本文件只描述 Individual Test Design。

A01 Full Validation 與 A02 Deterministic Fault Campaign 的 Suite / Campaign orchestration 會在後續 Automation Design 文件中獨立說明。

---

## 2. Test Design 原則

T01～T09 並不是單純確認 Mock Controller 是否能回傳資料，而是逐步建立完整的 Validation Coverage。

整體設計可分成五類：

| 類型 				| Test 			| 驗證重點 												|
| --- 				| --- 			| --- 													|
| Baseline 			| T01 			| Device identity / health baseline 					|
| Normal Path 		| T02 			| 正常 WRITE / READ / data verification 					|
| Negative Command 	| T03、T04 		| Invalid parameter / unsupported command handling 		|
| Fault / Recovery 	| T05、T09 		| Timeout、program failure、reset、retry 					|
| Data / Evidence 	| T06、T07、T08 	| Miscompare detection、log parsing、error correlation 	|

共同原則如下。

### 2.1 Expected Behavior 必須明確

每個 Test 都先定義預期結果，再執行 Command。

Test 不以「程式沒有 crash」作為 PASS，而是比較：

```text
Expected
vs
Actual
```

### 2.2 Command Status 與 Data Validation 分開

`SUCCESS` 只代表 Command-level completion 成功。

例如 T06 刻意建立：

```text
Completion Status = SUCCESS
Data = Incorrect
```

用來證明 Data Integrity 必須另外驗證。

### 2.3 Failure Detection 與 Recovery 分開

有些 Test 只驗證 Detection，例如 T03、T04、T08。

有些 Test 會繼續驗證 Recovery，例如 T05、T09。

### 2.4 Evidence 必須保留

TestResult 除了最終 PASS / FAIL，也保留：

- Command Result；
- Validation Checks；
- Queue State；
- Firmware-style Log；
- Reset / Retry State；
- Abort / Cancellation Information。

### 2.5 Test 必須可獨立執行

T01～T09 都可以由 GUI 單獨執行，也可以由 A01 呼叫。

因此 Individual Test 不依賴 A01 才能成立。

---

# 3. T01 — Device Baseline Check

## 3.1 測試目標

T01 用來確認 Mock Device 的基本 Identity 與 Health Data 是否符合 Validation Configuration。

這是整套驗證流程的 Baseline Test。

如果 Device Identity 或基本 Health State 不符合預期，後續 I/O Validation 的測試基礎就不可信。

## 3.2 主要檔案

```text
amnv/test_cases/t01_device_baseline.py
amnv/runner.py
amnv/mock_controller.py
amnv/validator.py
config/validation_config.json
data/mock_device.json
```

## 3.3 Command

T01 執行兩個 Command：

```text
IDENTIFY
SMART
```

## 3.4 驗證流程

```text
Load Validation Configuration
→ Execute IDENTIFY
→ Validate Completion
→ Validate Device Identity
→ Execute SMART
→ Validate Completion
→ Validate Health Data
→ Build TestResult
```

## 3.5 IDENTIFY Validation

主要驗證：

| Check | 預期 |
| --- | --- |
| Completion Status | `SUCCESS` |
| Model | `MockNVMe-01` |
| Firmware Revision | `1.0.3` |
| NSID | `1` |
| Capacity Blocks | `4096` |
| Logical Block Size | `512` bytes |

這些值來自 Validation Configuration，Test 不應只確認欄位存在，而是確認實際值符合預期 Baseline。

## 3.6 SMART / Health Validation

主要驗證：

| Check | 預期 |
| --- | --- |
| Completion Status | `SUCCESS` |
| Temperature | `<= 70°C` |
| Critical Warning | `0` |
| Media Errors | `0` |

Temperature 使用 Maximum Threshold，而不是要求固定溫度。

其餘 Health State 則要求符合預期正常狀態。

## 3.7 PASS 條件

T01 共有兩段驗證：

```text
IDENTIFY Validation
+
SMART / Health Validation
```

所有 Validation Check 都通過時：

```text
T01 = PASS
```

任何一項 Identity、Capacity、Block Size 或 Health Check 不符合預期：

```text
T01 = FAIL
```

## 3.8 設計意義

T01 對應真實 SSD Validation 中常見的 Baseline Verification：

- 確認測試對象；
- 確認 Firmware Revision；
- 確認 Namespace / Capacity；
- 確認基本 Health State。

在 AMNV 中不代表真實 NVMe Identify Controller / SMART Log Page 的完整規格驗證，而是保留 Baseline Validation 的核心概念。

---

# 4. T02 — Normal Write / Readback

## 4.1 測試目標

T02 驗證最基本的正常 I/O Path：

```text
WRITE
→ READ
→ Compare Data
```

測試重點是確認正常 WRITE 可以更新 Mock Storage，後續 READ 可以從相同 LBA 讀回相同資料。

## 4.2 主要檔案

```text
amnv/test_cases/t02_write_readback.py
amnv/runner.py
amnv/storage.py
amnv/validator.py
```

## 4.3 測試資料

```text
LBA = 600
Length = 1
Pattern = T02_WRITE_READBACK
```

## 4.4 執行流程

```text
WRITE LBA 600
Data = T02_WRITE_READBACK
→ Validate WRITE Completion
→ READ LBA 600
→ Validate READ Completion
→ Compare LBA / Length / Data
→ Build TestResult
```

## 4.5 Validation Checks

主要驗證：

| Check | 預期 |
| --- | --- |
| WRITE Completion | `SUCCESS` |
| READ Completion | `SUCCESS` |
| Readback LBA | `600` |
| Readback Length | `1` |
| Readback Data | `T02_WRITE_READBACK` |
| Unwritten Flag | `false` |

## 4.6 PASS 條件

WRITE 與 READ 都必須正常完成，而且 Readback Data 必須完全符合原始寫入資料。

因此：

```text
WRITE SUCCESS
AND
READ SUCCESS
AND
Readback Data Match
= PASS
```

## 4.7 設計意義

T02 建立後續 Fault Test 的 Normal Path Baseline。

如果正常 WRITE / READ 本身不可靠，就無法合理判斷後面的 Timeout、Miscompare、Program Failure 是否被正確處理。

---

# 5. T03 — Invalid Read Range

## 5.1 測試目標

T03 驗證 Host 發出超出 Mock Device Capacity 的 READ 時，Controller 是否能正確拒絕該 Command。

這是一個 Negative Parameter Validation。

## 5.2 主要檔案

```text
amnv/test_cases/t03_invalid_read_range.py
amnv/runner.py
amnv/mock_controller.py
amnv/storage.py
amnv/validator.py
```

## 5.3 測試條件

Mock Device Capacity：

```text
4096 blocks
Valid LBA = 0 ~ 4095
```

測試 Command：

```text
READ
LBA = 4095
Length = 2
```

這代表要求存取：

```text
LBA 4095
LBA 4096
```

其中 LBA 4096 已超出有效範圍。

## 5.4 執行流程

```text
Submit READ LBA 4095 Length 2
→ Mock Controller performs range validation
→ Reject command
→ Return INVALID_RANGE
→ Host validates error completion
```

## 5.5 Validation Checks

| Check | 預期 |
| --- | --- |
| Completion Status | `INVALID_RANGE` |
| Completion Error | `INVALID_RANGE` |
| Completion Data | `None` |
| Timed Out | `false` |

## 5.6 PASS 條件

PASS 的條件不是 Command 成功，而是：

> Invalid Command 被正確拒絕。

因此：

```text
Expected Error Observed
= PASS
```

如果 Command 被錯誤接受，或變成 Timeout / Unexpected Error，則 Test FAIL。

## 5.7 設計意義

T03 用來展示 Validation 中的重要觀念：

> Negative Test 的 PASS，不代表 Command SUCCESS；而是系統正確地產生預期 Failure Behavior。

---

# 6. T04 — Unsupported Command

## 6.1 測試目標

T04 驗證 Mock Controller 收到未支援 Opcode 時，是否回傳明確的 Unsupported Command Error，而不是 crash、timeout 或產生不確定結果。

## 6.2 主要檔案

```text
amnv/test_cases/t04_unsupported_command.py
amnv/runner.py
amnv/mock_controller.py
amnv/validator.py
```

## 6.3 測試 Command

```text
Opcode = FORMAT
```

AMNV 目前沒有實作 FORMAT Command，因此這個 Opcode 被刻意用來測試 Unsupported Command Path。

## 6.4 執行流程

```text
Submit FORMAT
→ Mock Controller checks opcode
→ Opcode not supported
→ Return UNSUPPORTED_COMMAND
→ Host validates result
```

## 6.5 Validation Checks

| Check | 預期 |
| --- | --- |
| Completion Status | `UNSUPPORTED_COMMAND` |
| Completion Error | `UNSUPPORTED_COMMAND` |
| Completion Data | `None` |
| Timed Out | `false` |
| Submitted Opcode | `FORMAT` |

## 6.6 PASS 條件

只有在 Controller 明確拒絕 FORMAT，而且回傳預期 Error Behavior 時才 PASS。

## 6.7 設計意義

這個 Test 驗證錯誤 Command Path 是否具備：

- 明確 Error Classification；
- 可預測的 Host Result；
- 不產生 Timeout；
- 不使 Controller Process 異常崩潰。

---

# 7. T05 — Read Timeout + Recovery

## 7.1 測試目標

T05 是 AMNV 最重要的 Recovery Test 之一。

它驗證：

```text
READ Timeout
→ Outstanding CID remains
→ Controller Reset
→ Queue cleared
→ CID progression preserved
→ Retry READ
→ Successful recovery
```

此 Test 不只確認 Timeout Detection，也確認 Timeout 後的 Recovery State。

## 7.2 主要檔案

```text
amnv/test_cases/t05_read_timeout_recovery.py
amnv/runner.py
amnv/queue_model.py
amnv/cancellation.py
amnv/validator.py
```

## 7.3 測試條件

Initial Command：

```text
READ
LBA = 100
Fault = timeout
```

Baseline Data：

```text
TEST_PATTERN_A
```

## 7.4 第一階段 — Timeout

Command 使用第一個 CID：

```text
CID 1
```

Fault Injection 讓 Command 無法在 Host Timeout Window 內正常完成。

Expected：

```text
Host Status = TIMEOUT
Timed Out = true
Completion = None
Controller Result = None
Outstanding CID = [1]
SQ = [1, 1]
CQ = [0, 0]
next_cid = 2
```

這裡的重要設計是：

> Timeout 不等於正常 Completion Failure。

因此 Timeout 時不建立正常 CQ Completion，CID 仍維持 Outstanding。

## 7.5 第二階段 — Controller Reset

Timeout 後執行 logical Controller Reset。

Expected：

```text
SQ = [0, 0]
CQ = [0, 0]
Outstanding CID = []
next_cid = 2
```

Reset 清除 Queue / Outstanding State，但不回收或重複使用已配置過的 CID。

## 7.6 第三階段 — Retry

Retry READ：

```text
READ LBA 100
Fault = None
CID = 2
```

Expected：

```text
Completion Status = SUCCESS
Readback LBA = 100
Readback Data = TEST_PATTERN_A
Timed Out = false
```

Final Queue：

```text
SQ = [1, 1]
CQ = [1, 1]
Outstanding CID = []
next_cid = 3
```

## 7.7 主要 Validation Checks

T05 驗證的重點包括：

- Initial CID；
- Host Timeout Status；
- Timed Out flag；
- Timeout Completion 必須為 None；
- Timeout Controller Result 必須為 None；
- Outstanding CID after timeout；
- SQ / CQ state after timeout；
- next CID after timeout；
- Reset SQ / CQ；
- Outstanding CID cleared；
- CID preserved across reset；
- Retry Completion；
- Retry CID；
- Retry Data；
- Final Queue State；
- Final next CID。

## 7.8 PASS 條件

T05 必須完整通過：

```text
Timeout Detection
+
Timeout Queue State
+
Controller Reset
+
CID Preservation
+
Retry Success
+
Final Queue State
```

其中任何 Recovery State 不符合預期，都不能判定為 PASS。

## 7.9 設計意義

T05 展示 AMNV 不只測「Command 是否失敗」，而是測完整 Recovery Lifecycle。

這也是本專案用 QueueModel 與 CID Progression 的主要理由之一。

---

# 8. T06 — Data Integrity Failure

## 8.1 測試目標

T06 驗證一個重要情境：

```text
Command Completion = SUCCESS
但
Returned Data != Expected Data
```

目的是證明：

> Completion SUCCESS 不等於 Data Integrity PASS。

## 8.2 主要檔案

```text
amnv/test_cases/t06_data_integrity_failure.py
amnv/runner.py
amnv/fault_injector.py
amnv/storage.py
amnv/validator.py
```

## 8.3 測試資料

```text
LBA = 700
Expected Pattern = T06_EXPECTED_DATA
```

## 8.4 執行流程

第一步先建立正確 Baseline：

```text
WRITE LBA 700
Data = T06_EXPECTED_DATA
→ SUCCESS
```

第二步使用 Miscompare Fault：

```text
READ LBA 700
Fault = miscompare
→ Completion = SUCCESS
→ Returned Data = TEST_PATTERN_B
```

第三步再執行 Normal READ：

```text
READ LBA 700
Fault = None
→ Returned Data = T06_EXPECTED_DATA
```

## 8.5 Validation Checks

主要驗證：

| Check | 預期 |
| --- | --- |
| Initial WRITE | `SUCCESS` |
| Fault READ Completion | `SUCCESS` |
| Fault READ LBA | `700` |
| Returned Data | `!= T06_EXPECTED_DATA` |
| Timed Out | `false` |
| Verification READ | `SUCCESS` |
| Stored Data | `T06_EXPECTED_DATA` |
| Stored Data LBA | `700` |

## 8.6 PASS 條件

Test PASS 的必要條件：

1. Fault READ 必須仍然是 Command-level `SUCCESS`；
2. Validator 必須偵測 Data Miscompare；
3. Miscompare 只能影響 Returned Data；
4. Mock Storage 原始資料必須保持正確。

## 8.7 設計意義

T06 將：

```text
Command Status Validation
```

與：

```text
Data Integrity Validation
```

明確分開。

這是 Storage Validation 中非常重要的觀念。

---

# 9. T07 — Firmware Log Parsing

## 9.1 測試目標

T07 不執行 I/O Fault，而是單獨驗證 Firmware-style Log Parser。

目的是先確認 Parser 可以正確把文字 Log 轉換為 Structured Data，再讓 T08、T09 使用 Runtime Log 做 Error Correlation。

## 9.2 主要檔案

```text
amnv/test_cases/t07_firmware_log_parsing.py
amnv/log_parser.py
data/sample_fw.log
amnv/validator.py
```

## 9.3 測試資料

來源：

```text
data/sample_fw.log
```

Sample Log 預期包含：

```text
10 entries
```

每筆 Entry 需要能解析：

- Timestamp
- CID
- Opcode
- LBA
- Status
- Error

## 9.4 執行流程

```text
Load sample_fw.log
→ Parse each line
→ Build structured entries
→ Validate entry count
→ Validate required fields
→ Query known CID / LBA records
→ Validate parsed values
```

## 9.5 Validation Checks

總共驗證 10 個主要項目：

| Check | 預期 |
| --- | --- |
| Parsed Entry Count | `10` |
| Required Fields Present | `true` |
| CID 5 Entry Count | `1` |
| CID 5 Opcode | `READ` |
| CID 5 LBA | `300` |
| CID 5 Status | `FAILED` |
| CID 5 Error | `NAND_READ_FAIL` |
| LBA 2000 Entry Count | `1` |
| LBA 2000 Opcode | `WRITE` |
| LBA 2000 Error | `NAND_PROGRAM_FAIL` |

## 9.6 PASS 條件

Parser 必須：

- 解析正確數量；
- 保留必要欄位；
- 讓 CID / LBA 查詢得到正確 Entry；
- 正確解析 Status / Error。

## 9.7 設計意義

T07 是後續 Error Correlation Test 的基礎。

它刻意把：

```text
Parser correctness
```

與：

```text
Runtime fault correlation
```

拆開驗證。

這樣 T08 / T09 失敗時，可以區分問題來自：

- Fault / Runtime Log；
或
- Parser 本身。

---

# 10. T08 — Read Error Correlation

## 10.1 測試目標

T08 驗證 READ Command 發生 `NAND_READ_FAIL` 時：

1. Host 收到正確 Failure Completion；
2. Runtime Firmware-style Log 產生對應 Error Entry；
3. Command Result 可以和 Log 依 CID / LBA / Opcode / Status / Error 正確 Correlation。

## 10.2 主要檔案

```text
amnv/test_cases/t08_read_error_correlation.py
amnv/runner.py
amnv/fault_injector.py
amnv/log_parser.py
logs/runtime_fw.log
amnv/validator.py
```

## 10.3 測試條件

```text
READ
LBA = 300
Fault = NAND_READ_FAIL
```

## 10.4 執行流程

```text
Clear / prepare runtime log
→ Execute READ with NAND_READ_FAIL
→ Receive FAILED completion
→ Parse runtime firmware log
→ Search by CID
→ Search by LBA
→ Compare command and log fields
→ Build TestResult
```

## 10.5 Completion Validation

Expected：

| Check | 預期 |
| --- | --- |
| Completion Status | `FAILED` |
| Completion Error | `NAND_READ_FAIL` |
| Completion Data | `None` |
| Timed Out | `false` |

這表示 T08 測的是 Controller Error Completion，不是 Timeout。

## 10.6 Log Correlation Validation

Expected：

| Check | 預期 |
| --- | --- |
| Runtime Log Entry Count | `1` |
| CID Correlation Count | `1` |
| LBA Correlation Count | `1` |
| Log CID | 與 Command CID 相同 |
| Log Opcode | `READ` |
| Log LBA | `300` |
| Log Status | `FAILED` |
| Log Error | `NAND_READ_FAIL` |

## 10.7 PASS 條件

只有 Failure Completion 與 Firmware Log Evidence 同時吻合時才 PASS：

```text
FAILED Completion
+
Correct Error
+
Correct Runtime Log
+
CID / LBA / Opcode / Status / Error Correlation
= PASS
```

## 10.8 設計意義

真實 Firmware Validation 不會只看 Host Error。

工程師通常還需要利用 Firmware Trace / Log 確認錯誤來源。

T08 用簡化模型展示這種：

```text
Host Evidence
↔
Firmware Evidence
```

的 Correlation Workflow。

---

# 11. T09 — Write Failure + Recovery

## 11.1 測試目標

T09 是最完整的 WRITE Error Recovery Scenario。

它驗證：

```text
NAND_PROGRAM_FAIL
→ Failed WRITE
→ Firmware Log Correlation
→ Old Data Preserved
→ Controller Reset
→ Retry WRITE
→ READ Back
→ New Data Verified
```

## 11.2 主要檔案

```text
amnv/test_cases/t09_write_failure_recovery.py
amnv/runner.py
amnv/queue_model.py
amnv/fault_injector.py
amnv/storage.py
amnv/log_parser.py
logs/runtime_fw.log
amnv/validator.py
```

## 11.3 測試資料

```text
LBA = 400
Old Pattern = OLD_PATTERN
New Pattern = T09_RECOVERED_DATA
Fault = NAND_PROGRAM_FAIL
```

## 11.4 第一階段 — Failed WRITE

Initial WRITE：

```text
CID 1
WRITE LBA 400
Data = T09_RECOVERED_DATA
Fault = NAND_PROGRAM_FAIL
```

Expected：

```text
Completion Status = FAILED
Error = NAND_PROGRAM_FAIL
Data = None
Timed Out = false
```

這是 Error Completion，不是 Timeout。

## 11.5 第二階段 — Firmware Log Correlation

Runtime Log 必須記錄這筆 Failure。

主要驗證：

- Log Entry Count；
- CID；
- Opcode = WRITE；
- LBA = 400；
- Status = FAILED；
- Error = NAND_PROGRAM_FAIL。

## 11.6 第三階段 — Storage Protection

Failed WRITE 後執行正常 READ 驗證舊資料。

Expected：

```text
CID 2
READ LBA 400
Data = OLD_PATTERN
```

這代表 Failed Program 不應將錯誤的新資料寫入 Storage。

因此：

```text
Failed WRITE
→ Old Data remains intact
```

是 T09 的重要 Validation Point。

## 11.7 第四階段 — Controller Reset

在 Failed WRITE 與 Verification READ 後執行 Controller Reset。

Reset 清除：

- SQ；
- CQ；
- Outstanding CID。

但保持 CID progression。

此時：

```text
next_cid = 3
```

## 11.8 第五階段 — Retry WRITE

Retry：

```text
CID 3
WRITE LBA 400
Data = T09_RECOVERED_DATA
Fault = None
```

Expected：

```text
Completion Status = SUCCESS
```

## 11.9 第六階段 — Final Readback

最後：

```text
CID 4
READ LBA 400
```

Expected：

```text
Data = T09_RECOVERED_DATA
```

Final Queue Expected：

```text
SQ = [2, 2]
CQ = [2, 2]
Outstanding = []
next_cid = 5
```

注意：

Reset 後 Queue Counter 被清零，因此 Final Queue 的 2 / 2 代表 Reset 後執行了兩筆正常 Command：

```text
Retry WRITE
+
Final READ
```

## 11.10 主要 Validation Checks

T09 包含較多 Check，核心可以分為五組：

### Failure Detection

- Completion = FAILED；
- CID = 1；
- Error = NAND_PROGRAM_FAIL；
- Data = None；
- Timed Out = false。

### Firmware Log Correlation

- Log CID；
- Opcode；
- LBA；
- Status；
- Error。

### Storage Protection

- Verification READ 成功；
- Old Data 仍為 `OLD_PATTERN`。

### Reset / CID

- Queue 清除；
- Outstanding 清除；
- `next_cid = 3`；
- CID progression 保留。

### Retry / Final Readback

- Retry WRITE CID = 3；
- Retry WRITE = SUCCESS；
- Final READ CID = 4；
- Data = `T09_RECOVERED_DATA`；
- Final Queue State 正確。

## 11.11 PASS 條件

T09 必須同時驗證成功：

```text
Failure Detection
+
Log Correlation
+
Old Data Preservation
+
Reset
+
CID Preservation
+
Retry WRITE
+
Final Readback
+
Final Queue State
```

不能只因 Retry 最後成功就判定整個 Test PASS。

## 11.12 設計意義

T09 將多個 Validation 技術整合在同一個 Scenario：

- Fault Injection；
- Error Completion；
- Firmware Log Evidence；
- Data Protection；
- Queue / CID State；
- Controller Reset；
- Retry；
- Final Data Integrity。

因此它比單純的 WRITE Failure Test 更接近完整的 Recovery Validation。

---

# 12. T01～T09 Coverage Summary

| Test | Positive / Negative | Command / Mechanism | Fault | Recovery | Log | Data Integrity |
| --- | --- | --- | --- | --- | --- | --- |
| T01 | Positive | IDENTIFY / SMART | No | No | No | Baseline |
| T02 | Positive | WRITE / READ | No | No | No | Yes |
| T03 | Negative | READ invalid range | Invalid parameter | No | No | No |
| T04 | Negative | Unsupported FORMAT | Unsupported opcode | No | No | No |
| T05 | Negative + Recovery | READ | Timeout | Reset + Retry | No | Readback |
| T06 | Negative | WRITE / READ | Miscompare | No | No | Yes |
| T07 | Parser Validation | Log Parser | Static log cases | No | Yes | No |
| T08 | Negative + Evidence | READ | NAND_READ_FAIL | No retry | Yes | No |
| T09 | Negative + Recovery | WRITE / READ | NAND_PROGRAM_FAIL | Reset + Retry | Yes | Yes |

這九個 Test 合起來形成 AMNV A01 Full Validation 的基本 Regression Coverage。

---

# 13. Result 判定

Individual Test 的正常結果包含：

```text
PASS
FAIL
ERROR
ABORTED
```

A01 中尚未開始執行的 Test 另外可能被標記為：

```text
NOT_RUN
```

### PASS

所有 Test-defined Validation Checks 通過。

### FAIL

Test 正常執行完成，但一個或多個 Expected / Actual Check 不符合。

### ERROR

執行期間發生非預期 Exception，無法按照 Test Design 完成判定。

### ABORTED

使用者提出 Stop Request，而且 Test 在完成前被 cooperative cancellation 中止。

### NOT_RUN

主要用於 Suite Execution。

代表因 Suite Stop 等原因，該 Test 尚未開始執行。

---

# 14. Cancellation 與 Test Design

T01～T09 的最終版本支援 Individual Stop。

Cancellation 使用共享的：

```text
CancellationToken
```

Test 會在適當執行點檢查 Stop State。

如果 Stop 發生在 active subprocess：

```text
Cancellation Requested
→ terminate subprocess
→ grace period
→ kill if required
→ logical reset
→ Test = ABORTED
```

Cancellation 不應被記錄成：

```text
FAIL
```

因為 User Abort 與 Functional Validation Failure 是不同事件。

STOP v1 的完整設計會在獨立文件中說明。

---

# 15. Test Design Boundary

T01～T09 驗證的是 AMNV Logical Model。

它們沒有驗證：

- 真實 PCIe Transport；
- 真實 MMIO Register；
- 真實 DMA；
- PRP / SGL；
- MSI / MSI-X；
- 真實 NVMe Driver；
- 真實 Controller Firmware；
- FTL；
- NAND Timing / ECC / Wear；
- 真實 Performance。

因此 Individual Test PASS 應解讀為：

> 在 AMNV 的 Host-side logical validation model 中，該 Scenario 的 Expected Behavior、Detection、Recovery 與 Evidence 符合設計。

---

# English Version

## 1. Document Purpose

This document describes the design of the T01–T09 individual validation tests in **Automation Mock NVMe Validation (AMNV)**.

Each test focuses on a specific Host-side NVMe validation scenario and defines:

- validation objective;
- commands, data, and faults used;
- preconditions;
- execution flow;
- validation checks;
- PASS criteria;
- validation mechanism and engineering purpose;
- related implementation files.

This document focuses only on individual test design.

A01 Full Validation and A02 Deterministic Fault Campaign orchestration are described separately in the Automation Design documentation.

---

## 2. Test Design Principles

T01–T09 are not intended merely to confirm that the Mock Controller can return data.

Together, they build validation coverage across five categories:

| Category | Tests | Validation Focus |
| --- | --- | --- |
| Baseline | T01 | Device identity / health baseline |
| Normal Path | T02 | Normal WRITE / READ / data verification |
| Negative Command | T03, T04 | Invalid parameter / unsupported command handling |
| Fault / Recovery | T05, T09 | Timeout, program failure, reset, retry |
| Data / Evidence | T06, T07, T08 | Miscompare detection, log parsing, error correlation |

The common design principles are:

1. expected behavior is defined before execution;
2. command status and data integrity are validated separately;
3. fault detection and recovery are treated as separate validation targets;
4. structured evidence is preserved;
5. each test can run independently or under A01.

---

# 3. T01 — Device Baseline Check

## 3.1 Objective

T01 verifies that the Mock Device identity and health data match the configured validation baseline.

## 3.2 Main Files

```text
amnv/test_cases/t01_device_baseline.py
amnv/runner.py
amnv/mock_controller.py
amnv/validator.py
config/validation_config.json
data/mock_device.json
```

## 3.3 Commands

```text
IDENTIFY
SMART
```

## 3.4 Flow

```text
Load Validation Configuration
→ Execute IDENTIFY
→ Validate Completion
→ Validate Device Identity
→ Execute SMART
→ Validate Completion
→ Validate Health Data
→ Build TestResult
```

## 3.5 IDENTIFY Checks

| Check | Expected |
| --- | --- |
| Completion Status | `SUCCESS` |
| Model | `MockNVMe-01` |
| Firmware Revision | `1.0.3` |
| NSID | `1` |
| Capacity Blocks | `4096` |
| Logical Block Size | `512` bytes |

## 3.6 SMART / Health Checks

| Check | Expected |
| --- | --- |
| Completion Status | `SUCCESS` |
| Temperature | `<= 70°C` |
| Critical Warning | `0` |
| Media Errors | `0` |

## 3.7 PASS Criteria

All IDENTIFY and SMART validation checks must pass.

## 3.8 Design Purpose

T01 represents baseline verification commonly performed before deeper I/O validation.

It confirms that the validation target and basic health state match the expected test environment.

---

# 4. T02 — Normal Write / Readback

## 4.1 Objective

T02 validates the normal I/O path:

```text
WRITE
→ READ
→ Compare Data
```

## 4.2 Main Files

```text
amnv/test_cases/t02_write_readback.py
amnv/runner.py
amnv/storage.py
amnv/validator.py
```

## 4.3 Test Data

```text
LBA = 600
Length = 1
Pattern = T02_WRITE_READBACK
```

## 4.4 Flow

```text
WRITE LBA 600
→ Validate WRITE Completion
→ READ LBA 600
→ Validate READ Completion
→ Compare LBA / Length / Data
→ Build TestResult
```

## 4.5 Checks

| Check | Expected |
| --- | --- |
| WRITE Completion | `SUCCESS` |
| READ Completion | `SUCCESS` |
| Readback LBA | `600` |
| Readback Length | `1` |
| Readback Data | `T02_WRITE_READBACK` |
| Unwritten Flag | `false` |

## 4.6 PASS Criteria

Both commands must complete successfully and the readback data must match exactly.

## 4.7 Design Purpose

T02 establishes the normal WRITE / READ baseline used by later negative and recovery tests.

---

# 5. T03 — Invalid Read Range

## 5.1 Objective

T03 verifies that a READ extending beyond the Mock Device capacity is rejected correctly.

## 5.2 Main Files

```text
amnv/test_cases/t03_invalid_read_range.py
amnv/runner.py
amnv/mock_controller.py
amnv/storage.py
amnv/validator.py
```

## 5.3 Condition

```text
Capacity = 4096 blocks
READ LBA = 4095
Length = 2
```

The request reaches beyond the valid range.

## 5.4 Flow

```text
Submit invalid READ
→ Range Validation
→ Reject Command
→ Return INVALID_RANGE
→ Host Validation
```

## 5.5 Checks

| Check | Expected |
| --- | --- |
| Completion Status | `INVALID_RANGE` |
| Completion Error | `INVALID_RANGE` |
| Completion Data | `None` |
| Timed Out | `false` |

## 5.6 PASS Criteria

The invalid request must be rejected with the expected error behavior.

## 5.7 Design Purpose

T03 demonstrates that a negative validation test passes when the expected error is correctly generated.

---

# 6. T04 — Unsupported Command

## 6.1 Objective

T04 validates the unsupported-command path.

## 6.2 Main Files

```text
amnv/test_cases/t04_unsupported_command.py
amnv/runner.py
amnv/mock_controller.py
amnv/validator.py
```

## 6.3 Command

```text
Opcode = FORMAT
```

FORMAT is intentionally unsupported by AMNV.

## 6.4 Flow

```text
Submit FORMAT
→ Opcode Check
→ Unsupported
→ Return UNSUPPORTED_COMMAND
→ Host Validation
```

## 6.5 Checks

| Check | Expected |
| --- | --- |
| Completion Status | `UNSUPPORTED_COMMAND` |
| Completion Error | `UNSUPPORTED_COMMAND` |
| Completion Data | `None` |
| Timed Out | `false` |
| Submitted Opcode | `FORMAT` |

## 6.6 PASS Criteria

The controller must explicitly reject the unsupported opcode with the expected result.

## 6.7 Design Purpose

The test confirms predictable error classification without timeout or uncontrolled failure.

---

# 7. T05 — Read Timeout + Recovery

## 7.1 Objective

T05 validates the complete timeout recovery lifecycle:

```text
READ Timeout
→ Outstanding CID
→ Controller Reset
→ Queue Clear
→ CID Progression Preserved
→ Retry READ
→ Recovery
```

## 7.2 Main Files

```text
amnv/test_cases/t05_read_timeout_recovery.py
amnv/runner.py
amnv/queue_model.py
amnv/cancellation.py
amnv/validator.py
```

## 7.3 Initial Command

```text
READ
LBA = 100
Fault = timeout
CID = 1
```

Expected baseline data is `TEST_PATTERN_A`.

## 7.4 Timeout Stage

Expected state:

```text
Host Status = TIMEOUT
Timed Out = true
Completion = None
Controller Result = None
Outstanding CID = [1]
SQ = [1, 1]
CQ = [0, 0]
next_cid = 2
```

## 7.5 Reset Stage

Expected after logical controller reset:

```text
SQ = [0, 0]
CQ = [0, 0]
Outstanding CID = []
next_cid = 2
```

The queue state is cleared while CID progression is preserved.

## 7.6 Retry Stage

```text
READ LBA 100
Fault = None
CID = 2
```

Expected:

```text
Completion = SUCCESS
Readback Data = TEST_PATTERN_A
Timed Out = false
```

Final state:

```text
SQ = [1, 1]
CQ = [1, 1]
Outstanding CID = []
next_cid = 3
```

## 7.7 PASS Criteria

Timeout detection, timeout queue state, reset, CID preservation, retry result, readback, and final queue state must all match expectations.

## 7.8 Design Purpose

T05 validates recovery state rather than treating reset as simple cleanup.

---

# 8. T06 — Data Integrity Failure

## 8.1 Objective

T06 verifies that AMNV can detect corrupted returned data even when command completion reports `SUCCESS`.

## 8.2 Main Files

```text
amnv/test_cases/t06_data_integrity_failure.py
amnv/runner.py
amnv/fault_injector.py
amnv/storage.py
amnv/validator.py
```

## 8.3 Test Data

```text
LBA = 700
Expected Pattern = T06_EXPECTED_DATA
```

## 8.4 Flow

```text
WRITE expected data
→ SUCCESS
→ READ with miscompare fault
→ Completion SUCCESS
→ Returned Data != Expected
→ Normal READ
→ Confirm stored data remains correct
```

The faulted read returns `TEST_PATTERN_B` while the underlying stored data remains `T06_EXPECTED_DATA`.

## 8.5 Checks

| Check | Expected |
| --- | --- |
| Initial WRITE | `SUCCESS` |
| Fault READ Completion | `SUCCESS` |
| Fault READ LBA | `700` |
| Data Miscompare | Returned data differs from expected |
| Timed Out | `false` |
| Verification READ | `SUCCESS` |
| Stored Data | `T06_EXPECTED_DATA` |
| Stored LBA | `700` |

## 8.6 PASS Criteria

The validator must detect the mismatch while confirming that persistent storage remains unchanged.

## 8.7 Design Purpose

T06 explicitly separates command completion status from data-integrity validation.

---

# 9. T07 — Firmware Log Parsing

## 9.1 Objective

T07 validates the firmware-style log parser independently from runtime fault execution.

## 9.2 Main Files

```text
amnv/test_cases/t07_firmware_log_parsing.py
amnv/log_parser.py
data/sample_fw.log
amnv/validator.py
```

## 9.3 Input

```text
data/sample_fw.log
Expected Entry Count = 10
```

Parsed fields include:

- Timestamp
- CID
- Opcode
- LBA
- Status
- Error

## 9.4 Flow

```text
Load sample log
→ Parse entries
→ Validate entry count
→ Validate required fields
→ Query known CID / LBA records
→ Validate parsed values
```

## 9.5 Checks

| Check | Expected |
| --- | --- |
| Parsed Entry Count | `10` |
| Required Fields Present | `true` |
| CID 5 Entry Count | `1` |
| CID 5 Opcode | `READ` |
| CID 5 LBA | `300` |
| CID 5 Status | `FAILED` |
| CID 5 Error | `NAND_READ_FAIL` |
| LBA 2000 Entry Count | `1` |
| LBA 2000 Opcode | `WRITE` |
| LBA 2000 Error | `NAND_PROGRAM_FAIL` |

## 9.6 PASS Criteria

All parsing, field-presence, and known-record validation checks must pass.

## 9.7 Design Purpose

T07 isolates parser correctness before T08 / T09 depend on runtime log correlation.

---

# 10. T08 — Read Error Correlation

## 10.1 Objective

T08 verifies that a READ failure can be correlated with firmware-style runtime evidence.

## 10.2 Main Files

```text
amnv/test_cases/t08_read_error_correlation.py
amnv/runner.py
amnv/fault_injector.py
amnv/log_parser.py
logs/runtime_fw.log
amnv/validator.py
```

## 10.3 Condition

```text
READ
LBA = 300
Fault = NAND_READ_FAIL
```

## 10.4 Flow

```text
Prepare runtime log
→ Execute faulted READ
→ Receive FAILED completion
→ Parse runtime log
→ Correlate by CID
→ Correlate by LBA
→ Compare Opcode / Status / Error
```

## 10.5 Completion Checks

| Check | Expected |
| --- | --- |
| Completion Status | `FAILED` |
| Completion Error | `NAND_READ_FAIL` |
| Completion Data | `None` |
| Timed Out | `false` |

## 10.6 Log Checks

| Check | Expected |
| --- | --- |
| Runtime Log Entry Count | `1` |
| CID Correlation Count | `1` |
| LBA Correlation Count | `1` |
| Log CID | Command CID |
| Log Opcode | `READ` |
| Log LBA | `300` |
| Log Status | `FAILED` |
| Log Error | `NAND_READ_FAIL` |

## 10.7 PASS Criteria

Both the Host-visible completion and firmware-style log evidence must describe the same failure.

## 10.8 Design Purpose

T08 demonstrates the validation workflow of correlating Host-side evidence with firmware-side evidence.

---

# 11. T09 — Write Failure + Recovery

## 11.1 Objective

T09 validates a full WRITE failure and recovery sequence:

```text
NAND_PROGRAM_FAIL
→ Failed WRITE
→ Log Correlation
→ Old Data Preserved
→ Reset
→ Retry WRITE
→ Readback
→ Recovered Data Verified
```

## 11.2 Main Files

```text
amnv/test_cases/t09_write_failure_recovery.py
amnv/runner.py
amnv/queue_model.py
amnv/fault_injector.py
amnv/storage.py
amnv/log_parser.py
logs/runtime_fw.log
amnv/validator.py
```

## 11.3 Test Data

```text
LBA = 400
Old Pattern = OLD_PATTERN
New Pattern = T09_RECOVERED_DATA
Fault = NAND_PROGRAM_FAIL
```

## 11.4 Failed WRITE

```text
CID 1
WRITE LBA 400
Fault = NAND_PROGRAM_FAIL
```

Expected:

```text
Completion = FAILED
Error = NAND_PROGRAM_FAIL
Data = None
Timed Out = false
```

## 11.5 Log Correlation

The runtime log must match the failed command by:

- CID;
- Opcode = WRITE;
- LBA = 400;
- Status = FAILED;
- Error = NAND_PROGRAM_FAIL.

## 11.6 Storage Protection

A normal READ after the failed WRITE uses CID 2 and must return:

```text
OLD_PATTERN
```

This verifies that failed programming did not corrupt the stored data.

## 11.7 Reset

Logical controller reset clears queue/outstanding state while preserving:

```text
next_cid = 3
```

## 11.8 Retry WRITE

```text
CID 3
WRITE LBA 400
Data = T09_RECOVERED_DATA
Fault = None
```

Expected completion is `SUCCESS`.

## 11.9 Final Readback

```text
CID 4
READ LBA 400
```

Expected:

```text
Data = T09_RECOVERED_DATA
```

Final queue:

```text
SQ = [2, 2]
CQ = [2, 2]
Outstanding = []
next_cid = 5
```

## 11.10 PASS Criteria

The following must all pass:

- failure detection;
- log correlation;
- old-data preservation;
- reset state;
- CID preservation;
- retry WRITE;
- final READ;
- final data integrity;
- final queue state.

A successful retry alone is not sufficient.

## 11.11 Design Purpose

T09 integrates fault injection, error completion, evidence correlation, data protection, reset, retry, and final data verification into one recovery scenario.

---

# 12. T01–T09 Coverage Summary

| Test | Positive / Negative | Command / Mechanism | Fault | Recovery | Log | Data Integrity |
| --- | --- | --- | --- | --- | --- | --- |
| T01 | Positive | IDENTIFY / SMART | No | No | No | Baseline |
| T02 | Positive | WRITE / READ | No | No | No | Yes |
| T03 | Negative | READ invalid range | Invalid parameter | No | No | No |
| T04 | Negative | Unsupported FORMAT | Unsupported opcode | No | No | No |
| T05 | Negative + Recovery | READ | Timeout | Reset + Retry | No | Readback |
| T06 | Negative | WRITE / READ | Miscompare | No | No | Yes |
| T07 | Parser Validation | Log Parser | Static log cases | No | Yes | No |
| T08 | Negative + Evidence | READ | NAND_READ_FAIL | No retry | Yes | No |
| T09 | Negative + Recovery | WRITE / READ | NAND_PROGRAM_FAIL | Reset + Retry | Yes | Yes |

Together, these tests form the primary regression coverage used by A01 Full Validation.

---

# 13. Result Classification

Individual tests can produce:

```text
PASS
FAIL
ERROR
ABORTED
```

When tests are orchestrated by A01, tests that have not started may additionally become:

```text
NOT_RUN
```

### PASS

All test-defined validation checks passed.

### FAIL

Execution completed, but one or more expected-versus-actual checks failed.

### ERROR

An unexpected exception prevented the test from completing its designed validation flow.

### ABORTED

The user requested stop and cooperative cancellation interrupted the active test.

### NOT_RUN

The test never started, typically because suite execution was stopped earlier.

---

# 14. Cancellation and Test Design

The final T01–T09 implementation supports individual Stop through a shared:

```text
CancellationToken
```

Tests check cancellation at appropriate execution points.

If cancellation occurs while a subprocess is active:

```text
Cancellation Requested
→ terminate subprocess
→ grace period
→ kill if required
→ logical reset
→ Test = ABORTED
```

User cancellation is not classified as `FAIL`, because execution control and functional validation failure are different conditions.

STOP v1 is documented separately in detail.

---

# 15. Test Design Boundary

T01–T09 validate the AMNV logical model.

They do not validate:

- real PCIe transport;
- physical MMIO registers;
- real DMA;
- PRP / SGL;
- MSI / MSI-X;
- a real NVMe driver;
- actual controller firmware;
- FTL;
- NAND timing, ECC, or wear behavior;
- real SSD performance.

A passing individual test therefore means:

> Within the AMNV Host-side logical validation model, the scenario's expected behavior, detection, recovery, and evidence matched the test design.
