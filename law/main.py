import streamlit as st
from law.data_loader import load_law_schools, DataValidationError
from law.matcher import rank_schools

_STATES = [
    "AL","AK","AZ","AR","CA","CO","CT","DC","DE","FL","GA","HI","ID","IL",
    "IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE",
    "NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD",
    "TN","TX","UT","VT","VA","WA","WV","WI","WY",
]

_TIER_COLORS = {
    "safety":     "🟢",
    "target":     "🔵",
    "reach":      "🟠",
    "hard reach": "🔴",
}

_INCOME_LABELS = {
    "under_65k":  "Under $65K",
    "65k_130k":   "$65K – $130K",
    "130k_200k":  "$130K – $200K",
    "over_200k":  "Over $200K",
    "prefer_not": "Prefer not to say",
}


@st.cache_data
def get_schools() -> list[dict]:
    return load_law_schools()


st.set_page_config(page_title="Opportunity — Law School Match", layout="wide")

try:
    schools = get_schools()
except FileNotFoundError:
    st.error("law_schools.json not found.")
    st.stop()
except DataValidationError as e:
    st.error(f"Invalid law school data: {e}")
    st.stop()

st.title("Opportunity")
st.markdown("*Find your best-fit law schools based on your profile and goals.*")

with st.form("profile_form"):

    # ── Academic Profile ──────────────────────────────────────────────────
    st.subheader("Academic Profile")

    no_lsat = st.checkbox(
        "I haven't taken the LSAT yet",
        help="Without an LSAT score, admissibility is estimated from GPA only and capped at 'Target' tier."
    )
    lsat = st.number_input(
        "LSAT Score", min_value=120, max_value=180, value=160, disabled=no_lsat
    )
    gpa = st.number_input(
        "Undergraduate GPA", min_value=0.0, max_value=4.0, value=3.5, step=0.01
    )

    # ── Career Goals ──────────────────────────────────────────────────────
    st.subheader("Career Goals")

    goal = st.selectbox(
        "Primary Career Goal",
        [
            "BigLaw",
            "Federal Clerkship",
            "Government",
            "Public Interest",
            "Solo/Small Firm",
            "In-house",
            "Academia",
            "Unsure",
        ],
    )

    target_state = st.selectbox(
        "State where you want to practice",
        options=[""] + _STATES,
        format_func=lambda x: "Select a state…" if x == "" else x,
    )

    # ── Location & Residency ──────────────────────────────────────────────
    st.subheader("Location & Residency")

    instate_states = st.multiselect(
        "States where you qualify for in-state tuition",
        options=_STATES,
        help="Select any states where you are a legal resident. Used to calculate tuition costs.",
    )

    # ── Financial Preferences ─────────────────────────────────────────────
    st.subheader("Financial Preferences")

    income_bracket = st.radio(
        "Approximate annual household income",
        options=list(_INCOME_LABELS.keys()),
        format_func=lambda k: _INCOME_LABELS[k],
        horizontal=True,
        index=4,
        help="Used only to estimate need-based aid eligibility. Not stored.",
    )

    # ── Priority Sliders ─────────────────────────────────────────────────
    st.subheader("Priorities")
    st.caption("Adjust how much each factor influences your ranking.")

    sl1, sl2, sl3 = st.columns(3)

    with sl1:
        st.markdown("**Career Goal Weight**")
        st.caption("Low ← → High")
        career_slider = st.slider(
            "Career Goal Weight", min_value=0, max_value=10, value=5,
            label_visibility="collapsed",
        )

    with sl2:
        st.markdown("**Location Weight**")
        st.caption("Low ← → High")
        location_slider = st.slider(
            "Location Weight", min_value=0, max_value=10, value=5,
            label_visibility="collapsed",
        )

    with sl3:
        st.markdown("**Scholarship Priority**")
        st.caption("Not important ← → Critical")
        scholarship_slider = st.slider(
            "Scholarship Priority", min_value=0, max_value=10, value=5,
            label_visibility="collapsed",
        )

    # ── Results count ──────────────────────────────────────────────────────
    num_results = st.number_input(
        "Schools to show", min_value=1, max_value=len(schools), value=10, step=1,
    )

    submitted = st.form_submit_button("Find My Schools")

# ── Results ───────────────────────────────────────────────────────────────

