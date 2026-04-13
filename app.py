"""
app.py — Financial Report Analyzer
Upload any annual report PDF → all 4 steps run automatically.
NO API KEY REQUIRED.

Run: streamlit run app.py
"""
import os, tempfile
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from step1_extract import classify_pdf, extract_text
from step2_clean   import clean_text
from step3_extract import extract_financials
from step4_store   import save, load_all

st.set_page_config(
    page_title="Financial Report Analyzer",
    page_icon="📊",
    layout="wide",
)

COLORS = ["#4ade80","#60a5fa","#fbbf24","#f87171","#a78bfa","#34d399","#fb7185","#38bdf8"]

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 Financial Analyzer")
    st.success("✓ No API Key Required")
    st.markdown("---")
    nav = st.radio("Navigate", [
        "📤 Upload & Analyze",
        "📋 All Reports",
        "📈 Compare Companies",
    ])
    records = load_all()
    if records:
        st.markdown("---")
        df_dl = pd.DataFrame(records)
        st.download_button("⬇️ Download CSV",
            df_dl.to_csv(index=False), "financials.csv", "text/csv")

def fmt(v):
    if v is None or (isinstance(v, float) and str(v) == "nan"): return "—"
    try: return f"{float(v):,.2f}"
    except: return str(v)

def gauge(val, title, max_v=30, suffix="%"):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=float(val or 0),
        title={"text": title, "font": {"size": 13}},
        number={"suffix": suffix, "valueformat": ".2f"},
        gauge={
            "axis": {"range": [0, max_v]},
            "bar":  {"color": "#4ade80"},
            "steps": [
                {"range": [0,           max_v*0.33], "color": "#fef9c3"},
                {"range": [max_v*0.33,  max_v*0.66], "color": "#dcfce7"},
                {"range": [max_v*0.66,  max_v],      "color": "#bbf7d0"},
            ],
        }
    ))
    fig.update_layout(height=220, margin=dict(t=50,b=10,l=20,r=20),
                      paper_bgcolor="rgba(0,0,0,0)")
    return fig

def bar_chart(df, x, y, title):
    d = df[[x,y]].dropna()
    if d.empty: return None
    fig = px.bar(d, x=x, y=y, title=title, color=x,
                 color_discrete_sequence=COLORS, text=y)
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
    fig.update_layout(showlegend=False, height=380,
                      plot_bgcolor="#f9fafb", paper_bgcolor="#f9fafb")
    return fig

