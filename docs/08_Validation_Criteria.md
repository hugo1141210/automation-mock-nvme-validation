# 驗證判定標準 / Validation Criteria

# 中文版

## 1. 文件目的

本文件定義 **Automation Mock NVMe Validation（AMNV）** 中所有 Individual Test、Automation Suite、Fault Campaign 與 STOP 行為的正式判定標準。

本文件回答的核心問題是：

> 在 AMNV 中，什麼情況應該被判定為 PASS、FAIL、ERROR、ABORTED、NOT_RUN 或 STOPPED？

同時也定義：

- Expected / Actual 的比較原則；
- Validation Check 的判定方式；
- Negative Test 的 PASS 語意；
- Timeout 與 Command Failure 的區別；
- Data Integrity 的判定方式；
- Recovery 的判定方式；
- Firmware Log Correlation 的判定方式；
- Suite Summary 的統計規則；
- STOP 後 Partial Execution 的判定方式；
- Evidence 必須保留到什麼程度。

本文件描述的是 **Validation Result Criteria**。

正式最終驗收要執行哪些 Scenario、要留下哪些 Evidence，會在 `09_Acceptance_Plan.md` 中另外定義。

---

# 2. 判定層級

AMNV 的 Result 分成三個層級：

```text
Validation Check
↓
Test / Case Result
↓
Suite / Campaign Result
```

三個層級不可混用。

例如：

```text
Completion Status = FAILED
```

不代表：

```text
Test = FAIL
```

如果 Test 本來就預期 Controller 回傳 `FAILED / NAND_READ_FAIL`，那這個 Check 反而可以是 PASS。

因此 AMNV 的最終判定一定是：

```text
Expected Behavior
vs
Actual Behavior
```

而不是單純：

```text
SUCCESS = PASS
FAILED = FAIL
```

---

# 3. Validation Check

每個 Test / Case 由多個 Validation Check 組成。

基本格式可概括為：

```text
Check Name
Expected
Actual
Passed
```

例如：

```text
Check Name: Completion Status
Expected: INVALID_RANGE
Actual: INVALID_RANGE
Passed: true
```

或：

```text
Check Name: Data Miscompare Detected
Expected: true
Actual: true
Passed: true
```

---

## 3.1 Check PASS

當 Actual 符合 Test Design 定義的 Expected 時：

```text
Check = PASS
```

Expected 不一定是單一固定值。

例如 Temperature：

```text
Expected <= 70
Actual = 35
```

仍為 PASS。

---

## 3.2 Check FAIL

如果 Test 正常執行，但 Actual 不符合 Expected：

```text
Check = FAIL
```

例如：

```text
Expected Error = NAND_READ_FAIL
Actual Error = None
```

代表 Fault Detection 不符合 Scenario 設計。

---

# 4. Expected 與 Actual

## 4.1 Expected

`Expected` 描述 Test Design 要求系統呈現的行為。

它可能是：

- 固定值；
- Threshold；
- Boolean Condition；
- Queue State；
- Result State；
- Data Pattern；
- Error Code；
- Recovery Outcome。

例如：

```text
Expected Completion = SUCCESS
```

或：

```text
Expected Returned Data != Stored Data
```

或：

```text
Expected Outstanding CID = [1]
```

---

## 4.2 Actual

`Actual` 是執行後實際取得的結果。

來源可能包括：

- Command Result；
- CQ Completion；
- Queue State；
- Mock Storage；
- Firmware-style Log；
- Cancellation Evidence；
- Retry Result。

Validation 必須使用實際 Evidence 建立 Actual，而不是直接複製 Expected。

---

# 5. Individual Test / Case Result State

Individual Test / A02 Case 使用：

```text
PASS
FAIL
ERROR
ABORTED
NOT_RUN
```

其中 `NOT_RUN` 主要出現在 Suite / Campaign Context。

---

# 6. PASS

## 6.1 定義

`PASS` 表示：

> Test / Case 已按照設計完成，而且所有要求的 Validation Check 都符合 Expected Behavior。

一般邏輯：

```text
all required checks passed
→ PASS
```

---

## 6.2 PASS 不等於 Command SUCCESS

這是 AMNV 最重要的判定原則之一。

