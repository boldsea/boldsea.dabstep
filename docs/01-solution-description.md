# Solution description: Passing DABstep on the basis of a preliminary BSL model of the subject domain

## 1. Solution concept

The key hypothesis of the experiment is to move the main analytical load from reactive LLM reasoning over raw files to the **preliminary construction of an executable subject domain model in BSL** (Boldsea Semantic Language), carried out strictly from the context data of the `adyen/DABstep` benchmark (`data/context/*`) before looking at the questions themselves.

Instead of interpreting the unstructured [manual.md](../data/context/manual.md), the rules of [fees.json](../data/context/fees.json) and the reference tables anew on each of the 450 questions, the subject domain is formalised **once** as a strict ontology with computed properties (`SetValue`), constraints (`ValueCondition`, `Required`) and an explicit applicability boundary (three-valued logic 3VL: absence of a concept or threshold in the ontology → `⊥` → `Not Applicable`).

---

## 2. Architecture (Hybrid / VKG-ready, Variant B)

DABstep data is sharply heterogeneous in volume:
- **The normative-reference and aggregate layer** (`acquirer_countries.csv`, `merchant_category_codes.csv`, `merchant_data.json`, `fees.json`, the rules of `manual.md`, monthly aggregates) — **1 917 individuals**. This layer lives and executes entirely in the live BOLDSEA graph.
- **The transactional layer** (`payments.csv`) — **138 236 rows** × 21 columns (~2.9 million events if loaded directly into the graph).

Therefore a **hybrid architecture with groundwork for a Virtual Knowledge Graph (VKG / OBDA)** was chosen:

```text
┌──────────────────────────────────────────────────────────────────────┐
│                   Live BOLDSEA graph (dabstep.bsl)                   │
│                                                                      │
│  Ontology and facts (1 917 individuals):                             │
│   • Country (10), CardScheme (4), AccountType (6), ACI (7)           │
│   • Acquirer (8), MerchantCategoryCode (776), DomainPolicy (16)      │
│   • Merchant (30)           [SetValue: captureDelayBucket,           │
│                              annualTxCount/Volume/FraudVolume/Rate]  │
│   • MonthlyMerchantStats(60)[SetValue: fraudRate, volumeBucket,      │
│                              fraudBucket]                            │
│   • FeeRule (1 000)         [full fee rules of fees.json]            │
│                                                                      │
│  Virtual transaction model:                                          │
│   • Model Payment (21 attributes/relations + SetValue: txMonth,      │
│     isIntracountry, calculatedFee)                                   │
│   • ExternalDataset: PaymentsDataset → external source registry      │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ 1:1 mapping of the Model Payment schema
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│        Model-driven external provider (payments_provider.py)         │
│   • Indexed SQLite DB (data/payments.sqlite, 138 236 rows)           │
│   • Canonical engine for FeeRule matching and what-if overrides      │
│   • Export of any transaction slice to valid BSL (`bsl-slice`)       │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│           Solver and verification (solve_dabstep.py + MCP)           │
│   • Pure ontology/fee tasks → BSL `evaluate` / FeeRule               │
│   • Transactional and what-if tasks → SQL + FeeRule engine           │
│   • Output: submissions/bsl_model_submission.jsonl (450 tasks)       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. Structure of the BSL subject domain model

The reference schema is defined in [dabstep.bsl](../dabstep.bsl) (application `DABstepApp`, vocabulary `DABstepVocabulary`).

### 3.1. Concepts and naming policy
Since individual labels in BOLDSEA are global across concepts, prefixes are used to rule out collisions (in particular, the codes `D` and `F` occur in both `AccountType` and `ACI`):
- `Country` (`Country-NL`, `Country-US`, …) — ISO Alpha-2 country codes;
- `CardScheme` (`GlobalCard`, `NexPay`, `TransactPlus`, `SwiftCharge`) — card schemes;
- `AccountType` (`AT-R`, `AT-D`, `AT-H`, `AT-F`, `AT-S`, `AT-O`) — merchant account types from §2 of `manual.md`;
- `ACI` (`ACI-A` … `ACI-G`) — Authorization Characteristics Indicators from §4 of `manual.md`;
- `Acquirer` (`gringotts`, `medici`, `lehman_brothers`, …) — acquiring banks with the relation `country → Country`;
- `MerchantCategoryCode` (`MCC-5812`, …) — the full classifier of 776 MCCs;
- `DomainPolicy` (`Policy-PinAttemptLimit`, `Policy-PciDssFine`, `Policy-FeeFormula`, `Policy-FraudDefinition`, …) — 16 formalised rules, limits, fines, glossary definitions and contacts from `manual.md`;
- `Merchant` (`Crossfit_Hanna`, `Belles_cookbook_store`, …) — 30 merchant profiles from `merchant_data.json`;
- `MonthlyMerchantStats` (`Stats-<merchant>-2023-<MM>`) — 60 monthly slices for 2023 (5 active merchants × 12 calendar months);
- `FeeRule` (`FeeRule-1` … `FeeRule-1000`) — all 1 000 fee rules from `fees.json`;
- `Payment` (`Model Payment`) — the canonical transaction model (virtualised);
- `ExternalDataset` (`PaymentsDataset`) — metadata of the external storage for `Model Payment`.

### 3.2. Executable business rules (`SetValue` in BSL)
The key domain rules are computed by the BOLDSEA engine itself when the facts are loaded:
1. **Normalisation of the capture delay (`Model Merchant.captureDelayBucket`):**
   - `"manual"` → `"manual"`, `"immediate"` → `"immediate"`, `"1"` / `"2"` → `"<3"`, `"3"`..`"5"` → `"3-5"`, `>5` → `">5"`.
2. **Determination of the fraud level and buckets (`Model MonthlyMerchantStats`):**
   - `fraudRate = fraudVolume / totalVolume` (strictly by volume in EUR, not by the number of transactions, according to §5 and §7 of `manual.md`);
   - `volumeBucket`: `<100k`, `100k-1m`, `1m-5m`, `>5m`;
   - `fraudBucket`: `<7.2%`, `7.2%-7.7%`, `7.7%-8.3%`, `>8.3%`.
3. **Applicability boundary (`Model Merchant.exceedsFraudThreshold`):**
   - the threshold is a `DomainPolicy` fact: `Policy-ExcessiveFraudThreshold` and `Policy-ExcessiveRetryFee` exist as notions from `manual.md`, but without `numericValue`, because the manual gives no number;
   - `exceedsFraudThreshold = annualFraudRate > threshold`; while there is no threshold, the value does not exist — this is exactly `Not Applicable` (neither "yes" nor "no");
   - verified on the graph: without a threshold, tasks 62, 70, 71 give `Not Applicable`; with a temporary threshold of 0.092 — "no" / "yes" (3 merchants above, 27 below); after the threshold is removed, the inference is retracted.
4. **Annual merchant summaries (`Model Merchant`):**
   - `annualTxCount`, `annualVolume`, `annualFraudVolume`, `annualFraudRate` are aggregated via `Sum(Map($($Base == "MonthlyMerchantStats", merchant == $CurrentIndividual), ...))`.
5. **Transaction semantics (`Model Payment`):**
   - `txMonth` is derived from `dayOfYear` by the calendar months of the non-leap year 2023;
   - `isIntracountry = (issuingCountry == acquirerCountry)`;
   - `monthStats` — the merchant's monthly aggregate that the transaction falls into (the source of the fraud and volume buckets);
   - `matchedFeeRules` — all `FeeRule` that match the transaction: matching on 9 fields is expressed by a `$(...)` query in the model, an empty list or a missing rule attribute is a wildcard;
   - `calculatedFee = Σ fixedAmount + Σ feeRate * eurAmount / 10000` over `matchedFeeRules`; no matching rules — no value (unknown, not zero).
   - Reconciliation: the slice `payments-slice.bsl` (200 transactions, one per feature tuple) was loaded into the graph, `matchedFeeRules` and `calculatedFee` matched `payments_provider.py` on 200 out of 200 (the reconciliation reference file is `payments-slice.expected.json`).

### 3.3. `FeeRule` matching rules
`FeeRule` and [payments_provider.py](../payments_provider.py) implement the exact matching rules from `manual.md` §5 and `fees.json`:
- empty lists (`accountTypes`, `mccs`, `acis`) and missing attributes (`captureDelayRule`, `monthlyFraudLevelRule`, `monthlyVolumeRule`, `isCreditRule`, `intracountryRule`) are treated as a wildcard ("matches any value");
- when several `FeeRule` match one transaction, the fees are applied **additively (`SUM`)** (confirmed on `dev.jsonl` Task 1871);
- when searching for the optimal ACI to move fraudulent transactions to (what-if), `min` among the matching rules is used, without discarding ACIs with uncovered schemes.

---

## 4. Components and files of the solution

| File | Purpose |
|---|---|
| [dabstep.bsl](../dabstep.bsl) | Reference BSL model of the subject domain (`DABstepApp`, vocabulary, 12 concepts, `SetValue`, basic Layout) |
| [build_dabstep_data.py](../build_dabstep_data.py) | Generator of the SQLite index and BSL data packages strictly from `data/context/*` |
| [dabstep-mccs-data.bsl](../dabstep-mccs-data.bsl) | Load package for all 776 MCCs |
| [dabstep-ref-data.bsl](../dabstep-ref-data.bsl) | Load package for the reference tables, 16 `DomainPolicy`, 30 `Merchant` and 60 `MonthlyMerchantStats` |
| `dabstep-fees-1.bsl` … `dabstep-fees-4.bsl` | 1 000 `FeeRule`, split into 4 chunks of 250 rules for stable loading into the browser runtime |
| [payments_provider.py](../payments_provider.py) | Model-driven provider over `data/payments.sqlite`: SQL queries, `FeeRule` matching engine, what-if calculations and `bsl-slice` export |
| [solve_dabstep.py](../solve_dabstep.py) | Regression test on `dev.jsonl` and a run of the 450 tasks of `all.jsonl` |
| [bsl_model_submission.jsonl](../submissions/bsl_model_submission.jsonl) | Final submission in the DABstep leaderboard format (450 lines) |
| [mcp_config.json](../../../.agents/plugins/boldsea-stand/mcp_config.json) | Configuration of the Antigravity project plugin for connecting the `boldsea-bsl` MCP server |

---

## 5. Groundwork for further development (Stage 2)

1. **Autonomous LLM agent on top of the BSL model (for the Validated Leaderboard):** replace the template parsing in `solve_dabstep.py` with a thin agent with two tools — `evaluate` over the live BOLDSEA graph and `payments_provider.py` — in order to obtain a verifiable result on arbitrary questions without hardcoding.
2. **Native VKG connector in the BOLDSEA engine:** the `row_to_bsl` method and the `MODEL_PAYMENT_FIELDS` mapping in `payments_provider.py` are already compatible with `Model Payment` (confirmed by `commit` `dryRun` on the stand) and can serve as a backend for a virtual event provider with predicate pushdown.

---

## 6. Autonomous agent on top of the graph (pilot, 2026-11-22)

- **Payment groups in the graph.** `Model PaymentGroup` — 4 363 groups of payments with identical fee-relevant features (merchant, scheme, month, credit, ACI, intracountry) with count and amount; files `dabstep-groups-1..9.bsl`, generator [build_payment_groups.py](../build_payment_groups.py). `FeeRule` matching is defined once in the group, `Model Payment` takes it via `feeGroup`. Reconciliation with the provider: 4 363 groups, 6 870 matches, the fee totals and the 56 464 payments without rules matched.
- **Agent.** The brief is [agent/AGENT.md](../agent/AGENT.md): two tools (`evaluate` over the graph and `payments_provider.py payments-sql` over the payments table only), with no access to the solver, the tasks or the answers.
- **Pilot on `dev.jsonl`:** 9 out of 10, the protocol is [agent/dev-run-1.json](../agent/dev-run-1.json). Six tasks were solved with the graph only, two with SQL only, two with SQL and the graph. Task 2697 (what-if on ACI) did not match: agent `C:131.20`, reference answer `E:13.57`.
