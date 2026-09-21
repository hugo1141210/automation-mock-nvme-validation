# Command 與 Recovery Lifecycle / Command and Recovery Lifecycle

# 中文版

## 1. 文件目的

本文件集中說明 **Automation Mock NVMe Validation（AMNV）** 中一筆 Host-side logical NVMe Command 從建立、送入 Submission Queue、交給 Mock Controller 執行、產生 Completion，到 Timeout、Controller Reset、Retry 與 Recovery 的完整生命週期。

前面的架構文件分別說明各模組責任；本文件則從「一筆 Command 實際如何流動」的角度整理：

- Command 建立；
- CID 配置；
- Submission Queue（SQ）狀態；
- Logical Doorbell；
- Controller Fetch；
- `fake_nvme.py` subprocess；
- Controller Result；
- Completion Queue（CQ）；
- Outstanding CID；
- Timeout；
- Error Completion；
- Controller Reset；
- Retry；
- CID Progression；
- Data / Storage Recovery；
- Cancellation 與 Timeout 的邊界。

本文件描述的是 AMNV 的 **Logical Command Lifecycle**，不是實際 PCIe / DMA / NVMe Hardware Lifecycle。

---

# 2. 主要模組

Command / Recovery Lifecycle 主要涉及：

```text
amnv/runner.py
amnv/queue_model.py
fake_nvme.py
amnv/mock_controller.py
amnv/storage.py
amnv/fault_injector.py
amnv/cancellation.py
```

另外由 Test Case 負責判斷 Lifecycle 是否符合 Expected：

```text
amnv/test_cases/*
amnv/validator.py
```

責任可概括為：

| 模組 | Lifecycle 角色 |
| --- | --- |
| `runner.py` | Host-side lifecycle coordinator |
| `queue_model.py` | SQ / CQ / CID state owner |
| `fake_nvme.py` | Mock Controller subprocess boundary |
| `mock_controller.py` | Command behavior |
| `storage.py` | Logical block data |
| `fault_injector.py` | Deterministic fault behavior |
| `cancellation.py` | User cancellation state |
| `test_cases/*` | Scenario / recovery decision |
| `validator.py` | Expected vs Actual checks |

---

# 3. Command Result 的核心資料

一筆 Runner Result 會保存多個層面的 Evidence。

概念上包含：

```text
host
command
controller_process
controller_result
completion
fault
timed_out
duration_sec
return_code
trace
queue_state
```

這種結構的目的，是把：

```text
Command Input
Execution State
Controller Output
Completion State
Queue Evidence
```

保存在同一筆 Result 中。

Test Case 不需要只依賴單一 Status String 判斷結果。

---

# 4. CID — Command Identifier

## 4.1 CID 的角色

CID 用來識別一筆 Command。

AMNV 由 Host-side Queue Model 配置 CID。

初始狀態：

```text
next_cid = 1
```

第一筆 Command：

```text
CID = 1
```

配置完成後：

```text
next_cid = 2
```

第二筆：

```text
CID = 2
```

依此類推。

---

## 4.2 CID 不因 Reset 回收

AMNV 的 Controller Reset 會清除 Queue State，但保留：

```text
next_cid
```

因此：

```text
CID 1
→ Timeout
→ Reset
→ Retry
→ CID 2
```

而不是：

```text
CID 1
→ Reset
→ Retry CID 1
```

這讓 Recovery Evidence 可以明確區分：

```text
Original Command
vs
Retry Command
```

---

# 5. Queue Model

## 5.1 主要 State

Queue Model 保存：

```text
sq_head
sq_tail
cq_head
cq_tail
outstanding_cids
next_cid
```

這些值不是實體 NVMe Queue Register，而是用來表示 logical queue progression。

---

## 5.2 Initial State

新的 CommandRunner / QueueModel 初始狀態可概括為：

```text
SQ = 0 / 0
CQ = 0 / 0
Outstanding = []
next_cid = 1
```

表示：

```text
尚未提交 Command
尚未完成 Command
沒有 Outstanding CID
下一個 CID 為 1
```

---

# 6. 正常 Command Lifecycle

一筆正常完成的 Command，主要 Trace 順序為：

```text
SQ_SUBMIT
↓
SQ_TAIL_DOORBELL
↓
CTRL_FETCH
↓
SUBPROCESS_START
↓
CTRL_RESULT
↓
CQ_POST
↓
CQ_CONSUME
↓
CQ_HEAD_DOORBELL
```

這是 AMNV 最核心的 Command Lifecycle。

---

# 7. Stage 1 — SQ_SUBMIT

Host 建立 Command，配置 CID，並把 Command 視為已提交到 Submission Queue。

例如第一筆 Command：

```text
CID = 1
```

State：

```text
Before:
SQ = 0 / 0
Outstanding = []
next_cid = 1

After SQ_SUBMIT:
SQ = 0 / 1
Outstanding = [1]
next_cid = 2
```