以下 Scenario 都可能是 Test PASS：

### Normal Path

```text
Expected Completion = SUCCESS
Actual Completion = SUCCESS
→ PASS
```

### Invalid Range

```text
Expected Completion = INVALID_RANGE
Actual Completion = INVALID_RANGE
→ PASS
```

### Unsupported Command

```text
Expected = UNSUPPORTED_COMMAND
Actual = UNSUPPORTED_COMMAND
→ PASS
```

### NAND Read Failure

```text
Expected = FAILED / NAND_READ_FAIL
Actual = FAILED / NAND_READ_FAIL
→ PASS
```

因此：

```text
Command FAILED
```

本身不能直接推導：

```text
Test FAIL
```

---

# 7. FAIL

## 7.1 定義

`FAIL` 表示：

> Test / Case 可以正常執行到足以做出判斷，但一個或多個 Required Validation Check 不符合 Expected Behavior。

例如：

```text
Expected Completion = INVALID_RANGE
Actual Completion = SUCCESS
→ FAIL
```

或：

```text
Expected Retry CID = 2
Actual Retry CID = 1
→ FAIL
```

或：

```text
Expected Data = T09_RECOVERED_DATA
Actual Data = OLD_PATTERN
→ FAIL
```

---

## 7.2 FAIL 是 Functional Validation Result

FAIL 應表示：

```text
Scenario executed
+
Evidence available
+
Expected != Actual
```

而不是：

```text
Unexpected Python exception
```

後者應該是 `ERROR`。

---

# 8. ERROR

## 8.1 定義

`ERROR` 表示：

> Test / Case 因非預期執行錯誤，無法按照原本 Test Design 完成正常 Validation 判定。

例如：

- 未處理 Exception；
- 無法解析必要資料；
- 必要檔案格式損壞；
- 非預期 Runtime Failure。

---

## 8.2 ERROR 與 FAIL 的差異

```text
FAIL
= 系統行為不符合 Expected

ERROR
= Test 本身無法正常完成判定
```

例如：

```text
Expected NAND_READ_FAIL
Actual SUCCESS
→ FAIL
```

但：

```text
Python raises unexpected KeyError
Test cannot finish validation
→ ERROR
```

---

# 9. ABORTED

## 9.1 定義

`ABORTED` 表示：

> Test / Case 已經開始執行，但在完成前因使用者提出 Stop Request 而被 Cooperative Cancellation 中止。

`ABORTED` 是 Execution State，不是 Functional Failure。

因此：

```text
ABORTED != FAIL
```

---

## 9.2 ABORTED Evidence

如果 active unit 被中止，應盡可能保存：

- Abort Stage；
- Stop Reason；
- Interrupted Command；
- CID；
- Opcode；
- LBA；
- Host Result；
- Timed Out Flag；
- Process Termination Method；
- Queue State after abort；
- Outstanding CID；
- Next CID。

實際 A01 STOP Report 已可保存 T05 的 `INITIAL_READ` abort stage、`Host Result ABORTED`、`Timed Out false`、subprocess `terminate`、Queue `0/0` 與 `Next CID 2`。fileciteturn98file1L47-L68

---

## 9.3 Partial Validation Check

ABORTED Test 可能已完成部分 Check。

因此：

```text
ABORTED
```

不代表：

```text
0 checks executed
```

例如 active A02 Fault Case 可能已完成 Setup Check，然後在 Fault Command 階段被中止；Report 仍可保留已完成的 Check 與 Abort Evidence。fileciteturn98file3L118-L140

最終 Result 仍為：

```text
ABORTED
```

因為完整 Case 沒有完成。

---

# 10. NOT_RUN

## 10.1 定義

`NOT_RUN` 表示：

> 該 Test / Case 原本被排入 Suite / Campaign，但在開始執行前，Suite 已因 Stop 或正常執行策略而停止。

典型 Stop 情況：

```text
T05 ABORTED
T06~T09 NOT_RUN
```

---

## 10.2 NOT_RUN 不算 Executed

NOT_RUN 的特性：

```text
Duration = 0
Validation Checks = Not executed
```

例如 A01 STOP Report 中，T07～T09 都明確標示 `NOT_RUN`，Actual 為 `Not run because suite stop was requested`。fileciteturn98file4L159-L174

