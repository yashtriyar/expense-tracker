"""
frontend/app.py — Streamlit UI for the Expense Tracker.

Architecture rule: this file is the ONLY place that knows about Streamlit.
All business logic is delegated to backend/crud.py via the Session layer.
"""

import sys
from pathlib import Path

# Ensure the project root is on the path so `backend.*` imports work
# regardless of where `streamlit run` is invoked from.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import datetime
from decimal import Decimal, InvalidOperation

import streamlit as st

from backend.db import init_db, SessionLocal
from backend.schemas import ExpenseCreate
from backend import crud

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

init_db()

# ---------------------------------------------------------------------------
# Page config & custom CSS
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Expense Tracker",
    page_icon="₹",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  /* ── Google Font ── */
  @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500;600&display=swap');

  html, body, [class*="css"] {
      font-family: 'DM Sans', sans-serif;
  }

  /* ── App background ── */
  .stApp { background: #f7f4ef; }

  /* ── Sidebar ── */
  section[data-testid="stSidebar"] {
      background: #1a1a2e;
      color: #e0ddd8;
  }
  section[data-testid="stSidebar"] * { color: #e0ddd8 !important; }
  section[data-testid="stSidebar"] .stSelectbox label,
  section[data-testid="stSidebar"] .stRadio label { color: #b0aaa2 !important; }

  /* ── Headings ── */
  h1, h2, h3 {
      font-family: 'DM Serif Display', serif;
      color: #1a1a2e;
  }

  /* ── Metric cards ── */
  div[data-testid="metric-container"] {
      background: #1a1a2e;
      border-radius: 12px;
      padding: 16px 20px;
      color: #f7f4ef !important;
  }
  div[data-testid="metric-container"] * { color: #f7f4ef !important; }

  /* ── Success / error banners ── */
  .stAlert { border-radius: 10px; }

  /* ── Form submit button ── */
  div[data-testid="stForm"] button[kind="primaryFormSubmit"],
  div[data-testid="stForm"] button {
      background: #e8572a !important;
      color: white !important;
      border: none !important;
      border-radius: 8px !important;
      font-weight: 600 !important;
      padding: 0.5rem 2rem !important;
      transition: opacity .2s;
  }
  div[data-testid="stForm"] button:hover { opacity: 0.88; }

  /* ── Dataframe ── */
  div[data-testid="stDataFrame"] {
      border-radius: 12px;
      overflow: hidden;
      border: 1px solid #e2ddd6;
  }

  /* ── Category pill ── */
  .pill {
      display: inline-block;
      padding: 2px 10px;
      border-radius: 99px;
      font-size: 0.78rem;
      font-weight: 600;
      background: #e8572a22;
      color: #e8572a;
      margin-right: 4px;
  }

  /* ── Divider ── */
  hr { border-color: #ddd8d0; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PRESET_CATEGORIES = [
    "Food & Dining",
    "Transport",
    "Shopping",
    "Entertainment",
    "Health",
    "Utilities",
    "Rent / Housing",
    "Travel",
    "Education",
    "Other",
]

CATEGORY_COLORS = {
    "Food & Dining": "#e8572a",
    "Transport": "#3a86ff",
    "Shopping": "#8338ec",
    "Entertainment": "#ff006e",
    "Health": "#2dc653",
    "Utilities": "#ffbe0b",
    "Rent / Housing": "#fb5607",
    "Travel": "#06d6a0",
    "Education": "#118ab2",
    "Other": "#6c757d",
}

# ---------------------------------------------------------------------------
# Sidebar — Filters
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("## ₹ Expense Tracker")
    st.markdown("---")

    st.markdown("### Filters")
    filter_category = st.selectbox(
        "Category",
        options=["All"] + PRESET_CATEGORIES,
        index=0,
    )

    sort_order = st.radio(
        "Sort by date",
        options=["Newest first", "Oldest first"],
        index=0,
    )

    st.markdown("---")
    st.markdown("### About")
    st.markdown(
        "Built with **FastAPI-style** backend + **Streamlit** UI. "
        "Uses **idempotency keys** to prevent duplicate entries.",
        unsafe_allow_html=False,
    )

# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------

st.markdown("# Expense Tracker")
st.markdown("Track your spending — fast, clean, duplicate-safe.")
st.markdown("---")

# ── Two columns: form | summary ────────────────────────────────────────────

col_form, col_gap, col_summary = st.columns([2, 0.15, 1.3])

# ── ADD EXPENSE FORM ────────────────────────────────────────────────────────

with col_form:
    st.markdown("### Add Expense")

    with st.form("add_expense_form", clear_on_submit=True):
        amount_str = st.text_input(
            "Amount (₹)",
            placeholder="e.g. 250.00",
        )

        category = st.selectbox("Category", options=PRESET_CATEGORIES)

        description = st.text_input(
            "Description",
            placeholder="e.g. Lunch at Café Coffee Day",
            max_chars=500,
        )

        expense_date = st.date_input(
            "Date",
            value=datetime.date.today(),
            max_value=datetime.date.today(),
        )

        submitted = st.form_submit_button(
            "➕  Add Expense",
            use_container_width=True,
        )

    if submitted:
        # ── Validation ────────────────────────────────────────────────────
        errors: list[str] = []

        if not amount_str.strip():
            errors.append("Amount is required.")
        else:
            try:
                parsed_amount = Decimal(amount_str.strip())
                if parsed_amount <= 0:
                    errors.append("Amount must be greater than zero.")
            except InvalidOperation:
                errors.append(f"'{amount_str}' is not a valid number.")

        if not category:
            errors.append("Category is required.")

        if expense_date is None:
            errors.append("Date is required.")

        if errors:
            for err in errors:
                st.error(f"⚠️ {err}")
        else:
            # ── Persist ───────────────────────────────────────────────────
            try:
                payload = ExpenseCreate(
                    amount=parsed_amount,
                    category=category,
                    description=description.strip(),
                    date=expense_date,
                )
                db = SessionLocal()
                try:
                    expense, created = crud.create_expense(db, payload)
                finally:
                    db.close()

                if created:
                    st.success(
                        f"✅ Expense of **₹{expense.amount:,.2f}** added "
                        f"under **{expense.category}**."
                    )
                else:
                    st.info(
                        "ℹ️ Duplicate detected — this expense was already recorded. "
                        "No new record was created."
                    )

            except ValueError as exc:
                st.error(f"⚠️ Validation error: {exc}")
            except Exception as exc:
                st.error(f"❌ Unexpected error: {exc}")

# ── SUMMARY PANEL ───────────────────────────────────────────────────────────

with col_summary:
    st.markdown("### Overview")

    # Fetch all expenses (unfiltered) for summary metrics
    db = SessionLocal()
    try:
        all_expenses = crud.get_expenses(db)
        category_summary = crud.get_category_summary(all_expenses)
    finally:
        db.close()

    grand_total = crud.get_total(all_expenses)

    st.metric(label="Total Spent", value=f"₹{grand_total:,.2f}")
    st.metric(label="Transactions", value=len(all_expenses))

    if category_summary:
        st.markdown("**By Category**")
        for cat, total in category_summary.items():
            pct = float(total / grand_total * 100) if grand_total else 0
            color = CATEGORY_COLORS.get(cat, "#6c757d")
            st.markdown(
                f"""
                <div style="margin-bottom:6px;">
                  <span class="pill" style="background:{color}22;color:{color};">{cat}</span>
                  <span style="font-size:0.85rem;color:#555;">₹{total:,.2f}</span>
                  <span style="font-size:0.75rem;color:#999;margin-left:4px;">({pct:.1f}%)</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

# ---------------------------------------------------------------------------
# Expense list
# ---------------------------------------------------------------------------

st.markdown("---")
st.markdown("### Expense History")

active_cat = None if filter_category == "All" else filter_category
sort_param = "date_asc" if sort_order == "Oldest first" else "date_desc"

db = SessionLocal()
try:
    expenses = crud.get_expenses(db, category=active_cat, sort=sort_param)
finally:
    db.close()

filtered_total = crud.get_total(expenses)

# Summary line above table
summary_label = (
    f"Showing **{len(expenses)}** expenses"
    + (f" in **{active_cat}**" if active_cat else "")
    + f" — Total: **₹{filtered_total:,.2f}**"
)
st.markdown(summary_label)

if not expenses:
    st.info("No expenses found. Add one above!")
else:
    # ── Table header ──────────────────────────────────────────────────────
    hcol1, hcol2, hcol3, hcol4, hcol5 = st.columns([1.2, 1.5, 3, 1.2, 0.6])
    hcol1.markdown("**Date**")
    hcol2.markdown("**Category**")
    hcol3.markdown("**Description**")
    hcol4.markdown("**Amount**")
    hcol5.markdown("**Del**")
    st.markdown("<hr style='margin:4px 0 8px 0;border-color:#ddd8d0;'>", unsafe_allow_html=True)

    # ── One row per expense ───────────────────────────────────────────────
    for expense in expenses:
        col1, col2, col3, col4, col5 = st.columns([1.2, 1.5, 3, 1.2, 0.6])

        col1.markdown(expense.date.strftime("%d %b %Y"))
        col2.markdown(expense.category)
        col3.markdown(expense.description or "—")
        col4.markdown(f"₹{expense.amount:,.2f}")

        # Delete button — uses expense.id as a unique key so each row
        # gets its own independent button state.
        if col5.button("🗑️", key=f"del_{expense.id}", help="Delete this expense"):
            # Store the id that was clicked; confirmation happens below.
            st.session_state["pending_delete_id"] = expense.id
            st.session_state["pending_delete_desc"] = (
                expense.description or expense.category
            )

    # ── Confirmation dialog ───────────────────────────────────────────────
    # Renders below the list only when a delete button has been clicked.
    if "pending_delete_id" in st.session_state:
        st.markdown("---")
        st.warning(
            f"⚠️ Delete **\"{st.session_state['pending_delete_desc']}\"**? "
            "This cannot be undone."
        )
        confirm_col, cancel_col, _ = st.columns([1, 1, 4])

        if confirm_col.button("✅ Yes, delete", key="confirm_delete"):
            db = SessionLocal()
            try:
                deleted = crud.delete_expense(db, st.session_state["pending_delete_id"])
            finally:
                db.close()

            if deleted:
                st.success("🗑️ Expense deleted.")
            else:
                st.error("Could not find that expense — it may have already been deleted.")

            # Clear the pending state and refresh the page.
            del st.session_state["pending_delete_id"]
            del st.session_state["pending_delete_desc"]
            st.rerun()

        if cancel_col.button("❌ Cancel", key="cancel_delete"):
            del st.session_state["pending_delete_id"]
            del st.session_state["pending_delete_desc"]
            st.rerun()

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#aaa;font-size:0.8rem;'>"
    "Expense Tracker · SQLite + SQLAlchemy · Idempotency-safe"
    "</div>",
    unsafe_allow_html=True,
)