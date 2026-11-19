"""Pricing rules, matter/tax categories, and auto-generated document checklists."""

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class CategorySpec:
    code: str
    domain: str  # "legal" or "accounting"
    title: str
    base_retainer: float
    hourly_rate: float
    included_hours: int
    documents: List[str]


CATEGORIES: Dict[str, CategorySpec] = {
    "corp-formation": CategorySpec(
        code="corp-formation",
        domain="legal",
        title="Corporate Formation & Governance",
        base_retainer=1500.0,
        hourly_rate=250.0,
        included_hours=5,
        documents=[
            "Founder ID / Passport Copies",
            "Proposed Entity Name & Ownership Split",
            "Registered Agent Authorization",
            "Operating Agreement / Bylaws Questionnaire",
        ],
    ),
    "contract-review": CategorySpec(
        code="contract-review",
        domain="legal",
        title="Commercial Contract Review & Drafting",
        base_retainer=1200.0,
        hourly_rate=275.0,
        included_hours=4,
        documents=[
            "Draft Agreement (DOCX/PDF)",
            "Counterparty Term Sheet or Email Thread",
            "Risk Tolerance & Redline Priorities",
        ],
    ),
    "ip-trademark": CategorySpec(
        code="ip-trademark",
        domain="legal",
        title="IP & Trademark Registration",
        base_retainer=1800.0,
        hourly_rate=260.0,
        included_hours=6,
        documents=[
            "Brand Name / Logo High-Res Specimen",
            "Goods & Services Class List",
            "First Use Date & Commerce Evidence",
        ],
    ),
    "tax-individual": CategorySpec(
        code="tax-individual",
        domain="accounting",
        title="Individual & Expat Tax Filing",
        base_retainer=650.0,
        hourly_rate=160.0,
        included_hours=3,
        documents=[
            "Prior Year Tax Return (2 years)",
            "W-2 / 1099 / Foreign Income Statements",
            "Bank Interest & Brokerage 1099-B/DIV",
            "Deductible Expense & Charity Receipts",
        ],
    ),
    "tax-business": CategorySpec(
        code="tax-business",
        domain="accounting",
        title="Business Tax & Monthly Bookkeeping",
        base_retainer=1400.0,
        hourly_rate=185.0,
        included_hours=7,
        documents=[
            "Prior Year Business Tax Return",
            "Trial Balance & General Ledger Export",
            "Bank & Credit Card Statements (12 months)",
            "Payroll Summary & Contractor 1099s",
        ],
    ),
    "audit-defense": CategorySpec(
        code="audit-defense",
        domain="accounting",
        title="Tax Audit Defense & Controversy",
        base_retainer=2500.0,
        hourly_rate=240.0,
        included_hours=8,
        documents=[
            "IRS / Tax Authority Notice Letter",
            "Power of Attorney (Form 2848)",
            "Filed Returns for Audited Periods",
            "Supporting Invoices & Bank Proof",
        ],
    ),
}

URGENCY_MULTIPLIERS: Dict[str, float] = {
    "standard": 1.0,
    "priority": 1.25,
    "rush": 1.5,
}

COMPLEXITY_MULTIPLIERS: Dict[str, float] = {
    "low": 0.9,
    "medium": 1.0,
    "high": 1.35,
}

PACKAGE_DISCOUNTS: Dict[str, float] = {
    "one-time": 0.0,
    "monthly-retainer": 0.10,
    "annual-retainer": 0.15,
}


def get_category(code: str) -> CategorySpec:
    if code not in CATEGORIES:
        valid = ", ".join(sorted(CATEGORIES.keys()))
        raise ValueError(f"Unknown category '{code}'. Valid categories: {valid}")
    return CATEGORIES[code]


def calculate_quote(
    category_code: str,
    urgency: str = "standard",
    complexity: str = "medium",
    package: str = "one-time",
    extra_hours: int = 0,
) -> Dict[str, object]:
    spec = get_category(category_code)
    if urgency not in URGENCY_MULTIPLIERS:
        raise ValueError(f"Invalid urgency '{urgency}'. Choose: {', '.join(URGENCY_MULTIPLIERS)}")
    if complexity not in COMPLEXITY_MULTIPLIERS:
        raise ValueError(f"Invalid complexity '{complexity}'. Choose: {', '.join(COMPLEXITY_MULTIPLIERS)}")
    if package not in PACKAGE_DISCOUNTS:
        raise ValueError(f"Invalid package '{package}'. Choose: {', '.join(PACKAGE_DISCOUNTS)}")
    if extra_hours < 0:
        raise ValueError("extra_hours must be >= 0")

    u_mult = URGENCY_MULTIPLIERS[urgency]
    c_mult = COMPLEXITY_MULTIPLIERS[complexity]
    discount_rate = PACKAGE_DISCOUNTS[package]

    base_adjusted = spec.base_retainer * u_mult * c_mult
    extra_fee = extra_hours * spec.hourly_rate
    subtotal = round(base_adjusted + extra_fee, 2)
    discount_amount = round(subtotal * discount_rate, 2)
    total = round(subtotal - discount_amount, 2)

    return {
        "category": spec.code,
        "domain": spec.domain,
        "title": spec.title,
        "urgency": urgency,
        "complexity": complexity,
        "package": package,
        "included_hours": spec.included_hours,
        "extra_hours": extra_hours,
        "hourly_rate": spec.hourly_rate,
        "subtotal": subtotal,
        "discount_amount": discount_amount,
        "total_quote": total,
    }