因此：

```text
NOT_RUN != FAIL
NOT_RUN != ERROR
NOT_RUN != ABORTED
```

---

# 11. Suite / Campaign Result State

A01 / A02 Suite Level 使用：

```text
PASS
FAIL
STOPPED
```

這和 Individual Test 的 State 不完全相同。

---

# 12. Suite PASS

## 12.1 定義

Suite `PASS` 表示：

> Suite 正常完成，而且所有要求執行的 Test / Case 都符合 Expected Behavior。

典型 A01：

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

A01 已有完整九項 PASS 的實際 Report Evidence。fileciteturn95file9L1080-L1093

A02 完整 PASS 則表示全部 Campaign Case 通過其 Fault-specific Validation。

---

# 13. Suite FAIL

## 13.1 定義

Suite `FAIL` 表示：

> 沒有 User Stop，但至少一個要求執行的 Test / Case 出現 Functional FAIL 或 ERROR，使整套 Validation 不符合完成條件。

例如：

```text
T01 PASS
T02 PASS
T03 FAIL
...
Suite = FAIL
```

或：

```text
A02-FP03-C01 ERROR
Campaign = FAIL
```

---

## 13.2 Suite FAIL 不等於所有 Test FAIL

Suite 只要有一個 Critical / Required Test 不通過，就可能是 FAIL。

其他已完成 Test 仍保留原本 Result。

例如：

```text
T01 PASS
T02 PASS
T03 FAIL
T04 PASS
```

不能因為 Suite FAIL 就把所有 Test 改成 FAIL。

---

# 14. Suite STOPPED

## 14.1 定義

`STOPPED` 專門代表：

> 使用者提出 Cancellation Request，導致 Suite / Campaign 未按照原定執行範圍完整完成。

因此：

```text
STOPPED != FAIL
```

---

## 14.2 STOPPED 的典型狀態

A01：

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

Suite = STOPPED
```

實際驗證結果：

```text
Total      9
Executed   5
Passed     4
Failed     0
Error      0
Aborted    1
Not Run    4
```

已由 A01 Partial Report 確認。fileciteturn98file0L10-L37

A02 也使用相同語意：

```text
Completed Cases
→ Preserve

Active Interrupted Case
→ ABORTED

Remaining Cases
→ NOT_RUN

