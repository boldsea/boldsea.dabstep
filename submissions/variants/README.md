# Submission variants

Each file differs from `base.jsonl` in one decision. Submit `base` first;
the score difference of any other file against it is the verdict on that decision.
The last column is the largest possible score change (tasks whose answer differs).

| File | Decision | Answers changed | By task family |
|---|---|---|---|
| `base.jsonl` | model as is: fraud level by volume, matched rules summed, rule-less payments cost 0 | 0 | — |
| `fraud-count.jsonl` | monthly fraud level = fraudulent tx count / tx count | 67 | applicable fee IDs 21, total fees 20, MCC-change delta 18, steer to card scheme 7, rate-change delta 1 |
| `agg-mean.jsonl` | total fee: average of the matched rules instead of their sum | 92 | total fees 45, steer to card scheme 29, MCC-change delta 18 |
| `agg-min.jsonl` | total fee: cheapest matched rule instead of the sum | 92 | total fees 45, steer to card scheme 29, MCC-change delta 18 |
| `agg-first.jsonl` | total fee: matched rule with the lowest ID instead of the sum | 92 | total fees 45, steer to card scheme 29, MCC-change delta 18 |
| `aci-min.jsonl` | move-fraud-to-ACI: cheapest matched rule instead of the sum | 7 | move fraud to ACI 7 |
| `uncovered-exclude.jsonl` | what-if scheme / ACI that leaves a payment without a rule is not a candidate | 44 | move fraud to ACI 25, steer to card scheme 19 |
