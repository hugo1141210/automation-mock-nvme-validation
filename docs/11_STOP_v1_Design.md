# STOP v1 設計 / STOP v1 Design

# 中文版

## 1. 文件目的

本文件說明 **Automation Mock NVMe Validation（AMNV）** 的 **STOP v1 Cooperative Cancellation** 設計。

STOP v1 的目的不是單純讓 GUI 上有一個「停止」按鈕，而是要建立一套可追蹤、可恢復、可報告的執行中止機制。

本文件集中說明：

- 為什麼不使用 `QThread.terminate()`；
- `CancellationToken` 的角色；
- GUI、Worker、Test、Automation、Runner 之間如何傳遞 Stop State；
- Individual Test 如何中止；
- A01 如何產生 `ABORTED / NOT_RUN / STOPPED`；
- A02 如何產生 `ABORTED / NOT_RUN / STOPPED`；
- Active `fake_nvme.py` subprocess 如何終止；
- Abort 後 Queue / Outstanding State 如何恢復；
- Timeout 與 User Abort 如何區分；
- Partial Report 如何保留 Evidence；
- STOP v1 的限制與非目標。

STOP v1 的核心原則可以概括為：

```text
Request Stop
→ Cooperative Detection
→ Controlled Termination
→ Logical Recovery
→ Preserve Evidence
→ Return Structured Result
```

---

# 2. STOP v1 的設計目標

STOP v1 需要同時滿足五個目標。

## 2.1 GUI 必須保持可操作

Test / Automation 執行時，Main Thread 不應被阻塞。

因此使用者必須能在：

```text
T05
A01
A02
```

執行期間按下：

```text
Test Stop
```

---

## 2.2 Stop 不能等於強制 Thread Kill

停止不能直接理解為：

```text
Kill worker thread immediately
```

因為這可能發生在：

- Queue State 正在更新；
- Storage 正在修改；
- Runtime Log 正在寫入；
- Result 正在建立；
- Report Evidence 尚未完成。

如果強制停止，可能留下：

```text
Partial State
Unknown State
Inconsistent State
```

因此 STOP v1 使用 Cooperative Cancellation。

---

## 2.3 User Stop 必須和 Functional Failure 分開

User Stop 不表示：

```text
Test FAIL
```

因此需要額外 Result State：

```text
ABORTED
```

Suite / Campaign 則使用：

```text
STOPPED
```

尚未開始的 Unit 使用：

```text
NOT_RUN
```

---

## 2.4 Abort 後必須恢復 Logical State

如果 Stop 發生在 active Mock Controller subprocess：

```text
Command 可能已經進入 SQ
CID 可能是 Outstanding
Controller Process 可能還在執行
```

所以不能只把 subprocess 終止就結束。

STOP v1 還需要：

```text
logical controller reset
```

以清除不完整 Queue / Outstanding State。

---

## 2.5 Partial Execution 也必須可報告

停止後仍需要知道：

- 哪些 Unit 已完成；
- 哪個 Unit 被中止；
- 哪些 Unit 未開始；
- Stop 發生在哪個 Stage；
- 是否有 active subprocess；
- Process 如何終止；
- Queue 是否恢復；
- CID progression 是否保留。

所以：

```text
STOP
```

不是：

```text
Discard execution
```

而是：

```text
Terminate execution while preserving evidence
```

---

# 3. STOP v1 主要模組

主要涉及：

```text
amnv/cancellation.py
amnv/runner.py
amnv/test_cases/t01...t09
amnv/automation/a01_full_validation.py
amnv/automation/a02_fault_campaign.py
amnv/ui/main_window.py
amnv/ui/test_worker.py
amnv/reporting/a01_reporter.py
amnv/reporting/a02_report.py
```

責任分工：

| 模組 | STOP 角色 |
| --- | --- |
| `cancellation.py` | 保存 Stop State / Reason |
| `main_window.py` | 建立 Token、接收 Stop Button |
| `test_worker.py` | 執行 Task，本身不負責 Stop |
| `test_cases/*` | 在 Scenario Boundary 檢查 Stop |
| `runner.py` | Active subprocess cancellation / recovery |
| `a01_full_validation.py` | Test-level stop orchestration |
| `a02_fault_campaign.py` | Case-level stop orchestration |
| Reporter | 保存 Partial Execution Evidence |

