import json
import os
import subprocess
import sys
import time
from typing import Any

from amnv.cancellation import CancellationToken
from amnv.config_loader import (
    PROJECT_ROOT,
    load_validation_config,
)
from amnv.models import CQEntry, SQEntry
from amnv.queue_model import QueueModel


class CommandRunner:
    POLL_INTERVAL_SEC = 0.05
    TERMINATE_GRACE_SEC = 0.5

    def __init__(
        self,
        cancellation_token: CancellationToken | None = None,
    ):
        self.config = load_validation_config()

        self.cancellation_token = cancellation_token

        self.queue = QueueModel()

        self.timeout_sec = float(
            self.config[
                "timeout"
            ]["command_timeout_sec"]
        )

        self.fake_nvme_path = (
            PROJECT_ROOT / "fake_nvme.py"
        )

        self.host_pid = os.getpid()

    def execute(
        self,
        opcode: str,
        nsid: int = 1,
        lba: int | None = None,
        length: int | None = None,
        data: str | None = None,
        fault: str | None = None,
    ) -> dict[str, Any]:

        opcode = opcode.upper()

        if opcode in {"READ", "WRITE"}:
            if length is None:
                length = 1
        else:
            lba = None
            length = None

        trace: list[
            dict[str, Any]
        ] = []

        # ---------------------------------------------
        # 1. Host submits Command into SQ.
        # ---------------------------------------------
        sq_entry = (
            self.queue.host_submit_command(
                opcode=opcode,
                nsid=nsid,
                lba=lba,
                length=length,
                data=data,
            )
        )

        trace.append(
            self._trace_event(
                stage="SQ_SUBMIT",
                cid=sq_entry.cid,
            )
        )

        # Logical SQ Tail Doorbell.
        trace.append(
            self._trace_event(
                stage="SQ_TAIL_DOORBELL",
                cid=sq_entry.cid,
            )
        )

        # ---------------------------------------------
        # 2. Controller fetches SQ Entry.
        # ---------------------------------------------
        fetched_entry = (
            self.queue.controller_fetch_command()
        )

        if fetched_entry is None:
            raise RuntimeError(
                "Controller could not fetch "
                "SQ Entry."
            )

        if (
            fetched_entry.cid
            != sq_entry.cid
        ):
            raise RuntimeError(
                "Fetched CID does not match "
                "submitted CID."
            )

        trace.append(
            self._trace_event(
                stage="CTRL_FETCH",
                cid=fetched_entry.cid,
            )
        )

        # ---------------------------------------------
        # 3. Launch external Mock Controller.
        # ---------------------------------------------
        command = (
            self._build_subprocess_command(
                entry=fetched_entry,
                fault=fault,
            )
        )

        trace.append(
            self._trace_event(
                stage="SUBPROCESS_START",
                cid=fetched_entry.cid,
                extra={
                    "fault": fault,
                },
            )
        )

        start_time = time.monotonic()

        process = subprocess.Popen(
            command,
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        stdout = ""
        stderr = ""

        while True:
            # Completion wins if the child process has
            # already exited normally.
            if process.poll() is not None:
                stdout, stderr = (
                    process.communicate()
                )
                break

            # User cancellation is checked before the
            # normal Host timeout path.
            if self._cancel_requested():
                # Re-check once to avoid aborting a
                # process that completed between polls.
                if process.poll() is not None:
                    stdout, stderr = (
                        process.communicate()
                    )
                    break

                abort_result = (
                    self._abort_active_process(
                        process=process,
                        entry=fetched_entry,
                        fault=fault,
                        trace=trace,
                        start_time=start_time,
                    )
                )

                if abort_result is not None:
                    return abort_result

                # A very small race is possible if the
                # process exits just before terminate().
                # In that case completion wins.
                stdout, stderr = (
                    process.communicate()
                )
                break

            elapsed_sec = (
                time.monotonic()
                - start_time
            )

            if elapsed_sec >= self.timeout_sec:
                # Match the previous subprocess.run()
                # timeout behavior by ensuring the child
                # process is reaped.
                process.kill()
                process.communicate()

                duration_sec = (
                    time.monotonic()
                    - start_time
                )

                # Host detects timeout.
                #
                # No CQ Entry is posted and the
                # Command remains outstanding.
                trace.append(
                    self._trace_event(
                        stage="HOST_TIMEOUT",
                        cid=fetched_entry.cid,
                        extra={
                            "fault": fault,
                            "timeout_sec":
                                self.timeout_sec,
                            "duration_sec":
                                duration_sec,
                        },
                    )
                )

                return {
                    "host": {
                        "pid": self.host_pid,
                        "status": self.config[
                            "completion_status"
                        ]["timeout"],
                    },
                    "command":
                        fetched_entry.to_dict(),
                    "controller_process": None,
                    "controller_result": None,
                    "completion": None,
                    "fault": fault,
                    "timed_out": True,
                    "aborted": False,
                    "abort_reason": None,
                    "abort_recovery": None,
                    "duration_sec":
                        duration_sec,
                    "return_code": None,
                    "trace": trace,
                    "queue_state":
                        self._queue_snapshot(),
                }

            time.sleep(
                self.POLL_INTERVAL_SEC
            )

        duration_sec = (
            time.monotonic()
            - start_time
        )

        # ---------------------------------------------
        # 4. Process-level validation.
        # ---------------------------------------------
        if process.returncode != 0:
            raise RuntimeError(
                "Mock Controller subprocess "
                "failed.\n"
                f"Return Code: "
                f"{process.returncode}\n"
                f"STDERR:\n"
                f"{stderr}"
            )

        try:
            payload = json.loads(
                stdout
            )

        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Mock Controller returned "
                "invalid JSON."
            ) from exc

        self._validate_controller_payload(
            payload=payload,
            expected_command=fetched_entry,
        )

        controller_result_data = (
            payload["controller_result"]
        )

        trace.append(
            self._trace_event(
                stage="CTRL_RESULT",
                cid=fetched_entry.cid,
                extra={
                    "status":
                        controller_result_data[
                            "status"
                        ],
                    "fault":
                        payload.get(
                            "fault"
                        ),
                },
            )
        )

        # ---------------------------------------------
        # 5. Build Completion template.
        # ---------------------------------------------
        completion_template = CQEntry(
            cid=controller_result_data[
                "cid"
            ],
            status=controller_result_data[
                "status"
            ],
            error=controller_result_data.get(
                "error"
            ),
            data=controller_result_data.get(
                "data"
            ),
        )

        # ---------------------------------------------
        # 6. Controller posts CQ Entry.
        # ---------------------------------------------
        self.queue.controller_post_completion(
            completion_template
        )

        trace.append(
            self._trace_event(
                stage="CQ_POST",
                cid=completion_template.cid,
                extra={
                    "sqhd":
                        completion_template.sq_head,
                },
            )
        )

        # ---------------------------------------------
        # 7. Host consumes CQ Entry.
        # ---------------------------------------------
        completion = (
            self.queue.host_consume_completion()
        )

        if completion is None:
            raise RuntimeError(
                "Host could not consume CQ Entry."
            )

        trace.append(
            self._trace_event(
                stage="CQ_CONSUME",
                cid=completion.cid,
            )
        )

        # Logical CQ Head Doorbell.
        trace.append(
            self._trace_event(
                stage="CQ_HEAD_DOORBELL",
                cid=completion.cid,
            )
        )

        return {
            "host": {
                "pid": self.host_pid,
                "status":
                    "COMMAND_COMPLETE",
            },
            "command":
                fetched_entry.to_dict(),
            "controller_process":
                payload.get("process"),
            "controller_result":
                controller_result_data,
            "completion":
                completion.to_dict(),
            "fault": fault,
            "timed_out": False,
            "aborted": False,
            "abort_reason": None,
            "abort_recovery": None,
            "duration_sec":
                duration_sec,
            "return_code":
                process.returncode,
            "trace": trace,
            "queue_state":
                self._queue_snapshot(),
        }

    def _cancel_requested(
        self,
    ) -> bool:

        if self.cancellation_token is None:
            return False

        return (
            self.cancellation_token
            .is_requested()
        )

    def _abort_active_process(
        self,
        process: subprocess.Popen[str],
        entry: SQEntry,
        fault: str | None,
        trace: list[dict[str, Any]],
        start_time: float,
    ) -> dict[str, Any] | None:

        reason = (
            self.cancellation_token.reason
            if self.cancellation_token
            is not None
            else "Cancellation requested"
        )

        try:
            process.terminate()

        except ProcessLookupError:
            # The subprocess completed in the narrow
            # race window between poll() and terminate().
            # Completion wins, so the caller continues
            # through the normal completion path.
            return None

        trace.append(
            self._trace_event(
                stage="CANCEL_REQUESTED",
                cid=entry.cid,
                extra={
                    "reason": reason,
                },
            )
        )

        trace.append(
            self._trace_event(
                stage="SUBPROCESS_TERMINATE",
                cid=entry.cid,
                extra={
                    "process_pid":
                        process.pid,
                    "grace_sec":
                        self.TERMINATE_GRACE_SEC,
                },
            )
        )

        termination = "terminate"

        try:
            process.communicate(
                timeout=
                    self.TERMINATE_GRACE_SEC
            )

        except subprocess.TimeoutExpired:
            process.kill()
            termination = "kill"

            trace.append(
                self._trace_event(
                    stage="SUBPROCESS_KILL",
                    cid=entry.cid,
                    extra={
                        "process_pid":
                            process.pid,
                    },
                )
            )

            process.communicate()

        duration_sec = (
            time.monotonic()
            - start_time
        )

        reset_result = (
            self.reset_controller()
        )

        trace.append(
            self._trace_event(
                stage="ABORT_CONTROLLER_RESET",
                cid=entry.cid,
                extra={
                    "queue_before":
                        reset_result["before"],
                    "queue_after":
                        reset_result["after"],
                },
            )
        )

        return {
            "host": {
                "pid": self.host_pid,
                "status": "ABORTED",
            },
            "command":
                entry.to_dict(),
            "controller_process": {
                "role": "MOCK_CONTROLLER",
                "pid": process.pid,
            },
            "controller_result": None,
            "completion": None,
            "fault": fault,
            "timed_out": False,
            "aborted": True,
            "abort_reason": reason,
            "abort_recovery": {
                "termination":
                    termination,
                "terminate_grace_sec":
                    self.TERMINATE_GRACE_SEC,
                "queue_before_reset":
                    reset_result["before"],
                "queue_after_reset":
                    reset_result["after"],
            },
            "duration_sec":
                duration_sec,
            "return_code":
                process.returncode,
            "trace": trace,
            "queue_state":
                self._queue_snapshot(),
        }

    def reset_controller(
        self,
    ) -> dict[str, Any]:

        before = (
            self._queue_snapshot()
        )

        self.queue.reset_controller_state()

        after = (
            self._queue_snapshot()
        )

        return {
            "stage":
                "CONTROLLER_RESET",
            "before": before,
            "after": after,
        }

    def _build_subprocess_command(
        self,
        entry: SQEntry,
        fault: str | None = None,
    ) -> list[str]:

        command = [
            sys.executable,
            str(self.fake_nvme_path),
            entry.opcode.lower(),
            "--cid",
            str(entry.cid),
            "--nsid",
            str(entry.nsid),
        ]

        if entry.lba is not None:
            command.extend(
                [
                    "--lba",
                    str(entry.lba),
                ]
            )

        if entry.length is not None:
            command.extend(
                [
                    "--length",
                    str(entry.length),
                ]
            )

        if entry.data is not None:
            command.extend(
                [
                    "--data",
                    str(entry.data),
                ]
            )

        if fault is not None:
            command.extend(
                [
                    "--fault",
                    fault,
                ]
            )

        return command

    def _validate_controller_payload(
        self,
        payload: dict[str, Any],
        expected_command: SQEntry,
    ) -> None:

        if (
            "controller_result"
            not in payload
        ):
            raise RuntimeError(
                "Missing controller_result "
                "in Mock Controller response."
            )

        if "command" not in payload:
            raise RuntimeError(
                "Missing command echo in "
                "Mock Controller response."
            )

        echoed_command = (
            payload["command"]
        )

        controller_result = (
            payload["controller_result"]
        )

        if echoed_command.get(
            "cid"
        ) != expected_command.cid:
            raise RuntimeError(
                "Mock Controller command "
                "CID mismatch."
            )

        if echoed_command.get(
            "opcode"
        ) != expected_command.opcode:
            raise RuntimeError(
                "Mock Controller opcode "
                "mismatch."
            )

        if controller_result.get(
            "cid"
        ) != expected_command.cid:
            raise RuntimeError(
                "Completion CID does not "
                "match the outstanding "
                "command."
            )

    def _queue_snapshot(
        self,
    ) -> dict[str, Any]:

        return {
            "sq_head":
                self.queue.sq_head,
            "sq_tail":
                self.queue.sq_tail,
            "cq_head":
                self.queue.cq_head,
            "cq_tail":
                self.queue.cq_tail,
            "outstanding_cids":
                sorted(
                    self.queue
                    .outstanding_cids
                ),
            "next_cid":
                self.queue.next_cid,
        }

    def _trace_event(
        self,
        stage: str,
        cid: int,
        extra: dict[
            str, Any
        ] | None = None,
    ) -> dict[str, Any]:

        event = {
            "stage": stage,
            "cid": cid,
            **self._queue_snapshot(),
        }

        if extra:
            event.update(
                extra
            )

        return event