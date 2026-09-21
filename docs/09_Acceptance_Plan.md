# 驗收計畫 / Acceptance Plan

# 中文版

## 1. 文件目的

本文件定義 **Automation Mock NVMe Validation（AMNV）** 在乾淨驗收環境完成專案建置後的正式驗收計畫。

驗收目的不是重新設計功能，而是確認：

1. 乾淨驗收環境可以依文件重建並執行專案；
2. T01～T09 Individual Tests 都符合既定 Validation Criteria；
3. A01 Full Validation 可以正常完成完整 Regression；
4. A02 Deterministic Fault Campaign 可以正常完成全部 Fault Cases；
5. STOP v1 可以正確處理 Active Unit 與 Remaining Units；
6. GUI 可以正確啟動 Test / Automation、顯示 Result、Stop 與開啟 Report；
7. PDF Report 能保存足夠 Evidence；
8. Runtime Storage / Log / Queue State 不會因中止或 Recovery 留下不合理狀態；
9. 最終可保留一組可供 GitHub / Demo 使用的代表性驗收證據。

本文件定義的是：

```text
驗收前要跑什麼
+
預期看到什麼
+
需要留下什麼證據
```

真正執行後的日期、結果、Report File 與 Evidence，應記錄在：

```text
12_Acceptance_Record.md
```

---

# 2. 驗收平台

正式 Acceptance Environment：

```text
Platform: VMware Virtual Machine
OS: Ubuntu 24.04.3 LTS
Architecture: x86-64
Python: 3.12.3
pip: 26.2.1
Project: automation-mock-nvme-validation
```

Python Package Baseline 由：

```text
requirements.txt
```

定義。

Virtual Environment：

```text
.venv
```

不納入 Git Repository。

正式驗收只以乾淨驗收環境中的正式 Repository 為準。


---

# 3. 驗收原則

## 3.1 Clean Environment Principle

驗收應從乾淨驗收環境中的正式 Repository 執行。

不得依賴：

- 其他環境的 Runtime State；
- 未納入版本控制的本機檔案；
- 未記錄的 Local Patch。

---

## 3.2 Repeatability Principle

相同的 Baseline、Configuration 與 Scenario 應能得到相同的邏輯 Result。

尤其：

```text
A01 PASS
A02 PASS
```

不得依賴手動修改 Runtime Data 才能成功。

---

## 3.3 Evidence Principle

驗收不能只記：

```text
"有跑成功"
```

每個主要 Acceptance Item 應至少保留：

- Expected Result；
- Actual Result；
- PASS / FAIL；
- 必要 Console Output；
- 必要 PDF Report；
- 必要 Screenshot / Record。

---

## 3.4 Scope Principle

驗收結果只證明：

```text
AMNV Host-side Logical NVMe Validation Framework
```

在正式驗收環境中符合既定設計。

不得將驗收結果擴張成：

- Real SSD Firmware Qualification；
- Real PCIe Validation；
- NVMe Certification；
- Real NAND Reliability Validation。

---

# 4. 驗收階段

正式驗收分成七個階段：

```text
AC-01 Environment
AC-02 Static / Startup
AC-03 Individual Tests
AC-04 A01 Full Validation
AC-05 A02 Fault Campaign
AC-06 STOP v1
AC-07 GUI / Report / Evidence
```

最後再做：

```text
Final Acceptance Review
```

---

# 5. AC-01 — Environment Acceptance

## 5.1 目的

確認 Repository 可以在正式 Python Environment 中運作。

---

## 5.2 驗收項目

### AC-01-01 Python Version

Expected：

```text
Python 3.12.3
```

### AC-01-02 pip Version

Expected：

```text
pip 26.2.1
```

### AC-01-03 Virtual Environment

Expected：

```text
.venv activated
```

### AC-01-04 Dependency Installation

使用：

```text
pip install -r requirements.txt
```

Expected：

```text
No installation error
```

### AC-01-05 Dependency Baseline

Expected Package Set：

```text
charset-normalizer==3.5.1
pillow==12.3.0
PySide6==6.11.2
PySide6_Addons==6.11.2
PySide6_Essentials==6.11.2
reportlab==5.0.1
shiboken6==6.11.2
```

