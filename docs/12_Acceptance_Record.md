# 驗收紀錄 / Acceptance Record

# 中文版

## 1. 文件目的

本文件用來記錄 **Automation Mock NVMe Validation（AMNV）** 的正式驗收結果。

本文件與 `09_Acceptance_Plan.md` 的差異如下：

```text
09_Acceptance_Plan.md
= 驗收前定義要測什麼、預期什麼

12_Acceptance_Record.md
= 驗收後記錄實際跑了什麼、實際得到什麼結果
```

因此本文件不得預先填入假想的 PASS。

只有在實際執行完成後，才能填寫：

- Actual Result；
- PASS / FAIL；
- Report Path；
- Screenshot；
- Console Evidence；
- Date；
- Note。

---

# 2. 驗收紀錄原則

正式 Acceptance Record 應遵守下列原則。

## 2.1 只記錄實際執行結果

不可因為：

```text
程式理論上應該成功
```

就填：

```text
PASS
```

必須真的執行過對應 Acceptance Item。

---

## 2.2 Expected 與 Actual 分開

每個項目都應明確記錄：

```text
Expected
Actual
```

避免只寫：

```text
PASS
```

卻沒有說明實際觀察到什麼。

---

## 2.3 Evidence 必須可追溯

如果 Acceptance Result 依據：

- PDF；
- Screenshot；
- Console Output；
- Runtime Log；
- Storage State；

應記錄實際 Evidence File / Path。

---

## 2.4 FAIL 不應被覆寫

如果某次 Acceptance FAIL：

先保留該次紀錄。

修正後再新增：

```text
Re-test
```

而不是把原本 FAIL 改成 PASS，讓失敗歷史消失。

---

# 3. Overall Acceptance Summary

> 此表只在實際驗收後填寫。

| Acceptance ID | Scenario | Result | Date | Evidence | Note |
| --- | --- | --- | --- | --- | --- |
| AC-01 | Environment |  |  |  |  |
| AC-02 | Static / Startup |  |  |  |  |
| AC-03 | T01～T09 Individual Tests |  |  |  |  |
| AC-04 | A01 Full Validation |  |  |  |  |
| AC-05 | A02 Fault Campaign |  |  |  |  |
| AC-06 | STOP v1 |  |  |  |  |
| AC-07 | GUI / Report / Evidence |  |  |  |  |
| FINAL | Final Acceptance Gate |  |  |  |  |

---

# 4. AC-01 — Environment

## 4.1 Python Version

Expected：

```text
Python 3.12.3
```

Actual：

```text

```

Result：

```text

```

Evidence：

```text

```

Date：

```text

```

Note：

```text

```

---

## 4.2 pip Version

Expected：

```text
pip 26.2.1
```

Actual：

```text

```

Result：

```text

```

Evidence：

```text

```

---

## 4.3 Virtual Environment

Expected：

```text
.venv activated successfully
```

Actual：

```text

```

Result：

```text

```

Evidence：

```text

```

---

## 4.4 Dependency Installation

Expected：

```text
pip install -r requirements.txt
completes without error
```

Actual：

```text

```

Result：

```text

```

Evidence：

```text

```

---

## 4.5 Dependency Baseline

Expected：

```text
charset-normalizer==3.5.1
pillow==12.3.0
PySide6==6.11.2
PySide6_Addons==6.11.2
PySide6_Essentials==6.11.2
reportlab==5.0.1
shiboken6==6.11.2
```

Actual：

```text

```

Result：

```text

```

Evidence：

```text

```

---

# 5. AC-02 — Static / Startup

## 5.1 Python Syntax Check

Expected：

```text
No SyntaxError
```

Actual：

```text

```

Result：

```text

```

Evidence：

```text

```

---

## 5.2 GUI Startup

Expected：

- Main Window opens；
- T01～T09 visible；
- A01 / A02 visible；
- Control buttons visible；
- Console initializes；
- No startup exception。

Actual：