---

# 4. 為什麼不使用 `QThread.terminate()`

`QThread.terminate()` 屬於非合作式強制終止。

它的風險在於 Thread 可能在任意 Python / Qt 執行點被停止。

例如：

```text
Queue State 更新到一半
```

或：

```text
Result object 尚未完成
```

或：

```text
Storage write 進行中
```

此時強制結束會讓系統難以回答：

```text
到底執行到哪裡？
Queue 是否一致？
Storage 是否完成？
這個 Test 應該算 FAIL、ERROR 還是 Stop？
```

因此 STOP v1 不依賴：

```text
QThread.terminate()
```

Worker Thread 會讓目前的 Task 自己返回，然後走正常：

```text
finished
→ thread.quit()
→ cleanup
```

流程。

---

# 5. CancellationToken

## 5.1 定位

`CancellationToken` 是 STOP v1 的共享執行控制物件。

核心實作基於：

```text
threading.Event
```

目的為：

- Thread-safe；
- GUI Thread 可直接設定；
- Worker / Test / Runner 可以查詢；
- 不依賴 Qt Event Queue 才能收到 Stop。

---

## 5.2 主要行為

概念 API：

```text
request()
is_requested()
wait()
reason
```

### `request()`

提出 Stop Request。

### `is_requested()`

讓 Test / Runner 查詢目前是否已要求停止。

### `wait()`

需要 blocking wait 的地方可使用。

### `reason`

保存 Stop Reason。

目前典型 Reason：

```text
User requested stop
```

---

## 5.3 第一次 Stop Reason 保留

如果 Stop Button 被連續按多次：

```text
Stop
Stop
Stop
```

不應一直覆寫原本 Reason。

STOP v1 保留第一次 Stop Reason。

目的為：

- Stop request idempotent；
- Evidence 穩定；
- 不因重複操作改變原始執行事實。

---

# 6. Token Lifecycle

每次執行都使用新的 Token：

```text
Start Test
→ New Token
→ Run
→ Finish
→ Discard Token
```

或：

```text
Start A01
→ New Token
→ Run Suite
→ Finish
→ Discard Token
```

或：

```text
Start A02
→ New Token
→ Run Campaign
→ Finish
→ Discard Token
```

不重用舊 Token。

也不設計：

```text
token.reset()
```

原因是 Stop State 不應跨 Run 汙染下一次執行。

---

# 7. GUI Stop Flow

GUI 的基本流程：

```text
User clicks Test Stop
↓
main_window.py
↓
active CancellationToken.request()
↓
Backend observes token
↓
Task returns ABORTED / STOPPED result
↓
Worker finishes
↓
Thread cleanup
```

GUI 只負責：

```text
Request Stop
```

不負責直接決定：

```text
T05 = ABORTED
A01 = STOPPED
```

這些 Result 由 Backend 根據實際執行狀態產生。

---

# 8. 為什麼 Token 要由 GUI 直接設定

如果 Stop 只透過 Worker Thread 的 Qt queued signal 傳入：

```text
GUI
→ queued slot
→ Worker
```

但 Worker 當時正在長時間執行 Python Function，可能沒有機會即時處理 Event Queue。

因此 STOP v1 使用共享 Token：

```text
GUI Thread
→ Event.set()
```

Backend 可以直接看見：

```text
is_requested() == true
```

不需要等 Worker 回到 Qt Event Loop。

---

# 9. TestWorker 的角色

`TestWorker` 是 Generic Background Worker。

它的責任只有：

```text
run callable
emit result
emit error
emit finished
```

它不實作：

- CancellationToken；
- subprocess terminate；
- Queue Reset；
- ABORTED 判定；
- STOPPED 判定。

這是刻意的設計。

STOP Logic 屬於：

```text
Execution / Validation Layer
```

而不是：

```text
Thread Adapter Layer
```

---

# 10. Cancellation Checkpoint

Individual Test 會在適當的 Scenario Boundary 檢查 Token。

常見位置例如：

```text
BEFORE_IDENTIFY
BEFORE_READ
BEFORE_COMMAND
INITIAL_READ
FAULT_COMMAND
```

Checkpoint 的目的，是讓 Result 能保留：

```text
Abort Stage
```

而不是只有：

```text
Stopped somewhere
```

