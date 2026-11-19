"""Zero-dependency CLI entrypoint for Legal & Accounting Client Intake & Retainer Quote."""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from .pricing import CATEGORIES, calculate_quote
from .storage import IntakeStorage


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="intake-cli",
        description="Legal & Accounting Client Intake & Retainer Quote CLI (Lite)",
    )
    parser.add_argument(
        "--db",
        default="intake.db",
        help="Path to SQLite database file (default: intake.db)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Initialize the SQLite intake database")

    sub.add_parser("categories", help="List available legal & accounting intake categories")

    p_quote = sub.add_parser("quote", help="Calculate a retainer quote without saving")
    p_quote.add_argument("--category", required=True, help="Category code")
    p_quote.add_argument("--urgency", default="standard", choices=["standard", "priority", "rush"])
    p_quote.add_argument("--complexity", default="medium", choices=["low", "medium", "high"])
    p_quote.add_argument(
        "--package",
        default="one-time",
        choices=["one-time", "monthly-retainer", "annual-retainer"],
    )
    p_quote.add_argument("--extra-hours", type=int, default=0)

    p_intake = sub.add_parser("intake", help="Create a new client intake record")
    p_intake.add_argument("--name", required=True, help="Client full name")
    p_intake.add_argument("--email", required=True, help="Client email address")
    p_intake.add_argument("--category", required=True, help="Category code")
    p_intake.add_argument("--company", default="", help="Company or entity name")
    p_intake.add_argument("--urgency", default="standard", choices=["standard", "priority", "rush"])
    p_intake.add_argument("--complexity", default="medium", choices=["low", "medium", "high"])
    p_intake.add_argument(
        "--package",
        default="one-time",
        choices=["one-time", "monthly-retainer", "annual-retainer"],
    )
    p_intake.add_argument("--extra-hours", type=int, default=0)
    p_intake.add_argument("--notes", default="", help="Optional intake notes")

    p_list = sub.add_parser("list", help="List client intakes")
    p_list.add_argument("--domain", choices=["legal", "accounting"], default=None)
    p_list.add_argument("--status", choices=["new", "quoted", "retained", "closed"], default=None)

    p_show = sub.add_parser("show", help="Show full client intake card & checklist")
    p_show.add_argument("client_id", type=int, help="Client ID")

    p_check = sub.add_parser("checklist", help="Mark a document checklist item received/pending")
    p_check.add_argument("client_id", type=int, help="Client ID")
    p_check.add_argument("--doc", type=int, required=True, help="1-based document index")
    p_check.add_argument("--undo", action="store_true", help="Mark as not received")

    p_status = sub.add_parser("status", help="Update client intake status")
    p_status.add_argument("client_id", type=int, help="Client ID")
    p_status.add_argument("new_status", choices=["new", "quoted", "retained", "closed"])

    p_export = sub.add_parser("export", help="Export client card to Markdown, JSON, or CSV")
    p_export.add_argument("client_id", type=int, help="Client ID")
    p_export.add_argument("--format", default="markdown", choices=["markdown", "json", "csv"])
    p_export.add_argument("--out", default=None, help="Optional output file path")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    storage = IntakeStorage(args.db)

    try:
        if args.command == "init":
            storage.init_db()
            print(f"Initialized SQLite database at {args.db}")
            return 0

        if args.command == "categories":
            for code, spec in sorted(CATEGORIES.items()):
                print(
                    f"{code:16} | {spec.domain:10} | ${spec.base_retainer:7.2f} "
                    f"({spec.included_hours}h) | {spec.title}"
                )
            return 0

        if args.command == "quote":
            q = calculate_quote(
                category_code=args.category,
                urgency=args.urgency,
                complexity=args.complexity,
                package=args.package,
                extra_hours=args.extra_hours,
            )
            print(json.dumps(q, indent=2))
            return 0

        if args.command == "intake":
            client = storage.create_intake(
                client_name=args.name,
                email=args.email,
                category=args.category,
                company=args.company,
                urgency=args.urgency,
                complexity=args.complexity,
                package=args.package,
                extra_hours=args.extra_hours,
                notes=args.notes,
            )
            print(
                f"Created intake #{client['id']} for {client['client_name']} "
                f"({client['category']}) | Quote: ${client['total_quote']:.2f}"
            )
            return 0

        if args.command == "list":
            rows = storage.list_clients(domain=args.domain, status=args.status)
            if not rows:
                print("No client intakes found.")
                return 0
            for r in rows:
                print(
                    f"#{r['id']:<3} | {r['client_name']:20} | {r['category']:16} | "
                    f"${r['total_quote']:8.2f} | {r['status']}"
                )
            return 0

        if args.command == "show":
            print(storage.export_client(args.client_id, fmt="markdown"), end="")
            return 0

        if args.command == "checklist":
            client = storage.mark_document(
                args.client_id, args.doc, received=not args.undo
            )
            state = "received" if not args.undo else "pending"
            print(f"Updated doc #{args.doc} for client #{client['id']} -> {state}")
            return 0

        if args.command == "status":
            client = storage.update_status(args.client_id, args.new_status)
            print(f"Updated client #{client['id']} status -> {client['status']}")
            return 0

        if args.command == "export":
            content = storage.export_client(args.client_id, fmt=args.format)
            if args.out:
                out_path = Path(args.out)
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(content, encoding="utf-8")
                print(f"Exported client #{args.client_id} to {args.out}")
            else:
                print(content, end="")
            return 0

    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