```text

```

Result：

```text

```

Evidence：

```text

```

---

## 5.3 Initial Runtime State

Expected：

```text
Runtime storage reset to baseline
Runtime log does not contain stale fault evidence
```

Actual：

```text

```

Result：

```text

```

Evidence：

```text

```

---

# 6. AC-03 — Individual Test Acceptance

## 6.1 Summary

| Test | Expected Result | Actual Result | Result | Evidence | Note |
| --- | --- | --- | --- | --- | --- |
| T01 | PASS |  |  |  |  |
| T02 | PASS |  |  |  |  |
| T03 | PASS |  |  |  |  |
| T04 | PASS |  |  |  |  |
| T05 | PASS |  |  |  |  |
| T06 | PASS |  |  |  |  |
| T07 | PASS |  |  |  |  |
| T08 | PASS |  |  |  |  |
| T09 | PASS |  |  |  |  |

---

## 6.2 T01 — Device Baseline

Expected：

```text
PASS
```

Required Evidence：

- IDENTIFY = SUCCESS；
- Device identity fields match baseline；
- SMART = SUCCESS；
- Health values within expected criteria。

Actual：

```text

```

Validation Result：

```text

```

Evidence：

```text

```

---

## 6.3 T02 — Write / Readback

Expected：

```text
PASS
```

Required Evidence：

```text
WRITE SUCCESS
READ SUCCESS
Readback matches written data
```

Actual：

```text

```

Validation Result：

```text

```

Evidence：

```text

```

---

## 6.4 T03 — Invalid Range

Expected：

```text
PASS
```

Required Evidence：

```text
Status = INVALID_RANGE
Error = INVALID_RANGE
Timed Out = false
```

Actual：

```text

```

Validation Result：

```text

```

Evidence：

```text

```

---

## 6.5 T04 — Unsupported Command

Expected：

```text
PASS
```

Required Evidence：

```text
FORMAT
→ UNSUPPORTED_COMMAND
```

Actual：

```text

```

Validation Result：

```text

```

Evidence：

```text

```

---

## 6.6 T05 — Timeout / Recovery

Expected：

```text
PASS
```

Required Evidence：

```text
Initial TIMEOUT
Outstanding CID retained
Reset clears SQ / CQ / Outstanding
next_cid preserved
Retry uses new CID
Retry succeeds
Final queue state correct
```

Actual：

```text

```

Validation Result：

```text

```

Evidence：

```text

```

---

## 6.7 T06 — Data Integrity

Expected：

```text
PASS
```

Required Evidence：

```text
CQ SUCCESS
Returned data mismatch detected
Underlying storage preserved
```

Actual：

```text

```

Validation Result：

```text

```

Evidence：

```text

```

---

## 6.8 T07 — Firmware Log Parsing

Expected：

```text
PASS
```

Required Evidence：

```text
Entry count correct
Required fields present
Known CID / LBA records parsed correctly
```

Actual：

```text

```

Validation Result：

```text

```

Evidence：

```text

```

---

## 6.9 T08 — Read Error Correlation

Expected：

```text
PASS
```

Required Evidence：

```text
FAILED / NAND_READ_FAIL
Timed Out = false
Firmware log correlation matches:
CID / Opcode / LBA / Status / Error
```

Actual：

```text

```

Validation Result：

```text

```

Evidence：

```text

```

---

## 6.10 T09 — Write Failure / Recovery

Expected：

```text
PASS
```

Required Evidence：

```text
FAILED / NAND_PROGRAM_FAIL
Old data preserved
Reset correct
CID progression preserved
Retry WRITE succeeds
Final READ returns recovered data
Final queue state correct
```

Actual：

```text

```

Validation Result：

```text

```

Evidence：

```text

```

---

# 7. AC-04 — A01 Full Validation

Expected：

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

Actual：

```text

```

Result：

```text

```

Report：

```text

```

Screenshot：

```text

```

Console Evidence：