---

## 5.3 Acceptance Criteria

AC-01 PASS：

```text
Python version correct
AND
pip version correct
AND
virtual environment works
AND
requirements install without error
```

---

# 6. AC-02 — Static / Startup Acceptance

## 6.1 目的

在進入 Functional Test 前，先確認程式可以正常 Import / Compile / Start。

---

## 6.2 Python Syntax Check

核心 Python Files 應進行：

```text
python -m py_compile
```

至少涵蓋：

```text
main.py
fake_nvme.py
amnv/*.py
amnv/test_cases/*.py
amnv/automation/*.py
amnv/reporting/*.py
amnv/ui/*.py
```

Expected：

```text
No SyntaxError
```

---

## 6.3 GUI Startup

執行：

```text
python main.py
```

Expected：

- Main Window 正常顯示；
- Window Title 正確；
- T01～T09 Button 可見；
- A01 / A02 Button 可見；
- Control Buttons 可見；
- Console 正常顯示 Initial Message；
- 無 Startup Exception。

---

## 6.4 Initial Runtime State

驗收開始前應確認：

```text
mock_storage.json
```

可以回復到：

```text
mock_storage_seed.json
```

定義的 Baseline。

同時：

```text
runtime_fw.log
```

不應包含會干擾新一輪 Acceptance 的舊 Fault Evidence。

---

# 7. AC-03 — Individual Test Acceptance

## 7.1 目的

逐一確認 T01～T09 都可以單獨執行並符合 `08_Validation_Criteria.md`。

正式 Acceptance 不應只依賴 A01。

原因是：

```text
A01 PASS
```

可以證明 Integration Flow 正常，但 Individual Acceptance 可以更清楚確認每一個 Scenario 本身。

---

## 7.2 T01 — Device Baseline

Expected：

```text
Result = PASS
```

主要 Evidence：

- IDENTIFY = SUCCESS；
- Model 正確；
- Firmware Revision 正確；
- NSID 正確；
- Capacity = 4096 blocks；
- Logical Block Size = 512；
- SMART = SUCCESS；
- Temperature <= 70°C；
- Critical Warning = 0；
- Media Errors = 0。

Acceptance：

```text
All required checks PASS
```

---

## 7.3 T02 — Write / Readback

Expected：

```text
Result = PASS
```

主要 Evidence：

```text
WRITE SUCCESS
READ SUCCESS
LBA = 600
Data = T02_WRITE_READBACK
```

Acceptance：

```text
Readback exactly matches written pattern
```

---

## 7.4 T03 — Invalid Range

Expected：

```text
Result = PASS
```

Command：

```text
READ LBA 4095
Length 2
```

主要 Evidence：

```text
Completion Status = INVALID_RANGE
Error = INVALID_RANGE
Data = None
Timed Out = false
```

Acceptance：

> Expected error behavior must be observed.

---

## 7.5 T04 — Unsupported Command

Expected：

```text
Result = PASS
```

Command：

```text
FORMAT
```

主要 Evidence：

```text
Status = UNSUPPORTED_COMMAND
Error = UNSUPPORTED_COMMAND
Timed Out = false
```

---

## 7.6 T05 — Timeout / Recovery

Expected：

```text
Result = PASS
```

主要 Evidence：

### Initial Timeout

```text
CID 1
Host Result = TIMEOUT
Completion = None
Outstanding = [1]
next_cid = 2
```

### Reset

```text
SQ = 0/0
CQ = 0/0
Outstanding = []
next_cid = 2
```

### Retry

```text
CID 2
SUCCESS
Data = TEST_PATTERN_A
```

Acceptance：

```text
Timeout
+
Reset
+
CID preservation
+
Retry
+
Final Queue State
= all PASS
```

---

## 7.7 T06 — Data Integrity

Expected：

```text
Result = PASS
```

主要 Evidence：

```text
Fault READ CQ = SUCCESS
Returned Data != Expected Data
Miscompare Detected = true
Stored Data remains T06_EXPECTED_DATA
```

Acceptance：

> Validator must detect corruption even though CQ reports SUCCESS.

---

## 7.8 T07 — Firmware Log Parsing

