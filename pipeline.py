import json, os, re, sys, urllib.request
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from rules import *

def act_in_force(credit, payment):
    earliest = min(credit, payment)
    return "ITA2025" if earliest >= date.fromisoformat(EFFECTIVE_FROM) else "ITA1961"

# ---------- Classifiers (the only probabilistic part) ----------
KEYWORDS = [  # ordered baseline: (item, regex)
  ("RENT_LB", r"\brent(al)?\b|\blease\b"),
  ("COMMISSION", r"commission|brokerage"),
  ("PROF", r"consultan|legal|audit|advisory|professional"),
  ("TECH", r"call cent(re|er)|technical service"),
  ("CONTRACT", r"fabricat|maintenance|printing|catering|transport|plumbing|electrical|contract work|civil work"),
]
def classify_keyword(text):
    hits = []
    for item, rx in KEYWORDS:
        m = re.search(rx, text, re.I)
        if m: hits.append((item, m.group(0)))
    if len(hits) == 1:
        return {"item": hits[0][0], "evidence": hits[0][1], "flags": []}
    if len(hits) > 1:
        return {"item": "ESCALATE", "evidence": hits[0][1], "flags": ["multiple_categories"]}
    return {"item": "ESCALATE", "evidence": "", "flags": ["no_match"]}

def classify_llm(text, candidates):
    """OpenRouter free-tier model. Not run in the submitted results (no API access in build env)."""
    key = os.environ["OPENROUTER_API_KEY"]; model = os.environ.get("OR_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
    cand = "\n".join(f"- {k}: {v['label']}" for k, v in candidates.items())
    prompt = (f"Classify this invoice line into exactly one candidate or ESCALATE if ambiguous/composite.\n"
              f"Candidates:\n{cand}\n- ESCALATE\nInvoice: \"{text}\"\n"
              'Reply ONLY JSON: {"item": "...", "evidence": "<verbatim substring of invoice>", "flags": []}. Never output rates.')
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps({"model": model, "temperature": 0, "messages": [{"role": "user", "content": prompt}]}).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    out = json.load(urllib.request.urlopen(req, timeout=60))["choices"][0]["message"]["content"]
    return json.loads(re.search(r"\{.*\}", out, re.S).group(0))

# ---------- Deterministic spine ----------
def q(x): return Decimal(x).quantize(Decimal("1"), ROUND_HALF_UP)

def process(case, classifier):
    credit, pay = date.fromisoformat(case["credit_date"]), date.fromisoformat(case["payment_date"])
    memo = {"id": case["id"], "rules_version": RULES_VERSION, "route": None, "item": None, "tds": 0, "reason": ""}
    if act_in_force(credit, pay) == "ITA1961":
        return {**memo, "route": "HUMAN", "item": "OUT_OF_SCOPE", "reason": "earlier of credit/payment before 1 Apr 2026: 1961 Act applies"}
    text = case["invoice_text"]
    c = classifier(text)
    item, ev = c["item"], c.get("evidence", "")
    # grounding check: evidence must really be in the input
    if item != "ESCALATE" and (not ev or ev.lower() not in text.lower()):
        item, c["flags"] = "ESCALATE", c.get("flags", []) + ["evidence_not_grounded"]
    # ambiguity list overrides confidence
    amb = [w for w in AMBIGUITY_WORDS if w in text.lower()]
    if amb and item != "ESCALATE":
        item, c["flags"] = "ESCALATE", c.get("flags", []) + [f"ambiguity_list:{amb[0]}"]
    if item == "ESCALATE":
        return {**memo, "route": "HUMAN", "item": "ESCALATE", "reason": ",".join(c.get("flags", [])) or "model escalated"}
    r = RULES[item]
    amount, ytd = Decimal(case["amount"]), Decimal(case["ytd_paid"])
    rate = Decimal(str(r["rate_ind"] if case["payee"] == "individual" else r["rate_other"]))
    if not case["has_pan"]: rate = Decimal(str(max(NO_PAN_RATE, float(rate)))) ; 
    thr = Decimal(r["threshold"])
    single = Decimal(r.get('single_threshold', 0))  # contractor: single-payment OR aggregate threshold
    if ytd + amount <= thr and amount <= single if single else ytd + amount <= thr:
        tds, base = Decimal(0), Decimal(0)
    else:  # SIMPLIFICATION: once threshold crossed, base = cumulative if first crossing else this payment
        base = (ytd + amount) if ytd <= thr else amount
        tds = q(base * rate)
    return {**memo, "route": "AUTO_PREPARE", "item": item, "tds": int(tds), "base": int(base), "rate": float(rate),
            "evidence": ev, "reason": "threshold not crossed" if tds == 0 else "deduct"}

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "keyword"
    cases = json.load(open("cases.json"))
    clf = classify_keyword if mode == "keyword" else (lambda t: classify_llm(t, RULES))
    rows, ok_route, ok_amt, unsafe = [], 0, 0, 0
    for c in cases:
        m = process(c, clf)
        exp = c["expected"]
        route_ok = m["route"] == exp["route"]
        amt_ok = route_ok and (m["route"] == "HUMAN" or (m["item"] == exp["item"] and m["tds"] == exp["tds"]))
        is_unsafe = m["route"] == "AUTO_PREPARE" and not (m["item"] == exp.get("item") and m["tds"] == exp.get("tds"))
        ok_route += route_ok; ok_amt += amt_ok; unsafe += is_unsafe
        rows.append((c["id"], c["invoice_text"][:48], exp["route"], exp.get("item", "-"), exp.get("tds", "-"),
                     m["route"], m["item"], m["tds"], "OK" if amt_ok else ("UNSAFE" if is_unsafe else "MISS")))
    print(f"mode={mode}  rules={RULES_VERSION}")
    print("id   | invoice | exp route | exp item | exp tds | got route | got item | got tds | verdict")
    for r in rows: print(" | ".join(map(str, r)))
    print(f"\nrouted correctly: {ok_route}/{len(cases)}   fully correct: {ok_amt}/{len(cases)}   UNSAFE auto-prepared errors: {unsafe}")
