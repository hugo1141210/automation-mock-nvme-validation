from amnv.config_loader import (
    load_mock_device,
    load_validation_config,
)
from amnv.models import CQEntry, SQEntry
from amnv.storage import MockStorage


class MockController:
    SUPPORTED_OPCODES = {
        "IDENTIFY",
        "SMART",
        "READ",
        "WRITE",
    }

    def __init__(self):
        self.config = load_validation_config()
        self.device = load_mock_device()
        self.storage = MockStorage()

        self.capacity_blocks = (
            self.device["namespace"]["capacity_blocks"]
        )

        self.status_success = (
            self.config["completion_status"]["success"]
        )

        self.status_invalid_range = (
            self.config["completion_status"]["invalid_range"]
        )

        self.status_unsupported = (
            self.config["completion_status"]["unsupported_command"]
        )

        self.status_failed = (
            self.config["completion_status"]["failed"]
        )

    def execute(
        self,
        command: SQEntry,
    ) -> CQEntry:

        opcode = command.opcode.upper()

        if opcode not in self.SUPPORTED_OPCODES:
            return CQEntry(
                cid=command.cid,
                status=self.status_unsupported,
                error="UNSUPPORTED_COMMAND",
            )

        if opcode == "IDENTIFY":
            return self._execute_identify(command)

        if opcode == "SMART":
            return self._execute_smart(command)

        if opcode == "READ":
            return self._execute_read(command)

        if opcode == "WRITE":
            return self._execute_write(command)

        return CQEntry(
            cid=command.cid,
            status=self.status_failed,
            error="UNKNOWN_CONTROLLER_ERROR",
        )

    def _execute_identify(
        self,
        command: SQEntry,
    ) -> CQEntry:

        namespace = self.device["namespace"]

        data = {
            "model": self.device["model"],
            "firmware_revision": (
                self.device["firmware_revision"]
            ),
            "nsid": namespace["nsid"],
            "capacity_blocks": (
                namespace["capacity_blocks"]
            ),
            "logical_block_size_bytes": (
                namespace["logical_block_size_bytes"]
            ),
        }

        return CQEntry(
            cid=command.cid,
            status=self.status_success,
            data=data,
        )

    def _execute_smart(
        self,
        command: SQEntry,
    ) -> CQEntry:

        data = dict(
            self.device["health"]
        )

        return CQEntry(
            cid=command.cid,
            status=self.status_success,
            data=data,
        )

    def _execute_read(
        self,
        command: SQEntry,
    ) -> CQEntry:

        if not self._is_valid_range(
            command.lba,
            command.length,
        ):
            return CQEntry(
                cid=command.cid,
                status=self.status_invalid_range,
                error="INVALID_RANGE",
            )

        # 目前所有正常 Read Test 都使用 Length = 1。
        # Multi-block I/O 的資料格式之後有需求再擴充。
        if command.length != 1:
            return CQEntry(
                cid=command.cid,
                status=self.status_failed,
                error="MULTI_BLOCK_NOT_IMPLEMENTED",
            )

        pattern = self.storage.read_pattern(
            command.lba
        )

        data = {
            "lba": command.lba,
            "length": command.length,
            "pattern": pattern,
            "unwritten": pattern is None,
        }

        return CQEntry(
            cid=command.cid,
            status=self.status_success,
            data=data,
        )

    def _execute_write(
        self,
        command: SQEntry,
    ) -> CQEntry:

        if not self._is_valid_range(
            command.lba,
            command.length,
        ):
            return CQEntry(
                cid=command.cid,
                status=self.status_invalid_range,
                error="INVALID_RANGE",
            )

        if command.length != 1:
            return CQEntry(
                cid=command.cid,
                status=self.status_failed,
                error="MULTI_BLOCK_NOT_IMPLEMENTED",
            )

        if not isinstance(command.data, str):
            return CQEntry(
                cid=command.cid,
                status=self.status_failed,
                error="INVALID_WRITE_DATA",
            )

        self.storage.write_pattern(
            command.lba,
            command.data,
        )

        return CQEntry(
            cid=command.cid,
            status=self.status_success,
            data={
                "lba": command.lba,
                "length": command.length,
            },
        )

    def _is_valid_range(
        self,
        lba: int | None,
        length: int | None,
    ) -> bool:

        if lba is None or length is None:
            return False

        if lba < 0:
            return False

        if length <= 0:
            return False

        end_lba = lba + length

        if end_lba > self.capacity_blocks:
            return False

        return True