Expected：

```text
Result = PASS
```

主要 Evidence：

```text
Parsed Entries = 10
Required Fields Present
Known CID / LBA queries correct
NAND_READ_FAIL parsed correctly
NAND_PROGRAM_FAIL parsed correctly
```

---

## 7.9 T08 — Read Error Correlation

Expected：

```text
Result = PASS
```

主要 Evidence：

```text
READ LBA 300
Completion = FAILED
Error = NAND_READ_FAIL
Timed Out = false
```

Firmware Log 必須和 Command 對上：

```text
CID
Opcode
LBA
Status
Error
```

---

## 7.10 T09 — Write Failure / Recovery

Expected：

```text
Result = PASS
```

主要 Evidence：

### Failed WRITE

```text
CID 1
FAILED / NAND_PROGRAM_FAIL
```

### Storage Protection

```text
CID 2 READ
Data = OLD_PATTERN
```

### Reset

```text
Outstanding = []
next_cid = 3
```

### Retry

```text
CID 3 WRITE = SUCCESS
```

### Final Readback

```text
CID 4 READ
Data = T09_RECOVERED_DATA
```

Final：

```text
SQ = 2/2
CQ = 2/2
Outstanding = []
next_cid = 5
```

---

# 8. AC-03 Completion Criteria

AC-03 只有在：

```text
T01 PASS
T02 PASS
T03 PASS
T04 PASS
T05 PASS
T06 PASS
T07 PASS
T08 PASS
T09 PASS
```

全部成立時才 PASS。

Individual Test 的 GUI Console Result 可作為 Acceptance Record 的補充證據。

不要求 T01～T09 每一項都產獨立 PDF。

---

# 9. AC-04 — A01 Full Validation Acceptance

## 9.1 目的

確認 T01～T09 能以完整 Automation Suite 執行。

---

## 9.2 前置條件

開始前：

```text
Storage Baseline Reset = true
No active task
No pending cancellation token
```

---

## 9.3 Expected Result

完整正常 A01：

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

## 9.4 Report Acceptance

A01 PASS Report 必須至少能看到：

- Suite ID / Name；
- Result = PASS；
- Total / Executed / Passed / Failed / Error / Aborted / Not Run；
- T01～T09 Result；
- Duration；
- Key Validation Evidence；
- Failure / Recovery Evidence；
- Scope / Limitation。

---

## 9.5 代表性 Evidence

Final Repository / Demo 應保留一份：

```text
A01 PASS PDF
```

正式展示用檔名可以在 Evidence 整理階段重新命名，例如：

```text
A01_PASS.pdf
```

但原始 timestamp Report 也應保留到 Acceptance Record 能追溯來源。

---

# 10. AC-05 — A02 Fault Campaign Acceptance

## 10.1 目的

確認所有 deterministic fault cases 都能完整執行。

---

## 10.2 Expected Coverage

```text
FP01 — timeout                 3 cases
FP02 — NAND_READ_FAIL         2 cases
FP03 — NAND_PROGRAM_FAIL      2 cases
FP04 — miscompare             2 cases

Total                         9 cases
```

---

## 10.3 Expected Result

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

---

## 10.4 FP01 Acceptance

三個 Timeout Case 必須驗證：

```text
Host TIMEOUT
No normal CQ completion
Outstanding CID
Reset
CID progression
Retry
```

WRITE Timeout Case 另外需要：

```text
Readback
```

---

## 10.5 FP02 Acceptance

兩個 NAND Read Failure Case：

```text
FAILED / NAND_READ_FAIL
```

並且：

```text
Firmware Log Correlation
=
CID + Opcode + LBA + Status + Error matched
```

不要求 Retry。

---

## 10.6 FP03 Acceptance

兩個 NAND Program Failure Case：

```text
FAILED / NAND_PROGRAM_FAIL
```

並驗證：

```text
Storage unchanged
Firmware Log correlation
Reset
Retry WRITE
Readback
```

---

## 10.7 FP04 Acceptance

兩個 Miscompare Case：

```text
CQ Status = SUCCESS
Returned Data != Stored Data
Data Miscompare Detected
Storage remains intact
```

---

## 10.8 Report Acceptance