```text

```

Date：

```text

```

Note：

```text

```

---

# 8. AC-05 — A02 Fault Campaign

Expected Coverage：

```text
FP01 timeout               3 cases
FP02 NAND_READ_FAIL        2 cases
FP03 NAND_PROGRAM_FAIL     2 cases
FP04 miscompare            2 cases
Total                      9 cases
```

Expected Result：

```text
Total       9
Executed    9
Passed      9
Failed      0
Error       0
Aborted     0
Not Run     0

Campaign = PASS
```

Actual：

```text

```

Result：

```text

```

Report：

```text

```

Screenshot：

```text

```

Console Evidence：

```text

```

Date：

```text

```

Note：

```text

```

---

# 9. A02 Profile Results

| Profile | Expected | Actual | Result | Evidence |
| --- | --- | --- | --- | --- |
| FP01 | All timeout cases PASS |  |  |  |
| FP02 | All NAND_READ_FAIL cases PASS |  |  |  |
| FP03 | All NAND_PROGRAM_FAIL cases PASS |  |  |  |
| FP04 | All miscompare cases PASS |  |  |  |

---

# 10. AC-06 — STOP v1

## 10.1 Individual Test Stop

Test Used：

```text

```

Expected：

```text
Active Test = ABORTED
Timed Out = false
Queue recovered
Outstanding = []
```

Actual：

```text

```

Result：

```text

```

Evidence：

```text

```

---

## 10.2 A01 STOPPED

Expected Semantics：

```text
Completed Tests
→ preserve result

Active Interrupted Test
→ ABORTED

Remaining Tests
→ NOT_RUN

Suite
→ STOPPED
```

Actual：

```text

```

Summary：

```text

```

Result：

```text

```

Report：

```text

```

Screenshot：

```text

```

Abort Evidence：

```text
Abort Stage:
Stop Reason:
Command:
Host Result:
Timed Out:
Termination Method:
Queue After Abort:
Outstanding:
Next CID:
```

---

## 10.3 A02 STOPPED

Expected Semantics：

```text
Completed Cases
→ preserve result

Active Interrupted Case
→ ABORTED

Remaining Cases
→ NOT_RUN

Campaign
→ STOPPED
```

Actual：

```text

```

Summary：

```text

```

Result：

```text

```

Report：

```text

```

Screenshot：

```text

```

Abort Evidence：

```text
Case ID:
Fault Profile:
Abort Stage:
Stop Reason:
Command:
Host Result:
Timed Out:
Termination Method:
Queue After Abort:
Outstanding:
Next CID:
```

---

# 11. AC-07 — GUI Functional Acceptance

| Item | Expected | Actual | Result | Evidence |
| --- | --- | --- | --- | --- |
| T01～T09 Buttons | Correct test launched |  |  |  |
| A01 Button | Full Validation launched |  |  |  |
| A02 Button | Fault Campaign launched |  |  |  |
| GUI Responsiveness | No freeze during background task |  |  |  |
| Single Active Task | Second task rejected |  |  |  |
| Test Stop | Cooperative stop works |  |  |  |
| Read Current Data | Runtime storage displayed |  |  |  |
| Reset Data | Storage restored to seed baseline |  |  |  |
| Clear Console | Visible text cleared only |  |  |  |
| Open Last Report | Latest PDF opens / safe no-report handling |  |  |  |

---

# 12. Representative PDF Evidence

正式驗收完成後，記錄四份代表性 PDF。

| Evidence | Source Report | Final Display File | Result | Verified |
| --- | --- | --- | --- | --- |
| A01 Full PASS |  | `A01_PASS.pdf` |  |  |
| A01 STOPPED |  | `A01_STOPPED.pdf` |  |  |
| A02 Full PASS |  | `A02_PASS.pdf` |  |  |
| A02 STOPPED |  | `A02_STOPPED.pdf` |  |  |

注意：

```text
Final Display File
```

