"""
Step 3 — Financial Entity Extraction
NO API KEY NEEDED. Uses smart regex verified against real PDFs.

Key insight from reading actual HCL/Infosys/TCS/Mphasis PDFs:
  Lines look like:  "Revenue from operations  12  2,55,324  2,40,893"
  The "12" is a note-number, NOT a value — patterns skip it
  and grab the first large number (≥ 4 digits) after the label.
"""

import re


def _num(s):
    try:
        return float(str(s).replace(",", "").strip())
    except:
        return None


def _find(text, *label_patterns, mult=1.0, min_val=10):
    """
    Search for each label pattern, return first large number found after it.
    Skips small note-numbers (1-3 digits) that appear between label and value.
    """
    # Regex: label … (optional note num 1-3 digits) … LARGE number
    big_num = r"((?:\d{1,3},)+\d{3}(?:\.\d+)?|\d{5,}(?:\.\d+)?)"
    for pat in label_patterns:
        # Try direct match with big number pattern
        m = re.search(pat + r"[^\n]{0,30}?" + big_num, text, re.IGNORECASE)
        if m:
            v = _num(m.group(1))
            if v and v >= min_val:
                return round(v * mult, 2)
    return None


def _find_small(text, *label_patterns):
    """For EPS / small values — find decimal numbers."""
    for pat in label_patterns:
        m = re.search(pat + r"[^\n]{0,80}?([\d,]+\.\d{2})", text, re.IGNORECASE)
        if m:
            v = _num(m.group(1))
            if v and v < 50000:
                return round(v, 2)
    return None


def _detect_unit_multiplier(text):
    """
    Detect if values are in Rs. million (→ ÷10 for crore) or already in crore.
    Mphasis reports in Rs. million; HCL/Infosys/TCS report in Rs. crore.
    """
    t = text[:3000].lower()
    if "inr million" in t or "rs. million" in t or "inr million" in t:
        return 0.1, "crore (converted from million)"
    if "in millions" in t or "(` million)" in t or "(inr million)" in t:
        return 0.1, "crore (converted from million)"
    return 1.0, "crore"


def _detect_company_and_year(text):
    """Extract company name and fiscal year from report text."""
    company = "Unknown Company"
    year    = "—"

    # Company name patterns
    for pat in [
        r"(hcltech|hcl technologies)",
        r"(infosys limited|infosys)",
        r"(tata consultancy services|tcs)",
        r"(mphasis limited|mphasis)",
        r"(wipro limited|wipro)",
        r"(tech mahindra)",
        r"(l&t infotech|ltimindtree)",
    ]:
        m = re.search(pat, text[:5000], re.IGNORECASE)
        if m:
            company = m.group(1).title()
            break

    # Fiscal year
    for pat in [
        r"annual report\s+(\d{4}[-–]\d{2,4})",
        r"for the year ended\s+(?:march|31)\s+(\d{4})",
        r"\bfy\s*(\d{4})\b",
        r"financial year\s+(\d{4}[-–]\d{2,4})",
        r"year ended\s+(?:31\s+march|march\s+31)[,\s]+(\d{4})",
    ]:
        m = re.search(pat, text[:8000], re.IGNORECASE)
        if m:
            year = m.group(1)
            break

    return company, year