A02 PASS Report 至少應包含：

- Campaign Matrix；
- 9 Cases；
- FP01～FP04 Summary；
- Expected Detection；
- Recovery；
- Validation Check Count；
- Fault Evidence；
- Firmware Log Correlation；
- Recovery Evidence；
- Campaign Conclusion；
- Technical Scope。

現有開發階段 A02 Report 已能呈現 FP04 的 `CQ SUCCESS + Returned Pattern mismatch + Stored Pattern preserved`，以及 Campaign Conclusion 的 timeout、controller failure、log correlation、recovery 與 data protection。這些欄位應在 Final Acceptance 中再次確認。fileciteturn99file5L307-L334 fileciteturn99file9L446-L464

---

## 10.9 代表性 Evidence

Final Repository / Demo 應保留：

```text
A02 PASS PDF
```

展示用可整理為：

```text
A02_PASS.pdf
```

---

# 11. AC-06 — STOP v1 Acceptance

## 11.1 目的

確認 STOP v1 不只是 Button 可按，而是真正符合 Cancellation Semantics。

正式 STOP Acceptance 至少驗證：

```text
A01 active stop
A02 active stop
```

Individual Test Stop 另外做 Functional Check。

---

# 12. Individual Test Stop Check

至少選擇一個會進入 active subprocess 的 Test，例如：

```text
T05
```

在執行中按：

```text
Test Stop
```

Expected：

```text
Test = ABORTED
Timed Out = false
```

如果 subprocess 尚在執行：

```text
Termination = terminate
or
kill fallback
```

並確認：

```text
Queue = recovered
Outstanding = []
```

---

# 13. A01 STOPPED Acceptance

## 13.1 操作

執行：

```text
A01 Full Validation
```

並在其中一個 Test 正在 active execution 時按：

```text
Test Stop
```

最好選擇 T05 這類有明顯 active command window 的 Test，以提高可重現性。

---

## 13.2 Expected Result

Acceptance 不要求固定「一定是 T05」才算正確。

真正判定標準是：

```text
Previously completed tests
→ preserve PASS / FAIL / ERROR

Active interrupted test
→ ABORTED

Remaining tests
→ NOT_RUN

Suite
→ STOPPED
```

如果刻意在 T05 Active Command 中止，預期代表性狀態可為：

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

此狀態已在開發環境曾被成功驗證，因此適合作為最終 Acceptance 的目標案例。fileciteturn99file0L10-L37

---

## 13.3 A01 Stop Evidence

Partial Report 必須至少保存：

```text
Stop Reason
Abort Stage
Interrupted Test
Interrupted CID / Opcode / LBA
Host Result = ABORTED
Timed Out = false
Process Termination
Outstanding after abort
Queue after abort
Next CID
NOT_RUN tests
```

---

## 13.4 Representative Evidence

Final Repository / Demo 應保留：

```text
A01 STOPPED PDF
```

展示用可整理成：

```text
A01_STOPPED.pdf
```

---

# 14. A02 STOPPED Acceptance

## 14.1 操作

執行：

```text
A02 Fault Campaign
```

在 active Fault Case 執行中按：

```text
Test Stop
```

---

## 14.2 Expected Result

同樣不強制一定中止某一個 Case。

判定核心為：

```text
Completed Cases
→ preserve result

Active Case
→ ABORTED

Remaining Cases
→ NOT_RUN

Campaign
→ STOPPED
```

一個適合 Demo 的代表性狀態為：

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

