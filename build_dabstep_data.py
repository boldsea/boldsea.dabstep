#!/usr/bin/env python3
"""
Builds:
  1. applications/dabstep/data/payments.sqlite  (indexed SQLite store for 138,236 payments + reference tables)
  2. applications/dabstep/dabstep-ref-data.bsl  (Countries, CardSchemes, AccountTypes, ACIs, Acquirers, MCCs, Merchants, MonthlyMerchantStats)
  3. applications/dabstep/dabstep-fees-data.bsl (1,000 FeeRule individuals)

Strictly derived from applications/dabstep/data/context/* without inspecting benchmark tasks.
"""

import csv
import json
import os
import sqlite3
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CTX = ROOT / "data" / "context"
SQLITE_PATH = ROOT / "data" / "payments.sqlite"
REF_BSL_PATH = ROOT / "dabstep-ref-data.bsl"
MCCS_BSL_PATH = ROOT / "dabstep-mccs-data.bsl"
FEES_CHUNK_SIZE = 250

DOMAIN_POLICIES = [
    {
        "id": "Policy-PinAttemptLimit",
        "policyCategory": "security",
        "metricName": "PIN Entry Attempt Limit",
        "numericValue": 3,
        "unitLabel": "consecutive incorrect attempts",
        "manualSection": "6",
        "summary": "Maximum 3 consecutive incorrect PIN entry attempts allowed before temporary card block; cardholder must contact issuing bank to unblock or reset PIN.",
    },
    {
        "id": "Policy-PciDssFine",
        "policyCategory": "compliance",
        "metricName": "PCI DSS Non-Compliance Penalty",
        "minNumericValue": 5000,
        "maxNumericValue": 100000,
        "unitLabel": "EUR/month",
        "manualSection": "7.4",
        "summary": "Failure to comply with PCI DSS can result in penalties of EUR 5,000 to EUR 100,000 per month depending on severity, plus reputation damage.",
    },
    {
        "id": "Policy-FeeFormula",
        "policyCategory": "pricing",
        "metricName": "Payment Processing Fee",
        "unitLabel": "EUR",
        "formulaText": "fee = fixed_amount + rate * transaction_value / 10000",
        "manualSection": "5",
        "summary": "Fixed amount in EUR plus variable rate multiplied by transaction value divided by 10000; null or empty list in fee rule means applies to all values; monthly volumes and fraud rates computed in natural calendar months.",
    },
    {
        "id": "Policy-FraudDefinition",
        "policyCategory": "fraud",
        "metricName": "Fraud Rate",
        "unitLabel": "ratio",
        "formulaText": "fraud_rate = fraudulent_volume / total_volume",
        "manualSection": "5, 7",
        "summary": "Fraud is defined as the ratio of monthly volume notified as fraud over monthly total volume (by EUR volume, not transaction count). Higher fraud levels increase processing fees.",
    },
    {
        "id": "Policy-ExcessiveFraudThreshold",
        "policyCategory": "fraud",
        "metricName": "Excessive Fraud Threshold",
        "unitLabel": "ratio",
        "manualSection": "7",
        "summary": "Fraud rate above which a merchant is considered excessive / liable to a high-fraud fine. The manual names the concern but gives no number: numericValue is intentionally absent.",
    },
    {
        "id": "Policy-ExcessiveRetryFee",
        "policyCategory": "pricing",
        "metricName": "Excessive Retry Fee",
        "unitLabel": "USD per retry",
        "manualSection": "5.1.5",
        "summary": "Charge per excessive transaction retry. The manual says excessive retrying leads to downgrades but gives no amount: numericValue is intentionally absent.",
    },
    {
        "id": "Policy-IntracountryDefinition",
        "policyCategory": "pricing",
        "metricName": "Local Acquiring / Intracountry",
        "formulaText": "intracountry = (issuing_country == acquirer_country)",
        "manualSection": "5, 5.1.1",
        "summary": "Domestic/local acquiring occurs when card issuer country equals acquiring bank country; cross-border transactions have different issuer and acquirer countries and typically higher fees.",
    },
    {
        "id": "Policy-TimelySettlement",
        "policyCategory": "settlement",
        "metricName": "Timely Settlement Window",
        "numericValue": 24,
        "unitLabel": "hours",
        "manualSection": "5.1.5",
        "summary": "Settle transactions within 24 hours (designated timeframe) to avoid transaction downgrades and less favorable interchange rate tiers.",
    },
    {
        "id": "Policy-VolumePricing",
        "policyCategory": "pricing",
        "metricName": "Volume-Based Pricing",
        "numericValue": 0,
        "unitLabel": "EUR minimum volume",
        "manualSection": "5.1.3",
        "summary": "No minimum volume requirement; cost per unit decreases at higher monthly volumes and flattens out at high scale.",
    },
    {
        "id": "Policy-Glossary-AVS",
        "policyCategory": "glossary",
        "metricName": "AVS",
        "manualSection": "9",
        "summary": "Address Verification Service",
    },
    {
        "id": "Policy-Glossary-CVV",
        "policyCategory": "glossary",
        "metricName": "CVV",
        "manualSection": "9",
        "summary": "Card Verification Value",
    },
    {
        "id": "Policy-Glossary-PCIDSS",
        "policyCategory": "glossary",
        "metricName": "PCI DSS",
        "manualSection": "9",
        "summary": "Payment Card Industry Data Security Standard",
    },
    {
        "id": "Policy-Glossary-ACI",
        "policyCategory": "glossary",
        "metricName": "ACI",
        "manualSection": "9",
        "summary": "Authorization Characteristics Indicator",
    },
    {
        "id": "Policy-Support-MerchantServices",
        "policyCategory": "support",
        "metricName": "Merchant Services Support",
        "manualSection": "10",
        "summary": "Phone 1-800-555-1234, Email support@paymentprocessor.com, Website www.paymentprocessor.com/support",
    },
    {
        "id": "Policy-Support-FraudPrevention",
        "policyCategory": "support",
        "metricName": "Fraud Prevention Team",
        "manualSection": "10",
        "summary": "Phone 1-800-555-5678, Email fraud@paymentprocessor.com",
    },
    {
        "id": "Policy-Support-Technical",
        "policyCategory": "support",
        "metricName": "Technical Support",
        "manualSection": "10",
        "summary": "Phone 1-800-555-9876, Email tech@paymentprocessor.com",
    },
]