此時：

- `sq_tail` 前進；
- CID 進入 Outstanding；
- `sq_head` 尚未前進。

代表：

> Host 已提交，但 Controller 尚未 Fetch。

---

# 8. Stage 2 — SQ_TAIL_DOORBELL

下一個 logical event：

```text
SQ_TAIL_DOORBELL
```

在真實 NVMe 中這對應 Host 寫 MMIO SQ Tail Doorbell。

AMNV 不實作真實 MMIO。

此 Stage 的作用是保存：

```text
Host 已完成 Submission Notification
```

的生命週期語意。

Queue State 通常仍為：

```text
SQ = 0 / 1
Outstanding = [CID]
```

---

# 9. Stage 3 — CTRL_FETCH

Controller logical fetch 後：

```text
CTRL_FETCH
```

State：

```text
SQ = 1 / 1
Outstanding = [CID]
```

`sq_head` 前進到和 `sq_tail` 相同。

表示：

> Controller 已取得這筆 Submission。

但 Command 還沒有 Completion，因此 CID 仍是 Outstanding。

---

# 10. Stage 4 — SUBPROCESS_START

Runner 啟動：

```text
fake_nvme.py
```

作為獨立 subprocess。

Trace：

```text
SUBPROCESS_START
```

Evidence 會保存：

```text
Host PID
Controller Process PID
CID
Fault
```

這建立一個明確的：

```text
Host Execution
↔
Mock Controller Execution
```

邏輯邊界。

---

# 11. Stage 5 — Controller Execution

`fake_nvme.py` 將 Command 交由 Mock Controller / Fault Path 處理。

可能結果包括：

```text
SUCCESS
INVALID_RANGE
UNSUPPORTED_COMMAND
FAILED / NAND_READ_FAIL
FAILED / NAND_PROGRAM_FAIL
```

或者沒有在 Host Timeout Window 內完成：

```text
TIMEOUT
```

另外 Miscompare Scenario 可以是：

```text
Controller Status = SUCCESS
Returned Data = intentionally corrupted
```

---

# 12. Stage 6 — CTRL_RESULT

如果 subprocess 在 Timeout 之前正常回傳：

```text
CTRL_RESULT
```

會記錄 Controller-side Status。

例如：

```text
status = SUCCESS
```

或：

```text
status = FAILED
fault = NAND_PROGRAM_FAIL
```

此時 Queue State 仍可能是：

```text
SQ = 1 / 1
CQ = 0 / 0
Outstanding = [CID]
```

因為 Controller Result 已取得，但 Host-side logical CQ 還沒完成 Post / Consume。

---

# 13. Stage 7 — CQ_POST

Runner 根據 Controller Result 建立 logical Completion。

Trace：

```text
CQ_POST
```

例如：

```text
CQ = 0 / 1
Outstanding = [CID]
```

此時：

- `cq_tail` 前進；
- Completion 已被 Post；
- Host 尚未 consume；
- CID 因此仍保留在 Outstanding。

---

# 14. Stage 8 — CQ_CONSUME

Host logical consume Completion：

```text
CQ_CONSUME
```

State：

```text
CQ = 1 / 1
Outstanding = []
```

此時：

> Host 已處理這筆 Completion。

因此 CID 從：

```text
outstanding_cids
```

移除。

---

# 15. Stage 9 — CQ_HEAD_DOORBELL

最後記錄：

```text
CQ_HEAD_DOORBELL
```

表示 Host 已完成 logical Completion Consumption Notification。

正常第一筆 Command 最後可形成：

```text
SQ = 1 / 1
CQ = 1 / 1
Outstanding = []
next_cid = 2
```

實際 Runtime Trace 中，正常 Command 會依序出現 `CQ_POST → CQ_CONSUME → CQ_HEAD_DOORBELL`，且完成後 Outstanding 清空、`next_cid` 前進。fileciteturn100file2L196-L250

---

# 16. 正常 Command State Summary

第一筆正常 Command：

| Stage | SQ | CQ | Outstanding | next CID |
| --- | --- | --- | --- | ---: |
| Initial | 0/0 | 0/0 | `[]` | 1 |
| SQ Submit | 0/1 | 0/0 | `[1]` | 2 |
| Controller Fetch | 1/1 | 0/0 | `[1]` | 2 |
| Controller Result | 1/1 | 0/0 | `[1]` | 2 |
| CQ Post | 1/1 | 0/1 | `[1]` | 2 |
| CQ Consume | 1/1 | 1/1 | `[]` | 2 |

---

# 17. 第二筆正常 Command

如果沒有 Reset，第二筆 Command 繼續沿用 Queue Counter：

```text
Before:
SQ = 1 / 1
CQ = 1 / 1
next_cid = 2
```

提交 CID 2 後：

```text
SQ = 1 / 2
Outstanding = [2]
next_cid = 3
```

完成後：

