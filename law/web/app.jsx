/* app.jsx — product flow: Profile form -> Results table -> School detail. */

const { useState, useMemo, useEffect } = React;

const BAR_COLORS = [
  "var(--target)", "#7c3aed", "var(--safety)", "var(--hard)", "#b45309", "var(--accent)",
];

const DEFAULT_FORM = {
  no_lsat: false,
  lsat: 160,
  gpa: 3.5,
  goals_weighted: [{ goal: "BigLaw", weight: 1 }],
  target_state: "",
  target_states_weighted: [{ state: "", weight: 100 }],
  instate_states: [""],
  income_bracket: "prefer_not",
  scholarship: 5,
  career_weight: 5,
  location_weight: 5,
  wants_transfer: false,
};

/* ------------------------------------------------------------------ */
/* Small form helpers                                                 */
/* ------------------------------------------------------------------ */

function Slider({ label, value, onChange, hint, help }) {
  return (
    <div>
      <div className="slider-head">
        <span>{label}{help && <InfoTip text={help} label={`About ${label}`} />}</span>
        <span className="val">{value}/10</span>
      </div>
      <input type="range" min="0" max="10" value={value}
        onChange={(e) => onChange(Number(e.target.value))} />
      {hint && <div className="mono">{hint}</div>}
    </div>
  );
}

/* Multi-state practice preference with relative weights (e.g. CA/NY = 70/30).
   Adding a state resets all rows to an even split (1 → 100, 2 → 50/50, 3 → 33…);
   the user can then nudge individual weights. */
