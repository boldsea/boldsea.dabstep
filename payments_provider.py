#!/usr/bin/env python3
"""
Model-driven external data provider for DABstep `Model Payment` (payments.csv -> payments.sqlite).

Aligned 1:1 with `applications/dabstep/dabstep.bsl`:
  - Maps SQLite rows to `Model Payment` BSL individuals (VKG-ready).
  - Implements canonical `FeeRule` matching and fee computation per `manual.md`.
  - Supports what-if overrides (MCC, capture_delay, account_type, ACI, fee rule rate/fixed).
"""

import argparse
import json
import sqlite3
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

SQLITE_PATH = Path(__file__).resolve().parent / "data" / "payments.sqlite"

# Canonical mapping: SQLite column -> Model Payment BSL property
MODEL_PAYMENT_FIELDS = {
    "psp_reference": ("pspReference", "attr"),
    "merchant": ("merchant", "rel"),
    "card_scheme": ("cardScheme", "rel"),
    "year": ("txYear", "attr"),
    "day_of_year": ("dayOfYear", "attr"),
    "hour_of_day": ("hourOfDay", "attr"),
    "minute_of_hour": ("minuteOfHour", "attr"),
    "is_credit": ("isCredit", "bool"),
    "eur_amount": ("eurAmount", "attr"),
    "ip_country": ("ipCountry", "country_rel"),
    "issuing_country": ("issuingCountry", "country_rel"),
    "acquirer_country": ("acquirerCountry", "country_rel"),
    "device_type": ("deviceType", "attr"),
    "ip_address": ("ipAddressHash", "attr"),
    "email_address": ("emailAddressHash", "attr"),
    "card_number": ("cardNumberHash", "attr"),
    "shopper_interaction": ("shopperInteraction", "attr"),
    "card_bin": ("cardBin", "attr"),
    "has_fraudulent_dispute": ("hasFraudulentDispute", "bool"),
    "is_refused_by_adyen": ("isRefusedByAdyen", "bool"),
    "aci": ("aci", "aci_rel"),
}


def capture_delay_bucket(raw: str) -> str:
    if raw in ("manual", "immediate", "<3", "3-5", ">5"):
        return raw
    d = int(raw)
    if d < 3:
        return "<3"
    if d <= 5:
        return "3-5"
    return ">5"


@dataclass(frozen=True)
class FeeRule:
    rule_id: int
    card_scheme: str
    account_types: frozenset
    capture_delay: Optional[str]
    monthly_fraud_level: Optional[str]
    monthly_volume: Optional[str]
    mccs: frozenset
    is_credit: Optional[int]
    acis: frozenset
    intracountry: Optional[int]
    fixed_amount: float
    rate: int

    def matches(
        self,
        *,
        card_scheme: str,
        account_type: str,
        capture_delay_bkt: str,
        fraud_bkt: str,
        volume_bkt: str,
        mcc: int,
        is_credit: int,
        aci: str,
        is_intracountry: int,
    ) -> bool:
        if self.card_scheme != card_scheme:
            return False
        if self.account_types and account_type not in self.account_types:
            return False
        if self.capture_delay is not None and self.capture_delay != capture_delay_bkt:
            return False
        if self.monthly_fraud_level is not None and self.monthly_fraud_level != fraud_bkt:
            return False
        if self.monthly_volume is not None and self.monthly_volume != volume_bkt:
            return False
        if self.mccs and mcc not in self.mccs:
            return False
        if self.is_credit is not None and self.is_credit != is_credit:
            return False
        if self.acis and aci not in self.acis:
            return False
        if self.intracountry is not None and self.intracountry != is_intracountry:
            return False
        return True

    def fee_for(self, eur_amount: float) -> float:
        return self.fixed_amount + self.rate * eur_amount / 10000.0


