/* app.jsx — product flow: Profile form -> Results table -> School detail. */

const { useState, useMemo } = React;

const BAR_COLORS = [
  "var(--target)", "#7c3aed", "var(--safety)", "var(--hard)", "#b45309", "var(--accent)",
];

const DEFAULT_FORM = {
  no_lsat: false,
  lsat: 160,
  gpa: 3.5,
  goal: "BigLaw",
  target_state: "",
  instate_states: [],
  income_bracket: "prefer_not",
  scholarship: 5,
  career_weight: 5,
  location_weight: 5,
};

/* ------------------------------------------------------------------ */
/* Small form helpers                                                 */
/* ------------------------------------------------------------------ */

function Slider({ label, value, onChange, hint }) {
  return (
    <div>
      <div className="slider-head">
        <span>{label}</span>
        <span className="val">{value}/10</span>
      </div>
      <input type="range" min="0" max="10" value={value}
        onChange={(e) => onChange(Number(e.target.value))} />
      {hint && <div className="mono">{hint}</div>}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Profile screen — facts (left) / weights (right)                    */
/* ------------------------------------------------------------------ */

function ProfileScreen({ form, setForm, onSubmit, loading }) {
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <div className="card profile-grid">
      {/* Left — who you are */}
      <section>
        <h3 style={{ marginBottom: 16 }}>Who you are</h3>

        <div className="checkbox-row" style={{ marginBottom: 14 }}>
          <input id="nolsat" type="checkbox" checked={form.no_lsat}
            onChange={(e) => set("no_lsat", e.target.checked)} />
          <label htmlFor="nolsat">I haven't taken the LSAT yet</label>
        </div>

        <div className="field-grid">
          <div className="field">
            <label>LSAT</label>
            <input type="number" min="120" max="180" value={form.lsat}
              disabled={form.no_lsat}
              onChange={(e) => set("lsat", Number(e.target.value))} />
          </div>
          <div className="field">
            <label>Undergrad GPA</label>
            <input type="number" min="0" max="4" step="0.01" value={form.gpa}
              onChange={(e) => set("gpa", Number(e.target.value))} />
          </div>
          <div className="field">
            <label>Career goal</label>
            <select value={form.goal} onChange={(e) => set("goal", e.target.value)}>
              {GOALS.map((g) => <option key={g} value={g}>{g}</option>)}
            </select>
          </div>
          <div className="field">
            <label>Practice state</label>
            <select value={form.target_state} onChange={(e) => set("target_state", e.target.value)}>
              <option value="">Any / undecided</option>
              {STATES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
        </div>

        <div className="field" style={{ marginTop: 16 }}>
          <label>In-state tuition eligibility</label>
          <select multiple size="5" value={form.instate_states}
            onChange={(e) => set("instate_states",
              Array.from(e.target.selectedOptions, (o) => o.value))}>
            {STATES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <span className="mono">Ctrl/Cmd-click to select multiple</span>
        </div>

        <div className="field" style={{ marginTop: 16 }}>
          <label>Household income</label>
          <div className="chip-group">
            {INCOME_OPTIONS.map(([k, lbl]) => (
              <button key={k} type="button"
                className={`chip ${form.income_bracket === k ? "active" : ""}`}
                onClick={() => set("income_bracket", k)}>{lbl}</button>
            ))}
          </div>
        </div>
      </section>

      {/* Right — what matters */}
      <section>
        <h3 style={{ marginBottom: 16 }}>What matters to you</h3>
        <div className="weights">
          <Slider label="Career fit" value={form.career_weight}
            onChange={(v) => set("career_weight", v)} />
          <Slider label="Location fit" value={form.location_weight}
            onChange={(v) => set("location_weight", v)} />
          <Slider label="Scholarship priority" value={form.scholarship}
            onChange={(v) => set("scholarship", v)} />
        </div>

        <div className="note" style={{ marginTop: 24 }}>
          Higher <strong>scholarship</strong> weight pushes high-aid and in-state schools up
          the list. Higher <strong>career</strong> weight favors schools with strong placement
          into your chosen path.
        </div>

        <div className="profile-actions">
          <button className="btn primary" onClick={onSubmit} disabled={loading}>
            {loading ? "Matching…" : "Find my schools →"}
          </button>
        </div>
      </section>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Results screen — sortable table with inline radars                 */
/* ------------------------------------------------------------------ */

const RESULT_COLS = [
  { k: "name",     label: "School",    sort: (s) => s.name },
  { k: "tier",     label: "Tier",      sort: (s) => s.admissibility_score },
  { k: "radar",    label: "Profile",   sort: null },
  { k: "rank",     label: "Rank",      sort: (s) => s.usnwr_rank_2026 },
  { k: "biglaw",   label: "BigLaw %",  sort: (s) => s.biglaw_pct },
  { k: "clerk",    label: "Clerk %",   sort: (s) => s.federal_clerkship_pct },
  { k: "bar",      label: "Bar %",     sort: (s) => s.bar_pass_rate_first_time },
  { k: "debt",     label: "Net debt",  sort: (s) => s.financial_breakdown.net_debt },
  { k: "comp",     label: "Composite", sort: (s) => s.composite_score },
];

function ResultsScreen({ data, onOpen, onBack }) {
  const [sortKey, setSortKey] = useState("comp");
  const [asc, setAsc] = useState(false);
  const [limit, setLimit] = useState(20);

  const sorted = useMemo(() => {
    const col = RESULT_COLS.find((c) => c.k === sortKey);
    if (!col || !col.sort) return data.schools;
    const arr = [...data.schools].sort((a, b) => {
      const av = col.sort(a), bv = col.sort(b);
      if (av < bv) return asc ? -1 : 1;
      if (av > bv) return asc ? 1 : -1;
      return 0;
    });
    return arr;
  }, [data.schools, sortKey, asc]);

  const onHeader = (col) => {
    if (!col.sort) return;
    if (sortKey === col.k) setAsc((v) => !v);
    else { setSortKey(col.k); setAsc(col.k === "name" || col.k === "rank"); }
  };

  const shown = sorted.slice(0, limit);

  return (
    <div className="card" style={{ padding: 22 }}>
      <div className="section-head">
        <div>
          <h3>Your matches</h3>
          <div className="mono">{data.schools.length} schools ranked · click any row for detail</div>
        </div>
        <div className="toolbar">
          <button className="btn sm ghost" onClick={onBack}>← Edit profile</button>
        </div>
      </div>

      <div style={{ overflowX: "auto" }}>
        <table className="results-table">
          <thead>
            <tr>
              {RESULT_COLS.map((c) => (
                <th key={c.k} onClick={() => onHeader(c)}>
                  {c.label}
                  {sortKey === c.k && <span className="arrow">{asc ? " ▲" : " ▼"}</span>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {shown.map((s, i) => (
              <tr key={s.id} onClick={() => onOpen(s)}>
                <td>
                  <div className="school-name">{i + 1}. {s.name}</div>
                  <div className="mono">{s.location}</div>
                </td>
                <td><TierPill tier={s.admissibility_tier} /></td>
                <td><Radar scores={s.radar} size={50} showLabels={false} showRings={false} /></td>
                <td className="num">#{s.usnwr_rank_2026}</td>
                <td className="num">{fmtPct(s.biglaw_pct)}</td>
                <td className="num">{fmtPct(s.federal_clerkship_pct)}</td>
                <td className="num">{fmtPct(s.bar_pass_rate_first_time)}</td>
                <td className="num">{fmtMoneyShort(s.financial_breakdown.net_debt)}</td>
                <td><span className="composite-badge">{Math.round(s.composite_score)}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {limit < sorted.length && (
        <div style={{ textAlign: "center", marginTop: 16 }}>
          <button className="btn ghost sm" onClick={() => setLimit(sorted.length)}>
            Show all {sorted.length} ↓
          </button>
        </div>
      )}

      <TransferPanel plan={data.transfer_plan} />
    </div>
  );
}

/* Transfer-up plan: where to enroll and aim to transfer into after 1L. */
function TransferPanel({ plan }) {
  if (!plan) return null;
  const { launchpads = [], targets = [] } = plan;
  if (!launchpads.length && !targets.length) return null;
  return (
    <div className="card" style={{ marginTop: 20, padding: 18, background: "var(--panel, #f7f7f9)" }}>
      <h4 style={{ margin: "0 0 4px" }}>Transfer-up path</h4>
      <div className="mono" style={{ marginBottom: 12 }}>
        Not competitive for your top tier yet? Enroll at a launchpad, excel in 1L, transfer up.
      </div>
      <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
        <div style={{ flex: "1 1 260px" }}>
          <div className="mono" style={{ fontWeight: 600, marginBottom: 6 }}>
            Launchpads — strongest 1L transfer-out mobility
          </div>
          {launchpads.map((s) => (
            <div key={s.id} className="transfer-row">
              {s.name} <span className="mono">· #{s.usnwr_rank_2026} · {Math.round(s.transfer_out_rate * 1000) / 10}% transfer out</span>
            </div>
          ))}
        </div>
        <div style={{ flex: "1 1 260px" }}>
          <div className="mono" style={{ fontWeight: 600, marginBottom: 6 }}>
            Targets — higher-ranked schools that admit the most transfers
          </div>
          {targets.map((s) => (
            <div key={s.id} className="transfer-row">
              {s.name} <span className="mono">· #{s.usnwr_rank_2026} · {s.transfers_in} transfers in</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Detail screen                                                      */
/* ------------------------------------------------------------------ */

const DISPLAY_YEARS = [1, 3, 5, 8, 10];

/* Amortize net_debt at 7% with a fixed monthly payment; snapshot key years. */
function buildSchedule(netDebt, monthlyPayment) {
  const r = 0.07 / 12;
  let balance = netDebt;
  const yearStart = {}, yearEnd = {}, paid = {};
  for (let year = 1; year <= 10; year++) {
    const start = balance;
    let yearPaid = 0;
    for (let m = 0; m < 12; m++) {
      const interest = balance * r;
      const pay = Math.min(monthlyPayment, balance + interest);
      balance = balance + interest - pay;
      yearPaid += pay;
      if (balance < 0) balance = 0;
    }
    yearStart[year] = start;
    yearEnd[year] = balance;
    paid[year] = yearPaid;
  }
  return DISPLAY_YEARS.map((y) => ({
    year: y, start: yearStart[y], paid: paid[y], end: yearEnd[y],
  }));
}

function ScheduleTable({ rows, forgivenLast }) {
  return (
    <table className="schedule-table">
      <thead>
        <tr><th>Year</th><th>Balance start</th><th>Paid</th><th>Balance end</th></tr>
      </thead>
      <tbody>
        {rows.map((row, idx) => (
          <tr key={row.year}>
            <td>{row.year}</td>
            <td>{fmtMoneyShort(row.start)}</td>
            <td>{fmtMoneyShort(row.paid)}</td>
            <td>{forgivenLast && idx === rows.length - 1 ? "forgiven" : fmtMoneyShort(row.end)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function DetailScreen({ school, profile, onBack }) {
  const [tab, setTab] = useState("standard");
  const bd = school.financial_breakdown;
  const composite = Math.round(school.composite_score);
  const userLsat = profile.lsat;

  const lsatPos = userLsat == null ? null :
    Math.max(0, Math.min(100,
      ((userLsat - school.lsat_25) / Math.max(school.lsat_75 - school.lsat_25, 1)) * 60 + 20));

  const stdRows = buildSchedule(bd.net_debt, bd.monthly_payment_estimate);
  const idrRows = bd.pslf_eligible ? buildSchedule(bd.net_debt, bd.idr_monthly_net) : null;

  const finTabs = [
    { k: "standard", label: "Standard 10-yr" },
    ...(bd.pslf_eligible ? [{ k: "pslf", label: "PSLF / IDR path" }] : []),
    { k: "schedule", label: "Year-by-year" },
  ];

  return (
    <div className="card" style={{ padding: 22 }}>
      <div className="detail-header">
        <div>
          <button className="btn sm ghost" onClick={onBack}>← Back to results</button>
          <h2 style={{ marginTop: 10 }}>{school.name}</h2>
          <div className="mono">
            {school.location} · USNWR #{school.usnwr_rank_2026} · acceptance {fmtPct(school.acceptance_rate)}
          </div>
        </div>
        <div className="head-actions">
          <div style={{ display: "flex", gap: 8 }}>
            <TierPill tier={school.admissibility_tier} />
            <span className="pill neutral">Composite {composite}</span>
          </div>
          <a href={school.website_url} target="_blank" rel="noreferrer" className="mono">Visit website ↗</a>
        </div>
      </div>

      {/* Hero */}
      <div className="hero">
        <div style={{ display: "flex", justifyContent: "center" }}>
          <Radar scores={school.radar} size={280} />
        </div>
        <div>
          <div className="stat-grid">
            <Stat label="LSAT 50" value={school.lsat_50} sub={`25/75 ${school.lsat_25}·${school.lsat_75}`} />
            <Stat label="GPA 50" value={school.gpa_50.toFixed(2)} sub={`25/75 ${school.gpa_25.toFixed(2)}·${school.gpa_75.toFixed(2)}`} />
            <Stat label="BigLaw" value={fmtPct(school.biglaw_pct)} />
            <Stat label="Clerk" value={fmtPct(school.federal_clerkship_pct)} />
            <Stat label="Bar" value={fmtPct(school.bar_pass_rate_first_time)} />
          </div>
          <div className="score-bars">
            {SCORE_NAMES_LONG.map((n, i) => (
              <Bar key={n} value={school.radar[i]} label={n} color={BAR_COLORS[i]} />
            ))}
          </div>
        </div>
      </div>

      {/* Story columns */}
      <div className="story-cols">
        <div className="box story-col">
          <h4>Will you get in?</h4>
          <div className="mono">your LSAT vs school 25/50/75</div>
          <div className="lsat-axis">
            <div className="track" />
            <div className="tick" style={{ left: "20%" }}>{school.lsat_25}</div>
            <div className="tick" style={{ left: "50%" }}>{school.lsat_50}</div>
            <div className="tick" style={{ left: "80%" }}>{school.lsat_75}</div>
            {lsatPos != null && (
              <div className="you" style={{ left: `${lsatPos}%` }}>
                <div className="dot" />
                <div className="lbl">you {userLsat}</div>
              </div>
            )}
          </div>
          <Bar value={school.radar[0]} label="Admissibility" color={BAR_COLORS[0]} />
          <div className="mono">tier: {TIER_LABEL[school.admissibility_tier]} · protects both medians</div>
        </div>

        <div className="box story-col">
          <h4>Will you get the job?</h4>
          <div style={{ fontSize: 14 }}>Goal: <strong>{profile.goal}</strong></div>
          <Bar value={school.biglaw_pct * 100} label="BigLaw" color={BAR_COLORS[0]} />
          <Bar value={school.federal_clerkship_pct * 100} label="Fed. Clerkship" color={BAR_COLORS[1]} />
          <Bar value={school.government_pct * 100} label="Government" color={BAR_COLORS[2]} />
          <Bar value={school.public_interest_pct * 100} label="Public Interest" color={BAR_COLORS[3]} />
          {school.target_states && school.target_states.length > 0 && (
            <div className="mono">feeder markets: {school.target_states.join(" · ")}</div>
          )}
        </div>

        <div className="box story-col">
          <h4>Can you afford it?</h4>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <div>
              <div className="mono">net debt</div>
              <div className="big-num">{fmtMoneyShort(bd.net_debt)}</div>
            </div>
            <div>
              <div className="mono">starting</div>
              <div className="big-num">{fmtMoneyShort(bd.starting_salary)}</div>
            </div>
          </div>
          <Bar value={school.radar[5]} label="Financial" color={BAR_COLORS[5]} />
          <div className="mono">
            debt-to-income {bd.debt_to_income_ratio}× ·
            {bd.qualifies_instate ? " in-state tuition" : " out-of-state tuition"}
          </div>
        </div>
      </div>

      {/* Financial detail tabs */}
      <div className="fin-detail">
        <div className="section-head" style={{ marginBottom: 8 }}>
          <h3>Financial detail</h3>
        </div>
        <div className="tabs">
          {finTabs.map((tb) => (
            <button key={tb.k} className={`tab ${tab === tb.k ? "active" : ""}`}
              onClick={() => setTab(tb.k)}>{tb.label}</button>
          ))}
        </div>

        {tab === "standard" && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, alignItems: "start" }}>
            <div className="box" style={{ padding: 14 }}>
              <div className="label" style={{ marginBottom: 8 }}>Standard repayment — 10-yr @ 7%</div>
              <div className="kv">
                <span className="k">Annual tuition (effective)</span><span className="v">{fmtMoney(bd.annual_tuition_effective)}</span>
                <span className="k">Est. 3-yr cost</span><span className="v">{fmtMoney(bd.gross_cost)}</span>
                <span className="k">Est. aid (3-yr)</span><span className="v">−{fmtMoney(bd.expected_aid)}</span>
                <span className="k">Net debt</span><span className="v">{fmtMoney(bd.net_debt)}</span>
                <span className="k">Starting salary</span><span className="v">{fmtMoney(bd.starting_salary)}</span>
                <span className="k">Monthly payment</span><span className="v">{fmtMoney(bd.monthly_payment_estimate)}</span>
                <span className="k">Debt / income</span><span className="v">{bd.debt_to_income_ratio}×</span>
              </div>
            </div>
            <div className="note">
              Standard federal repayment — what you pay if you take a private-sector job and pay
              the balance down over 10 years.
            </div>
          </div>
        )}

        {tab === "pslf" && bd.pslf_eligible && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, alignItems: "start" }}>
            <div className="box" style={{ padding: 14 }}>
              <div className="label" style={{ marginBottom: 8 }}>PSLF / IDR path</div>
              <div className="kv">
                <span className="k">IDR monthly (gross)</span><span className="v">{fmtMoney(bd.idr_monthly_gross)}</span>
                <span className="k">LRAP reduction</span><span className="v">−{fmtMoney(bd.lrap_monthly)}</span>
                <span className="k">Your monthly (net)</span><span className="v">{fmtMoney(bd.idr_monthly_net)}</span>
                <span className="k">Total paid (10 yr)</span><span className="v">{fmtMoney(bd.pslf_total_paid)}</span>
                <span className="k">Forgiven at year 10</span><span className="v">{fmtMoney(bd.pslf_forgiven)}</span>
              </div>
            </div>
            <div className="note">
              Only if you work for a government or 501(c)(3) employer. After 120 qualifying
              payments the remaining balance is forgiven, tax-free. Confirm eligibility at
              studentaid.gov before relying on this.
            </div>
          </div>
        )}

        {tab === "schedule" && (
          <div style={{ display: "grid", gridTemplateColumns: idrRows ? "1fr 1fr" : "1fr", gap: 24, alignItems: "start" }}>
            <div>
              <div className="label" style={{ marginBottom: 8 }}>Standard 10-yr schedule</div>
              <ScheduleTable rows={stdRows} forgivenLast={false} />
            </div>
            {idrRows && (
              <div>
                <div className="label" style={{ marginBottom: 8 }}>PSLF / IDR schedule</div>
                <ScheduleTable rows={idrRows} forgivenLast={true} />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function Stat({ label, value, sub }) {
  return (
    <div className="stat">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* App shell                                                          */
/* ------------------------------------------------------------------ */

function App() {
  const [view, setView] = useState("profile");
  const [form, setForm] = useState(DEFAULT_FORM);
  const [data, setData] = useState(null);
  const [opened, setOpened] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const submit = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/match", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error || "Matching failed.");
      setData(json);
      setView("results");
      window.scrollTo({ top: 0 });
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const openSchool = (s) => { setOpened(s); setView("detail"); window.scrollTo({ top: 0 }); };

  return (
    <div className="app">
      <div className="topbar">
        <div>
          <h1>Law School Matcher</h1>
          <div className="subtitle">Ranked by fit across admissibility, career, location, scholarship & cost</div>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {loading && (
        <div className="center-msg"><div className="spinner" />Matching schools…</div>
      )}

      {!loading && view === "profile" && (
        <ProfileScreen form={form} setForm={setForm} onSubmit={submit} loading={loading} />
      )}
      {!loading && view === "results" && data && (
        <ResultsScreen data={data} onOpen={openSchool} onBack={() => setView("profile")} />
      )}
      {!loading && view === "detail" && opened && (
        <DetailScreen school={opened} profile={data.profile} onBack={() => setView("results")} />
      )}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