if submitted:
    if not no_lsat and lsat < 120:
        st.warning("Enter your LSAT score or check 'I haven't taken the LSAT yet'.")
        st.stop()
    if gpa <= 0:
        st.warning("Enter your GPA.")
        st.stop()

    profile = {
        "lsat":            None if no_lsat else int(lsat),
        "gpa":             float(gpa),
        "goal":            goal,
        "target_state":    target_state,
        "instate_states":  instate_states,
        "income_bracket":  income_bracket,
        "scholarship":     scholarship_slider,
        "career_weight":   career_slider,
        "location_weight": location_slider,
    }

    lsat_display = "Not yet taken" if no_lsat else str(int(lsat))
    st.markdown(
        f"### LSAT: {lsat_display} &nbsp;|&nbsp; GPA: {gpa:.2f} &nbsp;|&nbsp; Goal: {goal}"
        + (f" &nbsp;|&nbsp; Target: {target_state}" if target_state else "")
    )
    st.divider()

    try:
        all_ranked = rank_schools(profile, schools, top_n=len(schools))
    except ValueError as e:
        st.error(f"Matching error: {e}")
        st.stop()

    if not all_ranked:
        st.warning("No schools matched. Try adjusting your preferences.")
        st.stop()

    # ── Tier filter (instant, no re-submit needed) ─────────────────────────
    tier_options = ["Safety", "Target", "Reach", "Hard Reach"]
    selected_tiers = st.multiselect(
        "Show tiers",
        options=tier_options,
        default=tier_options,
        help="Filter results to only show schools in the selected admissibility tiers.",
    )
    selected_tiers_lower = {t.lower() for t in selected_tiers}

    filtered = [s for s in all_ranked if s["admissibility_tier"] in selected_tiers_lower]

    if not filtered:
        st.warning("No schools match the selected tiers. Adjust the tier filter above.")
        st.stop()

    display = filtered[:int(num_results)]
    st.success(f"✓ Showing {len(display)} of {len(filtered)} matching schools — expand any for details")

    for idx, school in enumerate(display, 1):
        tier      = school["admissibility_tier"]
        tier_icon = _TIER_COLORS.get(tier, "⚪")
        bd        = school["financial_breakdown"]

        label = (
            f"**{idx}. {school['name']}**"
            f"  ·  {school['location']}"
            f"  ·  {tier_icon} {tier.title()}"
            f"  ·  #{school['usnwr_rank_2026']} USNWR"
            f"  ·  Fit: **{school['composite_score']:.0f}/100**"
        )

        with st.expander(label):

            # ── Score bars ────────────────────────────────────────────
            sc1, sc2, sc3, sc4, sc5 = st.columns(5)

            with sc1:
                v = school["admissibility_score"]
                st.metric("Admissibility", f"{v:.0f}/100")
                st.progress(v / 100)
            with sc2:
                v = school["career_fit_score"]
                st.metric("Career Fit", f"{v:.0f}/100")
                st.progress(v / 100)
            with sc3:
                v = school["location_fit_score"]
                st.metric("Location Fit", f"{v:.0f}/100")
                st.progress(v / 100)
            with sc4:
                v = school["scholarship_score"]
                st.metric("Scholarship", f"{v:.0f}/100")
                st.progress(v / 100)
            with sc5:
                v = school["financial_score"]
                st.metric("Financial", f"{v:.0f}/100")
                st.progress(v / 100)

            st.markdown(
                f"[Visit Website →]({school['website_url']}) &nbsp;·&nbsp; "
                f"Acceptance rate: {school['acceptance_rate']*100:.1f}%"
            )

            # ── Financial breakdown ────────────────────────────────────
            st.markdown("---")
            residency_label = "In-state" if bd["qualifies_instate"] else "Out-of-state"
            st.caption("**Standard repayment** — 10-yr at 7% (conservative baseline)")

            fc1, fc2, fc3, fc4 = st.columns(4)
            fc1.metric("Annual Tuition", f"${bd['annual_tuition_effective']:,}", delta=residency_label, delta_color="off")
            fc2.metric("Est. 3-yr Cost", f"${bd['gross_cost']:,}")
            fc3.metric("Est. Aid (3 yr)", f"${bd['expected_aid']:,}")
            fc4.metric("Net Debt", f"${bd['net_debt']:,}")

            fc5, fc6, fc7, _ = st.columns(4)
            fc5.metric("Starting Salary", f"${bd['starting_salary']:,}")
            fc6.metric("Monthly Payment", f"${bd['monthly_payment_estimate']:,}", help="Assumes 10-yr repayment at 7%")
            fc7.metric("Debt/Income Ratio", f"{bd['debt_to_income_ratio']:.1f}×")

            if bd.get("pslf_eligible"):
                st.markdown("---")
                st.caption(
                    "**PSLF / IDR path** — if you work 10 years for a qualifying government "
                    "or nonprofit employer, the remaining federal loan balance is forgiven."
                )
                pc1, pc2, pc3, pc4 = st.columns(4)
                pc1.metric("IDR Monthly (gross)", f"${bd['idr_monthly_gross']:,}", help="10% of income above 150% of the federal poverty line")
                pc2.metric("LRAP Reduction", f"−${bd['lrap_monthly']:,}", help="School loan repayment assistance covers this portion")
                pc3.metric("Your Monthly (net)", f"${bd['idr_monthly_net']:,}", help="What you actually pay per month after LRAP")
                pc4.metric("Forgiven at 10 yrs", f"${bd['pslf_forgiven']:,}", help="Remaining balance forgiven under PSLF after 120 qualifying payments")
                st.caption(
                    f"Total paid on IDR path: **\\${bd['pslf_total_paid']:,}** over 10 years "
                    f"vs **\\${bd['net_debt']:,}** on standard repayment. "
                    "Confirm PSLF eligibility at studentaid.gov before relying on this."
                )

            # ── Admissions stats ───────────────────────────────────────
            st.markdown("---")
            stat1, stat2, stat3, stat4, stat5 = st.columns(5)
            stat1.metric("LSAT Median", school["lsat_50"])
            stat2.metric("GPA Median",  f"{school['gpa_50']:.2f}")
            stat3.metric("BigLaw %",    f"{school['biglaw_pct']*100:.0f}%")
            stat4.metric("Clerkship %", f"{school['federal_clerkship_pct']*100:.0f}%")
            stat5.metric("Bar Pass %",  f"{school['bar_pass_rate_first_time']*100:.0f}%")
