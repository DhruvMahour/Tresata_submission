"""Versioned, effective-dated rules table.
ILLUSTRATIVE: values are a simplified subset for the prototype and MUST be verified
against the Income-tax Act 2025 s.393 table (and signed off by a CA) before any real use.
Table item numbers are deliberately not claimed except where a primary-style FAQ was found (contractor = Sl. 6(i))."""
RULES_VERSION = "2026-27.proto.1"
EFFECTIVE_FROM = "2026-04-01"
NO_PAN_RATE = 0.20  # higher-rate-without-PAN (s.397(2) per secondary sources) - verify

RULES = {
  "CONTRACT":   {"label": "Payment to contractor (old 194C; s.393(1) Sl.6(i))", "rate_ind": 0.01, "rate_other": 0.02, "threshold": 100000, "single_threshold": 30000},
  "PROF":       {"label": "Professional services (old 194J)", "rate_ind": 0.10, "rate_other": 0.10, "threshold": 50000},
  "TECH":       {"label": "Technical services / call centre (old 194J)", "rate_ind": 0.02, "rate_other": 0.02, "threshold": 50000},
  "RENT_LB":    {"label": "Rent: land/building (old 194I)", "rate_ind": 0.10, "rate_other": 0.10, "threshold": 600000},
  "COMMISSION": {"label": "Commission / brokerage (old 194H)", "rate_ind": 0.02, "rate_other": 0.02, "threshold": 20000},
}
# Cases that always go to a human regardless of model confidence
import os
AMBIGUITY_WORDS = [] if os.environ.get("NO_AMB") else ["software", "licen", "advertis", "spares", "amc", "annual maintenance", "reimburse", "supply of", "staff", "manpower"]
