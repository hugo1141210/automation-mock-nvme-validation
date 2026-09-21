import json
import shutil
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMainWindow

from amnv.automation.a01_full_validation import run as run_a01
from amnv.cancellation import CancellationToken
from amnv.automation.a02_fault_campaign import run as run_a02
from amnv.config_loader import load_validation_config
from amnv.reporting.a02_report import generate_a02_report
from amnv.reporting.a01_reporter import generate_suite_report
from amnv.test_cases.t01_device_baseline import run as run_t01
from amnv.test_cases.t02_write_readback import run as run_t02
from amnv.test_cases.t03_invalid_read_range import run as run_t03
from amnv.test_cases.t04_unsupported_command import run as run_t04
from amnv.test_cases.t05_read_timeout_recovery import run as run_t05
from amnv.test_cases.t06_data_integrity_failure import run as run_t06
from amnv.test_cases.t07_firmware_log_parsing import run as run_t07
from amnv.test_cases.t08_read_error_correlation import run as run_t08
from amnv.test_cases.t09_write_failure_recovery import run as run_t09
from amnv.ui.test_worker import TestWorker
from amnv.ui.ui_main_window import Ui_MainWindow


PROJECT_ROOT = Path(__file__).resolve().parents[2]

STORAGE_FILE = (
    PROJECT_ROOT / "data" / "mock_storage.json"
)

STORAGE_SEED_FILE = (
    PROJECT_ROOT / "data" / "mock_storage_seed.json"
)

REPORT_ROOT = (
    PROJECT_ROOT / "reports"
)


def run_a01_with_report(
    cancellation_token=None,
    progress_callback=None,
):
    suite_result = run_a01(
        cancellation_token=cancellation_token,
        progress_callback=progress_callback,
    )

    report_path = generate_suite_report(
        suite_result
    )

    return {
        "suite_result": suite_result,
        "report_path": str(report_path),
    }


def run_a02_with_report(
    cancellation_token=None,
    progress_callback=None,
):
    suite_result = run_a02(
        cancellation_token=cancellation_token,
        progress_callback=progress_callback,
    )

    report_path = generate_a02_report(
        suite_result
    )

    return {
        "suite_result": suite_result,
        "report_path": str(report_path),
    }