# Natural calendar months for non-leap year 2023
MONTH_ENDS_2023 = [31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334, 365]

ACCOUNT_TYPES = {
    "R": "Enterprise - Retail",
    "D": "Enterprise - Digital",
    "H": "Enterprise - Hospitality",
    "F": "Platform - Franchise",
    "S": "Platform - SaaS",
    "O": "Other",
}

ACIS = {
    "A": "Card present - Non-authenticated",
    "B": "Card Present - Authenticated",
    "C": "Tokenized card with mobile device",
    "D": "Card Not Present - Card On File",
    "E": "Card Not Present - Recurring Bill Payment",
    "F": "Card Not Present - 3-D Secure",
    "G": "Card Not Present - Non-3-D Secure",
}

COUNTRY_NAMES = {
    "NL": "Netherlands",
    "IT": "Italy",
    "BE": "Belgium",
    "SE": "Sweden",
    "FR": "France",
    "LU": "Luxembourg",
    "ES": "Spain",
    "GR": "Greece",
    "US": "United States",
    "GB": "United Kingdom",
}


def doy_to_month(doy: int) -> int:
    for m, end in enumerate(MONTH_ENDS_2023, 1):
        if doy <= end:
            return m
    return 12


def capture_delay_bucket(raw: str) -> str:
    if raw in ("manual", "immediate"):
        return raw
    d = int(raw)
    if d < 3:
        return "<3"
    if d <= 5:
        return "3-5"
    return ">5"


def volume_bucket(vol: float) -> str:
    if vol < 100_000:
        return "<100k"
    if vol <= 1_000_000:
        return "100k-1m"
    if vol <= 5_000_000:
        return "1m-5m"
    return ">5m"


def fraud_bucket(rate: float) -> str:
    if rate < 0.072:
        return "<7.2%"
    if rate <= 0.077:
        return "7.2%-7.7%"
    if rate <= 0.083:
        return "7.7%-8.3%"
    return ">8.3%"


def sanitize_bsl_text(s: str) -> str:
    # Single line, strip newlines/leading colons
    return " ".join(s.replace("\r", " ").replace("\n", " ").split())