---

# 11. Stop Before Command Starts

如果 Token 在 Command 尚未開始前已被 request：

```text
Cancellation Requested
↓
Test checks token
↓
No command executed
↓
Test = ABORTED
```

Evidence 可以是：

```text
Abort Stage = BEFORE_READ
Commands = []
```

此時不需要 terminate subprocess，因為根本沒有 active Controller Process。

---

# 12. Stop During Active Command

如果 Stop 發生在：

```text
runner.execute(...)
```

正在等待 `fake_nvme.py` subprocess 時：

```text
GUI requests stop
↓
Runner detects cancellation
↓
Begin active-command abort sequence
```

這是 STOP v1 最重要的路徑。

---

# 13. Active Subprocess Termination

STOP v1 對 active subprocess 採：

```text
terminate()
↓
wait approximately 0.5 seconds
↓
if still alive:
    kill()
```

目的：

### `terminate()`

先給 Process 一個正常終止機會。

### Grace Period

避免立刻使用更強制的 Kill。

### `kill()`

只有 Process 在 Grace Period 後仍未退出時才使用 fallback。

---

# 14. Process Termination Evidence

Abort Result 應保存：

```text
termination_method
```

例如：

```text
terminate
```

或必要時：

```text
kill
```

這讓 Report 能回答：

> Active Controller Process 最後是怎麼被停止的？

---

# 15. Abort 後 Logical Reset

只停止 subprocess 還不夠。

因為 active Command 可能已經完成：

```text
SQ_SUBMIT
CTRL_FETCH
```

因此 CID 可能仍存在：

```text
outstanding_cids
```

STOP v1 在 active command abort 後執行：

```text
logical controller reset
```

Reset 清除：

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

---

# 16. 為什麼保留 next_cid

假設：

```text
CID 1
```

已經被配置並進入 active execution。

即使使用者中止：

```text
CID 1
```

仍是一筆已經存在過的 Command。

因此 Recovery 後：

```text
next_cid = 2
```

而不是重新回到：

```text
next_cid = 1
```

這和 Timeout Recovery 使用相同 CID progression 原則。

---

# 17. Active Command Abort Result

active command 被成功中止後，Runner-level Evidence 應具有：

```text
Host Result = ABORTED
Timed Out = false
Completion = None
```

以及：

```text
Queue after abort = reset
Outstanding = []
Next CID = preserved
```

這裡：

```text
Timed Out = false
```

非常重要。

因為：

> 是使用者中止 Command，而不是 Host Timeout。

---

# 18. ABORTED 與 TIMEOUT

兩者都可能造成正常 CQ Lifecycle 沒有完成。

但 Result Semantics 完全不同。

| 項目 | TIMEOUT | ABORTED |
| --- | --- | --- |
| 原因 | Timeout Window 到期 | User Stop |
| Host Result | `TIMEOUT` | `ABORTED` |
| Timed Out | `true` | `false` |
| Normal CQ | No | No |
| Outstanding before recovery | remains | may remain |
| Recovery | Scenario-defined | cancellation cleanup |
| Test Meaning | Functional Scenario | Execution Control |

所以：

```text
ABORTED != TIMEOUT
```

---

# 19. ABORTED 與 FAIL

`FAIL`：

```text
Test 完整執行到可以判斷
但 Actual != Expected
```

`ABORTED`：

```text
Test 尚未完成
因使用者要求停止
```

因此：

```text
ABORTED != FAIL
```

這是 STOP v1 必須存在獨立 Result State 的主要原因。

---

# 20. Individual T01～T09 Stop

T01～T09 都支援 CancellationToken。

概念：

```text
run(cancellation_token=token)
```

Test 可以在：

```text
Before Command
Between Commands
Recovery Stage
```

檢查 Token。

如果 Stop：

```text
Result = ABORTED
```

Individual Test 不需要產生 Suite-level：

```text
STOPPED
```

因為它本身沒有剩餘排程單元。

---

# 21. Individual Test Stop Evidence

Individual Test 的 `details` 應至少保存：

```text
abort.stage
abort.reason
```

如果 active command 已啟動，還應包含：

```text
command
host result
termination
queue recovery
```

---

# 22. A01 Stop Orchestration

A01 依序執行：

```text
T01
T02
...
T09
```

Cancellation 可以發生在：