Campaign
→ STOPPED
```

---

# 15. Summary Counting Rules

A01 / A02 統計使用：

```text
Total
Executed
Passed
Failed
Error
Aborted
Not Run
```

正式關係：

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

以及：

```text
Total
=
Executed
+
Not Run
```

---

## 15.1 為什麼 ABORTED 算 Executed

因為：

```text
ABORTED
```

代表該 unit 已經開始執行，只是未完成。

所以必須計入：

```text
Executed
```

---

## 15.2 為什麼 NOT_RUN 不算 Executed

`NOT_RUN` 表示根本沒有開始。

所以：

```text
NOT_RUN
```

只能出現在 Total 與 Not Run Count 中。

---

# 16. Negative Test 判定

AMNV 包含多個 Negative Validation Scenario。

Negative Test 的判定規則是：

> 預期的錯誤行為正確發生，Test 就可以 PASS。

---

## 16.1 T03 Invalid Range

Expected：

```text
Completion Status = INVALID_RANGE
Error = INVALID_RANGE
Data = None
Timed Out = false
```

如果全部符合：

```text
T03 = PASS
```

---

## 16.2 T04 Unsupported Command

Expected：

```text
FORMAT
→ UNSUPPORTED_COMMAND
```

如果 Controller 明確拒絕：

```text
T04 = PASS
```

實際 Report 中 T04 的 5 項 Check 均以 `UNSUPPORTED_COMMAND` 為 Expected 並通過。fileciteturn98file5L185-L197

---

## 16.3 Error Injection

例如：

```text
Expected NAND_READ_FAIL
Actual NAND_READ_FAIL
```

則 Case PASS。

因此 Fault Injection 的目的不是追求 Command SUCCESS，而是追求：

```text
Controlled Expected Failure
```

---

# 17. Timeout 判定

Timeout 和 Error Completion 必須嚴格區分。

---

## 17.1 Timeout Expected State

典型 T05 / FP01：

```text
Host Result = TIMEOUT
Timed Out = true
Completion = None
Outstanding CID remains
```

這表示 Controller 沒有正常回傳 CQ Completion。

---

## 17.2 Error Completion

典型 NAND_READ_FAIL：

```text
Host command completed
CQ Status = FAILED
Error = NAND_READ_FAIL
Timed Out = false
```

這表示：

> Controller 有完成 Command，只是 Completion 是 Failure。

因此：

```text
TIMEOUT != FAILED Completion
```

---

# 18. Data Integrity 判定

Data Integrity 不依賴 CQ Status 單獨判定。

T06 / FP04 的核心條件：

```text
CQ Status = SUCCESS
Returned Data != Expected Data
```

Validation 必須偵測：

```text
Data Miscompare = true
```

同時確認：

```text
Underlying Storage remains correct
```

因此：

```text
SUCCESS Completion
```

不能自動等於：

```text
Data Integrity PASS
```

---

# 19. Storage Protection 判定

對 WRITE Failure Scenario，例如 T09 / FP03：

```text
WRITE
→ NAND_PROGRAM_FAIL
```

如果 Fault 是設計為 Program Failure，則失敗後的新資料不應被寫入 Mock Storage。

Expected：

```text
Storage After Failed WRITE
=
Old Data
```

只有在 Old Data 被保留時，Storage Protection Check 才 PASS。

---

# 20. Recovery 判定

Recovery Test 不可以只看「Retry 最後成功」。

完整 Recovery 必須驗證各階段。

---

## 20.1 Timeout Recovery

例如 T05：

```text
Initial Timeout
+
Outstanding CID
+
Reset Queue
+
Outstanding Cleared
+
CID Progression Preserved
+
Retry uses New CID
+
Retry SUCCESS
+
Expected Readback
```

所有 Required Recovery Check 都通過才是 Test PASS。

---

## 20.2 Program Failure Recovery

例如 T09：

```text
Failed WRITE
+
Correct Error
+
Firmware Log
+
Old Data Preserved
+
Reset
+
CID Progression
+
Retry WRITE SUCCESS
+
Final Readback
+
Final Queue State
```

不能因為：

```text
Final READ = expected data
```

就忽略前面 Recovery State 是否錯誤。

---

# 21. CID 判定

CID Validation 的主要原則：

```text
每一筆新 Command
→ 使用新的 CID
```

Controller Reset 清除：

```text
Queue State
Outstanding CID
```

但不應將：

```text
next_cid
```

重設回初始值。

因此：

```text
CID 1 timeout
→ reset
→ retry CID 2
```

是正常 Expected Behavior。

CID progression 是 Recovery Validation 的一部分，而不只是 Debug Information。

---

# 22. Queue State 判定

Queue Evidence 包括：

```text
sq_head
sq_tail
cq_head
cq_tail
outstanding_cids
next_cid
```

不同 Lifecycle 有不同 Expected State。

例如正常完成：

```text
SQ progressed
CQ progressed
Outstanding = []
```

Timeout：

```text
SQ progressed
CQ not completed
Outstanding contains timed-out CID
```

Reset：

```text
SQ = 0/0
CQ = 0/0
Outstanding = []
next_cid preserved
```

因此 Queue State 是正式 Validation Evidence。

---

# 23. Firmware Log 判定

T07、T08、T09、A02 Fault Case 使用 Firmware-style Log。

判定分兩類。

---

## 23.1 Parser Validation

T07 主要確認：

- Entry 數量；
- Required Field；
- CID；
- Opcode；
- LBA；
- Status；
- Error。

Parser 必須先能正確建立 Structured Entry。

---

## 23.2 Correlation Validation

Fault Correlation 主要比對：

```text
CID
Opcode
LBA
Status
Error
```

例如 FP02 已驗證：

```text
CQ Completion = FAILED / NAND_READ_FAIL
Firmware Log = same CID / READ / LBA / NAND_READ_FAIL
Correlation = matched
```

實際 A02 Report 有保存這類 Correlation Evidence。fileciteturn96file2L128-L149

---

# 24. Cancellation 判定

Cancellation 不可以和 Timeout 混在一起。

如果 User Stop 發生：

```text
Host Result = ABORTED
Timed Out = false
```

這表示：

```text
Cancellation
```

而不是：

```text
Timeout
```

實際 A01 Stop Evidence 也明確保存 `Host Result ABORTED` 與 `Timed Out false`。fileciteturn98file1L59-L68

---

# 25. Process Termination 判定

如果 User Stop 發生在 active `fake_nvme.py` subprocess：

正常 Cancellation Recovery 順序為：

```text
terminate()
→ grace period
→ kill() if required
→ logical reset
```

Evidence 應保存實際採用的 Process Termination Method。

`terminate` 成功本身不是 Test PASS 條件。

真正要求的是：

```text
Cancellation completed
+
logical state recovered
+
Result correctly classified as ABORTED
```

---

# 26. Evidence Completeness

對於 PASS / FAIL Test，Evidence 應足以回答：

```text
What was expected?
What actually happened?
Which checks passed or failed?
Which command was involved?
What state was observed?
```

對 Recovery Scenario 還應回答：

```text
What failed?
What state existed before reset?
What did reset clear?
Was CID progression preserved?
Did retry succeed?
Was final data correct?
```

對 STOP Scenario 還應回答：

```text
Where was execution interrupted?
Why was it stopped?
Was an active subprocess terminated?
Was queue state recovered?
Which units were not started?
```

---

# 27. Duration 的定位

`duration_sec` 是執行證據的一部分，但不是 Performance Qualification Result。

它可用來：

- 確認 Test 確實執行；
- 比較 Timeout / Normal Test 的相對行為；
- 在 Report 中提供執行紀錄。

但 AMNV 不以目前 Duration 判定：

- SSD Performance；
- NVMe Latency Compliance；
- Throughput；
- QoS。

---

# 28. Result 不可回溯改寫

如果 Test 已完成：

```text
PASS
FAIL
ERROR
```

之後才收到 User Stop，不應把已完成 Result 改成：

```text
ABORTED
```

因此 Result State 反映的是該 unit 真正完成時的 Execution Outcome。

---

# 29. Validation Criteria 與 Acceptance Criteria 的區別

本文件定義：

```text
一個 Test / Case / Suite 要怎麼判 PASS / FAIL / STOPPED
```

下一份 `09_Acceptance_Plan.md` 定義：

```text
正式驗收時
實際要跑哪些 Scenario
要看到哪些 Result
要留下哪些 Evidence
```

因此：

```text
Validation Criteria
= 判定規則

