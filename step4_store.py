"""Step 4 — Save to SQLite + CSV."""
import os, csv, json, sqlite3
from datetime import datetime

DB_PATH  = "outputs/financial_data.db"
CSV_PATH = "outputs/financial_data.csv"

FIELDS = [
    "company_name","fiscal_year","currency","unit","filename",
    "revenue","other_income","total_income","employee_expenses",
    "finance_costs","depreciation","total_expenses",
    "profit_before_tax","tax_expense","net_profit","eps_basic",
    "total_assets","non_current_assets","current_assets",
    "total_equity","share_capital",
    "non_current_liabilities","current_liabilities","total_liabilities",
    "net_profit_margin_pct","pbt_margin_pct","return_on_equity_pct",
    "expense_ratio_pct","debt_to_equity",
    "summary","extracted_at",
]

def _init():
    os.makedirs("outputs", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cols = ", ".join(
        f"{f} TEXT" if f in ("company_name","fiscal_year","currency","unit",
                             "filename","summary","extracted_at")
        else f"{f} REAL"
        for f in FIELDS
    )
    conn.execute(f"CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY AUTOINCREMENT, {cols})")
    conn.commit(); conn.close()

def _flatten(r, filename):
    inc = r.get("income_statement",{}) or {}
    bs  = r.get("balance_sheet",{})    or {}
    rat = r.get("ratios",{})           or {}
    return {
        "company_name":            r.get("company_name"),
        "fiscal_year":             r.get("fiscal_year"),
        "currency":                r.get("currency"),
        "unit":                    r.get("unit"),
        "filename":                filename,
        "revenue":                 inc.get("revenue_from_operations"),
        "other_income":            inc.get("other_income"),
        "total_income":            inc.get("total_income"),
        "employee_expenses":       inc.get("employee_expenses"),
        "finance_costs":           inc.get("finance_costs"),
        "depreciation":            inc.get("depreciation"),
        "total_expenses":          inc.get("total_expenses"),
        "profit_before_tax":       inc.get("profit_before_tax"),
        "tax_expense":             inc.get("tax_expense"),
        "net_profit":              inc.get("net_profit"),
        "eps_basic":               inc.get("eps_basic"),
        "total_assets":            bs.get("total_assets"),
        "non_current_assets":      bs.get("non_current_assets"),
        "current_assets":          bs.get("current_assets"),
        "total_equity":            bs.get("total_equity"),
        "share_capital":           bs.get("share_capital"),
        "non_current_liabilities": bs.get("non_current_liabilities"),
        "current_liabilities":     bs.get("current_liabilities"),
        "total_liabilities":       bs.get("total_liabilities"),
        "net_profit_margin_pct":   rat.get("net_profit_margin_pct"),
        "pbt_margin_pct":          rat.get("pbt_margin_pct"),
        "return_on_equity_pct":    rat.get("return_on_equity_pct"),
        "expense_ratio_pct":       rat.get("expense_ratio_pct"),
        "debt_to_equity":          rat.get("debt_to_equity"),
        "summary":                 r.get("summary"),
        "extracted_at":            datetime.now().isoformat(),
    }

def save(result, filename):
    _init()
    rec = _flatten(result, filename)
    conn = sqlite3.connect(DB_PATH)
    cols = list(rec.keys())
    conn.execute(
        f"INSERT INTO reports ({','.join(cols)}) VALUES ({','.join('?'*len(cols))})",
        [rec[c] for c in cols]
    )
    conn.commit(); conn.close()
    exists = os.path.exists(CSV_PATH)
    with open(CSV_PATH, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if not exists: w.writeheader()
        w.writerow({k: rec.get(k) for k in FIELDS})
    return rec

def load_all():
    _init()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM reports ORDER BY extracted_at DESC").fetchall()]
    conn.close()
    return rows