1. Test 之間；
2. Active Test 內；
3. Test 正好完成的邊界。

A01 必須依實際狀態分類。

---

# 23. A01 — Completed Test

如果某 Test 已經正常返回：

```text
PASS
FAIL
ERROR
```

之後才收到 Stop：

```text
保留原 Result
```

不回溯改成：

```text
ABORTED
```

這稱為：

```text
Completed Result Preservation
```

---

# 24. A01 — Active Test

如果 Stop 真正中斷目前 Test：

```text
Active Test = ABORTED
```

例如：

```text
T05 ABORTED
```

---

# 25. A01 — Remaining Tests

尚未開始的 Test：

```text
NOT_RUN
```

例如：

```text
T06 NOT_RUN
T07 NOT_RUN
T08 NOT_RUN
T09 NOT_RUN
```

這些不是 FAIL。

因為：

```text
沒有被執行
```

---

# 26. A01 Suite Result

只要是 User Stop 導致 Suite 未完整執行：

```text
Suite = STOPPED
```

而不是：

```text
FAIL
```

---

# 27. A01 Representative STOP State

代表性狀態：

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

---

# 28. A01 Executed Counting

`ABORTED` 算：

```text
Executed
```

因為 Test 已經開始。

所以：

```text
Executed
=
Passed + Failed + Error + Aborted
```

`NOT_RUN` 不算 Executed。

---

# 29. A01 Partial Report

STOPPED A01 仍產生 PDF。

Partial Report 必須能呈現：

```text
Suite = STOPPED
Stop Reason
Executed / Total
Aborted Test
Not Run Count
```

並保存 Active Test 的：

```text
Abort Stage
Command CID
Opcode
LBA
Host Result
Timed Out
Process Termination
Queue After Abort
Outstanding
Next CID
```

這讓 STOP 成為可驗證功能，而不只是 GUI 操作。

---

# 30. A02 Stop Orchestration

A02 的單位不是 T01～T09，而是：

```text
Fault Campaign Case
```

例如：

```text
A02-FP01-C01
A02-FP01-C02
...
```

STOP Semantics 和 A01 相同，但套用到 Case Level。

---

# 31. A02 — Completed Case

已完成的 Case：

```text
PASS
FAIL
ERROR
```

保留原 Result。

---

# 32. A02 — Active Case

被中斷的 Case：

```text
ABORTED
```

---

# 33. A02 — Remaining Cases

未開始的 Case：

```text
NOT_RUN
```

---

# 34. A02 Campaign Result

User Stop 導致 Campaign 未完成：

```text
Campaign = STOPPED
```

---

# 35. A02 Representative STOP State

代表性狀態：

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