A02 = STOPPED
```

也可以在第一個 active case 就中止，只要 `ABORTED / NOT_RUN / STOPPED` 語意正確。

---

## 14.3 A02 Stop Evidence

Partial Report 應至少保存：

- Active Case ID；
- Fault Profile；
- Abort Stage；
- Stop Reason；
- Interrupted Command；
- Host Result = ABORTED；
- Timed Out = false；
- Termination Method；
- Queue Recovery；
- Next CID；
- Remaining Case = NOT_RUN。

開發階段已有 A02 STOP Report 能保存 active fault command 的 CID、LBA、ABORTED、terminate、Queue `0/0` 與 `Next CID 2`，因此最終驗收應至少維持同等 Evidence Level。fileciteturn99file4L266-L297

---

## 14.4 Representative Evidence

Final Repository / Demo 應保留：

```text
A02 STOPPED PDF
```

展示用可整理為：

```text
A02_STOPPED.pdf
```

---

# 15. 四份代表性 PDF

正式專案最終至少選出四份 Representative Report：

```text
A01_PASS.pdf
A01_STOPPED.pdf
A02_PASS.pdf
A02_STOPPED.pdf
```

這四份 PDF 分別回答：

### A01 PASS

```text
完整 Regression 能不能全部跑完？
```

### A01 STOPPED

```text
Full Validation 被人為中止時，Result / Evidence 能不能保持正確？
```

### A02 PASS

```text
Deterministic Fault Campaign 能不能完整驗證？
```

### A02 STOPPED

```text
Fault Campaign 被中止時，Case / Profile / Evidence 能不能正確保存？
```

四份 Report 比單獨只放 PASS 更能展示：

```text
Normal Execution
+
Fault Validation
+
Recovery
+
Execution Control
+
Partial Evidence
```

---

# 16. AC-07 — GUI Functional Acceptance

## 16.1 T01～T09 Button

每一個 Button：

```text
T01 ~ T09
```

至少確認：

- 正確啟動對應 Test；
- 不啟動錯誤 Module；
- Console 顯示 Test ID；
- Console 顯示 Result；
- Button / Thread State 最後恢復正常。

---

## 16.2 A01 Button

Expected：

```text
Click A01
→ Full Validation starts
→ GUI remains responsive
→ Result shown
→ PDF path shown
```

---

## 16.3 A02 Button

Expected：

```text
Click A02
→ Fault Campaign starts
→ GUI remains responsive
→ Result shown
→ PDF path shown
```

---

## 16.4 Single Active Task

在一個 Test / Automation 執行期間，再點另一個 Task。

Expected：

```text
Second task is not started
```

Console 應有提示。

---

## 16.5 Test Stop

Expected：

- 有 Active Task 時可提出 Stop；
- GUI 不 freeze；
- 不使用強制 Worker Thread Kill；
- Backend 最終回傳正確 `ABORTED / STOPPED` Result。

---

## 16.6 Read Current Data

Expected：

```text
Current mock_storage.json
```

可以正確顯示到 Console。

---

## 16.7 Reset Data

先做一筆會改變 Storage 的操作。

再執行：

```text
Reset Data
```

Expected：

```text
Runtime Storage returns to seed baseline
```

---

## 16.8 Clear Console

Expected：

```text
Visible console cleared
```

但不影響：

- Storage；
- Report；
- Active Backend State。

---

## 16.9 Open Last Report

有 Report 的情況：

```text
Open Last Report
→ newest PDF open request succeeds
```

無 Report 的情況：

```text
No PDF report found
```

且 GUI 不 crash。

---

# 17. Report Acceptance

四份 Representative PDF 應確認：

### Common

- PDF 可正常開啟；
- 無損壞；
- 標題正確；
- Timestamp / Suite ID 正確；
- Result 正確；
- Summary Count 正確；
- 無明顯文字截斷到無法閱讀；
- Evidence 與實際執行一致；
- Scope 說明正確。

### PASS Report

必須能看到：

```text
完整執行
+
所有 unit PASS
+
Recovery / Fault Evidence
```

### STOPPED Report

必須能看到：

```text
STOPPED
+
ABORTED
+
NOT_RUN
+
Stop Reason
+
Abort Evidence
+
Partial Summary
```

---

# 18. Storage / Runtime State Acceptance

## 18.1 Normal Execution

正常 PASS 後：

- Outstanding CID 不應殘留；
- Queue 應和最後正常 Command State 一致；
- Runtime Storage 應符合 Test 最終結果。

---

## 18.2 STOP Recovery

Active Command 被取消後：

```text
Outstanding = []
SQ / CQ recovered
```

不得留下：

```text
stale outstanding CID
```

影響下一輪執行。

---

## 18.3 Next Run

完成 STOPPED Acceptance 後，再執行正常 Individual Test 或 Automation。

Expected：

```text
Next run can start normally
```

這是確認 Cancellation Recovery 沒有破壞後續執行的重要項目。

---

# 19. Repeat Run Acceptance

至少選：

```text
A01 PASS
```

或：

```text
A02 PASS
```

在同一正式驗收環境再執行一次。

Expected：

```text
Same logical result
```

允許：

- Duration 不同；
- PID 不同；
- Timestamp 不同。

不允許：

- Test Result 隨機改變；
- CID Logic 不一致；
- Storage Baseline 被前一次 Run 汙染；
- Fault Case 隨機失敗。

---

# 20. Acceptance Failure Handling

如果任何 Acceptance Item FAIL：

不得直接修改 Acceptance Record 成 PASS。

應先記錄：

```text
Acceptance Item
Expected
Actual
Evidence
Failure Classification
```

再回到 Development 修正。

修正完成後：

```text
Re-run affected acceptance item
```

必要時重新執行：

```text
A01
A02
STOP
```

以確認沒有 Regression。

---

# 21. Final Acceptance Gate

AMNV Final Acceptance 只有在以下條件全部成立時才完成：

```text
AC-01 Environment PASS
AC-02 Static / Startup PASS
AC-03 T01~T09 PASS
AC-04 A01 PASS
AC-05 A02 PASS
AC-06 STOP v1 PASS
AC-07 GUI / Report PASS
```

同時必須具有四份代表性 PDF：

```text
A01_PASS.pdf
A01_STOPPED.pdf
A02_PASS.pdf
A02_STOPPED.pdf
```

---

# 22. Final Evidence Set

建議最終 Acceptance Evidence 至少保留：

```text
Four Representative PDFs
GUI Main Screenshot
A01 Running / Result Screenshot
A02 Running / Result Screenshot
STOP Result Screenshot
Short Demo Video
Acceptance Record
```

這些 Evidence 的最終 GitHub 目錄結構可在 Demo / Repository Finalization 階段再決定。

本文件只先定義「需要保留什麼」，不提前凍結最終資料夾架構。

---

# 23. Acceptance Record

正式執行後，`12_Acceptance_Record.md` 應至少記錄：

| 欄位 | 說明 |
| --- | --- |
| Acceptance ID | 例如 AC-04 |
| Scenario | 驗收內容 |
| Expected | 預期結果 |
| Actual | 實際結果 |
| Result | PASS / FAIL |
| Evidence | PDF / Screenshot / Console |
| Date | 執行日期 |
| Note | 必要補充 |

Acceptance Plan 不寫入假想的 PASS。

只有真正於正式驗收環境執行後，才把 Actual Result 放入 Acceptance Record。

---

# 24. 驗收完成後

完成 Final Acceptance 後，才進入：

```text
Repository Evidence Cleanup
Demo Assets
Acceptance Record Finalization
README Finalization
```

也就是：

> 先證明專案能在乾淨驗收環境中依文件重建並通過，再整理成對外展示版本。

---

# English Version

## 1. Document Purpose

This document defines the formal acceptance plan for **Automation Mock NVMe Validation (AMNV)** after the project has been set up in a clean validation environment.

The acceptance process verifies that:

1. the project can be rebuilt and executed in a clean validation environment;
2. T01–T09 satisfy the defined validation criteria;
3. A01 can complete the full regression suite;
4. A02 can complete all deterministic fault cases;
5. STOP v1 preserves correct execution semantics;
6. the GUI can launch, stop, display, and report validation tasks;
7. PDF reports preserve sufficient evidence;
8. recovery leaves runtime state usable for later runs;
9. a representative evidence set can be retained for GitHub and demonstration.

Actual execution results are recorded later in:

```text
12_Acceptance_Record.md
```

---

# 2. Acceptance Platform

Formal environment:

```text
Platform: VMware Virtual Machine
OS: Ubuntu 24.04.3 LTS
Architecture: x86-64
Python: 3.12.3
pip: 26.2.1
Project: automation-mock-nvme-validation
```

Dependencies are defined by:

```text
requirements.txt
```

The `.venv` directory is not committed.

Only the formal repository in the clean validation environment is used for final acceptance.


---

# 3. Acceptance Principles

The acceptance process follows four principles:

1. **Clean environment** — do not depend on external runtime state, untracked local files, or undocumented patches.
2. **Repeatability** — identical baseline/configuration should produce the same logical result.
3. **Evidence** — major acceptance items must retain expected, actual, result, and evidence.
4. **Scope** — acceptance applies only to the AMNV Host-side logical validation framework.

---

# 4. Acceptance Phases

```text
AC-01 Environment
AC-02 Static / Startup
AC-03 Individual Tests
AC-04 A01 Full Validation
AC-05 A02 Fault Campaign
AC-06 STOP v1
AC-07 GUI / Report / Evidence
```

A final review is performed after all phases pass.

---

# 5. AC-01 — Environment Acceptance

Verify:

```text
Python 3.12.3
pip 26.2.1
.venv works
pip install -r requirements.txt succeeds
```

Expected dependency baseline:

```text
charset-normalizer==3.5.1
pillow==12.3.0
PySide6==6.11.2
PySide6_Addons==6.11.2
PySide6_Essentials==6.11.2
reportlab==5.0.1
shiboken6==6.11.2
```

---

# 6. AC-02 — Static / Startup Acceptance

Run Python syntax checks across the project.

Expected:

```text
No SyntaxError
```

Start:

```text
python main.py
```

Verify:

- main window opens;
- all T01–T09 controls are visible;
- A01 / A02 controls are visible;
- control buttons are visible;
- console initializes;
- no startup exception occurs.

Reset runtime storage to the seed baseline before functional acceptance.

---

# 7. AC-03 — Individual Test Acceptance

Each test must pass independently.

Expected final state:

```text
T01 PASS
T02 PASS
T03 PASS
T04 PASS
T05 PASS
T06 PASS
T07 PASS
T08 PASS
T09 PASS
```

Key expectations include:

- T01: device/health baseline;
- T02: normal write/readback;
- T03: correct invalid-range rejection;
- T04: correct unsupported-command rejection;
- T05: timeout/reset/CID/retry recovery;
- T06: miscompare detection with storage preserved;
- T07: firmware-style log parsing;
- T08: read-failure/log correlation;
- T09: write-failure/storage protection/reset/retry/readback.

Individual PDF reports are not required.

---

# 8. AC-04 — A01 Full Validation

Expected normal result:

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

The A01 report must preserve:

- suite metadata;
- summary counts;
- T01–T09 status;
- key validation evidence;
- recovery/failure evidence;
- scope information.

A representative `A01_PASS.pdf` is retained for final presentation.

---

# 9. AC-05 — A02 Fault Campaign

Expected coverage:

```text
FP01 timeout               3
FP02 NAND_READ_FAIL        2
FP03 NAND_PROGRAM_FAIL     2
FP04 miscompare            2
Total                      9
```

Expected normal result:

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

The report must demonstrate:

- timeout detection and reset/retry;
- NAND read failure and log correlation;
- NAND program failure, storage protection, reset/retry/readback;
- data miscompare with CQ SUCCESS and preserved storage.

A representative `A02_PASS.pdf` is retained.

---

# 10. AC-06 — STOP v1 Acceptance

STOP acceptance includes:

```text
Individual active stop
A01 active stop
A02 active stop
```

Cancellation must remain separate from timeout.

Expected active-unit behavior:

```text
Result = ABORTED
Timed Out = false
```

Logical queue/outstanding state must recover.

---

# 11. A01 STOPPED Acceptance

During active suite execution, request Stop.

Expected semantics:

```text
Completed tests
→ preserve existing result