```text
SQ = 2 / 2
CQ = 2 / 2
Outstanding = []
next_cid = 3
```

因此 Queue Counter 是 lifecycle progression，不是每一筆 Command 都從零開始。

---

# 18. Error Completion Lifecycle

不是所有 Command 都以 `SUCCESS` 完成。

例如：

```text
NAND_PROGRAM_FAIL
```

可以形成：

```text
CTRL_RESULT
status = FAILED
error = NAND_PROGRAM_FAIL
```

但只要 Controller 正常回傳 Failure Result，Host 仍然會完成：

```text
CQ_POST
→ CQ_CONSUME
→ CQ_HEAD_DOORBELL
```

因此 Error Completion 結束後：

```text
Outstanding = []
```

這一點和 Timeout 非常不同。

實際 NAND Program Failure Trace 仍完整經過 `CTRL_RESULT → CQ_POST → CQ_CONSUME → CQ_HEAD_DOORBELL`，而 `timed_out` 為 false。fileciteturn100file9L718-L823

---

# 19. Error Completion vs Test FAIL

Controller Error Completion 不代表 Test 一定 FAIL。

例如 Scenario 預期：

```text
NAND_PROGRAM_FAIL
```

Actual：

```text
FAILED / NAND_PROGRAM_FAIL
```

Validation Check 可以是 PASS。

所以必須區分：

```text
Command Result
```

和：

```text
Test Result
```

---

# 20. Timeout Lifecycle

Timeout 是特殊 Lifecycle。

例如：

```text
READ
CID = 1
Fault = timeout
```

仍會經過：

```text
SQ_SUBMIT
→ SQ_TAIL_DOORBELL
→ CTRL_FETCH
→ SUBPROCESS_START
```

但 Controller 沒有在：

```text
timeout_sec
```

內提供正常 Result。

Runner 因此進入：

```text
HOST_TIMEOUT
```

---

# 21. Timeout State

Timeout 發生時，不產生正常 CQ Completion。

典型 State：

```text
SQ = 1 / 1
CQ = 0 / 0
Outstanding = [1]
next_cid = 2
```

Evidence：

```text
Host Result = TIMEOUT
Timed Out = true
Completion = None
Controller Result = None
```

實際 Timeout Trace 可看到 `HOST_TIMEOUT` 後仍保留 Outstanding CID 1，而 CQ 沒有前進。fileciteturn100file5L347-L418

---

# 22. 為什麼 Timeout 保留 Outstanding CID

因為 logical meaning 是：

```text
Host 已提交
Controller 已 Fetch
但 Host 沒有收到正常 Completion
```

所以不能直接假裝：

```text
Command 已正常結束
```

因此在 Reset 之前：

```text
CID 1
```

仍保留為 Outstanding。

這個 State 本身就是 T05 / FP01 的 Validation Evidence。

---

# 23. Timeout 與 Error Completion 的差異

| 項目 | Timeout | Error Completion |
| --- | --- | --- |
| Controller normal result | No | Yes |
| CQ Completion | None | Exists |
| Timed Out | true | false |
| Outstanding after event | remains | cleared after consume |
| Recovery | usually Reset / Retry | depends on scenario |

因此：

```text
TIMEOUT
```

不能和：

```text
FAILED Completion
```

用相同方式處理。

---

# 24. Controller Reset

Timeout 或特定 Recovery Scenario 後，Test 可以呼叫 logical Controller Reset。

主要目標：

```text
清除 stale queue / outstanding state
```

而不是：

```text
重建整個 CommandRunner
```

---

# 25. Reset Before / After State

例如 Timeout：

```text
Before Reset:
SQ = 1 / 1
CQ = 0 / 0
Outstanding = [1]
next_cid = 2
```

Reset 後：

```text
After Reset:
SQ = 0 / 0
CQ = 0 / 0
Outstanding = []
next_cid = 2
```

實際 Runner Recovery 測試也確認 Reset 會清空 SQ / CQ / Outstanding，但保留 `next_cid = 2`。fileciteturn100file4L320-L336

---

# 26. Reset 清除什麼

Reset 清除：

```text
sq_head
sq_tail
cq_head
cq_tail
outstanding_cids
```

使 Queue 回到：

```text
0 / 0
```

---

# 27. Reset 保留什麼

Reset 保留：

```text
next_cid
```

這是刻意的 Validation Design。

理由是：

> Reset 是 Recovery Boundary，不是時間倒轉。

已經使用過的 CID 不因 Recovery 被視為從未存在。

---

# 28. Retry Lifecycle

Reset 後，Retry 是一筆新的 Command。

因此：

```text
Original Command:
CID 1
TIMEOUT

Retry:
CID 2
```

Retry 自己重新執行完整 Lifecycle：

```text
SQ_SUBMIT
→ SQ_TAIL_DOORBELL
→ CTRL_FETCH
→ SUBPROCESS_START
→ CTRL_RESULT
→ CQ_POST
→ CQ_CONSUME
→ CQ_HEAD_DOORBELL
```