可在驗收後由原始 timestamp Report 複製 / 重新命名。

Acceptance Record 應保留：

```text
Source Report
```

以確保可追溯。

---

# 13. Report Visual / Content Review

對四份代表性 PDF 分別確認：

| Check | A01 PASS | A01 STOPPED | A02 PASS | A02 STOPPED |
| --- | --- | --- | --- | --- |
| PDF opens correctly |  |  |  |  |
| Title correct |  |  |  |  |
| Result correct |  |  |  |  |
| Summary count correct |  |  |  |  |
| Evidence readable |  |  |  |  |
| No critical text clipping |  |  |  |  |
| Scope statement correct |  |  |  |  |
| STOP evidence correct | N/A |  | N/A |  |

---

# 14. Runtime State After STOP

Expected：

```text
No active controller subprocess
Outstanding = []
Logical queue recovered
Next run can start normally
```

Actual：

```text

```

Result：

```text

```

Evidence：

```text

```

---

# 15. Repeat-run Verification

Automation Used：

```text

```

First Run Result：

```text

```

Second Run Result：

```text

```

Expected：

```text
Same logical validation result
```

Allowed Differences：

```text
Timestamp
PID
Duration
Generated report filename
```

Unexpected Differences：

```text

```

Result：

```text

```

Evidence：

```text

```

---

# 16. Failure / Re-test Record

如果正式驗收過程中有 FAIL，使用此表保留歷史。

| Record ID | Acceptance ID | Attempt | Expected | Actual | Result | Fix / Action | Re-test Evidence | Date |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |  |  |

規則：

```text
不要刪除原始 FAIL
```

後續成功應新增另一筆：

```text
Re-test PASS
```

---

# 17. Final Acceptance Gate

只有在以下項目全部完成後，才能填寫 Final Acceptance。

| Requirement | Result | Evidence |
| --- | --- | --- |
| AC-01 Environment |  |  |
| AC-02 Static / Startup |  |  |
| AC-03 T01～T09 |  |  |
| AC-04 A01 Full Validation |  |  |
| AC-05 A02 Fault Campaign |  |  |
| AC-06 STOP v1 |  |  |
| AC-07 GUI / Report / Evidence |  |  |
| A01 PASS PDF |  |  |
| A01 STOPPED PDF |  |  |
| A02 PASS PDF |  |  |
| A02 STOPPED PDF |  |  |

Final Result：

```text

```

Acceptance Date：

```text

```

Reviewer：

```text

```

Final Note：

```text

```

---

# 18. Final Evidence Inventory

| Type | File / Path | Description | Verified |
| --- | --- | --- | --- |
| PDF |  | A01 PASS |  |
| PDF |  | A01 STOPPED |  |
| PDF |  | A02 PASS |  |
| PDF |  | A02 STOPPED |  |
| Screenshot |  | GUI Main Window |  |
| Screenshot |  | A01 Result |  |
| Screenshot |  | A02 Result |  |
| Screenshot |  | STOP Result |  |
| Video |  | Short Demo Video |  |
| Document |  | Acceptance Record |  |

---

# 19. 紀錄完成原則

本文件完成時應能讓另一位 Reviewer 不需要重新操作專案，也能回答：

```text
環境是否正確？
T01～T09 是否真的執行過？
A01 是否完整 PASS？
A02 是否完整 PASS？
STOP 是否真的中斷 active unit？
ABORTED / NOT_RUN / STOPPED 是否正確？
Queue 是否恢復？
四份代表性 PDF 是否存在？
有沒有發生過 FAIL？
如果有，怎麼修、怎麼重新驗收？
最後為什麼可以判定專案完成驗收？
```

---

# English Version

## 1. Document Purpose

This document records the actual formal acceptance results of **Automation Mock NVMe Validation (AMNV)**.

The difference between this document and `09_Acceptance_Plan.md` is:

```text
09_Acceptance_Plan.md
= defines what must be tested before acceptance

12_Acceptance_Record.md
= records what was actually executed and observed
```

