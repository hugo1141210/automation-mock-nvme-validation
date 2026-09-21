import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]

VALIDATION_CONFIG_FILE = (
    PROJECT_ROOT / "config" / "validation_config.json"
)


def load_json(file_path: Path) -> dict[str, Any]:
    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def resolve_project_path(relative_path: str) -> Path:
    return PROJECT_ROOT / relative_path


def load_validation_config() -> dict[str, Any]:
    return load_json(VALIDATION_CONFIG_FILE)


def load_mock_device() -> dict[str, Any]:
    config = load_validation_config()

    device_file = resolve_project_path(
        config["device"]["definition_file"]
    )

    return load_json(device_file)


def load_fault_campaign() -> dict[str, Any]:
    config = load_validation_config()

    campaign_file = resolve_project_path(
        config["automation"]["a02"]["campaign_file"]
    )

    return load_json(campaign_file)