Campaign = STOPPED
```

也可能在第一個 active Case 就中止：

```text
Case 1 ABORTED
Remaining 8 NOT_RUN
```

只要 Classification 正確即可。

---

# 36. A02 Partial Validation Checks

A02 Active Case 可能在 Abort 前已完成部分 Setup Check。

所以 Report 可能出現：

```text
Validation Checks 2 / 2 PASS
Result = ABORTED
```

這並不矛盾。

因為：

```text
已完成的局部 Checks = PASS
但完整 Case 尚未完成
```

所以 Case 最終仍是：

```text
ABORTED
```

---

# 37. NOT_RUN Result 建立

對 Remaining Test / Case，Automation 不應只把它們從 Result List 消失。

而應建立明確：

```text
NOT_RUN
```

Result。

目的：

- Summary Total 可以保持完整；
- Report 可以看出排程範圍；
- 使用者可以區分「沒有排入」與「排入但沒執行」。

---

# 38. NOT_RUN Evidence

典型：

```text
Expected: Scheduled for execution
Actual: Not run because suite stop was requested
Validation Checks: Not executed
Duration: 0.000 s
```

這樣 Report 可以完整描述 Partial Execution。

---

# 39. Stop Request 發生在 Test 完成邊界

可能發生 Race-like Timing：

```text
User clicks Stop
```

同時 Active Test 正好已完成。

STOP v1 原則：

> 以 Test 實際完成狀態為準。

如果 Test 已經成功回傳：

```text
PASS
```

就保留：

```text
PASS
```

剩餘 Unit 再依 Cancellation 判斷：

```text
NOT_RUN
```

不能因為 Stop Click 時間接近就把已完成 Unit 改成 ABORTED。

---

# 40. Stop Request 重複輸入

如果使用者連續按 Stop：

```text
request()
request()
request()
```

不應造成：

- 重複 terminate；
- 重複 reset；
- 重複產生 ABORTED；
- Reason 被覆寫。

STOP v1 將 Cancellation Request 視為：

```text
idempotent control signal
```

---

# 41. Stop 後 Worker Cleanup

Backend Task 返回後：

```text
TestWorker.result
or
TestWorker.error
```

最後一定會：

```text
finished
```

GUI 再進行：

```text
thread.quit()
cleanup references
restore active state
```

因此 Stop 不會讓 GUI Thread Lifecycle 留在不明狀態。

---

# 42. Stop 後下一次執行

STOP Recovery 完成後，下一輪 Test / Automation 應可以正常開始。

必要條件：

```text
No active controller subprocess
Outstanding = []
Queue logically recovered
Old cancellation token discarded
New token created
```

這是 STOP v1 Recovery 是否完整的重要判斷。

---

# 43. Cancellation Recovery 的範圍

STOP v1 Recovery 處理的是：

```text
AMNV logical command / queue state
```

它不聲稱模擬：

- 真實 NVMe Controller Reset；
- 真實 PCIe Function Level Reset；
- Driver Reinitialization；
- Hardware Power Cycle。

---

# 44. STOP v1 不保證 Hard-stop 任意 Python Code

STOP v1 是 Cooperative Cancellation。

所以它依賴：

```text
Task 有 Cancellation Checkpoint
```

或：

```text
Runner 正在控制 active subprocess
```

如果未來某段 Python Logic：

```text
while True:
    pass
