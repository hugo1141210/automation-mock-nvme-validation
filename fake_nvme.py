import argparse
import json
import os

from amnv.fault_injector import FaultInjector
from amnv.mock_controller import MockController
from amnv.models import SQEntry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Automation Mock NVMe Controller CLI"
    )

    parser.add_argument(
        "command",
        help=(
            "Command opcode, for example: "
            "identify, smart, read, write, or unsupported opcode"
        ),
    )

    parser.add_argument(
        "--cid",
        type=int,
        required=True,
        help="Host-assigned Command Identifier",
    )

    parser.add_argument(
        "--nsid",
        type=int,
        default=1,
        help="Namespace Identifier",
    )

    parser.add_argument(
        "--lba",
        type=int,
        default=None,
        help="Logical Block Address",
    )

    parser.add_argument(
        "--length",
        type=int,
        default=1,
        help="Number of logical blocks",
    )

    parser.add_argument(
        "--data",
        type=str,
        default=None,
        help="Write data pattern",
    )

    parser.add_argument(
        "--fault",
        type=str,
        default=None,
        help="Deterministic fault profile",
    )

    return parser


def validate_arguments(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
) -> None:
    opcode = args.command.upper()

    if args.cid < 0:
        parser.error(
            "--cid must be zero or greater."
        )

    if args.nsid <= 0:
        parser.error(
            "--nsid must be greater than zero."
        )

    if opcode in {"READ", "WRITE"}:
        if args.lba is None:
            parser.error(
                f"{opcode} requires --lba."
            )

        if args.length <= 0:
            parser.error(
                "--length must be greater than zero."
            )

    if (
        opcode == "WRITE"
        and args.data is None
    ):
        parser.error(
            "WRITE requires --data."
        )


def execute_command(
    args: argparse.Namespace,
) -> dict:
    controller = MockController()
    fault_injector = FaultInjector()

    opcode = args.command.upper()

    if opcode in {"READ", "WRITE"}:
        lba = args.lba
        length = args.length
    else:
        lba = None
        length = None

    command = SQEntry(
        cid=args.cid,
        opcode=opcode,
        nsid=args.nsid,
        lba=lba,
        length=length,
        data=args.data,
    )

    forced_completion = (
        fault_injector.before_execute(
            command=command,
            fault=args.fault,
        )
    )

    if forced_completion is not None:
        controller_result = forced_completion
    else:
        controller_result = (
            controller.execute(
                command
            )
        )

    controller_result = (
        fault_injector.after_execute(
            command=command,
            completion=controller_result,
            fault=args.fault,
        )
    )

    return {
        "process": {
            "role": "MOCK_CONTROLLER",
            "pid": os.getpid(),
        },
        "fault": args.fault,
        "command": command.to_dict(),
        "controller_result": (
            controller_result.to_dict()
        ),
    }


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    validate_arguments(
        parser,
        args,
    )

    result = execute_command(
        args
    )

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()