function evenSplit(n) {
  return Array.from({ length: n }, () => Math.round(100 / n));
}
function PracticeStates({ value, onChange }) {
  const addRow = () => {
    const n = value.length + 1;
    const weights = evenSplit(n);
    onChange([...value, { state: "", weight: 0 }].map((r, i) => ({ ...r, weight: weights[i] })));
  };
  const update = (i, patch) =>
    onChange(value.map((r, j) => (j === i ? { ...r, ...patch } : r)));
  const remove = (i) => onChange(value.filter((_, j) => j !== i));

  return (
    <div className="field" style={{ marginTop: 16 }}>
      <label>Practice state(s) &amp; weight</label>
      {value.map((row, i) => (
        <div className="weighted-row" key={i}>
          <select value={row.state} onChange={(e) => update(i, { state: e.target.value })}>
            <option value="">Select state</option>
            {STATES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <input type="number" min="0" value={row.weight}
            onChange={(e) => update(i, { weight: Number(e.target.value) })} />
          <button type="button" className="btn xs ghost" onClick={() => remove(i)}
            aria-label="Remove state">×</button>
        </div>
      ))}
      <div>
        <button type="button" className="btn sm ghost" onClick={addRow}>+ Add state</button>
      </div>
    </div>
  );
}

/* Multi-goal career preference (select one or more paths, equal weight). */
function CareerGoals({ value, onChange }) {
  const equalize = (goals) => goals.map((g) => ({ goal: g.goal, weight: 1 }));
  const addRow = () => {
    const used = value.map((r) => r.goal);
    const next = GOALS.find((g) => !used.includes(g)) || GOALS[0];
    onChange(equalize([...value, { goal: next }]));
  };
  const update = (i, goal) =>
    onChange(equalize(value.map((r, j) => (j === i ? { goal } : r))));
  const remove = (i) => onChange(equalize(value.filter((_, j) => j !== i)));

  return (
    <div className="field" style={{ marginTop: 16 }}>
      <label>Career goal(s)</label>
      {value.map((row, i) => (
        <div className="weighted-row" key={i}>
          <select value={row.goal} onChange={(e) => update(i, e.target.value)}>
            {GOALS.map((g) => <option key={g} value={g}>{g}</option>)}
          </select>
          {value.length > 1 && (
            <button type="button" className="btn xs ghost" onClick={() => remove(i)}
              aria-label="Remove goal">×</button>
          )}
        </div>
      ))}
      {value.length < GOALS.length && (
        <div><button type="button" className="btn sm ghost" onClick={addRow}>+ Add goal</button></div>
      )}
    </div>
  );
}

/* Add/remove list of states (no weights) — used for in-state tuition eligibility. */
function StateList({ value, onChange, addLabel }) {
  const add = () => onChange([...value, ""]);
  const update = (i, v) => onChange(value.map((s, j) => (j === i ? v : s)));
  const remove = (i) => onChange(value.filter((_, j) => j !== i));
  return (
    <div>
      {value.map((st, i) => (
        <div className="weighted-row" key={i}>
          <select value={st} onChange={(e) => update(i, e.target.value)}>
            <option value="">Select state</option>
            {STATES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <button type="button" className="btn xs ghost" onClick={() => remove(i)}
            aria-label="Remove state">×</button>
        </div>
      ))}
      <div><button type="button" className="btn sm ghost" onClick={add}>{addLabel}</button></div>
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

        <div className="field-grid">
          <div className="field">
            <label>LSAT</label>
            <input type="number" min="120" max="180" value={form.lsat}
              disabled={form.no_lsat} placeholder="120–180"
              onChange={(e) => set("lsat", e.target.value)} />
            <div className="checkbox-row tiny">
              <input id="nolsat" type="checkbox" checked={form.no_lsat}
                onChange={(e) => set("no_lsat", e.target.checked)} />
              <label htmlFor="nolsat">I haven't taken the LSAT yet</label>
            </div>
          </div>
          <div className="field">
            <label>Undergrad GPA</label>
            <input type="number" min="0" max="4" step="0.01" value={form.gpa}
              placeholder="0.00–4.00"
              onChange={(e) => set("gpa", e.target.value)} />
          </div>
        </div>

        <CareerGoals value={form.goals_weighted}
          onChange={(v) => set("goals_weighted", v)} />

        <div className="field" style={{ marginTop: 16 }}>
          <label>In-state tuition eligibility</label>
          <StateList value={form.instate_states}
            onChange={(v) => set("instate_states", v)}
            addLabel="+ Add state" />
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

        <PracticeStates value={form.target_states_weighted}
          onChange={(v) => set("target_states_weighted", v)} />
      </section>

      {/* Right — what matters */}
      <section>
        <h3 style={{ marginBottom: 16 }}>What matters to you</h3>
        <div className="weights">
          <Slider label="Career fit" value={form.career_weight}
            onChange={(v) => set("career_weight", v)} />
          <Slider label="Location fit" value={form.location_weight}
            onChange={(v) => set("location_weight", v)} />
          <Slider label="Cost sensitivity" value={form.scholarship}
            onChange={(v) => set("scholarship", v)}
            help={"Higher cost sensitivity gives real net debt (tuition + living − aid) a " +
                  "larger floor in the ranking and pushes high-aid / in-state schools up. " +
                  "Lower it if prestige or career outcomes matter more to you than price."} />
        </div>

        <div className="checkbox-row" style={{ marginTop: 24 }}>
          <input id="transfer-interest" type="checkbox" checked={form.wants_transfer}
            onChange={(e) => set("wants_transfer", e.target.checked)} />
          <label htmlFor="transfer-interest">
            I'd consider transferring to a higher-ranked school after 1L
          </label>
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

/* Career-outcome columns, keyed by metric. The two shown depend on the goal. */
const CAREER_COLS = {
  biglaw: { k: "biglaw", label: "BigLaw %", get: (s) => s.biglaw_pct },
  clerk:  { k: "clerk",  label: "Clerk %",  get: (s) => s.federal_clerkship_pct },
  gov:    { k: "gov",    label: "Gov %",    get: (s) => s.government_pct },
  pi:     { k: "pi",     label: "Pub. Int %", get: (s) => s.public_interest_pct },
  solo:   { k: "solo",   label: "Solo/Sm %", get: (s) => s.solo_small_firm_pct },
};

/* Which two career columns to surface for each goal (first = primary). */
const GOAL_CAREER_COLS = {
  "biglaw":            ["biglaw", "clerk"],
  "in-house":          ["biglaw", "gov"],
  "federal clerkship": ["clerk", "biglaw"],
  "government":        ["gov", "pi"],
  "public interest":   ["pi", "gov"],
  "solo/small firm":   ["solo", "biglaw"],
  "academia":          ["clerk", "biglaw"],
  "unsure":            ["biglaw", "pi"],
};

function matchGoalKey(goal) {
  const key = (goal || "").toLowerCase();
  return Object.keys(GOAL_CAREER_COLS).find((g) => key.includes(g)) || "unsure";
}

/* Career columns for the profile: one weighted goal → its two metrics; several
   goals → the primary metric of each (deduped, capped at 3) so the table shows
   exactly the career paths the applicant selected. */
function careerColsForProfile(profile) {
  const weighted = (profile.goals_weighted && profile.goals_weighted.length)
    ? [...profile.goals_weighted].sort((a, b) => b.weight - a.weight)
    : [{ goal: profile.goal, weight: 1 }];
  if (weighted.length <= 1) {
    return GOAL_CAREER_COLS[matchGoalKey(weighted[0].goal)].map((m) => CAREER_COLS[m]);
  }
  const metrics = [];
  for (const g of weighted) {
    const m = GOAL_CAREER_COLS[matchGoalKey(g.goal)][0];
    if (!metrics.includes(m)) metrics.push(m);
  }
  return metrics.slice(0, 3).map((m) => CAREER_COLS[m]);
}

/* Build the full column set; the career columns track the applicant's goal(s). */
function buildResultCols(profile) {
  const career = careerColsForProfile(profile);
  return [
    { k: "name", label: "School", sort: (s) => s.name,
      render: (s, i) => (
        <td><div className="school-name">{i + 1}. {s.name}</div>
          <div className="mono">{s.location}</div></td>) },
    { k: "tier", label: "Tier", sort: (s) => s.admissibility_score,
      render: (s) => <td><TierPill tier={s.admissibility_tier} /></td> },
    { k: "rank", label: "Rank", sort: (s) => s.usnwr_rank_2026,
      render: (s) => <td className="num">{fmtRank(s.usnwr_rank_2026)}</td> },
    ...career.map((c) => ({
      k: c.k, label: c.label, sort: c.get,
      render: (s) => <td className="num">{fmtPct(c.get(s))}</td>,
    })),
    { k: "bar", label: "Bar %", sort: (s) => s.bar_pass_rate_first_time,
      render: (s) => <td className="num">{fmtPct(s.bar_pass_rate_first_time)}</td> },
    { k: "debt", label: "Cost after aid", sort: (s) => s.financial_breakdown.net_debt,
      render: (s) => <td className="num">{fmtMoneyShort(s.financial_breakdown.net_debt)}</td> },
    { k: "comp", label: "Score", sort: (s) => s.composite_score,
      render: (s) => <td><span className="composite-badge">{Math.round(s.composite_score)}</span></td> },
  ];
}

const TIER_ORDER = ["safety", "target", "reach", "hard reach"];

/* Right-aligned filter icon that opens a dropdown of tier checkboxes (multi-select).
   None checked = show all; checking tiers filters down to them. */
function FilterMenu({ activeTiers, setActiveTiers, tierCounts }) {
  const [open, setOpen] = useState(false);
  const toggle = (t) =>
    setActiveTiers((ts) => ts.includes(t) ? ts.filter((x) => x !== t) : [...ts, t]);
  const filtering = activeTiers.length > 0;
  return (
    <div className="filter-menu">
      <button className={`btn sm icon-btn ${filtering ? "primary" : "ghost"}`}
        aria-label="Filter by tier" aria-expanded={open} onClick={() => setOpen((v) => !v)}>
        <span aria-hidden="true">▼</span> Filter{filtering ? ` · ${activeTiers.length}` : ""}
      </button>
      {open && (
        <div className="filter-dropdown" role="menu">
          {TIER_ORDER.map((t) => (
            <button key={t} className={`filter-opt ${activeTiers.includes(t) ? "active" : ""}`}
              onClick={() => toggle(t)}>
              <span><input type="checkbox" readOnly checked={activeTiers.includes(t)} /> {TIER_LABEL[t]}</span>
              <span className="chip-count">{tierCounts[t] || 0}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/* Share-link profile encoding: UTF-8-safe base64 of the form JSON. */
function encodeShare(form) {
  return btoa(unescape(encodeURIComponent(JSON.stringify(form))));
}
function decodeShare(hash) {
  return JSON.parse(decodeURIComponent(escape(atob(hash))));
}

/* CSV export of the current (filtered + sorted) results list. */
function exportCsv(rows) {
  const esc = (v) => {
    const s = String(v == null ? "" : v);
    return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  };
  const head = ["#", "School", "USNWR rank", "Tier", "Score",
    "LSAT 25/50/75", "GPA 25/50/75", "Acceptance", "BigLaw %", "Fed clerk %",
    "Gov %", "Pub int %", "Bar first-time", "Cost after aid", "Monthly payment",
    "Starting salary", "Tuition basis"];
  const lines = [head, ...rows.map((s, i) => [
    i + 1, s.name, fmtRank(s.usnwr_rank_2026), s.admissibility_tier, s.composite_score,
    `${s.lsat_25}/${s.lsat_50}/${s.lsat_75}`,
    `${s.gpa_25.toFixed(2)}/${s.gpa_50.toFixed(2)}/${s.gpa_75.toFixed(2)}`,
    fmtPct(s.acceptance_rate), fmtPct(s.biglaw_pct), fmtPct(s.federal_clerkship_pct),
    fmtPct(s.government_pct), fmtPct(s.public_interest_pct),
    fmtPct(s.bar_pass_rate_first_time),
    s.financial_breakdown.net_debt, s.financial_breakdown.monthly_payment_estimate,
    s.financial_breakdown.starting_salary,
    s.financial_breakdown.qualifies_instate ? "in-state" : "out-of-state",
  ])];
  const csv = "﻿" + lines.map((r) => r.map(esc).join(",")).join("\r\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "law-school-matches.csv";
  a.click();
  URL.revokeObjectURL(a.href);
}

/* Retake what-if: re-rank the same profile at LSAT +N and show which schools
   cross a full admit tier. Hidden for no-LSAT profiles. */
const TIER_ORDER = ["hard reach", "reach", "target", "safety"];

function WhatIfPanel({ data }) {
  const lsat = data.profile.lsat;
  const [delta, setDelta] = useState(0);
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  if (lsat == null) return null;

  const run = async (d) => {
    setDelta(d);
    if (!d) { setRes(null); return; }
    setBusy(true);
    try {
      const r = await fetch("/api/match", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...data.profile, lsat: Math.min(lsat + d, 180) }),
      });
      const j = await r.json();
      if (r.ok) setRes({ delta: d, schools: j.schools });
    } finally { setBusy(false); }
  };

  let ups = null;
  if (res && res.delta === delta && delta) {
    const baseTier = {};
    data.schools.forEach((s) => { baseTier[s.id] = s.admissibility_tier; });
    ups = res.schools
      .map((s) => ({ s, from: baseTier[s.id] }))
      .filter(({ s, from }) =>
        from && TIER_ORDER.indexOf(s.admissibility_tier) > TIER_ORDER.indexOf(from));
  }

  return (
    <div className="box" style={{ marginBottom: 16 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
        <strong>Retake what-if</strong>
        <span className="mono">your LSAT {lsat} →</span>
        {[0, 1, 3, 5].map((d) => (
          <button key={d} className={`btn sm ${delta === d ? "primary" : "ghost"}`}
            onClick={() => run(d)}>
            {d === 0 ? "off" : `+${d}`}
          </button>
        ))}
        {busy && <span className="mono">computing…</span>}
      </div>
      {ups && (
        <div style={{ marginTop: 10 }}>
          {ups.length === 0 ? (
            <div className="mono">no admit-tier changes at LSAT {Math.min(lsat + delta, 180)} — the gains show up in scores, not tiers</div>
          ) : (
            <React.Fragment>
              <div className="mono">{ups.length} school(s) improve a full admit tier at LSAT {Math.min(lsat + delta, 180)}:</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 6 }}>
                {ups.slice(0, 12).map(({ s, from }) => (
                  <span key={s.id} className="metric-badge">
                    {s.name}: {TIER_LABEL[from]} → {TIER_LABEL[s.admissibility_tier]}
                  </span>
                ))}
                {ups.length > 12 && <span className="mono">+{ups.length - 12} more</span>}
              </div>
            </React.Fragment>
          )}
        </div>
      )}
    </div>
  );
}

function ResultsScreen({ data, onOpen, onBack, selectedIds, onToggleSelect, onClearSelect, onCompare, onOpenSchool }) {
  const [sortKey, setSortKey] = useState("comp");
  const [asc, setAsc] = useState(false);
  const [limit, setLimit] = useState(20);
  const [activeTiers, setActiveTiers] = useState([]);   // empty = show all
  const wantsTransfer = !!data.profile.wants_transfer;
  const [tab, setTab] = useState("matches");
  const [copied, setCopied] = useState(false);

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch (e) { /* clipboard unavailable (http) — ignore */ }
  };

  const cols = useMemo(() => buildResultCols(data.profile), [data.profile]);

  const tierCounts = useMemo(() => {
    const c = {};
    for (const s of data.schools) c[s.admissibility_tier] = (c[s.admissibility_tier] || 0) + 1;
    return c;
  }, [data.schools]);

  const sorted = useMemo(() => {
    const col = cols.find((c) => c.k === sortKey);
    const filtered = activeTiers.length === 0
      ? data.schools
      : data.schools.filter((s) => activeTiers.includes(s.admissibility_tier));
    if (!col || !col.sort) return filtered;
    return [...filtered].sort((a, b) => {
      const av = col.sort(a), bv = col.sort(b);
      if (av < bv) return asc ? -1 : 1;
      if (av > bv) return asc ? 1 : -1;
      return 0;
    });
  }, [data.schools, sortKey, asc, activeTiers, cols]);

  const onHeader = (col) => {
    if (!col.sort) return;
    if (sortKey === col.k) setAsc((v) => !v);
    else { setSortKey(col.k); setAsc(col.k === "name" || col.k === "rank"); }
  };

  const shown = sorted.slice(0, limit);

  return (
    <div className="card" style={{ padding: 22 }}>
      <button className="btn sm ghost back-link" onClick={onBack}>← Edit profile</button>
      <div className="section-head">
        <div>
          <h3>Your results</h3>
          <div className="mono">click on a school for more details</div>
        </div>
        <div className="toolbar">
          <label className="list-len mono">Show
            <select value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
              <option value={9999}>All</option>
            </select>
          </label>
          <FilterMenu activeTiers={activeTiers} setActiveTiers={setActiveTiers} tierCounts={tierCounts} />
          <button className="btn sm ghost" onClick={() => exportCsv(sorted)}>Export CSV</button>
          <button className="btn sm ghost" onClick={copyLink}>{copied ? "Copied ✓" : "Copy share link"}</button>
        </div>
      </div>

      {wantsTransfer && (
        <div className="tabs" style={{ marginBottom: 16 }}>
          <button className={`tab ${tab === "matches" ? "active" : ""}`}
            onClick={() => setTab("matches")}>Matches</button>
          <button className={`tab ${tab === "transfer" ? "active" : ""}`}
            onClick={() => setTab("transfer")}>Transfers</button>
        </div>
      )}

      {wantsTransfer && tab === "transfer" ? (
        <TransferContent plan={data.transfer_plan} onOpenSchool={onOpenSchool} />
      ) : (
      <React.Fragment>

      <WhatIfPanel data={data} />

      {selectedIds.length > 0 && (
        <div className="compare-bar">
          <span className="mono">{selectedIds.length} selected</span>
          <button className="btn sm primary" disabled={selectedIds.length < 2} onClick={onCompare}>
            Compare side by side →
          </button>
          <button className="btn sm ghost" onClick={onClearSelect}>Clear</button>
        </div>
      )}

      <div style={{ overflowX: "auto" }}>
        <table className="results-table">
          <thead>
            <tr>
              <th className="cmp-col"></th>
              {cols.map((c) => (
                <th key={c.k} onClick={() => onHeader(c)}>
                  {c.label}
                  {sortKey === c.k && <span className="arrow">{asc ? " ▲" : " ▼"}</span>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {shown.map((s, i) => (
              <tr key={s.id} className={selectedIds.includes(s.id) ? "row-selected" : ""}
                onClick={() => onOpen(s)}>
                <td className="cmp-col" onClick={(e) => { e.stopPropagation(); onToggleSelect(s.id); }}>
                  <input type="checkbox" checked={selectedIds.includes(s.id)} readOnly
                    aria-label={`Select ${s.name} to compare`} />
                </td>
                {cols.map((c) => (
                  <React.Fragment key={c.k}>{c.render(s, i)}</React.Fragment>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {shown.length === 0 && (
        <div className="center-msg">No schools match the selected tiers.</div>
      )}
      {shown.length > 0 && (
        <div className="mono" style={{ marginTop: 12 }}>
          Showing {shown.length} of {sorted.length} schools
          {activeTiers.length > 0
            ? ` (${activeTiers.map((t) => TIER_LABEL[t]).join(", ")})` : ""}.
        </div>
      )}

      </React.Fragment>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Transfer-up body — rendered as the results "Transfer-up" tab        */
/* (only when the applicant opted in on the profile screen)            */
/* ------------------------------------------------------------------ */

function TransferContent({ plan, onOpenSchool }) {
  const { launchpads = [], targets = [] } = plan || {};
  const empty = !launchpads.length && !targets.length;

  return (
    <div className="transfer-page">
      <div className="note" style={{ marginBottom: 20 }}>
        A strong 1L can transfer up after first year. <strong>Launchpads</strong> are your best
        realistic matches now — enroll and excel. <strong>Targets</strong> are schools that are a
        reach today but admit transfers, ranked by how well they fit you. Click any school for detail.
      </div>

      {empty ? (
        <div className="center-msg">
          No transfer-up pipeline for this profile — your realistic admits already sit near the top,
          or the dataset lacks transfer data for eligible schools.
        </div>
      ) : (
        <div className="pipeline">
          <div className="box stage-card">
            <h4>① Launchpads — enroll &amp; excel</h4>
            <div className="mono" style={{ marginBottom: 8 }}>your best realistic matches</div>
            {launchpads.length === 0 && <div className="mono">no realistic admits found</div>}
            {launchpads.map((s) => (
              <div key={s.id} className="school-row" onClick={() => onOpenSchool(s.id)}
                style={{ cursor: "pointer" }}>
                <span><strong>{s.name}</strong> <span className="mono">{fmtRank(s.usnwr_rank_2026)} · {TIER_LABEL[s.admissibility_tier]}</span></span>
                <span className="metric-badge">Score {Math.round(s.composite_score)}</span>
              </div>
            ))}
          </div>

          <div className="box stage-card">
            <h4>② Targets — transfer in after 1L</h4>
            <div className="mono" style={{ marginBottom: 8 }}>a reach now, and they take transfers</div>
            {targets.length === 0 && (
              <div className="mono">no reach schools that admit transfers for this profile</div>
            )}
            {targets.map((s) => (
              <div key={s.id} className="school-row" onClick={() => onOpenSchool(s.id)}
                style={{ cursor: "pointer" }}>
                <span><strong>{s.name}</strong> <span className="mono">{fmtRank(s.usnwr_rank_2026)} · Score {Math.round(s.composite_score)}</span></span>
                <span className="metric-badge">{s.transfers_in} transfers/yr</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Compare screen — side-by-side, personalized vs raw stats           */
/* ------------------------------------------------------------------ */

/* Personalized rows: fit scores computed against the user's profile. */
const CMP_PERSONALIZED = [
  { label: "Admit tier", better: null,
    cell: (s) => ({ node: <TierPill tier={s.admissibility_tier} />, num: null }) },
  { label: "Score", better: "high",
    cell: (s) => ({ num: s.composite_score, node: Math.round(s.composite_score) }) },
  { label: "Admissibility fit", better: "high",
    cell: (s) => ({ num: s.radar[0], node: s.radar[0] }) },
  { label: "Prestige", better: "high",
    cell: (s) => ({ num: s.radar[1], node: s.radar[1] }) },
  { label: "Career fit", better: "high",
    cell: (s) => ({ num: s.radar[2], node: s.radar[2] }) },
  { label: "Location fit", better: "high",
    cell: (s) => ({ num: s.radar[3], node: s.radar[3] }) },
  { label: "Scholarship", better: "high",
    cell: (s) => ({ num: s.radar[4], node: s.radar[4] }) },
  { label: "Financial", better: "high",
    cell: (s) => ({ num: s.radar[5], node: s.radar[5] }) },
  { label: "Est. cost after aid", better: "low",
    cell: (s) => ({ num: s.financial_breakdown.net_debt, node: fmtMoney(s.financial_breakdown.net_debt) }) },
  { label: "Monthly payment", better: "low",
    cell: (s) => ({ num: s.financial_breakdown.monthly_payment_estimate, node: fmtMoney(s.financial_breakdown.monthly_payment_estimate) }) },
  { label: "Debt / income", better: "low",
    cell: (s) => ({ num: s.financial_breakdown.debt_to_income_ratio, node: s.financial_breakdown.debt_to_income_ratio + "×" }) },
  { label: "Tuition basis", better: null,
    cell: (s) => ({ num: null, node: s.financial_breakdown.qualifies_instate ? "in-state" : "out-of-state" }) },
];

/* Raw rows: the school's own numbers, independent of the user. */
const CMP_RAW = [
  { label: "USNWR rank", better: "low",
    cell: (s) => ({ num: s.usnwr_rank_2026, node: fmtRank(s.usnwr_rank_2026) }) },
  { label: "Acceptance rate", better: "low",
    cell: (s) => ({ num: s.acceptance_rate, node: fmtPct(s.acceptance_rate) }) },
  { label: "LSAT 25/50/75", better: null,
    cell: (s) => ({ num: null, node: `${s.lsat_25} · ${s.lsat_50} · ${s.lsat_75}` }) },
  { label: "GPA 25/50/75", better: null,
    cell: (s) => ({ num: null, node: `${s.gpa_25.toFixed(2)} · ${s.gpa_50.toFixed(2)} · ${s.gpa_75.toFixed(2)}` }) },
  { label: "BigLaw %", better: "high",
    cell: (s) => ({ num: s.biglaw_pct, node: fmtPct(s.biglaw_pct) }) },
  { label: "Fed. clerkship %", better: "high",
    cell: (s) => ({ num: s.federal_clerkship_pct, node: fmtPct(s.federal_clerkship_pct) }) },
  { label: "Government %", better: "high",
    cell: (s) => ({ num: s.government_pct, node: fmtPct(s.government_pct) }) },
  { label: "Public interest %", better: "high",
    cell: (s) => ({ num: s.public_interest_pct, node: fmtPct(s.public_interest_pct) }) },
  { label: "Bar pass (first-time)", better: "high",
    cell: (s) => ({ num: s.bar_pass_rate_first_time, node: fmtPct(s.bar_pass_rate_first_time) }) },
  { label: "Bar pass (ultimate)", better: "high",
    cell: (s) => ({ num: s.bar_pass_ultimate, node: fmtPct(s.bar_pass_ultimate) }) },
  { label: "Median private salary", better: "high",
    cell: (s) => ({ num: s.median_private_sector_salary, node: fmtMoney(s.median_private_sector_salary) }) },
  { label: "Median public salary", better: "high",
    cell: (s) => ({ num: s.median_public_sector_salary, node: fmtMoney(s.median_public_sector_salary) }) },
  { label: "Resident tuition", better: "low",
    cell: (s) => ({ num: s.annual_tuition_resident, node: fmtMoney(s.annual_tuition_resident) }) },
  { label: "Nonresident tuition", better: "low",
    cell: (s) => ({ num: s.annual_tuition_nonresident, node: fmtMoney(s.annual_tuition_nonresident) }) },
  { label: "Employed @10mo %", better: "high",
    cell: (s) => ({ num: s.employed_10mo_pct, node: s.employed_10mo_pct == null ? "—" : fmtPct(s.employed_10mo_pct) }) },
];

/* Index of the school(s) holding the best value in a row, for highlighting. */
function bestIdx(cells, better) {
  if (!better) return new Set();
  const nums = cells.map((c) => c.num).filter((n) => n != null && !Number.isNaN(n));
  if (!nums.length) return new Set();
  const best = better === "high" ? Math.max(...nums) : Math.min(...nums);
  const set = new Set();
  cells.forEach((c, i) => { if (c.num === best) set.add(i); });
  return set;
}

function CompareScreen({ schools, profile, onBack, onRemove }) {
  const [mode, setMode] = useState("personalized");
  const rows = mode === "personalized" ? CMP_PERSONALIZED : CMP_RAW;

  if (schools.length < 2) {
    return (
      <div className="card" style={{ padding: 22 }}>
        <button className="btn sm ghost back-link" onClick={onBack}>← Back to results</button>
        <h3>Compare schools</h3>
        <div className="center-msg">
          Select at least two schools to compare.<br />
          Go back to your results and tick the checkbox on the left of each school you want to line up.
          <div style={{ marginTop: 16 }}>
            <button className="btn primary" onClick={onBack}>← Back to results</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="card" style={{ padding: 22 }}>
      <button className="btn sm ghost back-link" onClick={onBack}>← Back to results</button>
      <div className="section-head">
        <h3>Compare schools</h3>
      </div>

      {/* All schools overlaid on a single six-axis radar, with a color legend. */}
      <div className="compare-overlay">
        <RadarOverlay series={schools.map((s, i) => ({
          scores: s.radar, color: SERIES_COLORS[i % SERIES_COLORS.length],
        }))} size={300} />
        <div className="overlay-legend">
          {schools.map((s, i) => (
            <div key={s.id} className="legend-row">
              <span className="legend-swatch"
                style={{ background: SERIES_COLORS[i % SERIES_COLORS.length] }} />
              <div>
                <div className="school-name">{s.name}</div>
                <div className="mono">
                  {fmtRank(s.usnwr_rank_2026)} · {TIER_LABEL[s.admissibility_tier]} · Score {Math.round(s.composite_score)}
                </div>
              </div>
              <button className="btn xs ghost" onClick={() => onRemove(s.id)}>remove</button>
            </div>
          ))}
        </div>
      </div>

      <div className="tabs" style={{ marginBottom: 12 }}>
        <button className={`tab ${mode === "personalized" ? "active" : ""}`}
          onClick={() => setMode("personalized")}>With your stats</button>
        <button className={`tab ${mode === "raw" ? "active" : ""}`}
          onClick={() => setMode("raw")}>Raw school stats</button>
      </div>

      <div style={{ overflowX: "auto" }}>
        <table className="compare-table">
          <thead>
            <tr>
              <th className="metric-col"></th>
              {schools.map((s) => (
                <th key={s.id}>
                  <div className="school-name">{s.name}</div>
                  <div className="mono">{s.location} · {fmtRank(s.usnwr_rank_2026)}</div>
                  <button className="btn xs ghost" onClick={() => onRemove(s.id)}>remove</button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const cells = schools.map((s) => row.cell(s));
              const best = bestIdx(cells, row.better);
              return (
                <tr key={row.label}>
                  <td className="metric-col">{row.label}</td>
                  {cells.map((c, i) => (
                    <td key={i} className={`num ${best.has(i) ? "best" : ""}`}>{c.node}</td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {mode === "personalized" && (
        <div className="note" style={{ marginTop: 16 }}>
          Fit scores and cost reflect your profile (LSAT {profile.lsat ?? "—"}, GPA {profile.gpa},
          goal {profile.goal}). Switch to <strong>Raw school stats</strong> to compare the schools
          on their own published numbers, independent of you.
        </div>
      )}
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
            {school.location} · USNWR {fmtRank(school.usnwr_rank_2026)} · acceptance {fmtPct(school.acceptance_rate)}
          </div>
        </div>
        <div className="head-actions">
          <div style={{ display: "flex", gap: 8 }}>
            <TierPill tier={school.admissibility_tier} />
            <span className="pill neutral">Score {composite}</span>
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
          <Bar value={school.radar[0]} label="Admissibility fit" color={BAR_COLORS[0]} />
          <div className="mono" style={{ marginTop: 4 }}>
            <strong>Not your odds of admission.</strong> This is a 0–100 fit score for how your
            LSAT/GPA sit against the class. The <strong>tier</strong> below is the admit read.
          </div>
          <div className="mono">tier: {TIER_LABEL[school.admissibility_tier]} · schools protect both the LSAT and GPA median</div>
          {(school.transfer_out_rate != null || school.transfer_in_rate != null) && (
            <div className="mono">
              transfer mobility: {Math.round((school.transfer_out_rate || 0) * 1000) / 10}% leave after 1L
              {school.transfers_in != null && <span> · admits {school.transfers_in} transfers/yr</span>}
            </div>
          )}
          {school.attrition_1l_pct != null && (
            <div className="mono">
              1L attrition: {fmtPct(school.attrition_1l_pct)}
              {school.attrition_1l_pct > 0.10 && <span> · <strong>high</strong>{school.conditional_scholarship ? " — and scholarships here are conditional" : ""}</span>}
            </div>
          )}
        </div>

        <div className="box story-col">
          <h4>Will you get the job?</h4>
          <div style={{ fontSize: 14 }}>Goal: <strong>{
            (profile.goals_weighted && profile.goals_weighted.length)
              ? profile.goals_weighted.map((g) => g.goal).join(" · ")
              : profile.goal
          }</strong></div>
          <Bar value={school.biglaw_pct * 100} label="BigLaw" color={BAR_COLORS[0]} />
          <Bar value={school.federal_clerkship_pct * 100} label="Fed. Clerkship" color={BAR_COLORS[1]} />
          <Bar value={school.government_pct * 100} label="Government" color={BAR_COLORS[2]} />
          <Bar value={school.public_interest_pct * 100} label="Public Interest" color={BAR_COLORS[3]} />
          <div className="mono">
            bar pass {fmtPct(school.bar_pass_rate_first_time)}
            {school.bar_pass_vs_state != null && (
              <span> · {school.bar_pass_vs_state >= 0 ? "+" : ""}{Math.round(school.bar_pass_vs_state * 1000) / 10} pts vs state avg</span>
            )}
            {school.bar_pass_ultimate != null && <span> · {fmtPct(school.bar_pass_ultimate)} ultimate</span>}
          </div>
          {school.target_states && school.target_states.length > 0 && (
            <div className="mono">feeder markets: {school.target_states.join(" · ")}</div>
          )}
          {school.hands_on_per_student != null && (
            <div className="mono">
              hands-on training: {school.hands_on_per_student} clinic/externship/sim seats per student
              {school.student_faculty_ratio != null && <span> · {school.student_faculty_ratio}:1 student-faculty</span>}
            </div>
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

      {/* Notable people (Wikipedia) */}
      {((school.notable_alumni && school.notable_alumni.length) ||
        (school.notable_faculty && school.notable_faculty.length)) && (
        <div className="notable-block">
          <h3 style={{ marginBottom: 10 }}>Notable people</h3>
          <div className="notable-cols">
            {school.notable_alumni && school.notable_alumni.length > 0 && (
              <div className="box story-col">
                <h4>Alumni</h4>
                <div className="people-list">
                  {school.notable_alumni.map((p) => (
                    <a key={p.url} href={p.url} target="_blank" rel="noreferrer" className="person">{p.name}</a>
                  ))}
                </div>
              </div>
            )}
            {school.notable_faculty && school.notable_faculty.length > 0 && (
              <div className="box story-col">
                <h4>Faculty</h4>
                <div className="people-list">
                  {school.notable_faculty.map((p) => (
                    <a key={p.url} href={p.url} target="_blank" rel="noreferrer" className="person">{p.name}</a>
                  ))}
                </div>
              </div>
            )}
          </div>
          <div className="mono" style={{ marginTop: 6 }}>Source: Wikipedia</div>
        </div>
      )}

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
/* Modals: How it works + Report a bug/feature                        */
/* ------------------------------------------------------------------ */

/* Change this to wherever bug/feature reports should be emailed. */
const REPORT_EMAIL = "lukechaussee119@gmail.com";

function Modal({ title, onClose, children }) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" role="dialog" aria-modal="true" aria-label={title}
        onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3>{title}</h3>
          <button className="btn xs ghost" onClick={onClose} aria-label="Close">✕</button>
        </div>
        {children}
      </div>
    </div>
  );
}

function HowItWorks({ onClose }) {
  return (
    <Modal title="How it works" onClose={onClose}>
      <div className="prose">
        <p>This tool ranks every ABA-accredited law school for <em>your</em> profile, not by
        prestige alone. Each school gets six 0–100 scores:</p>
        <ul>
          <li><strong>Admissibility</strong> — how your LSAT/GPA sit against the school's 25/50/75
            percentiles, mapped to a tier (Safety / Target / Reach / Hard reach). The tier is also
            capped by the school's acceptance rate, so a hyper-selective school is never a "safety".
            The number is a fit score, <em>not</em> your odds of admission.</li>
          <li><strong>Prestige</strong> — USNWR-rank standing.</li>
          <li><strong>Career fit</strong> — placement into your stated goal (BigLaw %, clerkships,
            government, public-interest + LRAP), discounted by real ABA employment outcomes and
            bar-passage vs. the state average.</li>
          <li><strong>Location fit</strong> — how strongly the school places graduates in your
            target state(s); multiple states are weighted (e.g. CA/NY = 70/30).</li>
          <li><strong>Scholarship</strong> — merit likelihood from the school's real ABA 509 award
            grid plus a need signal, net of conditional-scholarship risk.</li>
          <li><strong>Financial</strong> — net debt (resident vs. non-resident tuition + real ABA
            living costs − expected aid) against your goal's typical starting salary.</li>
        </ul>
        <p>The <strong>composite Score</strong> is a weighted average of the six, with the weights on
        career / location / cost driven by your sliders, then scaled by admissibility tier so
        unrealistic reaches don't top the list. Data: ABA 509 / Employment / Bar reports (2025–26),
        with notable people from Wikipedia.</p>
        <p className="mono">Estimates only — verify tuition, aid, and outcomes with each school before deciding.</p>
      </div>
    </Modal>
  );
}

function ReportForm({ onClose }) {
  const [kind, setKind] = useState("Bug");
  const [text, setText] = useState("");
  const send = () => {
    const subject = encodeURIComponent(`[Law School Matcher] ${kind} report`);
    const body = encodeURIComponent(text || "");
    window.location.href = `mailto:${REPORT_EMAIL}?subject=${subject}&body=${body}`;
    onClose();
  };
  return (
    <Modal title="Report a bug or request a feature" onClose={onClose}>
      <div className="report-form">
        <div className="chip-group" style={{ marginBottom: 12 }}>
          {["Bug", "Feature"].map((k) => (
            <button key={k} type="button" className={`chip ${kind === k ? "active" : ""}`}
              onClick={() => setKind(k)}>{k}</button>
          ))}
        </div>
        <textarea className="report-text" rows="6" value={text}
          placeholder={kind === "Bug"
            ? "What happened? What did you expect? Which school/profile?"
            : "What would you like the tool to do?"}
          onChange={(e) => setText(e.target.value)} />
        <div className="profile-actions" style={{ marginTop: 12 }}>
          <button className="btn ghost sm" onClick={onClose}>Cancel</button>
          <button className="btn primary sm" onClick={send} disabled={!text.trim()}>
            Send
          </button>
        </div>
      </div>
    </Modal>
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
  const [selectedIds, setSelectedIds] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [modal, setModal] = useState(null);   // "how" | "report" | null

  const toggleSelect = (id) =>
    setSelectedIds((ids) =>
      ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id]);

  const submit = async (f = form) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/match", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(f),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error || "Matching failed.");
      setData(json);
      setSelectedIds([]);
      setView("results");
      // Shareable link: profile lives in the URL hash, restored on load.
      try {
        window.history.replaceState(null, "", "#p=" + encodeShare(f));
      } catch (e) { /* ignore */ }
      window.scrollTo({ top: 0 });
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  // Opened via a share link: restore the profile and run the match once.
  useEffect(() => {
    const m = window.location.hash.match(/^#p=(.+)$/);
    if (!m) return;
    try {
      const f = { ...DEFAULT_FORM, ...decodeShare(m[1]) };
      setForm(f);
      submit(f);
    } catch (e) { /* malformed share link — start fresh */ }
  }, []);

  const openSchool = (s) => { setOpened(s); setView("detail"); window.scrollTo({ top: 0 }); };
  const openSchoolById = (id) => {
    const s = data && data.schools.find((x) => x.id === id);
    if (s) openSchool(s);
  };
  const openCompare = () => { setView("compare"); window.scrollTo({ top: 0 }); };
  const selectedSchools = useMemo(
    () => (data ? data.schools.filter((s) => selectedIds.includes(s.id)) : []),
    [data, selectedIds]);

  return (
    <div className="app">
      <div className="topbar">
        <h1>Law School Matcher</h1>
        <div className="topbar-actions">
          <button className="btn sm ghost" onClick={() => setModal("how")}>how it works</button>
          <button className="btn sm ghost" onClick={() => setModal("report")}>report bug / request feature</button>
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
        <ResultsScreen data={data} onOpen={openSchool} onBack={() => setView("profile")}
          selectedIds={selectedIds} onToggleSelect={toggleSelect}
          onClearSelect={() => setSelectedIds([])} onCompare={openCompare}
          onOpenSchool={openSchoolById} />
      )}
      {!loading && view === "detail" && opened && (
        <DetailScreen school={opened} profile={data.profile} onBack={() => setView("results")} />
      )}
      {!loading && view === "compare" && data && (
        <CompareScreen schools={selectedSchools} profile={data.profile}
          onBack={() => setView("results")} onRemove={toggleSelect} />
      )}

      {modal === "how" && <HowItWorks onClose={() => setModal(null)} />}
      {modal === "report" && <ReportForm onClose={() => setModal(null)} />}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
