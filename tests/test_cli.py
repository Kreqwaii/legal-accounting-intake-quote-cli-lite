import csv
import io
import json
import tempfile
import unittest
from pathlib import Path

from intake_cli.cli import main
from intake_cli.pricing import CATEGORIES, calculate_quote, get_category
from intake_cli.storage import IntakeStorage


class TestPricing(unittest.TestCase):
    def test_all_categories_have_documents(self):
        for code, spec in CATEGORIES.items():
            self.assertTrue(len(spec.documents) >= 3, f"{code} missing documents")

    def test_get_category_valid(self):
        spec = get_category("corp-formation")
        self.assertEqual(spec.domain, "legal")

    def test_get_category_invalid(self):
        with self.assertRaises(ValueError):
            get_category("unknown-cat")

    def test_quote_standard_one_time(self):
        q = calculate_quote("corp-formation")
        self.assertEqual(q["total_quote"], 1500.0)

    def test_quote_urgency_priority(self):
        q = calculate_quote("corp-formation", urgency="priority")
        self.assertEqual(q["total_quote"], 1875.0)

    def test_quote_urgency_rush(self):
        q = calculate_quote("tax-individual", urgency="rush")
        self.assertEqual(q["total_quote"], 975.0)

    def test_quote_complexity_low(self):
        q = calculate_quote("contract-review", complexity="low")
        self.assertEqual(q["total_quote"], 1080.0)

    def test_quote_complexity_high(self):
        q = calculate_quote("contract-review", complexity="high")
        self.assertEqual(q["total_quote"], 1620.0)

    def test_quote_monthly_retainer_discount(self):
        q = calculate_quote("tax-business", package="monthly-retainer")
        self.assertEqual(q["discount_amount"], 140.0)
        self.assertEqual(q["total_quote"], 1260.0)

    def test_quote_annual_retainer_discount(self):
        q = calculate_quote("ip-trademark", package="annual-retainer")
        self.assertEqual(q["discount_amount"], 270.0)
        self.assertEqual(q["total_quote"], 1530.0)

    def test_quote_extra_hours(self):
        q = calculate_quote("corp-formation", extra_hours=2)
        self.assertEqual(q["total_quote"], 2000.0)

    def test_quote_invalid_urgency(self):
        with self.assertRaises(ValueError):
            calculate_quote("corp-formation", urgency="urgent")

    def test_quote_invalid_complexity(self):
        with self.assertRaises(ValueError):
            calculate_quote("corp-formation", complexity="extreme")

    def test_quote_invalid_package(self):
        with self.assertRaises(ValueError):
            calculate_quote("corp-formation", package="weekly")

    def test_quote_negative_extra_hours(self):
        with self.assertRaises(ValueError):
            calculate_quote("corp-formation", extra_hours=-1)


class TestStorageAndCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp.name) / "test.db")
        self.storage = IntakeStorage(self.db_path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_init_db(self):
        self.storage.init_db()
        self.assertTrue(Path(self.db_path).exists())

    def test_create_intake_and_checklist(self):
        client = self.storage.create_intake(
            client_name="Jane Doe",
            email="jane@example.com",
            category="tax-individual",
            company="Doe Consulting",
        )
        self.assertEqual(client["id"], 1)
        self.assertEqual(client["status"], "new")
        self.assertEqual(len(client["checklist"]), 4)
        self.assertFalse(client["checklist"][0]["received"])

    def test_mark_document_received_and_undo(self):
        client = self.storage.create_intake("Bob", "bob@test.com", "contract-review")
        updated = self.storage.mark_document(client["id"], 1, received=True)
        self.assertTrue(updated["checklist"][0]["received"])
        reverted = self.storage.mark_document(client["id"], 1, received=False)
        self.assertFalse(reverted["checklist"][0]["received"])

    def test_mark_document_out_of_range(self):
        client = self.storage.create_intake("Bob", "bob@test.com", "contract-review")
        with self.assertRaises(ValueError):
            self.storage.mark_document(client["id"], 99)

    def test_update_status(self):
        client = self.storage.create_intake("Bob", "bob@test.com", "audit-defense")
        updated = self.storage.update_status(client["id"], "retained")
        self.assertEqual(updated["status"], "retained")

    def test_update_status_invalid(self):
        client = self.storage.create_intake("Bob", "bob@test.com", "audit-defense")
        with self.assertRaises(ValueError):
            self.storage.update_status(client["id"], "archived")

    def test_list_clients_filters(self):
        self.storage.create_intake("Legal Client", "l@test.com", "corp-formation")
        c2 = self.storage.create_intake("Tax Client", "t@test.com", "tax-business")
        self.storage.update_status(c2["id"], "quoted")

        self.assertEqual(len(self.storage.list_clients(domain="legal")), 1)
        self.assertEqual(len(self.storage.list_clients(status="quoted")), 1)

    def test_export_markdown(self):
        c = self.storage.create_intake("Alice", "a@test.com", "ip-trademark", notes="Urgent filing")
        md = self.storage.export_client(c["id"], fmt="markdown")
        self.assertIn("# Client Intake Card #1: Alice", md)
        self.assertIn("## Document Checklist", md)
        self.assertIn("Urgent filing", md)

    def test_export_json(self):
        c = self.storage.create_intake("Alice", "a@test.com", "ip-trademark")
        raw = self.storage.export_client(c["id"], fmt="json")
        parsed = json.loads(raw)
        self.assertEqual(parsed["client_name"], "Alice")

    def test_export_csv(self):
        c = self.storage.create_intake("Alice", "a@test.com", "ip-trademark")
        raw = self.storage.export_client(c["id"], fmt="csv")
        rows = list(csv.reader(io.StringIO(raw)))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][1], "Alice")

    def test_cli_init_and_categories(self):
        self.assertEqual(main(["--db", self.db_path, "init"]), 0)
        self.assertEqual(main(["--db", self.db_path, "categories"]), 0)

    def test_cli_quote_and_intake_flow(self):
        self.assertEqual(main(["--db", self.db_path, "quote", "--category", "tax-business"]), 0)
        self.assertEqual(
            main(
                [
                    "--db",
                    self.db_path,
                    "intake",
                    "--name",
                    "CLI User",
                    "--email",
                    "cli@test.com",
                    "--category",
                    "corp-formation",
                ]
            ),
            0,
        )
        self.assertEqual(main(["--db", self.db_path, "list"]), 0)
        self.assertEqual(main(["--db", self.db_path, "show", "1"]), 0)
        self.assertEqual(main(["--db", self.db_path, "checklist", "1", "--doc", "1"]), 0)
        self.assertEqual(main(["--db", self.db_path, "status", "1", "retained"]), 0)

    def test_cli_export_to_file(self):
        main(
            [
                "--db",
                self.db_path,
                "intake",
                "--name",
                "Export User",
                "--email",
                "exp@test.com",
                "--category",
                "tax-individual",
            ]
        )
        out_file = Path(self.tmp.name) / "card.md"
        rc = main(["--db", self.db_path, "export", "1", "--format", "markdown", "--out", str(out_file)])
        self.assertEqual(rc, 0)
        self.assertTrue(out_file.exists())


if __name__ == "__main__":
    unittest.main()