def extract_financials(cleaned_text: str) -> dict:
    """
    Full extraction pipeline — works on any Indian IT company annual report.
    Returns structured dict with income statement + balance sheet + ratios.
    """
    text = cleaned_text
    mult, unit_label = _detect_unit_multiplier(text)
    company, year    = _detect_company_and_year(text)

    # ── Income Statement ──────────────────────────────────────────────────────
    revenue = _find(text,
        r"revenue\s+from\s+operations",
        r"revenue\s+from\s+operations\s+\d{1,3}",   # with note number
        r"net\s+sales",
        r"turnover",
        mult=mult, min_val=100)

    other_income = _find(text,
        r"other\s+income[,\s]",
        mult=mult, min_val=1)

    total_income = _find(text,
        r"total\s+income\s*(?:\(i\))?",
        r"total\s+income\s*\d{0,3}\s",
        mult=mult, min_val=100)

    employee_exp = _find(text,
        r"employee\s+benefits?\s+expense",
        r"employee\s+cost",
        r"staff\s+cost",
        mult=mult, min_val=10)

    finance_cost = _find(text,
        r"finance\s+costs?",
        r"interest\s+expense",
        mult=mult, min_val=1)

    depreciation = _find(text,
        r"depreciation\s+and\s+amort",
        r"depreciation\s+expense",
        mult=mult, min_val=1)

    total_expenses = _find(text,
        r"total\s+expenses?\s*(?:\(ii\))?",
        r"total\s+expenses?\s+\d{0,3}\s",
        mult=mult, min_val=100)

    pbt = _find(text,
        r"profit\s+before\s+exceptional\s+item\s+and\s+tax",
        r"profit\s+before\s+tax\s*(?:\(iii\))?",
        r"profit\s+before\s+tax\s+\d{0,3}\s",
        mult=mult, min_val=10)

    tax_expense = _find(text,
        r"total\s+tax\s+expense",
        r"tax\s+expense",
        mult=mult, min_val=1)

    net_profit = _find(text,
        r"profit\s+for\s+the\s+year\s*\(a\)",
        r"profit\s+for\s+the\s+year\s*\d{0,3}\s",
        r"profit\s+after\s+tax",
        r"\bpat\b",
        mult=mult, min_val=10)

    eps = _find_small(text,
        r"basic\s+(?:earnings|eps)\s+per\s+(?:equity\s+)?share",
        r"earnings\s+per\s+(?:equity\s+)?share")

    # ── Balance Sheet ─────────────────────────────────────────────────────────
    total_assets = _find(text,
        r"total\s+assets",
        mult=mult, min_val=100)

    nc_assets = _find(text,
        r"total\s+non.?current\s+assets",
        mult=mult, min_val=10)

    curr_assets = _find(text,
        r"total\s+current\s+assets",
        mult=mult, min_val=10)

    total_equity = _find(text,
        r"total\s+equity(?!\s+and\s+liabil)",
        mult=mult, min_val=10)

    share_capital = _find(text,
        r"(?:equity\s+)?share\s+capital\s+\d{0,3}\s",
        r"share\s+capital",
        mult=mult, min_val=1)

    nc_liab = _find(text,
        r"total\s+non.?current\s+liabilit",
        mult=mult, min_val=1)

    curr_liab = _find(text,
        r"total\s+current\s+liabilit",
        mult=mult, min_val=1)

    # Derived
    total_liab = None
    if nc_liab and curr_liab:
        total_liab = round(nc_liab + curr_liab, 2)
    elif total_assets and total_equity:
        total_liab = round(total_assets - total_equity, 2)

    # ── Ratios ────────────────────────────────────────────────────────────────
    net_margin   = round(net_profit   / revenue * 100,  2) if net_profit   and revenue else None
    pbt_margin   = round(pbt          / revenue * 100,  2) if pbt          and revenue else None
    roe          = round(net_profit   / total_equity * 100, 2) if net_profit and total_equity else None
    de_ratio     = round(total_liab   / total_equity,   4) if total_liab   and total_equity else None
    exp_ratio    = round(total_expenses / total_income * 100, 2) if total_expenses and total_income else None

    # ── AI-style summary (rule-based) ─────────────────────────────────────────
    summary_parts = []
    if company != "Unknown Company":
        summary_parts.append(f"{company} reported for {year}.")
    if revenue:
        summary_parts.append(f"Revenue from operations stood at Rs.{revenue:,.2f} {unit_label}.")
    if net_profit:
        summary_parts.append(f"Net profit for the year was Rs.{net_profit:,.2f} {unit_label}.")
    if net_margin:
        summary_parts.append(f"Net profit margin was {net_margin:.2f}%.")
    if total_assets:
        summary_parts.append(f"Total assets stood at Rs.{total_assets:,.2f} {unit_label}.")
    if total_equity and total_liab:
        summary_parts.append(
            f"The company is financed with Rs.{total_equity:,.2f} equity and Rs.{total_liab:,.2f} liabilities.")
    summary = " ".join(summary_parts) if summary_parts else "Summary not available."

    return {
        "company_name": company,
        "fiscal_year":  year,
        "currency":     "INR",
        "unit":         unit_label,

        "income_statement": {
            "revenue_from_operations": revenue,
            "other_income":            other_income,
            "total_income":            total_income,
            "employee_expenses":       employee_exp,
            "finance_costs":           finance_cost,
            "depreciation":            depreciation,
            "total_expenses":          total_expenses,
            "profit_before_tax":       pbt,
            "tax_expense":             tax_expense,
            "net_profit":              net_profit,
            "eps_basic":               eps,
        },

        "balance_sheet": {
            "total_assets":            total_assets,
            "non_current_assets":      nc_assets,
            "current_assets":          curr_assets,
            "total_equity":            total_equity,
            "share_capital":           share_capital,
            "non_current_liabilities": nc_liab,
            "current_liabilities":     curr_liab,
            "total_liabilities":       total_liab,
        },

        "ratios": {
            "net_profit_margin_pct":   net_margin,
            "pbt_margin_pct":          pbt_margin,
            "return_on_equity_pct":    roe,
            "expense_ratio_pct":       exp_ratio,
            "debt_to_equity":          de_ratio,
        },

        "summary": summary,
    }