class MainWindow(QMainWindow):
    a01_progress = Signal(object)
    a02_progress = Signal(object)

    def __init__(self):
        super().__init__()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self._test_thread = None
        self._test_worker = None

        self._active_test_id = None
        self._active_test_name = None
        self._active_test_button = None
        self._active_cancellation_token = None

        self._setup_console()
        self._connect_signals()

    def _timestamp(self):
        return datetime.now().strftime(
            "%H:%M:%S.%f"
        )[:-3]

    def _log(self, message):
        self.ui.txtConsole.appendPlainText(
            f"[{self._timestamp()}] {message}"
        )

    def _blank_line(self):
        self.ui.txtConsole.appendPlainText("")

    def _setup_console(self):
        self.ui.txtConsole.document().setMaximumBlockCount(5000)

        self._log(
            "[SYSTEM] Automation Mock NVMe Validation initialized."
        )

        self._blank_line()

    def _connect_signals(self):
        # -------------------------------------------------
        # Console
        # -------------------------------------------------
        self.ui.btnClearConsole.clicked.connect(
            self.ui.txtConsole.clear
        )

        self.ui.btnTestStop.clicked.connect(
            self._request_stop
        )
        self.ui.btnTestStop.setEnabled(False)

        self.a01_progress.connect(
            self._on_a01_progress
        )

        self.a02_progress.connect(
            self._on_a02_progress
        )

        # -------------------------------------------------
        # Storage Utility
        # -------------------------------------------------
        self.ui.btnReadCurrentData.clicked.connect(
            self._read_current_data
        )

        self.ui.btnResetData.clicked.connect(
            self._reset_data
        )

        # -------------------------------------------------
        # Report Utility
        # -------------------------------------------------
        self.ui.btnOpenLastReport.clicked.connect(
            self._open_last_report
        )

        # -------------------------------------------------
        # Individual Validation Tests
        # T01 ~ T09
        # -------------------------------------------------
        self.ui.btnT01.clicked.connect(
            lambda: self._start_test(
                test_id="T01",
                test_name="Device Baseline Check",
                task=run_t01,
                button=self.ui.btnT01,
            )
        )

        self.ui.btnT02.clicked.connect(
            lambda: self._start_test(
                test_id="T02",
                test_name="Normal Write / Readback",
                task=run_t02,
                button=self.ui.btnT02,
            )
        )

        self.ui.btnT03.clicked.connect(
            lambda: self._start_test(
                test_id="T03",
                test_name="Invalid Read Range",
                task=run_t03,
                button=self.ui.btnT03,
            )
        )

        self.ui.btnT04.clicked.connect(
            lambda: self._start_test(
                test_id="T04",
                test_name="Unsupported Command",
                task=run_t04,
                button=self.ui.btnT04,
            )
        )

        self.ui.btnT05.clicked.connect(
            lambda: self._start_test(
                test_id="T05",
                test_name="Read Timeout + Recovery",
                task=run_t05,
                button=self.ui.btnT05,
            )
        )

        self.ui.btnT06.clicked.connect(
            lambda: self._start_test(
                test_id="T06",
                test_name="Data Integrity Failure",
                task=run_t06,
                button=self.ui.btnT06,
            )
        )

        self.ui.btnT07.clicked.connect(
            lambda: self._start_test(
                test_id="T07",
                test_name="Firmware Log Parsing",
                task=run_t07,
                button=self.ui.btnT07,
            )
        )

        self.ui.btnT08.clicked.connect(
            lambda: self._start_test(
                test_id="T08",
                test_name="Read Firmware Error + Correlation",
                task=run_t08,
                button=self.ui.btnT08,
            )
        )

        self.ui.btnT09.clicked.connect(
            lambda: self._start_test(
                test_id="T09",
                test_name="Write Failure + Recovery + Verification",
                task=run_t09,
                button=self.ui.btnT09,
            )
        )

        # -------------------------------------------------
        # Automation Suites
        # A01 / A02
        # -------------------------------------------------
        self.ui.btnA01.clicked.connect(
            self._start_a01
        )

        self.ui.btnA02.clicked.connect(
            self._start_a02
        )

    def _start_background_task(
        self,
        task_id,
        task_name,
        task,
        button,
        result_handler,
        cancellation_token=None,
    ):
        if self._test_thread is not None:
            self._log(
                "[SYSTEM] Another test is already running."
            )
            return

        self._active_test_id = task_id
        self._active_test_name = task_name
        self._active_test_button = button
        self._active_cancellation_token = (
            cancellation_token
        )

        self.ui.btnTestStop.setEnabled(
            cancellation_token is not None
        )

        self._log(
            f"[TEST] {task_id} - {task_name} started."
        )

        button.setEnabled(False)

        self._test_thread = QThread(self)
        self._test_worker = TestWorker(task)

        self._test_worker.moveToThread(
            self._test_thread
        )

        self._test_thread.started.connect(
            self._test_worker.run
        )

        self._test_worker.result.connect(
            result_handler
        )

        self._test_worker.error.connect(
            self._on_test_error
        )

        self._test_worker.finished.connect(
            self._test_thread.quit
        )

        self._test_worker.finished.connect(
            self._test_worker.deleteLater
        )

        self._test_thread.finished.connect(
            self._test_thread.deleteLater
        )

        self._test_thread.finished.connect(
            self._on_test_thread_finished
        )

        self._test_thread.start()

    def _start_test(
        self,
        test_id,
        test_name,
        task,
        button,
    ):
        cancellation_token = (
            CancellationToken()
        )

        def cancellable_task():
            return task(
                cancellation_token=(
                    cancellation_token
                )
            )

        self._start_background_task(
            task_id=test_id,
            task_name=test_name,
            task=cancellable_task,
            button=button,
            result_handler=self._on_test_result,
            cancellation_token=(
                cancellation_token
            ),
        )

    def _start_a01(self):
        cancellation_token = (
            CancellationToken()
        )

        def a01_task():
            return run_a01_with_report(
                cancellation_token=(
                    cancellation_token
                ),
                progress_callback=(
                    self.a01_progress.emit
                ),
            )

        self._start_background_task(
            task_id="A01",
            task_name="Automated Full Validation Suite",
            task=a01_task,
            button=self.ui.btnA01,
            result_handler=self._on_a01_result,
            cancellation_token=(
                cancellation_token
            ),
        )

    def _start_a02(self):
        cancellation_token = (
            CancellationToken()
        )

        def a02_task():
            return run_a02_with_report(
                cancellation_token=(
                    cancellation_token
                ),
                progress_callback=(
                    self.a02_progress.emit
                ),
            )

        self._start_background_task(
            task_id="A02",
            task_name="Automated Fault Injection Campaign",
            task=a02_task,
            button=self.ui.btnA02,
            result_handler=self._on_a02_result,
            cancellation_token=(
                cancellation_token
            ),
        )

    def _request_stop(self):
        test_id = (
            self._active_test_id
            or "UNKNOWN"
        )

        if self._test_thread is None:
            self._log(
                "[STOP] No test is currently running."
            )
            return

        token = (
            self._active_cancellation_token
        )

        if token is None:
            self._log(
                "[STOP] "
                f"{test_id} does not support Stop "
                "in the current phase."
            )
            return

        if token.is_requested():
            self._log(
                "[STOP] "
                f"Stop already requested for {test_id}."
            )
            return

        token.request()
        self.ui.btnTestStop.setEnabled(False)

        self._log(
            "[STOP] "
            f"Stop requested for {test_id}."
        )

    def _on_a01_progress(self, event):
        test_id = event.get(
            "test_id",
            "UNKNOWN",
        )
        test_name = event.get(
            "test_name",
            test_id,
        )
        event_type = event.get(
            "event",
            "UNKNOWN",
        )
        result = event.get(
            "result",
            "UNKNOWN",
        )

        if event_type == "TEST_STARTED":
            self._log(
                "[A01] "
                f"{test_id} - {test_name} STARTED"
            )
            return

        if event_type == "TEST_NOT_RUN":
            self._log(
                "[A01] "
                f"{test_id} Result: NOT_RUN"
            )
            return

        self._log(
            "[A01] "
            f"{test_id} Result: {result}"
        )

    def _on_a02_progress(self, event):
        case_id = event.get(
            "case_id",
            "UNKNOWN",
        )
        event_type = event.get(
            "event",
            "UNKNOWN",
        )
        result = event.get(
            "result",
            "UNKNOWN",
        )

        if event_type == "CASE_STARTED":
            self._log(
                "[A02] "
                f"{case_id} STARTED"
            )
            return

        if event_type == "CASE_NOT_RUN":
            self._log(
                "[A02] "
                f"{case_id} Result: NOT_RUN"
            )
            return

        self._log(
            "[A02] "
            f"{case_id} Result: {result}"
        )

    def _on_test_result(self, result):
        test_id = self._active_test_id or "UNKNOWN"

        if hasattr(result, "to_dict"):
            result_dict = result.to_dict()
        elif isinstance(result, dict):
            result_dict = result
        else:
            raise TypeError(
                "Test result must provide to_dict() "
                "or already be a dict."
            )

        self._log(
            f"[TEST] {test_id} Result: "
            f"{result_dict['result']}"
        )

        self._log(
            "[TEST] "
            f"Expected: {result_dict['expected']}"
        )

        self._log(
            "[TEST] "
            f"Actual: {result_dict['actual']}"
        )

        self._log(
            "[TEST] "
            f"Duration: {result_dict['duration_sec']:.3f} s"
        )

        checks = (
            result_dict
            .get("details", {})
            .get("checks", [])
        )

        passed_checks = sum(
            1
            for check in checks
            if check.get("passed")
        )

        result_status = result_dict.get(
            "result",
            "UNKNOWN",
        )

        if result_status == "ABORTED":
            abort = (
                result_dict
                .get("details", {})
                .get("abort", {})
            )

            self._log(
                "[STOP] "
                f"Abort Stage: "
                f"{abort.get('stage', 'UNKNOWN')}"
            )
            self._log(
                "[STOP] "
                f"Reason: "
                f"{abort.get('reason', 'Unknown')}"
            )

            if checks:
                self._log(
                    "[VALIDATE] "
                    f"Checks: "
                    f"{passed_checks}/{len(checks)} PASS"
                )
            else:
                self._log(
                    "[VALIDATE] "
                    "Checks: No completed "
                    "validation checks"
                )

        else:
            self._log(
                "[VALIDATE] "
                f"Checks: {passed_checks}/{len(checks)} PASS"
            )

    def _on_a01_result(self, payload):
        self.ui.btnTestStop.setEnabled(False)

        suite_result = payload[
            "suite_result"
        ]

        report_path = Path(
            payload["report_path"]
        )

        total = suite_result.get(
            "total_tests",
            suite_result.get(
                "total",
                len(
                    suite_result.get(
                        "tests",
                        [],
                    )
                ),
            ),
        )

        executed = suite_result.get(
            "executed",
            total,
        )
        passed = suite_result.get(
            "passed",
            0,
        )
        failed = suite_result.get(
            "failed",
            0,
        )
        errors = suite_result.get(
            "errors",
            0,
        )
        aborted = suite_result.get(
            "aborted",
            0,
        )
        not_run = suite_result.get(
            "not_run",
            0,
        )

        self._log(
            "[SUITE] "
            f"A01 Result: {suite_result['result']}"
        )
        self._log(
            "[SUITE] "
            f"Executed: {executed}/{total}"
        )
        self._log(
            "[SUITE] "
            f"Passed: {passed}"
        )
        self._log(
            "[SUITE] "
            f"Failed: {failed}"
        )
        self._log(
            "[SUITE] "
            f"Error: {errors}"
        )
        self._log(
            "[SUITE] "
            f"Aborted: {aborted}"
        )
        self._log(
            "[SUITE] "
            f"Not Run: {not_run}"
        )

        if suite_result.get(
            "stopped",
            False,
        ):
            self._log(
                "[STOP] "
                f"Reason: "
                f"{suite_result.get('stop_reason')}"
            )

        self._log(
            "[SUITE] "
            f"Duration: "
            f"{suite_result.get('duration_sec', 0):.3f} s"
        )

        self._log(
            "[REPORT] "
            f"PDF: {report_path}"
        )

        if self._report_auto_open_enabled():
            self._open_report(
                report_path,
                "A01"
            )

    def _on_a02_result(self, payload):
        self.ui.btnTestStop.setEnabled(False)

        suite_result = payload[
            "suite_result"
        ]

        report_path = Path(
            payload["report_path"]
        )

        total_cases = suite_result.get(
            "total_cases",
            0,
        )
        executed_cases = suite_result.get(
            "executed_cases",
            total_cases,
        )
        passed = suite_result.get(
            "passed",
            0,
        )
        failed = suite_result.get(
            "failed",
            0,
        )
        errors = suite_result.get(
            "errors",
            0,
        )
        aborted = suite_result.get(
            "aborted",
            0,
        )
        not_run = suite_result.get(
            "not_run",
            0,
        )

        profile_summary = suite_result.get(
            "profile_summary",
            {},
        )

        active_profiles = sum(
            1
            for item in profile_summary.values()
            if item.get(
                "total",
                0,
            ) > 0
        )

        self._log(
            "[SUITE] "
            f"A02 Result: {suite_result['result']}"
        )
        self._log(
            "[SUITE] "
            f"Executed: {executed_cases}/{total_cases}"
        )
        self._log(
            "[SUITE] "
            f"Passed: {passed}"
        )
        self._log(
            "[SUITE] "
            f"Failed: {failed}"
        )
        self._log(
            "[SUITE] "
            f"Error: {errors}"
        )
        self._log(
            "[SUITE] "
            f"Aborted: {aborted}"
        )
        self._log(
            "[SUITE] "
            f"Not Run: {not_run}"
        )
        self._log(
            "[SUITE] "
            f"Fault Profiles: {active_profiles}"
        )

        if suite_result.get(
            "stopped",
            False,
        ):
            self._log(
                "[STOP] "
                f"Reason: "
                f"{suite_result.get('stop_reason')}"
            )

        self._log(
            "[SUITE] "
            f"Duration: "
            f"{suite_result.get('duration_sec', 0):.3f} s"
        )

        self._log(
            "[REPORT] "
            f"PDF: {report_path}"
        )

        if self._report_auto_open_enabled():
            self._open_report(
                report_path,
                "A02"
            )

    def _report_auto_open_enabled(self):
        try:
            config = load_validation_config()

            return bool(
                config
                .get("report", {})
                .get("auto_open", False)
            )

        except Exception as exc:
            self._log(
                "[REPORT] "
                f"Could not read auto_open setting: {exc}"
            )

            return False

    def _open_report(
        self,
        report_path,
        report_label="PDF",
    ):
        report_path = Path(
            report_path
        ).resolve()

        if not report_path.exists():
            self._log(
                "[REPORT] "
                f"PDF not found: {report_path}"
            )
            return

        opened = QDesktopServices.openUrl(
            QUrl.fromLocalFile(
                str(report_path)
            )
        )

        if opened:
            self._log(
                "[REPORT] "
                f"{report_label} PDF open request sent."
            )
        else:
            self._log(
                "[REPORT] "
                f"Failed to open {report_label} PDF."
            )

    def _find_last_report(self):
        if not REPORT_ROOT.exists():
            return None

        report_files = [
            path
            for path in REPORT_ROOT.rglob("*.pdf")
            if path.is_file()
        ]

        if not report_files:
            return None

        return max(
            report_files,
            key=lambda path: path.stat().st_mtime,
        )

    def _open_last_report(self):
        report_path = self._find_last_report()

        if report_path is None:
            self._log(
                "[REPORT] No PDF report found."
            )

            self._blank_line()
            return

        self._log(
            "[REPORT] "
            f"Opening last report: {report_path}"
        )

        self._open_report(
            report_path,
            "Last Report"
        )

        self._blank_line()

    def _on_test_error(self, traceback_text):
        test_id = self._active_test_id or "UNKNOWN"

        self.ui.btnTestStop.setEnabled(False)

        self._log(
            f"[ERROR] {test_id} execution failed."
        )

        for line in traceback_text.rstrip().splitlines():
            self._log(
                f"[ERROR] {line}"
            )

    def _on_test_thread_finished(self):
        test_id = self._active_test_id or "UNKNOWN"

        if self._active_test_button is not None:
            self._active_test_button.setEnabled(
                True
            )

        self.ui.btnTestStop.setEnabled(False)

        self._log(
            f"[SYSTEM] {test_id} worker finished."
        )

        self._blank_line()

        self._test_thread = None
        self._test_worker = None

        self._active_test_id = None
        self._active_test_name = None
        self._active_test_button = None
        self._active_cancellation_token = None

    def _read_current_data(self):
        with STORAGE_FILE.open(
            "r",
            encoding="utf-8"
        ) as file:
            storage = json.load(file)

        self._log(
            "[STORAGE] Current Mock Storage"
        )

        self._log(
            "[STORAGE] LBA    DATA"
        )

        self._log(
            "[STORAGE] ------------------------------"
        )

        for lba, block in storage["blocks"].items():
            pattern = block["pattern"]

            self._log(
                f"[STORAGE] {lba:<6} {pattern}"
            )

        self._blank_line()

    def _reset_data(self):
        shutil.copyfile(
            STORAGE_SEED_FILE,
            STORAGE_FILE
        )

        self._log(
            "[STORAGE] Mock Storage reset completed."
        )

        self._blank_line()