如果 Retry 成功，Final State：

```text
SQ = 1 / 1
CQ = 1 / 1
Outstanding = []
next_cid = 3
```

---

# 29. T05 Recovery Lifecycle

T05 是最直接的 Timeout Recovery Example：

```text
READ CID 1
↓
TIMEOUT
↓
Outstanding [1]
↓
Controller Reset
↓
Queue 0/0
Outstanding []
next_cid 2
↓
READ Retry CID 2
↓
SUCCESS
↓
Data = TEST_PATTERN_A
↓
Final:
SQ 1/1
CQ 1/1
Outstanding []
next_cid 3
```

這個 Lifecycle 的 PASS 條件不是只有：

```text
Retry SUCCESS
```

而是整條鏈都必須符合 Expected。

---

# 30. WRITE Failure Recovery Lifecycle

T09 則展示：

```text
WRITE CID 1
↓
FAILED / NAND_PROGRAM_FAIL
↓
CQ completed
Outstanding cleared
↓
READ CID 2
↓
Verify old data preserved
↓
Controller Reset
↓
next_cid remains 3
↓
Retry WRITE CID 3
↓
SUCCESS
↓
Final READ CID 4
↓
New data verified
```

與 Timeout 不同的是：

> Original failed WRITE 本身有正常 CQ Failure Completion。

所以在 Reset 之前，CID 1 已不再 Outstanding。

---

# 31. T09 為什麼 Reset 時 next_cid = 3

在 T09 中 Reset 前已執行：

```text
CID 1 = Failed WRITE
CID 2 = Verification READ
```

因此：

```text
next_cid = 3
```

Reset 之後仍是：

```text
next_cid = 3
```

Retry WRITE 使用：

```text
CID 3
```

Final READ：

```text
CID 4
```

Retry WRITE 的實際 Trace 也顯示 CID 3 從 SQ Submit 一路完成 CQ Consume，最後 `next_cid = 4`。fileciteturn100file6L432-L529

---

# 32. Recovery Decision 的責任

`CommandRunner` 提供：

```text
execute command
detect timeout
return result
reset controller
```

但 Test Case 決定：

```text
是否需要 Reset
是否需要 Retry
Retry 哪個 Command
Retry 後驗證什麼
```

因此：

```text
Runner
= Mechanism

Test Case
= Scenario Policy
```

這個分工避免 Runner 被綁死在 T05 或 T09 的特定流程。

---

# 33. WRITE Timeout 與 Data Protection

對 WRITE Timeout / Program Failure Scenario，Recovery Validation 還要確認：

```text
失敗或未完成的 WRITE
```

沒有在成功 Recovery 前錯誤修改 Storage。

所以 Recovery 不只有：

```text
Queue recovery
```

也可能包含：

```text
Data-state recovery / protection
```

---

# 34. Miscompare Lifecycle

Miscompare 是另一種特殊情況。

Controller Lifecycle 可以正常完成：

```text
SQ
→ Controller
→ CQ SUCCESS
```

但 Returned Data 被 Fault Injector 刻意改變。

例如：

```text
Completion Status = SUCCESS
Returned Pattern = TEST_PATTERN_B
Stored Pattern = Expected Pattern
```

所以 Queue Lifecycle 完全正常，不需要 Reset。

Validation Failure Point 位於：

```text
Data Comparison
```

而不是：

```text
Command Transport / Completion
```

---

# 35. Runtime Trace 的用途

Runner 的 `trace` 不是單純 Debug Text。

它可以用來重建：

```text
Command 在哪個 Stage
Queue State 如何變化
CID 何時進入 / 離開 Outstanding
是否有 CQ Completion
Timeout 發生在哪裡
```

因此 Trace 是正式 Evidence Source。

---

# 36. Queue State 與 Trace 的差異

`trace`：

```text
Lifecycle History
```

`queue_state`：

```text
Final Snapshot
```

例如 Timeout：

```text
trace
→ 看得出 SQ Submit / Fetch / Timeout

queue_state
→ 看得到最後 Outstanding [1]
```

兩者用途不同。

---

# 37. Host Result 與 Controller Result

Command Result 要分成兩個觀點。

### Host Result

表示 Host 如何解讀這次 Execution。

例如：

```text
COMMAND_COMPLETE
TIMEOUT
ABORTED
```

### Controller Result

表示 Mock Controller 實際回傳：

```text
SUCCESS
FAILED
INVALID_RANGE
UNSUPPORTED_COMMAND
```

Timeout / Abort 情況下可能不存在正常 Controller Result。

---

# 38. Completion 的定位

`completion` 是 Host-side logical CQ Completion。

只有在 Controller Result 可以形成正常 Completion 時才存在。

因此：

```text
Controller Error
→ Completion can exist

Timeout
→ Completion = None

Abort during active command
→ no normal completion
```