```

而且完全不檢查 Token：

STOP v1 不保證能立即停止這段任意 Python Code。

---

# 45. STOP v1 對 Deadlock 的限制

如果未來某個 Python Thread 發生真正的 Deadlock，而且：

- 不返回；
- 不檢查 Token；
- 不在 Runner 可控制的 subprocess 中；

STOP v1 也不能保證硬中止。

這是 v1 的明確限制。

---

# 46. 為什麼接受這個限制

因為目前 AMNV 的執行模式主要是：

```text
短時間 Python Scenario Logic
+
可控制的 fake_nvme.py subprocess
```

對目前專案而言，Cooperative Cancellation：

- 風險較低；
- State 較容易保持一致；
- Evidence 比較完整；
- 不需要引入 Process-based Worker Architecture。

因此符合 v1 的 Scope。

---

# 47. STOP v1 非目標

STOP v1 不處理：

- 任意 Python hard kill；
- OS-level process tree manager；
- distributed cancellation；
- remote machine cancellation；
- multi-worker coordinated stop；
- crash recovery after application termination；
- persistent resume / checkpoint；
- power-loss recovery。

---

# 48. STOP v1 Result State Matrix

| Situation | Unit Result | Suite / Campaign | Timed Out |
| --- | --- | --- | --- |
| Normal completion | PASS / FAIL / ERROR | PASS / FAIL | Depends on scenario |
| User abort before command | ABORTED | STOPPED if in suite | false |
| User abort during command | ABORTED | STOPPED if in suite | false |
| Scheduled but never started | NOT_RUN | STOPPED | N/A |
| Functional timeout scenario | PASS / FAIL based on checks | PASS / FAIL | true |
| Unexpected exception | ERROR | FAIL unless cancellation semantics apply | depends |

---

# 49. STOP v1 Evidence Checklist

一個完整的 Active Stop Evidence 至少應能回答：

```text
Was stop requested?
Why?
Which unit was active?
Which stage?
Which command?
Was a subprocess running?
How was it terminated?
Was it a timeout?
What was the queue state after recovery?
Were outstanding CIDs cleared?
What was next_cid?
Which remaining units were NOT_RUN?
What was the final suite result?
```

---

# 50. STOP v1 設計總結

STOP v1 的完整概念是：

```text
GUI Stop
↓
CancellationToken.request()
↓
Active code observes token
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
Suite / Campaign = STOPPED
↓
Partial Evidence Report
```

它的核心價值不是「可以停」，而是：

> 可以在停止時仍保持正確的 Result Classification、Logical State Recovery 與可追查 Evidence。

---

# English Version

## 1. Document Purpose

This document describes the **STOP v1 cooperative cancellation design** of **Automation Mock NVMe Validation (AMNV)**.

STOP v1 is not merely a GUI stop button.

It provides a controlled execution-cancellation mechanism that preserves result semantics, logical recovery state, and validation evidence.

The design covers:

- why `QThread.terminate()` is not used;
- the `CancellationToken`;
- stop-state propagation across GUI, tests, automation, and runner;
- individual-test cancellation;
- A01 `ABORTED / NOT_RUN / STOPPED` behavior;
- A02 `ABORTED / NOT_RUN / STOPPED` behavior;
- active subprocess termination;
- queue/outstanding recovery;
- timeout versus user cancellation;
- partial reporting;
- STOP v1 limitations.

The core model is:

```text
Request Stop
→ Cooperative Detection
→ Controlled Termination
→ Logical Recovery
→ Preserve Evidence
→ Structured Result
```

---

# 2. Design Goals

STOP v1 has five main goals:

1. keep the GUI responsive while validation is running;
2. avoid forcefully killing worker threads;
3. separate user cancellation from functional validation failure;
4. restore logical queue/outstanding state after interruption;
5. preserve partial execution evidence.

---

# 3. Main Modules

The design primarily involves:

```text
amnv/cancellation.py
amnv/runner.py
amnv/test_cases/t01...t09
amnv/automation/a01_full_validation.py
amnv/automation/a02_fault_campaign.py
amnv/ui/main_window.py
amnv/ui/test_worker.py
amnv/reporting/a01_reporter.py
amnv/reporting/a02_report.py
```

---

# 4. Why `QThread.terminate()` Is Avoided

Forceful worker-thread termination can interrupt execution at arbitrary points.

Possible consequences include:

- partially updated queue state;
- incomplete storage operations;
- incomplete log/evidence generation;
- inconsistent result objects.

STOP v1 therefore uses cooperative cancellation.

The backend returns normally, allowing the worker to emit `finished` and the Qt thread lifecycle to clean up normally.

---

# 5. CancellationToken

`CancellationToken` is the shared execution-control object.

It is based on a thread-safe event and conceptually provides:

```text
request()
is_requested()
wait()
reason
```

The first stop reason is preserved.

Repeated stop requests do not replace the original reason.

---

# 6. Token Lifecycle

Every individual test, A01 run, or A02 run receives a fresh token.

```text
Run Start
→ New Token
→ Optional Stop Request
→ Run Finish
→ Discard Token
```

Tokens are not reused or reset.

This prevents cancellation state from contaminating later runs.

---

# 7. GUI Stop Flow

```text
User clicks Test Stop
→ main_window.py
→ CancellationToken.request()
→ Backend observes token
→ Structured ABORTED / STOPPED result
→ Worker finishes
→ Thread cleanup
```

The GUI requests cancellation but does not directly assign validation result states.

---

# 8. Why the GUI Sets the Shared Token Directly

A worker that is busy executing a long Python function may not immediately process a queued Qt slot.

A shared event allows the GUI thread to set cancellation state directly.

The active backend code can observe it without requiring the worker to return to the Qt event loop.

---

# 9. TestWorker Responsibility

`TestWorker` remains a generic callable executor.

It does not implement:

- cancellation policy;
- subprocess termination;
- logical reset;
- ABORTED classification;
- STOPPED classification.

Those responsibilities belong to validation/execution code.

---

# 10. Cancellation Checkpoints

Individual tests inspect cancellation at meaningful scenario boundaries.

Examples include stages such as:

```text
BEFORE_IDENTIFY
BEFORE_READ
BEFORE_COMMAND
INITIAL_READ
FAULT_COMMAND
```

A named checkpoint allows evidence to record exactly where execution was interrupted.

---

# 11. Stop Before a Command

If cancellation is already requested before a command starts:

```text
Test checks token
→ Command not launched
→ Result = ABORTED
```

No subprocess termination is required.

---

# 12. Stop During an Active Command

When a stop occurs while `CommandRunner` is waiting for an active `fake_nvme.py` subprocess:

```text
Runner detects cancellation
→ begin active-command abort sequence
```

---

# 13. Active Subprocess Termination

STOP v1 uses:

```text
terminate()
→ approximately 0.5 s grace period
→ kill() fallback if still alive
```

The design prefers graceful process termination before using the stronger fallback.

---

# 14. Termination Evidence

Abort evidence records the actual termination method, such as:

```text
terminate
```

or:

```text
kill
```

This makes active-command interruption auditable.

---

# 15. Logical Reset After Abort

Terminating the subprocess alone is insufficient because the command may already be in SQ/outstanding state.

STOP v1 therefore performs logical controller reset after an active-command abort.

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

---

# 16. CID Progression After Abort

An allocated CID remains historically consumed even when its command is aborted.

Example:

```text
CID 1 active
→ User Stop
→ Reset
→ next_cid = 2
```

This keeps original and later commands distinguishable.

---

# 17. Active Abort Result

Expected active-command cancellation evidence includes:

```text
Host Result = ABORTED
Timed Out = false
Completion = None
Outstanding after recovery = []
Queue logically reset
next_cid preserved
```

The `Timed Out = false` distinction is essential.

---

# 18. ABORTED vs TIMEOUT

| Item | TIMEOUT | ABORTED |
| --- | --- | --- |
| Cause | Timeout window | User stop |
| Host Result | `TIMEOUT` | `ABORTED` |
| Timed Out | true | false |
| Normal CQ | No | No |
| Recovery reason | Scenario recovery | Cancellation cleanup |

Therefore:

```text
ABORTED != TIMEOUT
```

---

# 19. ABORTED vs FAIL

`FAIL` means validation completed but actual behavior did not match expected behavior.

`ABORTED` means the unit did not complete because execution was cancelled by the user.

Therefore:

```text
ABORTED != FAIL
```

---

# 20. Individual Test Stop

T01–T09 accept a cancellation token and can stop at scenario checkpoints.

Individual tests return:

```text
ABORTED
```

They do not return suite-level `STOPPED`, because there are no remaining scheduled units at the individual-test level.

---

# 21. Individual Abort Evidence

Individual abort evidence should preserve:

```text
abort stage
stop reason
```

and, when an active command exists:

```text
command
host result
termination method
queue recovery
```

---

# 22. A01 Stop Orchestration

A01 must classify three kinds of tests:

```text
Completed
Active Interrupted
Never Started
```

---

# 23. Completed A01 Tests

Tests that already returned:

```text
PASS
FAIL
ERROR
```

retain their original result.

They are never retroactively changed to `ABORTED`.

---

# 24. Active A01 Test

The test actually interrupted by cancellation becomes:

```text
ABORTED
```

---

# 25. Remaining A01 Tests

Scheduled tests that never start become:

```text
NOT_RUN
```

---

# 26. A01 Suite Result

If user cancellation prevents the full scheduled suite from completing:

```text
Suite = STOPPED
```

not `FAIL`.

---

# 27. Representative A01 Stop State

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

# 28. A01 Counting

`ABORTED` is included in `Executed` because the test started.

`NOT_RUN` is excluded because the test never started.

```text
Executed
=
Passed + Failed + Error + Aborted
```

---

# 29. A01 Partial Report

A stopped A01 run still produces a PDF report.

The report should preserve:

- suite STOPPED state;
- stop reason;
- executed / total counts;
- aborted test;
- not-run count;
- interruption stage;
- command information;
- termination method;
- queue recovery;
- next CID.

---

# 30. A02 Stop Orchestration

A02 applies the same semantics at fault-case level.

The units are campaign cases rather than T01–T09 tests.

---

# 31. Completed A02 Cases

Completed cases retain:

```text
PASS
FAIL
ERROR
```

---

# 32. Active A02 Case

The interrupted case becomes:

```text
ABORTED
```

---

# 33. Remaining A02 Cases

Cases that never start become:

```text
NOT_RUN
```

---

# 34. A02 Campaign Result

A user-cancelled campaign becomes:

```text
STOPPED
```

---

# 35. Representative A02 Stop State

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

Campaign = STOPPED
```