class PaymentsProvider:
    def __init__(self, db_path: Path = SQLITE_PATH) -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        self.conn.row_factory = sqlite3.Row
        self.merchants: Dict[str, Dict[str, Any]] = {}
        self.monthly_stats: Dict[Tuple[str, int, int], Dict[str, Any]] = {}
        self.rules_by_scheme: Dict[str, List[FeeRule]] = {}
        self._load_metadata()

    def _load_metadata(self) -> None:
        for r in self.conn.execute("SELECT * FROM merchants"):
            self.merchants[r["merchant"]] = {
                "capture_delay": r["capture_delay"],
                "capture_delay_bucket": r["capture_delay_bucket"],
                "mcc": int(r["mcc"]),
                "account_type": r["account_type"],
                "acquirers": json.loads(r["acquirers_json"]),
            }
        for r in self.conn.execute("SELECT * FROM monthly_stats"):
            self.monthly_stats[(r["merchant"], int(r["tx_year"]), int(r["tx_month"]))] = {
                "tx_count": int(r["tx_count"]),
                "total_volume": float(r["total_volume"]),
                "fraud_tx_count": int(r["fraud_tx_count"]),
                "fraud_volume": float(r["fraud_volume"]),
                "refused_tx_count": int(r["refused_tx_count"]),
                "fraud_rate": float(r["fraud_rate"]),
                "volume_bucket": r["volume_bucket"],
                "fraud_bucket": r["fraud_bucket"],
            }
        for r in self.conn.execute("SELECT * FROM fee_rules ORDER BY rule_id"):
            rule = FeeRule(
                rule_id=int(r["rule_id"]),
                card_scheme=r["card_scheme"],
                account_types=frozenset(json.loads(r["account_types_json"])),
                capture_delay=r["capture_delay"],
                monthly_fraud_level=r["monthly_fraud_level"],
                monthly_volume=r["monthly_volume"],
                mccs=frozenset(int(x) for x in json.loads(r["mccs_json"])),
                is_credit=None if r["is_credit"] is None else int(r["is_credit"]),
                acis=frozenset(json.loads(r["acis_json"])),
                intracountry=None if r["intracountry"] is None else int(r["intracountry"]),
                fixed_amount=float(r["fixed_amount"]),
                rate=int(r["rate"]),
            )
            self.rules_by_scheme.setdefault(rule.card_scheme, []).append(rule)

    def match_rules_for_tx(
        self,
        tx: sqlite3.Row,
        *,
        override_mcc: Optional[int] = None,
        override_capture_delay: Optional[str] = None,
        override_account_type: Optional[str] = None,
        override_aci: Optional[str] = None,
        override_intracountry: Optional[int] = None,
    ) -> List[FeeRule]:
        m = self.merchants[tx["merchant"]]
        st = self.monthly_stats[(tx["merchant"], int(tx["year"]), int(tx["tx_month"]))]
        scheme = tx["card_scheme"]
        mcc = m["mcc"] if override_mcc is None else override_mcc
        cd_bkt = (
            m["capture_delay_bucket"]
            if override_capture_delay is None
            else capture_delay_bucket(override_capture_delay)
        )
        at = m["account_type"] if override_account_type is None else override_account_type
        aci = tx["aci"] if override_aci is None else override_aci
        intra = int(tx["is_intracountry"]) if override_intracountry is None else override_intracountry
        is_credit = int(tx["is_credit"])

        return [
            rule
            for rule in self.rules_by_scheme.get(scheme, ())
            if rule.matches(
                card_scheme=scheme,
                account_type=at,
                capture_delay_bkt=cd_bkt,
                fraud_bkt=st["fraud_bucket"],
                volume_bkt=st["volume_bucket"],
                mcc=mcc,
                is_credit=is_credit,
                aci=aci,
                is_intracountry=intra,
            )
        ]

    def row_to_bsl(self, tx: sqlite3.Row, applied_rule: Optional[FeeRule] = None) -> str:
        lines = [
            f"Payment: Individual: Payment-{tx['psp_reference']}",
            ": Model: Model Payment",
        ]
        for col, (prop, kind) in MODEL_PAYMENT_FIELDS.items():
            val = tx[col]
            if val is None or val == "":
                continue
            if kind == "country_rel":
                lines.append(f": {prop}: Country-{val}")
            elif kind == "aci_rel":
                lines.append(f": {prop}: ACI-{val}")
            elif kind == "bool":
                lines.append(f": {prop}: {1 if int(val) else 0}")
            else:
                lines.append(f": {prop}: {val}")
        # matchedFeeRules / calculatedFee are derived by Model Payment (SetValue) and are never written here
        return "\n".join(lines)

    def query_payments(self, where_sql: str = "1=1", params: Tuple[Any, ...] = (), limit: Optional[int] = None) -> List[sqlite3.Row]:
        sql = f"SELECT * FROM payments WHERE {where_sql}"
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        return list(self.conn.execute(sql, params))

    def self_test(self) -> Dict[str, Any]:
        # Cache matching by unique fee-relevant feature tuple for speed
        cache: Dict[Tuple[Any, ...], List[int]] = {}
        match_hist = Counter()
        total_tx = 0
        total_fee = 0.0
        for tx in self.conn.execute(
            "SELECT merchant, card_scheme, year, tx_month, is_credit, aci, is_intracountry, eur_amount FROM payments"
        ):
            total_tx += 1
            key = (
                tx["merchant"],
                tx["card_scheme"],
                tx["year"],
                tx["tx_month"],
                tx["is_credit"],
                tx["aci"],
                tx["is_intracountry"],
            )
            rule_ids = cache.get(key)
            if rule_ids is None:
                matched = self.match_rules_for_tx(tx)
                rule_ids = [r.rule_id for r in matched]
                cache[key] = rule_ids
            match_hist[len(rule_ids)] += 1
            if rule_ids:
                # Look up first matched rule for sample fee sum
                first_id = rule_ids[0]
                for r in self.rules_by_scheme[tx["card_scheme"]]:
                    if r.rule_id == first_id:
                        total_fee += r.fee_for(float(tx["eur_amount"]))
                        break
        return {
            "total_transactions": total_tx,
            "unique_feature_tuples": len(cache),
            "matched_rule_count_histogram": dict(sorted(match_hist.items())),
            "sample_first_rule_total_fee_eur": round(total_fee, 2),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="DABstep Model Payment external provider")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("self-test", help="Verify fee rule matching across all 138,236 payments")

    p_bsl = sub.add_parser("bsl-slice", help="Emit filtered payments as Model Payment BSL")
    p_bsl.add_argument("--where", default="1=1", help="SQL WHERE clause on payments table")
    p_bsl.add_argument("--limit", type=int, default=5)
    p_bsl.add_argument("--with-fee", action="store_true")

    p_sql = sub.add_parser("sql", help="Run read-only SQL query against payments.sqlite")
    p_sql.add_argument("query")

    p_psql = sub.add_parser(
        "payments-sql",
        help="Read-only SQL restricted to the payments table (the agent tool: transactions only, "
        "merchants / fee rules / monthly stats are read from the BOLDSEA graph)",
    )
    p_psql.add_argument("query")

    args = parser.parse_args()
    prov = PaymentsProvider()

    if args.cmd == "self-test":
        print(json.dumps(prov.self_test(), indent=2))
    elif args.cmd == "bsl-slice":
        rows = prov.query_payments(args.where, limit=args.limit)
        blocks = []
        for tx in rows:
            rule = None
            if args.with_fee:
                matched = prov.match_rules_for_tx(tx)
                rule = matched[0] if matched else None
            blocks.append(prov.row_to_bsl(tx, applied_rule=rule))
        print("\n\n".join(blocks))
    elif args.cmd == "payments-sql":
        def only_payments(action, arg1, arg2, db_name, trigger):
            if action == sqlite3.SQLITE_READ and arg1 != "payments":
                return sqlite3.SQLITE_DENY
            if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION):
                return sqlite3.SQLITE_OK
            return sqlite3.SQLITE_DENY

        prov.conn.set_authorizer(only_payments)
        try:
            cur = prov.conn.execute(args.query)
        except sqlite3.DatabaseError as e:
            raise SystemExit(f"payments-sql: refused or failed ({e}); only SELECT over the payments table is allowed")
        cols = [d[0] for d in cur.description] if cur.description else []
        print(json.dumps([dict(zip(cols, r)) for r in cur.fetchall()], indent=1))
    elif args.cmd == "sql":
        cur = prov.conn.execute(args.query)
        cols = [d[0] for d in cur.description] if cur.description else []
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