這是 Validation 中非常重要的區分。

---

# 39. Cancellation 與 Command Lifecycle

STOP v1 的詳細設計在：

```text
11_STOP_v1_Design.md
```

本文件只說明它和 Command Lifecycle 的交界。

如果 Cancellation 發生在 active subprocess：

```text
Cancellation Requested
↓
Runner detects request
↓
terminate subprocess
↓
grace period
↓
kill fallback if required
↓
logical controller reset
↓
Host Result = ABORTED
```

---

# 40. Cancellation 與 Timeout 的差異

User Abort：

```text
Host Result = ABORTED
Timed Out = false
```

Timeout：

```text
Host Result = TIMEOUT
Timed Out = true
```

不能因為兩者都會中止正常 Command Flow，就把它們視為同一 Failure Type。

實際 STOP Evidence 中，active Command 被取消後保存 `Host Result ABORTED`、`Timed Out false`，Queue Recovery 後 Outstanding 為空。fileciteturn100file0L10-L31

---

# 41. Cancellation Recovery 與普通 Reset

兩者最後都可能執行 logical reset。

但原因不同：

### Timeout Recovery

```text
Scenario expected timeout
→ Test decides reset
```

### Cancellation Recovery

```text
User requested stop
→ Runner / Test must leave safe logical state
```

因此最終 Queue 都可能：

```text
SQ = 0/0
CQ = 0/0
Outstanding = []
```

但 Result Semantics 不同。

---

# 42. Lifecycle Invariants

AMNV Command Lifecycle 應維持下列基本不變條件。

### Invariant 1

每個新 Command 使用新的 CID。

### Invariant 2

SQ Submit 後 CID 必須成為 Outstanding。

### Invariant 3

正常 CQ Consume 後 CID 必須離開 Outstanding。

### Invariant 4

Timeout 不可假裝有正常 Completion。

### Invariant 5

Reset 必須清除 Outstanding。

### Invariant 6

Reset 不回復 CID progression。

### Invariant 7

Retry 是新 Command，不是延續舊 CID。

### Invariant 8

User Abort 不等於 Timeout。

### Invariant 9

Command SUCCESS 不等於 Data Integrity PASS。

---

# 43. 正常、Failure、Timeout、Abort 對照

| Lifecycle | Controller Result | Completion | Timed Out | Outstanding 最後狀態 | 典型後續 |
| --- | --- | --- | --- | --- | --- |
| Normal SUCCESS | SUCCESS | Exists | false | `[]` | Validate data |
| Error Completion | FAILED / error | Exists | false | `[]` | Correlate / recover |
| Timeout | None | None | true | `[CID]` | Reset / Retry |
| User Abort | No normal result | None | false | reset to `[]` | Stop execution |

---

# 44. Recovery 成功的判定

Recovery Success 不是單一 Boolean。

應根據 Scenario 驗證：

```text
Failure correctly detected
+
Pre-recovery state correct
+
Reset state correct
+
CID progression correct
+
Retry behavior correct
+
Final data correct
+
Final queue state correct
```

某些 Scenario 不需要全部項目，但凡 Test Design 要求的 Recovery Check 都必須通過。

---

# 45. Command Lifecycle Boundary

AMNV 的 Lifecycle 只模擬：

```text
Host-side logical command
SQ / CQ state
Mock Controller process
fault / timeout
logical reset / retry
validation evidence
```

它沒有實作：

- 真實 Host Memory Queue；
- MMIO Register；
- PCIe TLP；
- DMA；
- PRP / SGL；
- MSI / MSI-X；
- 真實 Controller Register Reset；
- 真實 Driver Reinitialization。

所以文件中的：

```text
SQ
CQ
Doorbell
Controller Fetch
Reset
```

都應解讀為 AMNV logical model 中的對應概念。

---

# 46. Lifecycle 設計總結

AMNV 的 Command / Recovery Lifecycle 核心是：

```text
Command
→ CID
→ SQ
→ Controller
→ CQ
→ Validation
```

遇到 Timeout：

```text
Command
→ Outstanding
→ Timeout
→ Reset
→ New CID
→ Retry
→ Validation
```

遇到 Error Completion：

```text
Command
→ FAILED Completion
→ Evidence
→ Scenario-specific Recovery
```

遇到 User Stop：

```text
Command
→ Cancellation
→ Controlled termination
→ Logical recovery
→ ABORTED
```

這些 Lifecycle 是 T05、T08、T09、A01、A02 與 STOP v1 的共同基礎。

---

# English Version

## 1. Document Purpose

This document describes the complete **logical command and recovery lifecycle** used by **Automation Mock NVMe Validation (AMNV)**.

It focuses on how one Host-side command moves through:

- command construction;
- CID allocation;
- Submission Queue state;
- logical doorbell events;
- controller fetch;
- `fake_nvme.py` subprocess execution;
- controller result;
- Completion Queue state;
- outstanding-command tracking;
- timeout;
- controller reset;
- retry;
- CID progression;
- storage/data recovery;
- cancellation boundaries.

This is an AMNV logical lifecycle, not a physical PCIe / DMA / NVMe hardware lifecycle.

---

# 2. Main Modules

The lifecycle primarily involves:

```text
amnv/runner.py
amnv/queue_model.py
fake_nvme.py
amnv/mock_controller.py
amnv/storage.py
amnv/fault_injector.py
amnv/cancellation.py
```

Validation policy is provided by:

```text
amnv/test_cases/*
amnv/validator.py
```

The main responsibility split is:

```text
Runner
= lifecycle coordination

QueueModel
= SQ / CQ / CID state ownership

Test Case
= scenario and recovery policy

Validator
= expected-versus-actual decision
```

---

# 3. Command Result Structure

A runner result conceptually preserves:

```text
host
command
controller_process
controller_result
completion
fault
timed_out
duration_sec
return_code
trace
queue_state
```

This preserves command input, execution state, controller output, completion state, and queue evidence in one structured result.

---

# 4. CID Allocation

The logical queue model owns CID allocation.

Initial:

```text
next_cid = 1
```

First command:

```text
CID = 1
next_cid = 2
```

Second command:

```text
CID = 2
next_cid = 3
```

Controller reset does not roll `next_cid` backward.

This allows the original command and recovery retry to remain distinguishable.

---

# 5. Queue State

QueueModel tracks:

```text
sq_head
sq_tail
cq_head
cq_tail
outstanding_cids
next_cid
```

Initial state:

```text
SQ = 0/0
CQ = 0/0
Outstanding = []
next_cid = 1
```

These values represent logical queue progression rather than physical NVMe queue registers.

---

# 6. Normal Command Lifecycle

A normal command follows:

```text
SQ_SUBMIT
→ SQ_TAIL_DOORBELL
→ CTRL_FETCH
→ SUBPROCESS_START
→ CTRL_RESULT
→ CQ_POST
→ CQ_CONSUME
→ CQ_HEAD_DOORBELL
```

---

# 7. SQ_SUBMIT

The Host allocates a CID and submits the command.

For CID 1:

```text
Before:
SQ = 0/0
Outstanding = []
next_cid = 1

After:
SQ = 0/1
Outstanding = [1]
next_cid = 2
```

The command is now pending controller consumption.

---

# 8. SQ_TAIL_DOORBELL

The logical `SQ_TAIL_DOORBELL` event represents notification that new submission work is available.

AMNV does not perform a physical MMIO register write.

---

# 9. CTRL_FETCH

After logical controller fetch:

```text
SQ = 1/1
Outstanding = [1]
```

The submission has been consumed by the controller side, but no completion exists yet.

---

# 10. SUBPROCESS_START

`CommandRunner` starts:

```text
fake_nvme.py
```

as an independent subprocess.

This creates an observable Host / Mock Controller execution boundary and enables timeout and controlled process termination behavior.

---

# 11. Controller Execution

The controller path can return results such as:

```text
SUCCESS
INVALID_RANGE
UNSUPPORTED_COMMAND
FAILED / NAND_READ_FAIL
FAILED / NAND_PROGRAM_FAIL
```

or fail to complete within the timeout window.

A miscompare case can return `SUCCESS` while deliberately corrupting returned data.

---

# 12. CTRL_RESULT

When the subprocess returns normally, the trace records:

```text
CTRL_RESULT
```

At this point, a controller result exists but the Host-side logical CQ lifecycle has not necessarily completed.

---

# 13. CQ_POST

The controller result is converted into a logical completion.

Typical state:

```text
CQ = 0/1
Outstanding = [CID]
```

The completion exists but has not yet been consumed by the Host.

---

# 14. CQ_CONSUME

Host consumption advances:

```text
CQ = 1/1
Outstanding = []
```

The completed CID is removed from outstanding state.

---

# 15. CQ_HEAD_DOORBELL

`CQ_HEAD_DOORBELL` records the final logical notification that the Host consumed the completion.

A normal first command therefore finishes at:

```text
SQ = 1/1
CQ = 1/1
Outstanding = []
next_cid = 2
```

---

# 16. Normal State Summary

| Stage | SQ | CQ | Outstanding | next CID |
| --- | --- | --- | --- | ---: |
| Initial | 0/0 | 0/0 | `[]` | 1 |
| SQ Submit | 0/1 | 0/0 | `[1]` | 2 |
| Controller Fetch | 1/1 | 0/0 | `[1]` | 2 |
| Controller Result | 1/1 | 0/0 | `[1]` | 2 |
| CQ Post | 1/1 | 0/1 | `[1]` | 2 |
| CQ Consume | 1/1 | 1/1 | `[]` | 2 |

---

# 17. Multiple Commands

