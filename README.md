# boldsea.dabstep

A BOLDSEA (BSL) domain model for the [DABstep](https://huggingface.co/spaces/adyen/DABstep)
benchmark — *Data Agent Benchmark for Multi-step Reasoning* by Adyen and Hugging Face —
together with the data loaders, a solver and the submissions it produces.

The experiment asks one question: how far does a benchmark about payment fees
get when the domain is modelled once, before any task is read — merchants, fee
rules, monthly statistics and the fee calculation itself as a semantic model —
and the tasks are then answered from that model.

## What is here

| Path | What it is |
|---|---|
| `dabstep.bsl` | The model: concepts, properties and the derived values (fee-rule matching, fees, buckets, fraud rates) |
| `dabstep-mccs-data.bsl`, `dabstep-ref-data.bsl`, `dabstep-fees-*.bsl` | Reference data as BSL: 776 MCCs, merchants, monthly statistics, policies from the manual, 1,000 fee rules |
| `dabstep-groups-*.bsl` | 4,363 payment groups covering all 138,236 payments (merchant, scheme, month, credit flag, ACI, intracountry flag) |
| `payments-slice.bsl`, `payments-slice.expected.json` | 200 payments used to verify the model's matching against an independent calculation |
| `build_dabstep_data.py`, `build_payment_groups.py` | Generators of the files above and of `data/payments.sqlite` |
| `payments_provider.py` | Read-only access to the payments table (the transactions stay outside the graph) |
| `solve_dabstep.py` | Solver for all 450 tasks; writes `submissions/bsl_model_submission.jsonl` |
| `build_submission_variants.py`, `submissions/variants/` | One submission per disputed modelling decision (see below) |
| `agent/` | Brief and pilot protocol of an agent that answers from the live graph with two tools only |
| `docs/` | Solution description and the report on preparation and runs |

## Results

Stated as they are:

- **Official dev set:** 9 of 10. The failing task (2697) has a reference answer
  `E:13.57`; the solver answers `E`. The number could not be reproduced under
  any semantics we tried (see `docs/02-preparation-and-runs-report.md`, §7).
- **Hidden set (450 tasks):** no leaderboard score yet. Against the answers the
  leaderboard accepted in a random sample of 200 public submissions
  (`data/task_scores` of the dataset), the current submission agrees on
  **439 of 450**. The comparison is approximate (numeric tolerance, lists as
  sets); it was used to check the semantics of task families, not to copy
  answers (§8 of the report).
- **Agent on the live graph:** 9 of 10 on dev in a pilot run; not run on the
  450 tasks.

Three modelling decisions were disputed and are confirmed by that comparison:
the monthly fraud level is a ratio of volumes, not of counts; when several fee
rules fit a payment, their fees add up; a what-if option that leaves a payment
without a fitting rule stays a candidate and that payment costs nothing.
`submissions/variants/README.md` lists what each alternative changes.

## Limitations

- **The graph needs the BOLDSEA engine**, which is not publicly available. The
  `.bsl` files are readable as a specification of the model, but loading and
  querying them requires the engine. Everything in Python runs without it.
- **The solver does not query the graph.** It recognises task templates and
  computes over SQLite with the same semantics as the model; the two were
  cross-checked (200 payments and control totals), but they are two
  implementations. The agent in `agent/` is the graph-only path.
- Eleven tasks of the 450 still disagree with accepted answers; they are listed
  in §8.1 of the report.

## Reproduce

Python 3.9+, standard library only.

```bash
python3 fetch_data.py            # context files and tasks from adyen/DABstep (~23 MB)
python3 build_dabstep_data.py    # data/payments.sqlite and the reference-data .bsl files
python3 build_payment_groups.py  # dabstep-groups-*.bsl
python3 solve_dabstep.py         # dev check + submissions/bsl_model_submission.jsonl
python3 build_submission_variants.py
```

## Data and licence of the benchmark

The benchmark data is not copied here; `fetch_data.py` downloads it. The `.bsl`
data files and the payment slice are derived from it.

DABstep: Data Agent Benchmark for Multi-step Reasoning © 2025 by Alexander David
Egg, Martin Iglesias Goyanes, Andreu Mora, Friso H. Kingma, Thomas Wolf, Leandro
Von Werra, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Source: <https://huggingface.co/datasets/adyen/DABstep>.
