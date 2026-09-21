import json
import shutil
from pathlib import Path
from typing import Any

from amnv.config_loader import (
    load_validation_config,
    resolve_project_path,
)


class MockStorage:
    def __init__(self):
        config = load_validation_config()

        storage_config = config["storage"]

        self.runtime_file = resolve_project_path(
            storage_config["runtime_file"]
        )

        self.seed_file = resolve_project_path(
            storage_config["seed_file"]
        )

        self.block_size_bytes = self._load_block_size()

    def _load_block_size(self) -> int:
        storage = self._load_storage_file(
            self.runtime_file
        )

        return storage["block_size_bytes"]

    @staticmethod
    def _load_storage_file(
        file_path: Path
    ) -> dict[str, Any]:

        with file_path.open(
            "r",
            encoding="utf-8"
        ) as file:
            return json.load(file)

    @staticmethod
    def _save_storage_file(
        file_path: Path,
        storage: dict[str, Any]
    ) -> None:

        with file_path.open(
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                storage,
                file,
                indent=2,
                ensure_ascii=False
            )

            file.write("\n")

    def read_pattern(
        self,
        lba: int
    ) -> str | None:

        storage = self._load_storage_file(
            self.runtime_file
        )

        block = storage["blocks"].get(
            str(lba)
        )

        if block is None:
            return None

        return block["pattern"]

    def read_block(
        self,
        lba: int
    ) -> bytes:

        pattern = self.read_pattern(lba)

        # Unwritten LBA:
        # Return one block filled with 0x00.
        if pattern is None:
            return bytes(self.block_size_bytes)

        encoded = pattern.encode("utf-8")

        if len(encoded) > self.block_size_bytes:
            raise ValueError(
                f"Data exceeds block size: "
                f"{len(encoded)} > "
                f"{self.block_size_bytes}"
            )

        return encoded.ljust(
            self.block_size_bytes,
            b"\x00"
        )

    def write_pattern(
        self,
        lba: int,
        pattern: str
    ) -> None:

        encoded = pattern.encode("utf-8")

        if len(encoded) > self.block_size_bytes:
            raise ValueError(
                f"Data exceeds block size: "
                f"{len(encoded)} > "
                f"{self.block_size_bytes}"
            )

        storage = self._load_storage_file(
            self.runtime_file
        )

        storage["blocks"][str(lba)] = {
            "pattern": pattern
        }

        self._save_storage_file(
            self.runtime_file,
            storage
        )

    def get_blocks(
        self
    ) -> dict[str, Any]:

        storage = self._load_storage_file(
            self.runtime_file
        )

        return storage["blocks"]

    def reset(
        self
    ) -> None:

        shutil.copyfile(
            self.seed_file,
            self.runtime_file
        )