Without a reset, queue counters continue progressing.

After the first completed command:

```text
SQ = 1/1
CQ = 1/1
next_cid = 2
```

After the second completed command:

```text
SQ = 2/2
CQ = 2/2
Outstanding = []
next_cid = 3
```

Queue counters therefore represent lifecycle history within the current logical queue epoch.

---

# 18. Error Completion Lifecycle

A command can complete with an error such as:

```text
FAILED / NAND_PROGRAM_FAIL
```

and still follow the normal completion lifecycle:

```text
CTRL_RESULT
→ CQ_POST
→ CQ_CONSUME
→ CQ_HEAD_DOORBELL
```

After completion:

```text
Outstanding = []
```

This is fundamentally different from timeout.

---

# 19. Command Failure vs Test Failure

A controller error does not automatically mean the validation test failed.

If the expected scenario is:

```text
NAND_PROGRAM_FAIL
```

and the observed result is:

```text
FAILED / NAND_PROGRAM_FAIL
```

the validation check can pass.

Command status and test status remain separate concepts.

---

# 20. Timeout Lifecycle

A timeout case still enters:

```text
SQ_SUBMIT
→ SQ_TAIL_DOORBELL
→ CTRL_FETCH
→ SUBPROCESS_START
```

but no normal controller result arrives before the Host timeout window.

The runner records:

```text
HOST_TIMEOUT
```

instead of normal CQ completion.

---

# 21. Timeout State

Typical timeout state:

```text
SQ = 1/1
CQ = 0/0
Outstanding = [1]
next_cid = 2
```

Result semantics:

```text
Host Result = TIMEOUT
Timed Out = true
Completion = None
Controller Result = None
```

The original CID remains outstanding until recovery.

---

# 22. Why Timeout Preserves Outstanding CID

The logical meaning is:

```text
Host submitted command
Controller fetched command
No normal completion returned
```

The framework therefore does not pretend that command completion occurred.

The outstanding CID is intentional validation evidence.

---

# 23. Timeout vs Error Completion

| Item | Timeout | Error Completion |
| --- | --- | --- |
| Normal controller result | No | Yes |
| CQ completion | None | Exists |
| `timed_out` | true | false |
| Outstanding after event | remains | cleared after consume |
| Typical next action | Reset / Retry | scenario-dependent |

---

# 24. Logical Controller Reset

A recovery scenario can call logical controller reset to clear stale queue state.

The reset is a recovery boundary; it is not a recreation of the entire application.

---

# 25. Reset State

Example before reset:

```text
SQ = 1/1
CQ = 0/0
Outstanding = [1]
next_cid = 2
```

After reset:

```text
SQ = 0/0
CQ = 0/0
Outstanding = []
next_cid = 2
```

---

# 26. What Reset Clears

Logical reset clears:

```text
sq_head
sq_tail
cq_head
cq_tail
outstanding_cids
```

---

# 27. What Reset Preserves

Reset preserves:

```text
next_cid
```

The design treats reset as recovery, not as erasing command history.

---

# 28. Retry Lifecycle

A retry is a new command.

Example:

```text
Original CID 1
→ TIMEOUT
→ Reset
→ Retry CID 2
```

The retry executes the complete command lifecycle again.

A successful retry can end with:

```text
SQ = 1/1
CQ = 1/1
Outstanding = []
next_cid = 3
```

---

# 29. T05 Recovery Example

T05 demonstrates:

```text
READ CID 1
→ TIMEOUT
→ Outstanding [1]
→ Reset
→ Queue 0/0
→ Outstanding []
→ next_cid 2
→ Retry READ CID 2
→ SUCCESS
→ Expected Data
→ Final Queue Healthy
```

The test does not pass merely because the final retry succeeds.

All required timeout and recovery-state checks must also pass.

---

# 30. WRITE Failure Recovery

T09 follows a different recovery path:

```text
WRITE CID 1
→ FAILED / NAND_PROGRAM_FAIL
→ CQ completion consumed
→ READ CID 2 verifies old data
→ Reset
→ next_cid remains 3
→ Retry WRITE CID 3
→ SUCCESS
→ Final READ CID 4
→ New data verified
```

The original failed WRITE has a valid error completion, so CID 1 is already removed from outstanding state before reset.

---

# 31. CID Progression in T09

Before reset, two commands have already been allocated:

```text
CID 1 = failed WRITE
CID 2 = verification READ
```

Therefore:

```text
next_cid = 3
```

Reset preserves that value.

Retry WRITE uses CID 3 and final READ uses CID 4.

---

# 32. Recovery Policy Ownership

`CommandRunner` provides mechanisms:

```text
execute
timeout detection
result collection
controller reset
```

The test case decides:

```text
whether reset is required
whether retry is required
which command to retry
what must be verified after retry
```

Therefore:

```text
Runner = mechanism
Test Case = scenario policy
```

---

# 33. WRITE Protection