No hypothetical PASS result should be pre-filled.

Actual values are entered only after real execution.

---

# 2. Recording Principles

The acceptance record follows these principles:

1. record only real execution results;
2. keep Expected and Actual separate;
3. preserve traceable evidence;
4. do not overwrite a failed attempt after a fix;
5. record re-test results as additional evidence.

---

# 3. Overall Acceptance Summary

| Acceptance ID | Scenario | Result | Date | Evidence | Note |
| --- | --- | --- | --- | --- | --- |
| AC-01 | Environment |  |  |  |  |
| AC-02 | Static / Startup |  |  |  |  |
| AC-03 | T01–T09 Individual Tests |  |  |  |  |
| AC-04 | A01 Full Validation |  |  |  |  |
| AC-05 | A02 Fault Campaign |  |  |  |  |
| AC-06 | STOP v1 |  |  |  |  |
| AC-07 | GUI / Report / Evidence |  |  |  |  |
| FINAL | Final Acceptance Gate |  |  |  |  |

---

# 4. AC-01 — Environment

Record actual values for:

```text
Python version
pip version
virtual environment
dependency installation
dependency baseline
```

Expected baseline:

```text
Python 3.12.3
pip 26.2.1
```

Dependencies:

```text
charset-normalizer==3.5.1
pillow==12.3.0
PySide6==6.11.2
PySide6_Addons==6.11.2
PySide6_Essentials==6.11.2
reportlab==5.0.1
shiboken6==6.11.2
```

Actual:

```text

```

Result:

```text

```

Evidence:

```text

```

---

# 5. AC-02 — Static / Startup

Expected:

```text
No SyntaxError
GUI starts successfully
Required controls visible
Console initializes
Runtime state prepared
```

Actual:

```text

```

Result:

```text

```

Evidence:

```text

```

---

# 6. AC-03 — Individual Tests

| Test | Expected | Actual | Result | Evidence |
| --- | --- | --- | --- | --- |
| T01 | PASS |  |  |  |
| T02 | PASS |  |  |  |
| T03 | PASS |  |  |  |
| T04 | PASS |  |  |  |
| T05 | PASS |  |  |  |
| T06 | PASS |  |  |  |
| T07 | PASS |  |  |  |
| T08 | PASS |  |  |  |
| T09 | PASS |  |  |  |

Detailed evidence should confirm the scenario-specific validation criteria defined in the test-design and validation-criteria documents.

---

# 7. AC-04 — A01 Full Validation

Expected:

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

Actual:

```text

```

Result:

```text

```

Report:

```text

```

Screenshot:

```text

```

Console Evidence:

```text

```

Date:

```text

```

---

# 8. AC-05 — A02 Fault Campaign

Expected coverage:

```text
FP01 timeout               3
FP02 NAND_READ_FAIL        2
FP03 NAND_PROGRAM_FAIL     2
FP04 miscompare            2
Total                      9
```

Expected result:

```text
Total       9
Executed    9
Passed      9
Failed      0
Error       0
Aborted     0
Not Run     0

Campaign = PASS
```

Actual:

```text

```

Result:

```text

```

Report:

```text

```

Evidence:

```text

```

---

# 9. AC-06 — STOP v1

Record three categories:

```text
Individual Test Stop
A01 STOPPED
A02 STOPPED
```

Required semantics:

```text
Completed unit
→ preserve result

Active interrupted unit
→ ABORTED

Never-started unit
→ NOT_RUN

Suite / Campaign
→ STOPPED
```

Also record:

```text
Abort Stage
Stop Reason
Interrupted Command
Host Result
Timed Out
Termination Method
Queue After Abort
Outstanding
Next CID
```

---

# 10. AC-07 — GUI Functional Acceptance