# ══════════════════════════════════════════════════════════════════════════════
#  UPLOAD & ANALYZE
# ══════════════════════════════════════════════════════════════════════════════
if nav == "📤 Upload & Analyze":
    st.title("📤 Upload Annual Report PDF")
    st.markdown("Upload any company's annual report. All **4 steps run automatically**.")

    uploaded = st.file_uploader(
        "Drop PDF here", type=["pdf"], label_visibility="collapsed"
    )

    if uploaded:
        st.markdown(f"**File:** {uploaded.name}  &nbsp;·&nbsp;  {uploaded.size/1024/1024:.1f} MB")

        if st.button("⚡  Analyze Report", type="primary", use_container_width=True):

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded.read())
                tmp_path = tmp.name

            prog   = st.progress(0)
            status = st.empty()

            # ── STEP 1 ────────────────────────────────────────────────────────
            status.info("**Step 1 / 4** — Classifying PDF and extracting all text...")
            cl       = classify_pdf(tmp_path)
            raw_text = extract_text(tmp_path)
            prog.progress(25)

            # ── STEP 2 ────────────────────────────────────────────────────────
            status.info("**Step 2 / 4** — Cleaning and normalising text...")
            cleaned = clean_text(raw_text)
            prog.progress(45)

            # ── STEP 3 ────────────────────────────────────────────────────────
            status.info("**Step 3 / 4** — Extracting financial figures...")
            try:
                result = extract_financials(cleaned)
            except Exception as e:
                st.error(f"Extraction failed: {e}")
                st.stop()
            prog.progress(80)

            # ── STEP 4 ────────────────────────────────────────────────────────
            status.info("**Step 4 / 4** — Saving to database and CSV...")
            rec = save(result, uploaded.name)
            prog.progress(100)
            status.success("✅ Done! Report analyzed and saved.")
            os.unlink(tmp_path)

            # ── RESULTS ───────────────────────────────────────────────────────
            inc = result.get("income_statement", {}) or {}
            bs  = result.get("balance_sheet",    {}) or {}
            rat = result.get("ratios",           {}) or {}

            st.markdown("---")

            # Company header
            st.markdown(f"""
            <div style='background:#1a1d27;border-radius:14px;padding:20px 24px;
                        border-left:4px solid #4ade80;margin-bottom:20px'>
              <div style='font-size:24px;font-weight:700;color:#e8eaf0'>
                {result.get('company_name','—')}
              </div>
              <div style='font-size:14px;color:#9ca3af;margin-top:4px'>
                {result.get('fiscal_year','—')} &nbsp;·&nbsp;
                Unit: {result.get('unit','Rs. Crore')} &nbsp;·&nbsp;
                {cl['total_pages']} pages &nbsp;·&nbsp;
                Type: {cl['type'].upper()}
              </div>
            </div>
            """, unsafe_allow_html=True)

            # Step 1 details
            with st.expander("📂 Step 1 — PDF Classification"):
                c1,c2,c3,c4 = st.columns(4)
                c1.metric("PDF Type",      cl["type"].upper())
                c2.metric("Total Pages",   cl["total_pages"])
                c3.metric("Text Pages",    cl["text_pages"])
                c4.metric("Scanned Pages", cl["scanned_pages"])

            # ── Income Statement ──────────────────────────────────────────────
            st.subheader("📄 Income Statement")
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Revenue",           fmt(inc.get("revenue_from_operations")))
            c2.metric("Total Income",      fmt(inc.get("total_income")))
            c3.metric("Total Expenses",    fmt(inc.get("total_expenses")))
            c4.metric("Profit Before Tax", fmt(inc.get("profit_before_tax")))
            c5,c6,c7,c8 = st.columns(4)
            c5.metric("Net Profit",        fmt(inc.get("net_profit")))
            c6.metric("Tax Expense",       fmt(inc.get("tax_expense")))
            c7.metric("Employee Expenses", fmt(inc.get("employee_expenses")))
            c8.metric("EPS (Basic) Rs.",     fmt(inc.get("eps_basic")))

            # Waterfall
            r  = inc.get("revenue_from_operations") or 0
            e  = inc.get("total_expenses") or 0
            tx = inc.get("tax_expense") or 0
            np = inc.get("net_profit") or 0
            if r > 0:
                fig = go.Figure(go.Waterfall(
                    orientation="v",
                    measure=["absolute","relative","relative","total"],
                    x=["Revenue","− Expenses","− Tax","Net Profit"],
                    y=[r, -e, -tx, 0],
                    text=[f"{v:,.0f}" for v in [r,-e,-tx,np]],
                    textposition="outside",
                    connector={"line":{"color":"#4b5563"}},
                    decreasing={"marker":{"color":"#f87171"}},
                    increasing={"marker":{"color":"#4ade80"}},
                    totals={"marker":{"color":"#60a5fa"}},
                ))
                fig.update_layout(title="P&L Waterfall", height=360,
                                  plot_bgcolor="#f9fafb", paper_bgcolor="#f9fafb")
                st.plotly_chart(fig, use_container_width=True)

            # ── Balance Sheet ─────────────────────────────────────────────────
            st.subheader("🏦 Balance Sheet")
            c1,c2,c3 = st.columns(3)
            c1.metric("Total Assets",            fmt(bs.get("total_assets")))
            c2.metric("Total Equity",            fmt(bs.get("total_equity")))
            c3.metric("Total Liabilities",       fmt(bs.get("total_liabilities")))
            c4,c5,c6 = st.columns(3)
            c4.metric("Current Assets",          fmt(bs.get("current_assets")))
            c5.metric("Current Liabilities",     fmt(bs.get("current_liabilities")))
            c6.metric("Non-Current Liabilities", fmt(bs.get("non_current_liabilities")))

            eq   = bs.get("total_equity")
            liab = bs.get("total_liabilities")
            if eq and liab:
                col1, col2 = st.columns([1,1])
                with col1:
                    fig = px.pie(
                        names=["Equity","Liabilities"],
                        values=[eq, liab],
                        color_discrete_sequence=["#4ade80","#f87171"],
                        title="Equity vs Liabilities", hole=0.45,
                    )
                    fig.update_layout(height=320)
                    st.plotly_chart(fig, use_container_width=True)
                with col2:
                    ca = bs.get("current_assets") or 0
                    nca= bs.get("non_current_assets") or 0
                    if ca or nca:
                        fig = px.pie(
                            names=["Current Assets","Non-Current Assets"],
                            values=[ca, nca],
                            color_discrete_sequence=["#60a5fa","#fbbf24"],
                            title="Assets Breakdown", hole=0.45,
                        )
                        fig.update_layout(height=320)
                        st.plotly_chart(fig, use_container_width=True)

            # ── Ratios ────────────────────────────────────────────────────────
            st.subheader("📊 Key Ratios & Margins")
            g1,g2,g3,g4 = st.columns(4)
            with g1: st.plotly_chart(gauge(rat.get("net_profit_margin_pct"), "Net Margin %"), use_container_width=True)
            with g2: st.plotly_chart(gauge(rat.get("pbt_margin_pct"),        "PBT Margin %", 35), use_container_width=True)
            with g3: st.plotly_chart(gauge(rat.get("return_on_equity_pct"),  "Return on Equity %", 40), use_container_width=True)
            with g4: st.plotly_chart(gauge(rat.get("debt_to_equity"),        "Debt / Equity", 2, "×"), use_container_width=True)

            # ── Summary ───────────────────────────────────────────────────────
            st.subheader("📝 Financial Summary")
            st.info(result.get("summary","—"))

    else:
        st.markdown("""
        <div style='border:2px dashed #2a2d3a;border-radius:16px;
                    padding:52px 32px;text-align:center;background:#1a1d27'>
          <div style='font-size:44px;margin-bottom:16px'>📄</div>
          <div style='font-size:18px;font-weight:600;color:#e8eaf0;margin-bottom:8px'>
            Upload any company annual report PDF above
          </div>
          <div style='font-size:13px;color:#6b7280;margin-bottom:28px'>
            Works with HCL · Infosys · TCS · Mphasis · Wipro · any IT company
          </div>
          <div style='display:inline-block;text-align:left;font-size:13px;color:#9ca3af;line-height:2'>
            🟢 <b style='color:#4ade80'>Step 1</b> — Classify PDF (text/scanned) + extract all text &amp; tables<br/>
            🟢 <b style='color:#4ade80'>Step 2</b> — Clean text, normalize currency &amp; numbers<br/>
            🟢 <b style='color:#4ade80'>Step 3</b> — Extract Revenue, Profit, Assets, Liabilities, Ratios<br/>
            🟢 <b style='color:#4ade80'>Step 4</b> — Save to SQLite database + CSV file
          </div>
        </div>
        """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  ALL REPORTS
# ══════════════════════════════════════════════════════════════════════════════
elif nav == "📋 All Reports":
    st.title("📋 All Analyzed Reports")
    records = load_all()

    if not records:
        st.info("No reports yet. Go to Upload & Analyze to get started.")
    else:
        df = pd.DataFrame(records)
        show = ["company_name","fiscal_year","unit","revenue","net_profit",
                "total_assets","total_liabilities","net_profit_margin_pct","extracted_at"]
        avail = [c for c in show if c in df.columns]
        st.dataframe(
            df[avail].rename(columns={c:c.replace("_"," ").title() for c in avail}),
            use_container_width=True, hide_index=True,
        )

        st.markdown("---")
        companies = df["company_name"].dropna().unique().tolist()
        sel = st.selectbox("View details for", companies)
        row = df[df["company_name"]==sel].iloc[0]

        c1,c2 = st.columns(2)
        with c1:
            st.markdown("**📄 Income Statement**")
            for f in ["revenue","total_income","total_expenses",
                      "profit_before_tax","net_profit","eps_basic"]:
                v = row.get(f)
                if v and str(v)!="nan":
                    st.markdown(f"- **{f.replace('_',' ').title()}**: {float(v):,.2f}")
        with c2:
            st.markdown("**🏦 Balance Sheet**")
            for f in ["total_assets","total_equity","non_current_liabilities",
                      "current_liabilities","total_liabilities"]:
                v = row.get(f)
                if v and str(v)!="nan":
                    st.markdown(f"- **{f.replace('_',' ').title()}**: {float(v):,.2f}")

        s = row.get("summary")
        if s and str(s)!="nan":
            st.markdown("**📝 Summary**")
            st.info(s)

# ══════════════════════════════════════════════════════════════════════════════
#  COMPARE COMPANIES
# ══════════════════════════════════════════════════════════════════════════════
elif nav == "📈 Compare Companies":
    st.title("📈 Compare Companies")
    records = load_all()

    if len(records) < 2:
        st.info("Upload at least 2 company reports to compare.")
    else:
        df = pd.DataFrame(records)
        df = df.sort_values("extracted_at").groupby("company_name").last().reset_index()

        metric = st.selectbox("Metric", [
            "revenue","net_profit","total_assets","total_equity",
            "total_liabilities","profit_before_tax",
            "net_profit_margin_pct","debt_to_equity","return_on_equity_pct",
        ])
        fig = bar_chart(df, "company_name", metric, metric.replace("_"," ").title()+" Comparison")
        if fig: st.plotly_chart(fig, use_container_width=True)

        c1,c2 = st.columns(2)
        for col, m in [(c1,"revenue"),(c2,"net_profit")]:
            f = bar_chart(df,"company_name",m,m.replace("_"," ").title())
            if f: col.plotly_chart(f, use_container_width=True)

        # Grouped bar
        melt = df[["company_name","revenue","total_expenses","net_profit"]].melt(
            id_vars="company_name", var_name="Metric", value_name="Value")
        melt["Metric"] = melt["Metric"].map({
            "revenue":"Revenue","total_expenses":"Total Expenses","net_profit":"Net Profit"})
        fig2 = px.bar(melt, x="company_name", y="Value", color="Metric", barmode="group",
                      color_discrete_sequence=["#4ade80","#f87171","#60a5fa"],
                      title="Revenue vs Expenses vs Net Profit")
        fig2.update_layout(height=400, plot_bgcolor="#f9fafb", paper_bgcolor="#f9fafb")
        st.plotly_chart(fig2, use_container_width=True)

        st.subheader("📋 Side-by-Side Table")
        show = ["company_name","fiscal_year","revenue","net_profit","total_assets",
                "total_liabilities","total_equity","net_profit_margin_pct","debt_to_equity"]
        avail = [c for c in show if c in df.columns]
        st.dataframe(
            df[avail].rename(columns={c:c.replace("_"," ").title() for c in avail}),
            use_container_width=True, hide_index=True,
        )

        st.subheader("💡 Insights")
        for col, emoji, label in [
            ("revenue",             "📈","Highest Revenue"),
            ("net_profit",          "💰","Highest Net Profit"),
            ("net_profit_margin_pct","📊","Best Net Margin %"),
            ("total_assets",        "🏦","Largest Total Assets"),
        ]:
            d = df[["company_name",col]].dropna()
            if not d.empty:
                best = d.loc[d[col].idxmax()]
                st.info(f"{emoji} **{label}:** {best['company_name']} — {best[col]:,.2f}")
