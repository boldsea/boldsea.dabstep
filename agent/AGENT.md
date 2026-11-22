# DABstep agent brief

You answer one question about a payment-processing domain. The domain is
already modelled as a live BOLDSEA graph; the transactions themselves sit in a
SQL table. You have exactly two tools and nothing else.

## Rules

- **Tool 1 — graph.** `evaluate` of the `boldsea-bsl` MCP server (load it with
  ToolSearch, query `select:mcp__boldsea-bsl__evaluate`). It computes a BSL
  expression over the graph. Read-only.
- **Tool 2 — transactions.** From `applications/dabstep/`:
  `python3 payments_provider.py payments-sql "<SELECT …>"` — read-only SQL over
  the single table `payments`. Other tables are refused.
- Do not use `commit`, `load`, `query`, `export` or any other graph channel.
- Do not open any file except this brief and `applications/dabstep/dabstep.bsl`
  (the model). In particular not `solve_dabstep.py`, `docs/`, `submissions/`,
  `data/`, the `*.py` sources or the `*-data.bsl` / `fees` / `groups` files.
  Do not search the web. Arithmetic on tool results may be done with a plain
  `python3 -c`.
- Merchants, fee rules, MCCs, monthly statistics, policies and fees come from
  the graph. SQL is for facts about individual transactions only.
- If the graph has no fact that the question needs (a threshold, a fee, a
  definition without a value), the answer is `Not Applicable`. Do not fill
  the gap from general knowledge.

## The evaluate call

```
Agent: Individual: EvaluateAgent1
: Model: Model EvaluateAgent
: query: <expression>
: agentCall: 1
```

The answer repeats the block with `:: result: …` or `:: error: …`. Check that
the echoed `query` is yours — other agents share the same channel; if it is
not, resend. A list `[a, b, c]` evaluates several expressions in one call.
A timeout is safe to resend.

## The graph

Labels are global, hence the prefixes. Relations hold individuals: compare
with `Ind("Label")`, never with a string.

| Model | Labels | Properties |
|---|---|---|
| `Model Country` | `Country-NL` | `isoCode`, `summary` |
| `Model CardScheme` | `GlobalCard`, `NexPay`, `TransactPlus`, `SwiftCharge` | `summary` |
| `Model AccountType` | `AT-R`, `AT-D`, `AT-H`, `AT-F`, `AT-S`, `AT-O` | `codeLabel`, `summary` |
| `Model ACI` | `ACI-A` … `ACI-G` | `codeLabel`, `summary` |
| `Model Acquirer` | `gringotts`, … | `country` |
| `Model MCC` | `MCC-5812` | `mccCode`, `summary` (description text) |
| `Model DomainPolicy` | `Policy-…` | `policyCategory`, `metricName`, `numericValue`, `minNumericValue`, `maxNumericValue`, `unitLabel`, `formulaText`, `manualSection`, `summary` |
| `Model Merchant` | `Rafa_AI`, … (30) | `captureDelayRaw`, `captureDelayBucket`, `acquirers`*, `mcc`, `accountType`, `annualTxCount`, `annualVolume`, `annualFraudVolume`, `annualFraudRate`, `exceedsFraudThreshold` |
| `Model MonthlyMerchantStats` | `Stats-<merchant>-2023-<MM>` | `merchant`, `txYear`, `txMonth`, `txCount`, `totalVolume`, `fraudTxCount`, `fraudVolume`, `refusedTxCount`, `fraudRate`, `volumeBucket`, `fraudBucket` |
| `Model FeeRule` | `FeeRule-1` … `FeeRule-1000` | `ruleId`, `cardScheme`, `accountTypes`*, `captureDelayRule`, `monthlyFraudLevelRule`, `monthlyVolumeRule`, `mccs`*, `isCreditRule`, `acis`*, `intracountryRule`, `fixedAmount`, `feeRate` |
| `Model PaymentGroup` | `PG-<merchant>-<scheme>-2023-<MM>-<credit\|debit>-<A…G>-<intra\|cross>` | `merchant`, `cardScheme`, `txYear`, `txMonth`, `isCredit`, `aci`, `isIntracountry`, `txCount`, `totalVolume`, `monthStats`, `matchedFeeRules`*, `calculatedFee` |

\* multiple-valued.

What the model states (read `dabstep.bsl` for the exact expressions):