| Item | Expected | Actual | Result | Evidence |
| --- | --- | --- | --- | --- |
| T01–T09 Buttons | Correct test launched |  |  |  |
| A01 Button | Full Validation launched |  |  |  |
| A02 Button | Fault Campaign launched |  |  |  |
| GUI Responsiveness | No freeze |  |  |  |
| Single Active Task | Second task rejected |  |  |  |
| Test Stop | Cooperative stop works |  |  |  |
| Read Current Data | Storage displayed |  |  |  |
| Reset Data | Baseline restored |  |  |  |
| Clear Console | Visible text only cleared |  |  |  |
| Open Last Report | Latest PDF / safe no-report behavior |  |  |  |

---

# 11. Representative PDF Evidence

| Evidence | Source Report | Final Display File | Result | Verified |
| --- | --- | --- | --- | --- |
| A01 Full PASS |  | `A01_PASS.pdf` |  |  |
| A01 STOPPED |  | `A01_STOPPED.pdf` |  |  |
| A02 Full PASS |  | `A02_PASS.pdf` |  |  |
| A02 STOPPED |  | `A02_STOPPED.pdf` |  |  |

The original source report should remain traceable even if a presentation copy is renamed.

---

# 12. Report Review

For each representative PDF, verify:

- file opens correctly;
- title is correct;
- result is correct;
- summary counts are correct;
- evidence is readable;
- no critical content is clipped;
- scope wording is correct;
- STOP evidence is correct where applicable.

---

# 13. Runtime State After STOP

Expected:

```text
No active controller subprocess
Outstanding = []
Logical queue recovered
Next run starts normally
```

Actual:

```text

```

Result:

```text

```

Evidence:

```text

```

---

# 14. Repeat-run Verification

Automation Used:

```text

```

First Result:

```text

```

Second Result:

```text

```

Expected:

```text
Same logical validation result
```

Allowed differences:

```text
Timestamp
PID
Duration
Generated report filename
```

Result:

```text

```

Evidence:

```text

```

---

# 15. Failure / Re-test Record

| Record ID | Acceptance ID | Attempt | Expected | Actual | Result | Fix / Action | Re-test Evidence | Date |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |  |  |

Failed attempts remain in the record.

A later successful re-test is added as a new record rather than replacing the previous failure.

---

# 16. Final Acceptance Gate

| Requirement | Result | Evidence |
| --- | --- | --- |
| AC-01 Environment |  |  |
| AC-02 Static / Startup |  |  |
| AC-03 T01–T09 |  |  |
| AC-04 A01 Full Validation |  |  |
| AC-05 A02 Fault Campaign |  |  |
| AC-06 STOP v1 |  |  |
| AC-07 GUI / Report / Evidence |  |  |
| A01 PASS PDF |  |  |
| A01 STOPPED PDF |  |  |
| A02 PASS PDF |  |  |
| A02 STOPPED PDF |  |  |

Final Result:

```text

```

Acceptance Date:

```text

```

Reviewer:

```text

```

Final Note:

```text

```

---

# 17. Final Evidence Inventory

| Type | File / Path | Description | Verified |
| --- | --- | --- | --- |
| PDF |  | A01 PASS |  |
| PDF |  | A01 STOPPED |  |
| PDF |  | A02 PASS |  |
| PDF |  | A02 STOPPED |  |
| Screenshot |  | GUI Main Window |  |
| Screenshot |  | A01 Result |  |
| Screenshot |  | A02 Result |  |
| Screenshot |  | STOP Result |  |
| Video |  | Short Demo Video |  |
| Document |  | Acceptance Record |  |

---

# 18. Completion Principle

A completed acceptance record should allow another reviewer to determine, without rerunning the project:

- whether the environment was correct;
- whether T01–T09 were actually executed;
- whether A01 and A02 completed successfully;
- whether STOP truly interrupted an active unit;
- whether `ABORTED / NOT_RUN / STOPPED` semantics were correct;
- whether queue recovery completed;
- whether all representative reports exist;
- whether failures occurred and how they were re-tested;
- why the final project acceptance result was assigned.
