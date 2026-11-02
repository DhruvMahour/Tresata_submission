# TDS classification assistant: prototype (India, Income-tax Act 2025, resident payees)

Companion to the written brief. Shows the architecture's *deterministic spine* working end to end on 14 synthetic invoices.

## Run
```
python3 pipeline.py keyword          # keyword baseline classifier, no network, no dependencies (Python 3.9+)
NO_AMB=1 python3 pipeline.py keyword # ablation: ambiguity list switched off
OPENROUTER_API_KEY=... OR_MODEL=<free model id> python3 pipeline.py llm   # LLM classifier (NOT RUN, see below)
```

## What is real and what is not (read this)
- **All 14 invoices in `cases.json` are made up.** Expected outcomes were labelled by the author, not by a CA.
- **`rules.py` is an illustrative, simplified subset** of the section 393 table. Rates/thresholds were taken from secondary sources that disagree with each other in places; they must be verified against the Act and signed off by a CA. Simplifications: threshold base after first crossing, no surcharge, no lower-deduction certificates, single payee type split (individual vs other).
- **The LLM classifier (`classify_llm`) is implemented but was not run** for the reported results: the build environment had no OpenRouter access. Reported numbers are for the **keyword baseline**, which is the thing the brief says must be beaten before claiming AI adds value. Intended model: a free OpenRouter model (name it in your run notes; free model ids change).
- Two-run agreement from the design is not exercised, since the baseline is deterministic.

## What the pipeline does
1. Date rule: earlier of credit/payment before 1 Apr 2026 -> 1961 Act -> out of scope, human.
2. Classifier picks one table item or ESCALATE, with an evidence quote.
3. Grounding check: evidence must be a verbatim substring of the invoice, else escalate.
4. Ambiguity list (software, licence, advertising, spares, AMC, staff supply, ...) forces human review.
5. Rules engine: rate by payee type, higher rate without PAN, threshold(s) with cumulative state, Decimal rounding.
6. Output memo: item, rate, base, evidence, rules version, route.

## Results (keyword baseline)
| Setting | Routed correctly | Fully correct | Unsafe auto-prepared errors |
|---|---|---|---|
| Full pipeline | 13/14 | 13/14 | 0 |
| Ambiguity list OFF | 12/14 | 11/14 | 3 |

See `results_keyword.txt` and `results_keyword_no_ambiguity_list.txt`.

## Where it fails (honest)
- **C11 (cab rental for staff):** correct answer is contractor payment, but the pipeline escalates because "staff" is on the ambiguity list. Safe, but a false escalation: the list costs human time. With the list off, the keyword "rental" misfires to *rent of building* and auto-prepares a wrong item (unsafe).
- **C09 and C10** (composite AMC with software; legal outsourcing with staff supply): with the ambiguity list off the baseline confidently auto-prepares the wrong category. Only the list protects them; the keyword classifier alone cannot.
- **A bug found while testing:** my first rules table had only the aggregate contractor threshold and wrongly returned no deduction for C01; contractor payments have a single-payment limit as well as an aggregate one. Fixed in `rules.py`. Moral: the rules table needs primary-source review and its own golden tests.
- **Not covered:** 14 cases is a demo, not evidence of accuracy. Real invoices are messier, multi-line, and often need the contract. The LLM's accuracy and calibration are untested here.

## Jurisdiction
India, resident-payee payments only. For another country, replace `rules.py` and the date rule.
