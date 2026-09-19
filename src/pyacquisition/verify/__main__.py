"""Command line front end: `python -m pyacquisition.verify hardware.toml`.

By default only read-only checks run. Ask for more deliberately:

    --reversible   also change settings and put them back
    --hazardous    also run checks that can act on the outside world
    --dry-run      contact nothing, and print every command that would be sent
    --list         print the plan and stop
"""

import argparse
import json
import sys

from .inventory import load_inventory
from .model import Hazard, SpecError
from .runner import Bench
from .session import Policy


def build_parser():
    parser = argparse.ArgumentParser(
        prog="python -m pyacquisition.verify",
        description="Verify instrument classes against the instruments connected.",
    )
    parser.add_argument("inventory", help="the hardware inventory (TOML)")
    parser.add_argument(
        "--reversible",
        action="store_true",
        help="also run checks that change a setting and put it back",
    )
    parser.add_argument(
        "--hazardous",
        action="store_true",
        help="also run hazardous checks (outputs, heaters...); implies --reversible",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="contact nothing and print the commands that would be sent",
    )
    parser.add_argument("--list", action="store_true", help="print the plan and stop")
    parser.add_argument(
        "--only", nargs="+", metavar="NAME", help="only these instruments"
    )
    parser.add_argument("--json", metavar="PATH", help="also write the report as JSON")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="show the commands sent"
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    max_hazard = Hazard.READ_ONLY
    if args.reversible:
        max_hazard = Hazard.REVERSIBLE
    if args.hazardous:
        max_hazard = Hazard.HAZARDOUS

    try:
        entries = load_inventory(args.inventory)
    except (SpecError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    if args.only:
        unknown = set(args.only) - {entry.name for entry in entries}
        if unknown:
            print(f"error: not in the inventory: {sorted(unknown)}", file=sys.stderr)
            return 2
        entries = [entry for entry in entries if entry.name in args.only]

    with Bench(Policy(max_hazard), dry_run=args.dry_run) as bench:
        try:
            if args.list:
                for entry in entries:
                    print(f"{entry.name} ({entry.cls.__name__})")
                    for check in bench.plan(entry):
                        print(f"  {check.hazard.value:<10} {check.id}")
                return 0
            for entry in entries:
                bench.run_entry(entry)
        except SpecError as error:
            print(f"error: {error}", file=sys.stderr)
            return 2
        except KeyboardInterrupt:
            print(
                "\ninterrupted: putting the instruments in their safe state",
                file=sys.stderr,
            )

    print(bench.report.text(verbose=args.verbose))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as file:
            json.dump(bench.report.to_dict(), file, indent=2)
    return 0 if bench.report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