Acceptance Plan
= 最終驗收執行清單
```

---

# 30. Validation Boundary

AMNV 的所有 PASS / FAIL 判定都只適用於：

```text
Host-side Logical NVMe Validation Model
```

PASS 不代表：

- Real PCIe Compliance PASS；
- Real NVMe Certification PASS；
- Real SSD Firmware Qualification PASS；
- Real NAND Reliability PASS；
- Real Performance PASS。

正確解讀是：

> 指定 Scenario 在 AMNV 的 deterministic logical model 中，實際行為與預期 Validation Criteria 一致。

---

# English Version

## 1. Document Purpose

This document defines the formal validation criteria used by **Automation Mock NVMe Validation (AMNV)** for individual tests, fault-campaign cases, automation suites, and STOP behavior.

It defines the meaning of:

```text
PASS
FAIL
ERROR
ABORTED
NOT_RUN
STOPPED
```

and also covers:

- expected-versus-actual comparison;
- validation-check rules;
- negative-test semantics;
- timeout versus command failure;
- data-integrity validation;
- recovery validation;
- firmware-log correlation;
- suite summary counting;
- partial execution after cancellation;
- minimum evidence requirements.

This document defines result semantics.

The final acceptance execution plan is defined separately in `09_Acceptance_Plan.md`.

---

# 2. Validation Levels

AMNV uses three levels of evaluation:

```text
Validation Check
↓
Test / Case Result
↓
Suite / Campaign Result
```

These levels must not be confused.

A controller `FAILED` completion does not automatically mean the test failed.

If the expected behavior is `FAILED / NAND_READ_FAIL`, observing that error can produce a passing validation check and a passing test.

---

# 3. Validation Check

A validation check contains the conceptual fields:

```text
Check Name
Expected
Actual
Passed
```

A check passes when the observed value or condition matches the test-defined expectation.

A check fails when execution completed normally but the observed value does not satisfy the expectation.

---

# 4. Expected vs Actual

`Expected` defines the required behavior.

It may represent:

- a fixed value;
- a threshold;
- a Boolean condition;
- queue state;
- result state;
- data pattern;
- error code;
- recovery outcome.

`Actual` must be derived from runtime evidence such as:

- command result;
- completion;
- queue state;
- storage;
- firmware-style log;
- cancellation evidence;
- retry result.

---

# 5. Individual Result States

Individual tests and A02 cases can use:

```text
PASS
FAIL
ERROR
ABORTED
NOT_RUN
```

`NOT_RUN` is primarily used when individual units are part of a larger suite or campaign.

---

# 6. PASS

`PASS` means the test or case completed according to its design and all required validation checks matched expected behavior.

PASS does not mean the controller must return `SUCCESS`.

Expected failures can also produce a passing test.

Examples include:

```text
INVALID_RANGE
UNSUPPORTED_COMMAND
FAILED / NAND_READ_FAIL
FAILED / NAND_PROGRAM_FAIL
```

when those outcomes are explicitly expected by the scenario.

---

# 7. FAIL

`FAIL` means the test or case executed far enough to make a normal validation decision, but one or more required checks did not match expected behavior.

Examples include:

```text
Expected INVALID_RANGE
Actual SUCCESS
```

or:

```text
Expected retry CID 2
Actual retry CID 1
```

FAIL represents a functional validation mismatch.

---

# 8. ERROR

`ERROR` means an unexpected execution problem prevented the designed validation flow from completing normally.

The distinction is:

```text
FAIL
= validation completed, expected behavior was not observed

