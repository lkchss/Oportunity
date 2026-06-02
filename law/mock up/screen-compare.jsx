/* screen-compare.jsx — Compare variations (2) */

function CompareVarA({ anno, picks = SAMPLE_SCHOOLS.slice(0, 3) }) {
  const rows = [
    { k: "tier",    label: "Tier",         render: s => <TierPill tier={s.tier} /> },
    { k: "rank",    label: "USNWR rank",   render: s => <span style={{ fontFamily: "var(--hand-bold)", fontSize: 22 }}>#{s.rank}</span> },
    { k: "radar",   label: "Score shape",  render: s => <Radar scores={s.scores} size={130} showLabels={false} /> },
    { k: "biglaw",  label: "BigLaw %",     render: s => <span style={{ fontFamily: "var(--mono)" }}>{(s.biglaw*100).toFixed(0)}%</span> },
    { k: "clerk",   label: "Clerkship %",  render: s => <span style={{ fontFamily: "var(--mono)" }}>{(s.clerk*100).toFixed(0)}%</span> },
    { k: "bar",     label: "Bar pass",     render: s => <span style={{ fontFamily: "var(--mono)" }}>{(s.bar*100).toFixed(0)}%</span> },
    { k: "debt",    label: "Net debt",     render: s => <span style={{ fontFamily: "var(--hand-bold)" }}>{s.debt}</span> },
    { k: "salary",  label: "Starting sal", render: () => <span style={{ fontFamily: "var(--mono)" }}>$215k</span> },
    { k: "pslf",    label: "PSLF/LRAP",    render: (s, i) => i === 1 ? <span className="sk-pill">excellent</span> : <span className="sk-pill">moderate</span> },
  ];
  return (
    <div className="sk-card" style={{ padding: 22, position: "relative" }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
        <h3>Side-by-side compare</h3>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="sk-btn sm ghost">+ add school</button>
          <button className="sk-btn sm">highlight diffs</button>
        </div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: `160px repeat(${picks.length}, 1fr)`, gap: "0 14px" }}>
        {/* header row */}
        <div></div>
        {picks.map(s => (
          <div key={s.id} className="sk-box" style={{ padding: 10, marginBottom: 6 }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <strong>{s.name.replace(" School of Law", "")}</strong>
              <button className="sk-btn sm ghost" style={{ padding: "2px 8px", fontSize: 13 }}>×</button>
            </div>
            <div className="label-mono">{s.loc}</div>
          </div>
        ))}
        {rows.map(r => (
          <React.Fragment key={r.k}>
            <div className="label-tiny" style={{ alignSelf: "center", borderRight: "2px solid var(--ink)", paddingRight: 10, textAlign: "right", padding: "10px 10px 10px 0" }}>{r.label}</div>
            {picks.map((s, i) => (
              <div key={s.id} style={{ padding: "10px 0", borderBottom: "1.5px dashed var(--ink-soft)", display: "flex", alignItems: "center", justifyContent: "center", background: r.k === "radar" ? "rgba(255,240,102,0.15)" : "transparent" }}>
                {r.render(s, i)}
              </div>
            ))}
          </React.Fragment>
        ))}
      </div>
      {anno && (<>
        <Anno style={{ position: "absolute", top: 20, right: 200 }} rot={-2}>radar overlay shows where they differ</Anno>
      </>)}
    </div>
  );
}

function CompareVarB({ anno, picks = SAMPLE_SCHOOLS.slice(0, 3) }) {
  // Overlay radar — 3 polygons on one chart
  const size = 380;
  const cx = size / 2, cy = size / 2;
  const r = size * 0.36;
  const axes = 6;
  const colors = ["var(--marker-blue)", "var(--marker-red)", "var(--marker-green)"];
  const polygons = picks.map((s, idx) => {
    const pts = s.scores.map((v, i) => {
      const angle = (Math.PI * 2 / axes) * i - Math.PI / 2;
      const rad = v / 100 * r;
      const jx = jitter(idx * 11 + i * 3, 2);
      const jy = jitter(idx * 11 + i * 3 + 1, 2);
      return [cx + Math.cos(angle) * rad + jx, cy + Math.sin(angle) * rad + jy];
    });
    return { pts, color: colors[idx % colors.length] };
  });
  const axisPts = Array.from({ length: axes }, (_, i) => {
    const angle = (Math.PI * 2 / axes) * i - Math.PI / 2;
    return [cx + Math.cos(angle) * r, cy + Math.sin(angle) * r];
  });

  return (
    <div className="sk-card" style={{ padding: 22, position: "relative", display: "grid", gridTemplateColumns: "1.1fr 1fr", gap: 22 }}>
      <div>
        <h3 style={{ marginBottom: 10 }}>Overlay radar</h3>
        <div style={{ position: "relative", display: "flex", justifyContent: "center" }}>
          <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ overflow: "visible" }}>
            {[0.33, 0.66, 1.0].map((s, ri) => {
              const ringPts = Array.from({ length: axes }, (_, i) => {
                const angle = (Math.PI * 2 / axes) * i - Math.PI / 2;
                return `${cx + Math.cos(angle) * r * s},${cy + Math.sin(angle) * r * s}`;
              }).join(" ");
              return <polygon key={ri} points={ringPts} fill="none" stroke="rgba(0,0,0,0.18)" strokeWidth="1.4" />;
            })}
            {axisPts.map(([x, y], i) => <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke="rgba(0,0,0,0.18)" strokeWidth="1.2" />)}
            {polygons.map((p, i) => (
              <polygon key={i} points={p.pts.map(pt => pt.join(",")).join(" ")} fill={p.color} fillOpacity="0.18" stroke={p.color} strokeWidth="3" strokeLinejoin="round" />
            ))}
            {axisPts.map(([x, y], i) => {
              const dx = (x - cx) * 1.2, dy = (y - cy) * 1.2;
              return (
                <text key={i} x={cx + dx} y={cy + dy + 4} textAnchor="middle"
                  fontFamily="Architects Daughter, Kalam, sans-serif" fontSize="13" fill="var(--ink)">{SCORE_NAMES[i]}</text>
              );
            })}
          </svg>
        </div>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <h3>Schools</h3>
        {picks.map((s, i) => (
          <div key={s.id} className="sk-box" style={{ padding: 12, display: "grid", gridTemplateColumns: "20px 1fr auto", gap: 12, alignItems: "center" }}>
            <div style={{ width: 16, height: 16, background: colors[i], border: "2px solid var(--ink)", borderRadius: 4 }} />
            <div>
              <div style={{ fontFamily: "var(--hand-bold)", fontSize: 18 }}>{s.name}</div>
              <div className="label-mono">#{s.rank} · {s.loc} · {s.debt}</div>
            </div>
            <button className="sk-btn sm ghost" style={{ padding: "2px 8px" }}>×</button>
          </div>
        ))}
        <button className="sk-btn sm ghost">+ add 4th school</button>
        <div className="sk-box" style={{ padding: 12, background: "var(--hi-yellow-soft)" }}>
          <div className="label-tiny">Biggest gap</div>
          <div style={{ fontSize: 15, marginTop: 2 }}>
            <strong>Financial</strong>: Fordham +33 vs Yale.
            <br />
            <strong>Prestige</strong>: Yale +20 vs Fordham.
          </div>
        </div>
      </div>
      {anno && (<>
        <Anno style={{ position: "absolute", top: 30, left: 20 }} rot={-2}>overlay tells the trade-off story</Anno>
      </>)}
    </div>
  );
}

window.CompareVariations = [
  { key: "A", title: "Spec-sheet table",   Comp: CompareVarA },
  { key: "B", title: "Overlaid radar",     Comp: CompareVarB },
];