WRITE recovery scenarios may also validate that an unsuccessful or incomplete WRITE does not modify persistent mock storage before successful recovery.

Recovery can therefore include both:

```text
Queue-state recovery
```

and:

```text
Data-state protection
```

---

# 34. Miscompare Lifecycle

A miscompare case can complete normally through the entire SQ/CQ lifecycle:

```text
CQ Status = SUCCESS
```

while returning corrupted data.

No reset is required because the command lifecycle itself succeeded.

The validation failure point is the data comparison rather than queue/completion handling.

---

# 35. Runtime Trace

The runner trace is structured lifecycle evidence.

It can reconstruct:

- current stage;
- queue progression;
- outstanding CID behavior;
- completion behavior;
- timeout point.

It is more than a debug string.

---

# 36. Trace vs Queue Snapshot

```text
trace
= lifecycle history

queue_state
= final state snapshot
```

Both are useful evidence and answer different questions.

---

# 37. Host Result vs Controller Result

The Host result describes how the Host interpreted execution:

```text
COMMAND_COMPLETE
TIMEOUT
ABORTED
```

The controller result describes what the Mock Controller returned:

```text
SUCCESS
FAILED
INVALID_RANGE
UNSUPPORTED_COMMAND
```

Timeout or user cancellation may have no normal controller result.

---

# 38. Completion Semantics

`completion` represents the logical Host-side CQ completion.

A controller error can still produce a valid completion.

Timeout does not.

Cancellation during active execution does not produce a normal completion.

---

# 39. Cancellation Boundary

STOP v1 is documented in detail in:

```text
11_STOP_v1_Design.md
```

At the command lifecycle boundary, active cancellation can produce:

```text
Cancellation Requested
→ terminate subprocess
→ grace period
→ kill fallback if needed
→ logical reset
→ Host Result = ABORTED
```

---

# 40. Cancellation vs Timeout

Cancellation:

```text
Host Result = ABORTED
Timed Out = false
```

Timeout:

```text
Host Result = TIMEOUT
Timed Out = true
```

These are separate execution semantics even though both interrupt normal command completion.

---

# 41. Cancellation Recovery vs Timeout Recovery

Both may eventually clear logical queue state.

However, their reasons differ:

```text
Timeout recovery
= scenario-defined recovery

Cancellation recovery
= execution-control cleanup
```

The resulting queue state may look similar while the result classification remains different.

---

# 42. Lifecycle Invariants

AMNV should preserve these invariants:

1. every new command receives a new CID;
2. SQ submission makes the CID outstanding;
3. normal CQ consumption removes the CID from outstanding state;
4. timeout does not create a fake normal completion;
5. reset clears outstanding state;
6. reset preserves CID progression;
7. retry is a new command;
8. user cancellation is not timeout;
9. command SUCCESS does not guarantee data integrity.

---

# 43. Lifecycle Comparison

| Lifecycle | Controller Result | Completion | Timed Out | Final Outstanding | Typical Next Step |
| --- | --- | --- | --- | --- | --- |
| Normal SUCCESS | SUCCESS | Exists | false | `[]` | Validate data |
| Error Completion | FAILED / error | Exists | false | `[]` | Correlate / recover |
| Timeout | None | None | true | `[CID]` | Reset / Retry |
| User Abort | No normal result | None | false | reset to `[]` | Stop execution |

---

# 44. Recovery Success Criteria

Recovery is not represented by a single Boolean.

Depending on the scenario, successful recovery may require:

```text
Correct failure detection
+
Correct pre-recovery state
+
Correct reset state
+
Preserved CID progression
+
Correct retry behavior
+
Correct final data
+
Correct final queue state
```

All recovery checks required by the scenario must pass.

---

# 45. Lifecycle Scope Boundary

AMNV models:

```text
Host-side logical commands
SQ / CQ state
Mock Controller process
fault / timeout behavior
logical reset / retry
validation evidence
```

It does not implement:

- physical Host Memory queues;
- MMIO registers;
- PCIe TLPs;
- DMA;
- PRP / SGL movement;
- MSI / MSI-X;
- real NVMe controller-register reset;
- real driver reinitialization.

Terms such as SQ, CQ, doorbell, controller fetch, and reset therefore refer to the AMNV logical model.

---

# 46. Lifecycle Design Summary

The core normal lifecycle is:

```text
Command
→ CID
→ SQ
→ Controller
→ CQ
→ Validation
```

Timeout recovery is:

```text
Command
→ Outstanding
→ Timeout
→ Reset
→ New CID
→ Retry
→ Validation
```

Error-completion recovery is:

```text
Command
→ Error Completion
→ Evidence
→ Scenario-specific Recovery
```

User cancellation is:

```text
Command
→ Cancellation
→ Controlled Termination
→ Logical Recovery
→ ABORTED
```

These lifecycle models form the common technical basis for T05, T08, T09, A01, A02, and STOP v1.