ERROR
= validation could not complete normally
```

---

# 9. ABORTED

`ABORTED` means a test or case had already started but was interrupted by a user-requested cooperative cancellation.

It is an execution state, not a functional validation failure.

Therefore:

```text
ABORTED != FAIL
```

Abort evidence should preserve as much as possible about the interruption point and recovery state.

---

# 10. NOT_RUN

`NOT_RUN` means the unit was scheduled but never started.

A NOT_RUN unit normally has:

```text
Duration = 0
Validation Checks = Not executed
```

It is not counted as executed and must not be classified as a failure.

---

# 11. Suite / Campaign States

A01 and A02 use:

```text
PASS
FAIL
STOPPED
```

at suite level.

---

# 12. Suite PASS

A suite passes when normal execution completes and every required executed unit satisfies its validation criteria.

Typical A01 all-pass result:

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

---

# 13. Suite FAIL

A suite fails when there is no user cancellation but one or more required tests/cases produce `FAIL` or `ERROR`.

Completed passing units retain their own PASS state even if the overall suite fails.

---

# 14. Suite STOPPED

`STOPPED` specifically indicates that a cancellation request prevented the suite or campaign from completing its scheduled scope.

Typical behavior:

```text
Completed Units
→ preserve result

Active Interrupted Unit
→ ABORTED

Never-started Units
→ NOT_RUN

