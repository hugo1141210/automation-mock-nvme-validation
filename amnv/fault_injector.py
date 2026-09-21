import time
from datetime import datetime

from amnv.config_loader import (
    PROJECT_ROOT,
    load_validation_config,
)
from amnv.models import CQEntry, SQEntry


class FaultInjector:
    def __init__(self):
        config = load_validation_config()

        self.command_timeout_sec = float(
            config["timeout"]["command_timeout_sec"]
        )

        self.supported_faults = set(
            config["fault_injection"]["supported_faults"]
        )

        self.runtime_log_path = (
            PROJECT_ROOT
            / "logs"
            / "runtime_fw.log"
        )

    def before_execute(
        self,
        command: SQEntry,
        fault: str | None,
    ) -> CQEntry | None:

        if fault is None:
            return None

        self._validate_fault(
            command=command,
            fault=fault,
        )

        # -------------------------------------------------
        # TIMEOUT
        #
        # Controller does not return a normal Completion.
        # Host-side CommandRunner detects timeout.
        # -------------------------------------------------
        if fault == "timeout":
            self._simulate_timeout()

        # -------------------------------------------------
        # NAND READ FAILURE
        # -------------------------------------------------
        if fault == "NAND_READ_FAIL":
            return CQEntry(
                cid=command.cid,
                status="FAILED",
                error="NAND_READ_FAIL",
                data=None,
            )

        # -------------------------------------------------
        # NAND PROGRAM FAILURE
        # -------------------------------------------------
        if fault == "NAND_PROGRAM_FAIL":
            return CQEntry(
                cid=command.cid,
                status="FAILED",
                error="NAND_PROGRAM_FAIL",
                data=None,
            )

        # miscompare occurs after normal execution.
        return None

    def after_execute(
        self,
        command: SQEntry,
        completion: CQEntry,
        fault: str | None,
    ) -> CQEntry:

        if fault is not None:
            self._validate_fault(
                command=command,
                fault=fault,
            )

            # ---------------------------------------------
            # DATA MISCOMPARE
            #
            # Command completes successfully.
            # Only returned data is corrupted.
            # ---------------------------------------------
            if (
                fault == "miscompare"
                and completion.status == "SUCCESS"
                and isinstance(
                    completion.data,
                    dict,
                )
            ):
                corrupted_data = dict(
                    completion.data
                )

                corrupted_data["pattern"] = (
                    "TEST_PATTERN_B"
                )

                completion.data = (
                    corrupted_data
                )

        # -------------------------------------------------
        # Mock firmware runtime log
        #
        # Executed inside the Mock Controller subprocess.
        # Timeout does not reach this point because Host
        # terminates the subprocess first.
        # -------------------------------------------------
        self._append_runtime_log(
            command=command,
            completion=completion,
        )

        return completion

    def _simulate_timeout(
        self,
    ) -> None:

        time.sleep(
            self.command_timeout_sec + 1.0
        )

    def _append_runtime_log(
        self,
        command: SQEntry,
        completion: CQEntry,
    ) -> None:

        self.runtime_log_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        timestamp = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        lba_text = (
            "-"
            if command.lba is None
            else str(command.lba)
        )

        error_text = (
            "NONE"
            if completion.error is None
            else completion.error
        )

        line = (
            f"{timestamp} "
            f"CID={command.cid} "
            f"OPCODE={command.opcode} "
            f"LBA={lba_text} "
            f"STATUS={completion.status} "
            f"ERROR={error_text}\n"
        )

        with self.runtime_log_path.open(
            "a",
            encoding="utf-8",
        ) as file:
            file.write(line)

    def _validate_fault(
        self,
        command: SQEntry,
        fault: str,
    ) -> None:

        if fault not in self.supported_faults:
            raise ValueError(
                f"Unsupported fault profile: {fault}"
            )

        if (
            fault == "NAND_READ_FAIL"
            and command.opcode != "READ"
        ):
            raise ValueError(
                "NAND_READ_FAIL can only be "
                "injected into READ commands."
            )

        if (
            fault == "NAND_PROGRAM_FAIL"
            and command.opcode != "WRITE"
        ):
            raise ValueError(
                "NAND_PROGRAM_FAIL can only be "
                "injected into WRITE commands."
            )

        if (
            fault == "miscompare"
            and command.opcode != "READ"
        ):
            raise ValueError(
                "miscompare can only be "
                "injected into READ commands."
            )