def main() -> None:
    # 1. Load reference files
    acquirers = []
    with open(CTX / "acquirer_countries.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            acquirers.append((row["acquirer"].strip(), row["country_code"].strip()))

    mcc_desc = {}
    with open(CTX / "merchant_category_codes.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            mcc_desc[int(row["mcc"])] = sanitize_bsl_text(row["description"])

    with open(CTX / "merchant_data.json", encoding="utf-8") as f:
        merchants = json.load(f)

    with open(CTX / "fees.json", encoding="utf-8") as f:
        fees = json.load(f)

    # 2. Build SQLite database
    if SQLITE_PATH.exists():
        SQLITE_PATH.unlink()

    conn = sqlite3.connect(SQLITE_PATH)
    cur = conn.cursor()
    cur.executescript(
        """
        PRAGMA journal_mode = OFF;
        PRAGMA synchronous = OFF;

        CREATE TABLE acquirers (
            acquirer TEXT PRIMARY KEY,
            country_code TEXT NOT NULL
        );

        CREATE TABLE mccs (
            mcc INTEGER PRIMARY KEY,
            description TEXT NOT NULL
        );

        CREATE TABLE merchants (
            merchant TEXT PRIMARY KEY,
            capture_delay TEXT NOT NULL,
            capture_delay_bucket TEXT NOT NULL,
            mcc INTEGER NOT NULL,
            account_type TEXT NOT NULL,
            acquirers_json TEXT NOT NULL
        );

        CREATE TABLE fee_rules (
            rule_id INTEGER PRIMARY KEY,
            card_scheme TEXT NOT NULL,
            account_types_json TEXT NOT NULL,
            capture_delay TEXT,
            monthly_fraud_level TEXT,
            monthly_volume TEXT,
            mccs_json TEXT NOT NULL,
            is_credit INTEGER,
            acis_json TEXT NOT NULL,
            intracountry INTEGER,
            fixed_amount REAL NOT NULL,
            rate INTEGER NOT NULL
        );

        CREATE TABLE payments (
            psp_reference TEXT PRIMARY KEY,
            merchant TEXT NOT NULL,
            card_scheme TEXT NOT NULL,
            year INTEGER NOT NULL,
            day_of_year INTEGER NOT NULL,
            tx_month INTEGER NOT NULL,
            hour_of_day INTEGER NOT NULL,
            minute_of_hour INTEGER NOT NULL,
            is_credit INTEGER NOT NULL,
            eur_amount REAL NOT NULL,
            ip_country TEXT NOT NULL,
            issuing_country TEXT NOT NULL,
            acquirer_country TEXT NOT NULL,
            is_intracountry INTEGER NOT NULL,
            device_type TEXT NOT NULL,
            ip_address TEXT,
            email_address TEXT,
            card_number TEXT NOT NULL,
            shopper_interaction TEXT NOT NULL,
            card_bin TEXT NOT NULL,
            has_fraudulent_dispute INTEGER NOT NULL,
            is_refused_by_adyen INTEGER NOT NULL,
            aci TEXT NOT NULL
        );

        CREATE TABLE monthly_stats (
            merchant TEXT NOT NULL,
            tx_year INTEGER NOT NULL,
            tx_month INTEGER NOT NULL,
            tx_count INTEGER NOT NULL,
            total_volume REAL NOT NULL,
            fraud_tx_count INTEGER NOT NULL,
            fraud_volume REAL NOT NULL,
            refused_tx_count INTEGER NOT NULL,
            fraud_rate REAL NOT NULL,
            volume_bucket TEXT NOT NULL,
            fraud_bucket TEXT NOT NULL,
            PRIMARY KEY (merchant, tx_year, tx_month)
        );
        """
    )

    cur.executemany("INSERT INTO acquirers VALUES (?, ?)", acquirers)
    cur.executemany("INSERT INTO mccs VALUES (?, ?)", sorted(mcc_desc.items()))
    cur.executemany(
        "INSERT INTO merchants VALUES (?, ?, ?, ?, ?, ?)",
        [
            (
                m["merchant"],
                m["capture_delay"],
                capture_delay_bucket(m["capture_delay"]),
                int(m["merchant_category_code"]),
                m["account_type"],
                json.dumps(m["acquirer"]),
            )
            for m in merchants
        ],
    )
    cur.executemany(
        "INSERT INTO fee_rules VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                int(r["ID"]),
                r["card_scheme"],
                json.dumps(r["account_type"] or []),
                r["capture_delay"],
                r["monthly_fraud_level"],
                r["monthly_volume"],
                json.dumps(r["merchant_category_code"] or []),
                None if r["is_credit"] is None else (1 if r["is_credit"] else 0),
                json.dumps(r["aci"] or []),
                None if r["intracountry"] is None else (1 if float(r["intracountry"]) >= 0.5 else 0),
                float(r["fixed_amount"]),
                int(r["rate"]),
            )
            for r in fees
        ],
    )

    # Stream payments.csv into SQLite and accumulate monthly_stats + observed domains
    stats = defaultdict(lambda: [0, 0.0, 0, 0.0, 0])  # count, vol, fcount, fvol, rcount
    observed_countries = set(c for _, c in acquirers)
    observed_schemes = set(r["card_scheme"] for r in fees)
    batch = []
    total_rows = 0

    with open(CTX / "payments.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            total_rows += 1
            year = int(row["year"])
            doy = int(row["day_of_year"])
            mo = doy_to_month(doy)
            is_credit = 1 if row["is_credit"] == "True" else 0
            amt = float(row["eur_amount"])
            ip_c = row["ip_country"]
            iss_c = row["issuing_country"]
            acq_c = row["acquirer_country"]
            intra = 1 if iss_c == acq_c else 0
            fraud = 1 if row["has_fraudulent_dispute"] == "True" else 0
            refused = 1 if row["is_refused_by_adyen"] == "True" else 0

            observed_countries.update((ip_c, iss_c, acq_c))
            observed_schemes.add(row["card_scheme"])

            st = stats[(row["merchant"], year, mo)]
            st[0] += 1
            st[1] += amt
            if fraud:
                st[2] += 1
                st[3] += amt
            if refused:
                st[4] += 1

            batch.append(
                (
                    row["psp_reference"],
                    row["merchant"],
                    row["card_scheme"],
                    year,
                    doy,
                    mo,
                    int(row["hour_of_day"]),
                    int(row["minute_of_hour"]),
                    is_credit,
                    amt,
                    ip_c,
                    iss_c,
                    acq_c,
                    intra,
                    row["device_type"],
                    row["ip_address"] or None,
                    row["email_address"] or None,
                    row["card_number"],
                    row["shopper_interaction"],
                    row["card_bin"],
                    fraud,
                    refused,
                    row["aci"],
                )
            )
            if len(batch) >= 10000:
                cur.executemany(
                    "INSERT INTO payments VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    batch,
                )
                batch.clear()

    if batch:
        cur.executemany(
            "INSERT INTO payments VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            batch,
        )

    monthly_rows = []
    for (merchant, year, mo), (cnt, vol, fcnt, fvol, rcnt) in sorted(stats.items()):
        fr = (fvol / vol) if vol > 0 else 0.0
        monthly_rows.append(
            (
                merchant,
                year,
                mo,
                cnt,
                round(vol, 6),
                fcnt,
                round(fvol, 6),
                rcnt,
                fr,
                volume_bucket(vol),
                fraud_bucket(fr),
            )
        )
    cur.executemany(
        "INSERT INTO monthly_stats VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        monthly_rows,
    )

    cur.executescript(
        """
        CREATE INDEX idx_payments_merchant_month ON payments(merchant, tx_month);
        CREATE INDEX idx_payments_merchant_doy ON payments(merchant, day_of_year);
        CREATE INDEX idx_payments_scheme ON payments(card_scheme);
        CREATE INDEX idx_payments_countries ON payments(issuing_country, acquirer_country);
        CREATE INDEX idx_payments_fraud ON payments(has_fraudulent_dispute);
        CREATE INDEX idx_payments_refused ON payments(is_refused_by_adyen);
        CREATE INDEX idx_payments_aci ON payments(aci);
        CREATE INDEX idx_payments_card_bin ON payments(card_bin);
        CREATE INDEX idx_fee_rules_scheme ON fee_rules(card_scheme);
        """
    )
    conn.commit()
    conn.close()

    # 3. Collect ALL MCCs (all 769 from merchant_category_codes.csv + any referenced in merchant_data.json / fees.json)
    all_mccs = set(mcc_desc.keys())
    for m in merchants:
        all_mccs.add(int(m["merchant_category_code"]))
    for r in fees:
        for code in (r["merchant_category_code"] or []):
            all_mccs.add(int(code))

    # 3b. Generate dabstep-mccs-data.bsl (all MCCs)
    mcc_lines = [
        "# ============================================================",
        "# DABstep Complete Merchant Category Codes (all MCCs from merchant_category_codes.csv + fees.json).",
        "# Auto-generated by build_dabstep_data.py.",
        "# ============================================================",
        "",
    ]
    for code in sorted(all_mccs):
        mcc_lines.append(f"MerchantCategoryCode: Individual: MCC-{code}")
        mcc_lines.append(": Model: Model MCC")
        mcc_lines.append(f": mccCode: {code}")
        desc = mcc_desc.get(code, f"MCC {code}")
        mcc_lines.append(f": summary: {desc}")
        mcc_lines.append("")
    MCCS_BSL_PATH.write_text("\n".join(mcc_lines), encoding="utf-8")

    # 4. Generate dabstep-ref-data.bsl (depends on MCCs being loaded first)
    ref_lines = [
        "# ============================================================",
        "# DABstep Reference Data, Domain Policies & Pre-aggregated Monthly Stats (BSL).",
        "# Auto-generated by build_dabstep_data.py from data/context/*.",
        "# ============================================================",
        "",
        "# --- Countries ---",
    ]
    for code in sorted(observed_countries):
        ref_lines.append(f"Country: Individual: Country-{code}")
        ref_lines.append(": Model: Model Country")
        ref_lines.append(f": isoCode: {code}")
        if code in COUNTRY_NAMES:
            ref_lines.append(f": summary: {COUNTRY_NAMES[code]}")
        ref_lines.append("")

    ref_lines.append("# --- Card Schemes ---")
    for scheme in sorted(observed_schemes):
        ref_lines.append(f"CardScheme: Individual: {scheme}")
        ref_lines.append(": Model: Model CardScheme")
        ref_lines.append(f": summary: Card network {scheme}")
        ref_lines.append("")

    ref_lines.append("# --- Account Types ---")
    for code, desc in ACCOUNT_TYPES.items():
        ref_lines.append(f"AccountType: Individual: AT-{code}")
        ref_lines.append(": Model: Model AccountType")
        ref_lines.append(f": codeLabel: {code}")
        ref_lines.append(f": summary: {desc}")
        ref_lines.append("")

    ref_lines.append("# --- Authorization Characteristics Indicators (ACI) ---")
    for code, desc in ACIS.items():
        ref_lines.append(f"ACI: Individual: ACI-{code}")
        ref_lines.append(": Model: Model ACI")
        ref_lines.append(f": codeLabel: {code}")
        ref_lines.append(f": summary: {desc}")
        ref_lines.append("")

    ref_lines.append("# --- Acquirers ---")
    for acq, country_code in acquirers:
        ref_lines.append(f"Acquirer: Individual: {acq}")
        ref_lines.append(": Model: Model Acquirer")
        ref_lines.append(f": country: Country-{country_code}")
        ref_lines.append("")

    ref_lines.append("# --- Domain Policies (manual.md) ---")
    for pol in DOMAIN_POLICIES:
        ref_lines.append(f"DomainPolicy: Individual: {pol['id']}")
        ref_lines.append(": Model: Model DomainPolicy")
        ref_lines.append(f": policyCategory: {pol['policyCategory']}")
        ref_lines.append(f": metricName: {pol['metricName']}")
        if "numericValue" in pol:
            ref_lines.append(f": numericValue: {pol['numericValue']}")
        if "minNumericValue" in pol:
            ref_lines.append(f": minNumericValue: {pol['minNumericValue']}")
        if "maxNumericValue" in pol:
            ref_lines.append(f": maxNumericValue: {pol['maxNumericValue']}")
        if "unitLabel" in pol:
            ref_lines.append(f": unitLabel: {pol['unitLabel']}")
        if "formulaText" in pol:
            ref_lines.append(f": formulaText: {pol['formulaText']}")
        if "manualSection" in pol:
            ref_lines.append(f": manualSection: {pol['manualSection']}")
        ref_lines.append(f": summary: {pol['summary']}")
        ref_lines.append("")

    ref_lines.append("# --- Merchants (captureDelayBucket and annual rollups derived via SetValue) ---")
    for m in merchants:
        ref_lines.append(f"Merchant: Individual: {m['merchant']}")
        ref_lines.append(": Model: Model Merchant")
        ref_lines.append(f": captureDelayRaw: {m['capture_delay']}")
        for acq in m["acquirer"]:
            ref_lines.append(f": acquirers: {acq}")
        ref_lines.append(f": mcc: MCC-{int(m['merchant_category_code'])}")
        ref_lines.append(f": accountType: AT-{m['account_type']}")
        ref_lines.append("")

    ref_lines.append("# --- Monthly Merchant Stats 2023 (fraudRate, volumeBucket, fraudBucket derived via SetValue) ---")
    for merchant, year, mo, cnt, vol, fcnt, fvol, rcnt, *_ in monthly_rows:
        label = f"Stats-{merchant}-{year}-{mo:02d}"
        ref_lines.append(f"MonthlyMerchantStats: Individual: {label}")
        ref_lines.append(": Model: Model MonthlyMerchantStats")
        ref_lines.append(f": merchant: {merchant}")
        ref_lines.append(f": txYear: {year}")
        ref_lines.append(f": txMonth: {mo}")
        ref_lines.append(f": txCount: {cnt}")
        ref_lines.append(f": totalVolume: {vol:.2f}")
        ref_lines.append(f": fraudTxCount: {fcnt}")
        ref_lines.append(f": fraudVolume: {fvol:.2f}")
        ref_lines.append(f": refusedTxCount: {rcnt}")
        ref_lines.append("")

    REF_BSL_PATH.write_text("\n".join(ref_lines), encoding="utf-8")

    # 5. Generate chunked dabstep-fees-{1..4}.bsl (250 rules per chunk for fast stand loading)
    chunk_files = []
    for idx in range(0, len(fees), FEES_CHUNK_SIZE):
        chunk = fees[idx : idx + FEES_CHUNK_SIZE]
        part = idx // FEES_CHUNK_SIZE + 1
        chunk_path = ROOT / f"dabstep-fees-{part}.bsl"
        fee_lines = [
            "# ============================================================",
            f"# DABstep Fee Rules Part {part} ({len(chunk)} rules from fees.json).",
            "# Auto-generated by build_dabstep_data.py.",
            "# Empty relations / omitted attributes represent wildcards (all values).",
            "# ============================================================",
            "",
        ]
        for r in chunk:
            rid = int(r["ID"])
            fee_lines.append(f"FeeRule: Individual: FeeRule-{rid}")
            fee_lines.append(": Model: Model FeeRule")
            fee_lines.append(f": ruleId: {rid}")
            fee_lines.append(f": cardScheme: {r['card_scheme']}")
            for at in (r["account_type"] or []):
                fee_lines.append(f": accountTypes: AT-{at}")
            if r["capture_delay"] is not None:
                fee_lines.append(f": captureDelayRule: {r['capture_delay']}")
            if r["monthly_fraud_level"] is not None:
                fee_lines.append(f": monthlyFraudLevelRule: {r['monthly_fraud_level']}")
            if r["monthly_volume"] is not None:
                fee_lines.append(f": monthlyVolumeRule: {r['monthly_volume']}")
            for code in (r["merchant_category_code"] or []):
                fee_lines.append(f": mccs: MCC-{int(code)}")
            if r["is_credit"] is not None:
                fee_lines.append(f": isCreditRule: {1 if r['is_credit'] else 0}")
            for a in (r["aci"] or []):
                fee_lines.append(f": acis: ACI-{a}")
            if r["intracountry"] is not None:
                fee_lines.append(f": intracountryRule: {1 if float(r['intracountry']) >= 0.5 else 0}")
            fee_lines.append(f": fixedAmount: {r['fixed_amount']}")
            fee_lines.append(f": feeRate: {int(r['rate'])}")
            fee_lines.append("")
        chunk_path.write_text("\n".join(fee_lines), encoding="utf-8")
        chunk_files.append(chunk_path.name)

    print(f"SQLite built: {SQLITE_PATH} ({SQLITE_PATH.stat().st_size / 1024 / 1024:.2f} MB, {total_rows} payments)")
    print(f"MCCs BSL built: {MCCS_BSL_PATH} ({len(mcc_lines)} lines, {len(all_mccs)} MCCs)")
    print(f"Ref BSL built: {REF_BSL_PATH} ({len(ref_lines)} lines, {len(DOMAIN_POLICIES)} policies, {len(merchants)} merchants, {len(monthly_rows)} monthly stats)")
    print(f"Fees BSL built: {', '.join(chunk_files)} ({len(fees)} fee rules total)")


if __name__ == "__main__":
    main()
