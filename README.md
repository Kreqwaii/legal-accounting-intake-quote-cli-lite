# Legal & Accounting Client Intake & Retainer Quote CLI (Lite)

A **zero-dependency Python 3.9+ stdlib CLI** backed by **SQLite** for law firms, solo attorneys, CPAs, and accounting practices. Streamline structured client intake by legal/tax category, auto-generate required document checklists, calculate transparent retainer quotes, and export client cards to **Markdown, JSON, or CSV**.

## Key Features (Lite)

- **Zero External Dependencies**: Runs on pure Python 3.9+ standard library (`sqlite3`, `argparse`, `json`, `csv`).
- **Structured Legal & Tax Categories**:
  - Legal: `corp-formation`, `contract-review`, `ip-trademark`
  - Accounting & Tax: `tax-individual`, `tax-business`, `audit-defense`
- **Auto-Generated Document Checklists**: Every intake automatically creates a tailored document checklist that can be tracked item-by-item.
- **Dynamic Retainer Quote Engine**: Calculates quotes based on category base retainer, urgency (`standard`, `priority`, `rush`), complexity (`low`, `medium`, `high`), package discounts (`one-time`, `monthly-retainer`, `annual-retainer`), and extra hours.
- **Multi-Format Export**: Export any client intake card to Markdown, JSON, or CSV.

## Quickstart

```bash
# 1. Initialize SQLite database
python -m intake_cli.cli --db intake.db init

# 2. List supported legal & accounting categories
python -m intake_cli.cli categories

# 3. Preview a retainer quote
python -m intake_cli.cli quote --category tax-business --urgency priority --package monthly-retainer

# 4. Create a client intake
python -m intake_cli.cli --db intake.db intake \
  --name "Alice Mercer" \
  --email "alice@mercerlabs.io" \
  --company "Mercer Labs LLC" \
  --category corp-formation \
  --urgency priority \
  --package annual-retainer

# 5. Track document checklist & export client card
python -m intake_cli.cli --db intake.db checklist 1 --doc 1
python -m intake_cli.cli --db intake.db export 1 --format markdown --out client_1.md
```

## Lite vs Pro (Telegram Bot + Web CRM)

Need automated client onboarding via **Telegram Bot**, a **Web CRM dashboard**, PDF engagement letters, and payment links? Check out the **Pro Edition** on FunPay: **[Get Pro Edition on FunPay](https://funpay.com/users/20096179/)**.

| Feature | Lite (Open-Source CLI) | Pro (Telegram Bot + Web CRM) |
| :--- | :---: | :---: |
| SQLite Local Storage | ✅ | ✅ (PostgreSQL / SQLite) |
| Legal & Tax Categories | ✅ | ✅ (Custom Builder) |
| Auto Document Checklist | ✅ | ✅ (With File Uploads) |
| Retainer Quote Calculator | ✅ | ✅ (Custom Tiers & Taxes) |
| Markdown / JSON / CSV Export | ✅ | ✅ (+ Branded PDF Quotes) |
| **Telegram Intake Bot** | ❌ | ✅ |
| **Web CRM & Pipeline Board** | ❌ | ✅ |
| **Automated Reminders & Invoices** | ❌ | ✅ |

👉 **[Upgrade to Pro on FunPay](https://funpay.com/users/20096179/)**

## Running Tests

```bash
python -m unittest discover -s tests -v
```

## License

MIT License — see [LICENSE](LICENSE).