Stopping during the first case is also valid if the classification and evidence are correct.

---

# 36. Partial Checks in an Aborted Case

An A02 case may complete setup checks before being interrupted during the fault command.

It is therefore valid for a report to contain:

```text
Validation Checks: completed subset PASS
Case Result: ABORTED
```

The partial checks describe completed work; the final case result describes incomplete execution.

---

# 37. NOT_RUN Result Creation

Remaining scheduled tests/cases are explicitly represented as `NOT_RUN` rather than being omitted from the result list.

This preserves:

- total scheduled scope;
- summary accuracy;
- report traceability.

---

# 38. NOT_RUN Evidence

A NOT_RUN result can include:

```text
Expected: Scheduled for execution
Actual: Not run because stop was requested
Validation Checks: Not executed
Duration: 0.000 s
```

---

# 39. Cancellation Near Completion

If a cancellation request arrives at nearly the same time a test completes, the actual completed state is preserved.

A completed PASS / FAIL / ERROR is not retroactively replaced by ABORTED.

Cancellation only affects units that are truly interrupted or not yet started.

---

# 40. Repeated Stop Requests

Repeated stop requests are treated as idempotent control input.

They should not cause:

- repeated process termination;
- repeated reset;
- duplicate ABORTED results;
- replacement of the first stop reason.