- **Fee of one rule** for an amount: `fixedAmount + feeRate * amount / 10000`.
- **A rule applies** when every one of its nine fields fits; an empty list
  (`accountTypes`, `mccs`, `acis`) or an absent attribute (`captureDelayRule`,
  `monthlyFraudLevelRule`, `monthlyVolumeRule`, `isCreditRule`,
  `intracountryRule`) fits anything. The fields are compared with: the card
  scheme, credit flag, ACI and intracountry flag of the payment; the account
  type, MCC and `captureDelayBucket` of its merchant; the `fraudBucket` and
  `volumeBucket` of the merchant's month.
- **PaymentGroup** is all payments of 2023 that share merchant, card scheme,
  month, credit flag, ACI and intracountry flag — the 4,363 groups cover the
  whole `payments` table. `matchedFeeRules` is the set of rules that apply to
  the group; `calculatedFee` is the group's fee, the sum over all matched
  rules. A group with no matched rule has no `calculatedFee` (unknown, not 0).
- **Fraud rate** is fraudulent volume over total volume in EUR, not a count
  ratio. **Intracountry** means issuing country equals acquirer country.
- Months are calendar months of 2023 (not a leap year); `tx_month` in SQL and
  `txMonth` in the graph agree.

## The payments table

`payments(psp_reference, merchant, card_scheme, year, day_of_year, tx_month,
hour_of_day, minute_of_hour, is_credit, eur_amount, ip_country,
issuing_country, acquirer_country, is_intracountry, device_type, ip_address,
email_address, card_number, shopper_interaction, card_bin,
has_fraudulent_dispute, is_refused_by_adyen, aci)` — 138,236 rows, year 2023.
Text values are plain codes (`'NexPay'`, `'NL'`, `'F'`); flags are 0/1;
`ip_address` and `email_address` may be NULL.

## Expression idioms (verified on this graph)

```
Count($($Model == "Model FeeRule"))
$($Model == "Model PaymentGroup", merchant == Ind("Rafa_AI"), txMonth == 3)
Sum($($Model == "Model PaymentGroup", merchant == Ind("Rafa_AI"), txMonth == 3).calculatedFee)
Distinct($($Model == "Model PaymentGroup", merchant == Ind("Rafa_AI"), txMonth == 3).matchedFeeRules)
Avg(Map($($Model == "Model FeeRule", cardScheme == Ind("NexPay")), $It.fixedAmount + $It.feeRate * 100 / 10000))
$($Model == "Model FeeRule", Count($$It.accountTypes) == 0 || accountTypes == Ind("AT-R"))     # list field with wildcard
$($Model == "Model FeeRule", IsUndefined($$It.isCreditRule) == true || isCreditRule == true)   # scalar field with wildcard
First(@("Rafa_AI").captureDelayBucket)                       # a property of a named individual
First($($Model == "Model MCC", summary == "Fast Food Restaurants")).$Value   # label of an individual
Coalesce(First(@("Policy-PinAttemptLimit").numericValue), "Not Applicable")
```

- Filters inside `$(…)` are joined by commas (AND); `||` is OR. Every filter
  needs an explicit comparison: `IsDefined($$It.x) == true`, not `IsDefined($$It.x)`.
- Inside a filter a bare property name is the candidate's property; `$$It.x`
  is the same, tolerant of absence. `$It` is the element in `Map`, `Filter`,
  `Any`, `All`, `OrderBy`, `MinBy`, `MaxBy`.
- `==` between a multiple-valued property and one value is membership.
- `@("Label").prop` yields a collection: take `First(…)`, test presence with
  `Count(…) > 0` or `IsDefined(First(…))`.
- `Sum` of nothing is undefined; wrap in `Coalesce(…, 0)` when 0 is meant.
- Collections: `Count Sum Avg MinOf MaxOf Median First Last Distinct Union
  Difference Intersection Filter Map Any All OrderBy MinBy MaxBy GroupBy
  Contains`. Projection: `collection.property`. Large answers come back as a
  comma-separated list of labels or values.
- A what-if (another MCC, scheme, ACI, account type, a changed rule) is the
  same rule filter with the hypothetical value written as a literal.
- Comparing what-if options (card schemes, ACIs): a payment that no rule fits
  under an option adds 0 to that option's total, the option stays a candidate.
  "A different ACI / scheme" excludes the value the payments already have.
- "Only applied to account type X" narrows a rule: affected are the merchants
  the rule applied to that are not of type X.
- "Most expensive ACI" for a given transaction: fees of all fitting rules add
  up. "Most expensive MCC … in general": average fee over fitting rules, among
  MCCs that some rule names.
- Move-fraud-to-ACI questions are answered with the ACI letter alone.

## Answer

Follow the question's own formatting guidelines exactly. Finish with:

```
ANSWER: <the answer, exactly as it should be submitted>
TRACE: <two or three lines: which expressions / SQL produced it, and any assumption you made>
```
