/* screen-rankings.jsx — the Docket: dense raw-data browser, no algorithm. */

const RK_COLS = [
{ k: "name", label: "School", l: true, sort: (s) => s.name,
  render: (s) => <td className="l school-cell"><span className="nm">{s.name}</span><span className="lc">{s.loc}</span></td> },
{ k: "rank", label: "Rank", sort: (s) => s.rank, render: (s) => <td>{fmtRank(s.rank)}</td> },
{ k: "lsat", label: "LSAT 25/50/75", sort: (s) => s.l50,
  render: (s) => <td>{s.l25}/{s.l50}/{s.l75}</td> },
{ k: "gpa", label: "GPA 50", sort: (s) => s.g50, render: (s) => <td>{s.g50.toFixed(2)}</td> },
{ k: "accept", label: "Accept", sort: (s) => s.accept, render: (s) => <td>{fmtPct(s.accept)}</td> },
{ k: "biglaw", label: "BigLaw", sort: (s) => s.biglaw,
  render: (s) => <td>{fmtPct(s.biglaw)}</td> },
{ k: "emp", label: "Employed", sort: (s) => s.emp, render: (s) => <td>{fmtPct(s.emp)}</td> },
{ k: "bar", label: "Bar", sort: (s) => s.bar, render: (s) => <td>{fmtPct(s.bar)}</td> },
{ k: "tuit", label: "Tuition", sort: (s) => s.tuitNon, render: (s) => <td>{fmtMoneyK(s.tuitNon)}</td> }];


/* percentile of a value among all schools (higher = better standing) */
function rkPctile(key, v) {
  const vals = SCHOOLS.map((s) => s[key]);
  const below = vals.filter((x) => x < v).length;
  return Math.round(below / Math.max(vals.length - 1, 1) * 100);
}
const ord = (n) => n + (["th", "st", "nd", "rd"][(n % 100 > 10 && n % 100 < 14) ? 0 : Math.min(n % 10, 4)] || "th");

function RawDetail({ s }) {
  const row = (k, v, pkey) => (
    <React.Fragment>
      <span className="k">{k}</span>
      <span className="v">{v}{pkey != null &&
        <span style={{ color: "var(--faint)", marginLeft: 6 }}>· {rkPctile(pkey, s[pkey])}%</span>}
      </span>
    </React.Fragment>);
  return (
    <div className="raw-detail">
      <div className="kv">
        {row("Acceptance rate", fmtPct(s.accept))}
        {row("1L class size", s.size)}
        {row("BigLaw %", fmtPct(s.biglaw), "biglaw")}
        {row("Fed. clerkship %", fmtPct(s.clerk), "clerk")}
        {row("Government %", fmtPct(s.gov), "gov")}
        {row("Public interest %", fmtPct(s.pi), "pi")}
        {row("Employed @10 mo", fmtPct(s.emp), "emp")}
        {row("Bar pass (first-time)", fmtPct(s.bar), "bar")}
        {row("Bar pass (ultimate)", fmtPct(s.barUlt), "barUlt")}
      </div>
      <div className="kv">
        {row("Resident tuition", fmtMoney(s.tuitRes))}
        {row("Nonresident tuition", fmtMoney(s.tuitNon))}
        {row("Living budget /yr", fmtMoney(s.living))}
        {row("Any-grant rate", fmtPct(s.grantRate), "grantRate")}
        {row("Median grant /yr", fmtMoney(s.medGrant), "medGrant")}
        {row("Transfers in / out rate", `${s.trIn} / ${fmtPct1(s.trOut)}`)}
        {row("Real grad debt · earnings @4yr", `${fmtMoneyK(s.scDebt)} · ${fmtMoneyK(s.scEarn)}`)}
      </div>
      <div className="mono" style={{ gridColumn: "1 / -1" }}>
        <a href={wiki(s.name)} target="_blank" rel="noreferrer">About the school ↗</a>
      </div>
    </div>);

}

function RankingsScreen({ onBack }) {
  const [q, setQ] = React.useState("");
  const [stateFilter, setStateFilter] = React.useState("");
  const [sortKey, setSortKey] = React.useState("rank");
  const [asc, setAsc] = React.useState(true);
  const [openId, setOpenId] = React.useState(null);

  const list = React.useMemo(() => {
    const needle = q.trim().toLowerCase();
    let rows = SCHOOLS;
    if (needle) rows = rows.filter((s) => s.name.toLowerCase().includes(needle) || s.loc.toLowerCase().includes(needle));
    if (stateFilter) rows = rows.filter((s) => s.state === stateFilter);
    const col = RK_COLS.find((c) => c.k === sortKey);
    if (col) rows = [...rows].sort((a, b) => {
      const av = col.sort(a),bv = col.sort(b);
      return (av < bv ? -1 : av > bv ? 1 : 0) * (asc ? 1 : -1);
    });
    return rows;
  }, [q, stateFilter, sortKey, asc]);

  const onHeader = (col) => {
    if (sortKey === col.k) setAsc((v) => !v);else
    {setSortKey(col.k);setAsc(["rank", "name", "accept", "tuit"].includes(col.k));}
  };

  return (
    <div data-screen-label="rankings">
      <div className="results-head">
        <div>
          <h1 className="display">All schools<span className="colon">:</span></h1>
          <p> 
            <span className="mono">(Prototype: 24 of 196 schools.)</span></p>
        </div>
        <div style={{ display: "flex", gap: 8, flex: "none" }}>
          <input type="text" placeholder="Search school or city…" value={q} style={{ width: 220 }}
          onChange={(e) => setQ(e.target.value)} />
          <select value={stateFilter} onChange={(e) => setStateFilter(e.target.value)}>
            <option value="">All states</option>
            {STATES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
      </div>

      <div className="dense-wrap">
        <table className="dense">
          <thead>
            <tr>
              {RK_COLS.map((c) =>
              <th key={c.k} className={c.l ? "l" : ""} onClick={() => onHeader(c)}>
                  {c.label}{sortKey === c.k && <span className="arrow">{asc ? " ▲" : " ▼"}</span>}
                </th>
              )}
            </tr>
          </thead>
          <tbody>
            {list.map((s) =>
            <React.Fragment key={s.id}>
                <tr tabIndex={0} aria-expanded={openId === s.id}
              onClick={() => setOpenId(openId === s.id ? null : s.id)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  setOpenId(openId === s.id ? null : s.id);
                }
              }}>
                  {RK_COLS.map((c) => <React.Fragment key={c.k}>{c.render(s)}</React.Fragment>)}
                </tr>
                {openId === s.id &&
              <tr className="raw-detail-row">
                    <td colSpan={RK_COLS.length} className="l"><RawDetail s={s} /></td>
                  </tr>
              }
              </React.Fragment>
            )}
          </tbody>
        </table>
        {list.length === 0 && <div className="center-msg">No schools match your search.</div>}
        <div className="table-foot">
          <span>{list.length} SCHOOLS</span>
          <span>SORT: {RK_COLS.find((c) => c.k === sortKey).label.toUpperCase()} {asc ? "ASC" : "DESC"}</span>
          <span className="right">CLICK ROW → FULL DATA SHEET</span>
        </div>
      </div>
    </div>);

}

window.RankingsScreen = RankingsScreen;