---

# 41. Worker Cleanup

After backend execution returns, `TestWorker` still emits `finished`.

The GUI then performs normal thread cleanup.

Cancellation therefore does not bypass the standard worker/thread lifecycle.

---

# 42. Next Run After Stop

A new test or automation run should start normally after STOP recovery.

Required conditions include:

```text
No active controller subprocess
Outstanding = []
Logical queue recovered
Old token discarded
New token created
```

---

# 43. Recovery Scope

STOP v1 recovers the AMNV logical command/queue model.

It does not claim to implement or validate:

- real NVMe controller reset;
- PCIe Function Level Reset;
- real driver reinitialization;
- hardware power cycling.

---

# 44. No Arbitrary Python Hard-stop Guarantee

STOP v1 is cooperative.

It depends on code reaching a cancellation checkpoint or being inside an active subprocess controlled by the runner.

If arbitrary Python code enters a non-cooperative infinite loop, STOP v1 does not guarantee immediate termination.

---

# 45. Deadlock Limitation

A true worker-thread deadlock that:

- never returns;
- never checks the token;
- is not inside a runner-managed subprocess;

cannot be guaranteed to stop under STOP v1.

---

# 46. Why This Limitation Is Accepted

The current AMNV workload consists mainly of:

```text
short Python scenario logic
+
runner-controlled mock-controller subprocesses
```

For this architecture, cooperative cancellation provides:

- safer state handling;
- better evidence preservation;
- lower complexity;
- no need for a process-based worker framework.

This matches the intended v1 scope.

---

# 47. STOP v1 Non-goals

STOP v1 does not implement:

- arbitrary Python thread hard kill;
- operating-system process-tree management;
- distributed cancellation;
- remote-host cancellation;
- multi-worker coordinated shutdown;
- persistent resume/checkpoint;
- crash recovery after application termination;
- power-loss recovery.

---

# 48. Result State Matrix

| Situation | Unit Result | Suite / Campaign | Timed Out |
| --- | --- | --- | --- |
| Normal completion | PASS / FAIL / ERROR | PASS / FAIL | Scenario-dependent |
| User abort before command | ABORTED | STOPPED if orchestrated | false |
| User abort during command | ABORTED | STOPPED if orchestrated | false |
| Scheduled but never started | NOT_RUN | STOPPED | N/A |
| Functional timeout scenario | PASS / FAIL by checks | PASS / FAIL | true |
| Unexpected exception | ERROR | FAIL unless cancellation semantics apply | Scenario-dependent |

---

# 49. Evidence Checklist

A complete active-stop record should answer:

```text
Was stop requested?
Why?
Which unit was active?
At which stage?
Which command was interrupted?
Was a subprocess active?
How was it terminated?
Was this a timeout?
What queue state remained after recovery?
Were outstanding CIDs cleared?
What was next_cid?
Which scheduled units were NOT_RUN?
What was the final suite/campaign result?
```

---

# 50. STOP v1 Design Summary

The complete STOP v1 flow is:

```text
GUI Stop
↓
CancellationToken.request()
↓
Active code observes token
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
Suite / Campaign = STOPPED
↓
Partial Evidence Report
```

The key value of STOP v1 is not merely the ability to stop execution.

It is the ability to stop while preserving correct result classification, logical state recovery, and traceable validation evidence.