Active interrupted test
→ ABORTED

Remaining tests
→ NOT_RUN

Suite
→ STOPPED
```

A representative target is:

```text
T01 PASS
T02 PASS
T03 PASS
T04 PASS
T05 ABORTED
T06~T09 NOT_RUN

Total      9
Executed   5
Passed     4
Failed     0
Error      0
Aborted    1
Not Run    4
```

The exact active test does not have to be T05 as long as the semantics are correct.

Retain:

```text
A01_STOPPED.pdf
```

---

# 12. A02 STOPPED Acceptance

During an active fault case, request Stop.

Expected semantics:

```text
Completed cases
→ preserve result

Active case
→ ABORTED

Remaining cases
→ NOT_RUN

Campaign
→ STOPPED
```

A representative example is:

```text
Case 1 PASS
Case 2 ABORTED
Remaining 7 NOT_RUN

Total       9
Executed    2
Passed      1
Failed      0
Error       0
Aborted     1
Not Run     7
```

Retain:

```text
A02_STOPPED.pdf
```

---

# 13. Four Representative Reports

The final presentation set includes:

```text
A01_PASS.pdf
A01_STOPPED.pdf
A02_PASS.pdf
A02_STOPPED.pdf
```

Together they demonstrate:

```text
Normal Regression
+
Fault Validation
+
Recovery
+
Cancellation
+
Partial Evidence Preservation
```

---

# 14. AC-07 — GUI Functional Acceptance

Verify:

- T01–T09 buttons launch the correct tests;
- A01 launches the full suite;
- A02 launches the fault campaign;
- the GUI remains responsive during background execution;
- a second concurrent validation task is rejected;
- Test Stop triggers cooperative cancellation;
- Read Current Data displays runtime storage;
- Reset Data restores the seed baseline;
- Clear only clears visible console output;
- Open Last Report opens the newest available PDF or handles the no-report case safely.

---

# 15. Report Acceptance

Each representative PDF must:

- open successfully;
- contain the correct title and suite/campaign identity;
- contain correct result and summary counts;
- present readable validation evidence;
- match the actual execution result;
- include correct scope language.

STOPPED reports must additionally show:

```text
STOPPED
ABORTED
NOT_RUN
Stop Reason
Abort Evidence
Partial Summary
```

---

# 16. Runtime State Acceptance

After normal execution:

```text
No stale outstanding CID
```

After cancellation:

```text
Outstanding = []
Logical queue recovered
```

A new test or automation run must be able to start successfully after a stopped run.

This confirms that cancellation recovery did not corrupt later execution.

---

# 17. Repeat-run Acceptance

Repeat at least one full automation run in the same final validation environment.

Expected:

```text
Same logical result
```

Differences in timestamp, PID, and duration are allowed.

Random changes in validation result, CID behavior, storage baseline, or fault outcome are not acceptable.

---

# 18. Acceptance Failure Handling

If an acceptance item fails:

1. record expected and actual behavior;
2. preserve evidence;
3. classify the failure;
4. return to development;
5. fix the implementation;
6. rerun the affected acceptance item;
7. rerun broader A01/A02/STOP checks when regression risk exists.

An acceptance record must not be changed to PASS without a real rerun.

---

# 19. Final Acceptance Gate

Final acceptance requires:

```text
AC-01 Environment PASS
AC-02 Static / Startup PASS
AC-03 T01~T09 PASS
AC-04 A01 PASS
AC-05 A02 PASS
AC-06 STOP v1 PASS
AC-07 GUI / Report PASS
```

and the four representative reports:

```text
A01_PASS.pdf
A01_STOPPED.pdf
A02_PASS.pdf
A02_STOPPED.pdf
```

---

# 20. Final Evidence Set

The final evidence set should include at least:

```text
Four Representative PDFs
GUI Main Screenshot
A01 Running / Result Screenshot
A02 Running / Result Screenshot
STOP Result Screenshot
Short Demo Video
Acceptance Record
```

The final GitHub directory structure for these assets can be decided later during repository finalization.

---

# 21. Acceptance Record

`12_Acceptance_Record.md` should record at least:

| Field | Description |
| --- | --- |
| Acceptance ID | AC-xx identifier |
| Scenario | Acceptance item |
| Expected | Required result |
| Actual | Observed result |
| Result | PASS / FAIL |
| Evidence | PDF / screenshot / console |
| Date | Execution date |
| Note | Additional information |

The plan does not pre-fill hypothetical PASS results.

Only real execution results from the final validation environment are entered into the acceptance record.

---

# 22. After Acceptance

After final acceptance, the project can move to:

```text
Repository Evidence Cleanup
Demo Assets
Acceptance Record Finalization
README Finalization
```

The project is therefore documented, implemented, and verified before the public-facing repository presentation is finalized.