Suite
→ STOPPED
```

STOPPED is not equivalent to FAIL.

---

# 15. Summary Counting

The formal counting rule is:

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

ABORTED is counted as executed because the unit started.

NOT_RUN is not counted as executed because it never started.

---

# 16. Negative Test Criteria

A negative test passes when the expected error behavior is observed.

Examples:

```text
Invalid Range
→ INVALID_RANGE
→ PASS
```

```text
Unsupported FORMAT
→ UNSUPPORTED_COMMAND
→ PASS
```

```text
Injected NAND_READ_FAIL
→ FAILED / NAND_READ_FAIL
→ PASS
```

The validation target is expected behavior, not controller SUCCESS.

---

# 17. Timeout Criteria

Timeout must remain distinct from failed completion.

Expected timeout behavior includes:

```text
Host Result = TIMEOUT
Timed Out = true
Completion = None
Outstanding CID remains
```

A failed controller completion instead has:

```text
CQ Status = FAILED
Timed Out = false
```

Therefore:

```text
TIMEOUT != FAILED Completion
```

---

# 18. Data Integrity Criteria

Command completion and data integrity are validated independently.

For miscompare scenarios:

```text
CQ Status = SUCCESS
Returned Data != Expected Data
```

The validator must detect the mismatch.

The underlying stored data should remain correct when the fault only corrupts the returned response.

---

# 19. Storage Protection Criteria

For a failed WRITE caused by `NAND_PROGRAM_FAIL`, the new data must not modify storage.

Expected behavior:

```text
Failed WRITE
→ Old Data Preserved
```

Storage preservation is a required recovery/evidence check.

---

# 20. Recovery Criteria

Recovery scenarios must validate the complete lifecycle rather than only the final retry.

Timeout recovery may require:

```text
Timeout
Outstanding CID
Reset
Queue Clear
CID Preservation
Retry with New CID
Successful Completion
Correct Readback
```

Program-failure recovery may additionally require:

```text
Firmware Log Correlation
Old Data Preservation
Retry WRITE
Final READ
Final Queue State
```

---

# 21. CID Criteria

Every new command receives a new CID.

Logical controller reset clears queue/outstanding state but preserves CID progression.

Therefore:

```text
CID 1 timeout
→ reset
→ retry CID 2
```

is the expected model behavior.

---

# 22. Queue-State Criteria

Queue evidence includes:

```text
sq_head
sq_tail
cq_head
cq_tail
outstanding_cids
next_cid
```

Expected state depends on lifecycle stage.

Normal completion should clear the completed command from outstanding state.

Timeout should preserve the timed-out CID as outstanding.

Reset should clear SQ/CQ/outstanding state while preserving `next_cid`.

---

# 23. Firmware Log Criteria

Firmware-style log validation has two purposes.

Parser validation confirms that required fields are extracted correctly.

Correlation validation confirms that Host command evidence and firmware evidence match on fields such as:

```text
CID
Opcode
LBA
Status
Error
```

---

# 24. Cancellation Criteria

User cancellation must remain distinct from timeout.

Expected cancellation evidence includes:

```text
Host Result = ABORTED
Timed Out = false
```

This indicates execution control rather than command timeout.

---

# 25. Process Termination Criteria

When cancellation interrupts an active mock-controller subprocess, the controlled sequence is:

```text
terminate
→ grace period
→ kill fallback if required
→ logical reset
```

The validation target is not simply successful process termination.

The important criteria are:

- cancellation completed;
- logical state recovered;
- result classified as ABORTED;
- evidence preserved.

---

# 26. Evidence Completeness

PASS / FAIL evidence should allow a reviewer to determine:

```text
What was expected?
What actually happened?
Which checks passed or failed?
Which command and state were involved?
```

Recovery evidence should additionally explain pre-reset state, post-reset state, CID progression, retry behavior, and final data.

STOP evidence should explain interruption stage, reason, process termination, recovery state, and which scheduled units never started.

---

# 27. Duration

Execution duration is evidence, not a real SSD performance qualification metric.

AMNV does not use current duration values to claim:

- NVMe latency compliance;
- throughput;
- QoS;
- SSD performance.

---

# 28. Result Immutability

A completed test result is not retroactively changed because a later cancellation request arrives.

Completed:

```text
PASS
FAIL
ERROR
```

results remain unchanged.

Only the active interrupted unit becomes `ABORTED`.

---

# 29. Validation Criteria vs Acceptance Plan

This document defines:

```text
How a Test / Case / Suite is judged.
```

`09_Acceptance_Plan.md` defines:

```text
Which scenarios must be executed during final acceptance,
which results are required,
and what evidence must be retained.
```

Therefore:

```text
Validation Criteria = decision rules
Acceptance Plan = final verification checklist
```

---

# 30. Validation Boundary

All AMNV validation results apply only to the:

```text
Host-side Logical NVMe Validation Model
```

A PASS result does not represent:

- PCIe compliance;
- NVMe certification;
- real SSD firmware qualification;
- NAND reliability qualification;
- real SSD performance qualification.

The correct interpretation is:

> Within the deterministic logical model implemented by AMNV, the observed behavior matched the scenario's defined validation criteria.
