/* screen-results.jsx — Results variations (4) — all radar-forward */

function ResultsVarA({ profile, anno, onOpen }) {
  return (
    <div className="sk-card" style={{ padding: 22, position: "relative" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 14 }}>
        <h3>Your top matches</h3>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="sk-btn sm ghost">Sort: composite ▾</button>
          <button className="sk-btn sm ghost">Filter ▾</button>
        </div>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {SAMPLE_SCHOOLS.slice(0, 4).map((s, i) => (
          <div key={s.id} className="sk-box clickable" onClick={() => onOpen(s)} style={{ padding: 16, display: "grid", gridTemplateColumns: "210px 1fr 160px", gap: 18, alignItems: "center" }}>
            <Radar scores={s.scores} size={200} />
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
                <span className="label-mono">#{i + 1}</span>
                <h3 style={{ fontSize: 22 }}>{s.name}</h3>
                <TierPill tier={s.tier} />
              </div>
              <div className="label-mono">{s.loc} · USNWR #{s.rank} · bar pass {(s.bar*100).toFixed(0)}%</div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8, marginTop: 4 }}>
                <Bar value={Math.round(s.biglaw*100)} label="BigLaw" color="var(--marker-blue)" />
                <Bar value={Math.round(s.clerk*100*5)} label="Clerkship" color="var(--marker-purple)" />
                <Bar value={s.scores[5]} label="Financial" color="var(--marker-green)" />
              </div>
            </div>
            <div style={{ textAlign: "right", display: "flex", flexDirection: "column", gap: 4, alignItems: "flex-end" }}>
              <div style={{ fontFamily: "var(--hand-bold)", fontSize: 28 }}>{Math.round(s.scores.reduce((a,b)=>a+b,0)/6)}</div>
              <div className="label-mono">composite</div>
              <div style={{ marginTop: 6 }} className="label-mono">net debt</div>
              <div style={{ fontFamily: "var(--hand-bold)", fontSize: 18 }}>{s.debt}</div>
              <button className="sk-btn sm" onClick={(e)=>{e.stopPropagation(); onOpen(s);}}>Open →</button>
            </div>
          </div>
        ))}
        <div style={{ display: "flex", justifyContent: "center", padding: 8 }}>
          <button className="sk-btn ghost sm">Show 4 more ↓</button>
        </div>
      </div>
      {anno && (<>
        <Anno style={{ position: "absolute", top: 60, left: 30 }} rot={-2}>radar = primary lens</Anno>
        <Anno style={{ position: "absolute", top: 60, right: 30 }} rot={2} color="var(--marker-blue)">debt + composite up front</Anno>
      </>)}
    </div>
  );
}

function ResultsVarB({ profile, anno, onOpen }) {
  const tiers = [
    { tier: "safety", label: "Safety", hint: "your stats > their 75th" },
    { tier: "target", label: "Target", hint: "around their median" },
    { tier: "reach",  label: "Reach",  hint: "below median but possible" },
    { tier: "hard reach", label: "Hard Reach", hint: "long shot — apply if dream" },
  ];
  return (
    <div className="sk-card" style={{ padding: 22, position: "relative" }}>
      <h3 style={{ marginBottom: 12 }}>Bucketed by admissibility</h3>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14 }}>
        {tiers.map((col, ci) => {
          const items = SAMPLE_SCHOOLS.filter(s => s.tier === col.tier);
          return (
            <div key={col.tier} className="sk-box" style={{ padding: 12, display: "flex", flexDirection: "column", gap: 10, minHeight: 460, background: ci % 2 ? "var(--paper)" : "var(--paper-2)" }}>
              <div>
                <TierPill tier={col.tier} />
                <div className="label-mono" style={{ marginTop: 4 }}>{col.hint}</div>
              </div>
              {items.length === 0 && <div className="label-mono" style={{ opacity: 0.5, fontStyle: "italic" }}>no matches in this bucket</div>}
              {items.map(s => (
                <div key={s.id} className="clickable" onClick={() => onOpen(s)} style={{ border: "2px solid var(--ink)", borderRadius: 6, padding: 8, background: "var(--paper)", display: "flex", flexDirection: "column", gap: 4 }}>
                  <div style={{ fontFamily: "var(--hand-bold)", fontSize: 16, lineHeight: 1.1 }}>{s.name.replace(" School of Law", "").replace(" Law School", "")}</div>
                  <div className="label-mono">#{s.rank} · {s.loc}</div>
                  <div style={{ display: "flex", justifyContent: "center", marginTop: 4 }}>
                    <Radar scores={s.scores} size={120} showLabels={false} />
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginTop: 2 }}>
                    <span className="label-mono">{s.debt}</span>
                    <span className="label-mono">BigLaw {(s.biglaw*100).toFixed(0)}%</span>
                  </div>
                </div>
              ))}
            </div>
          );
        })}
      </div>
      {anno && (<>
        <Anno style={{ position: "absolute", top: 16, right: 30 }} rot={-2}>columns map to user's gut categories</Anno>
      </>)}
    </div>
  );
}

function ResultsVarC({ profile, anno, onOpen }) {
  return (
    <div className="sk-card" style={{ padding: 22, position: "relative" }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
        <h3>Radar grid</h3>
        <span className="label-mono">click any school to drill in →</span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14 }}>
        {SAMPLE_SCHOOLS.slice(0, 8).map((s, i) => (
          <div key={s.id} className="sk-box clickable" onClick={() => onOpen(s)} style={{ padding: 14, display: "flex", flexDirection: "column", gap: 6, alignItems: "center", textAlign: "center", transform: `rotate(${(i % 3 - 1) * 0.25}deg)` }}>
            <div style={{ display: "flex", justifyContent: "space-between", width: "100%", alignItems: "center" }}>
              <span className="label-mono">#{i + 1}</span>
              <TierPill tier={s.tier} />
            </div>
            <Radar scores={s.scores} size={170} color={["var(--marker-blue)","var(--marker-purple)","var(--marker-green)","var(--marker-red)"][i % 4]} />
            <div style={{ fontFamily: "var(--hand-bold)", fontSize: 17, lineHeight: 1.1, marginTop: 4 }}>{s.name.replace(" School of Law", "").replace(" Law School", "")}</div>
            <div className="label-mono">USNWR #{s.rank} · {s.debt}</div>
          </div>
        ))}
      </div>
      {anno && (<>
        <Anno style={{ position: "absolute", top: 14, left: 140 }} rot={-2}>shape-matching: similar radars = similar schools</Anno>
      </>)}
    </div>
  );
}

function ResultsVarD({ profile, anno, onOpen }) {
  const cols = [
    { k: "name",   label: "School",      w: "1.7fr" },
    { k: "tier",   label: "Tier",        w: "auto" },
    { k: "radar",  label: "Profile",     w: "auto" },
    { k: "rank",   label: "Rank",        w: "auto" },
    { k: "biglaw", label: "BigLaw %",    w: "auto" },
    { k: "clerk",  label: "Clerk %",     w: "auto" },
    { k: "bar",    label: "Bar %",       w: "auto" },
    { k: "debt",   label: "Net debt",    w: "auto" },
    { k: "comp",   label: "Composite",   w: "auto" },
  ];
  const gridCols = cols.map(c => c.w).join(" ");
  return (
    <div className="sk-card" style={{ padding: 22, position: "relative", overflowX: "auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
        <h3>Sortable comparison</h3>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="sk-btn sm ghost">Export CSV</button>
          <button className="sk-btn sm">Compare ✓ 0</button>
        </div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: gridCols, gap: "0 14px", alignItems: "center", minWidth: 980 }}>
        {cols.map(c => (
          <div key={c.k} className="label-tiny" style={{ borderBottom: "2.5px solid var(--ink)", paddingBottom: 6 }}>{c.label} ▾</div>
        ))}
        {SAMPLE_SCHOOLS.slice(0, 6).map((s, i) => (
          <React.Fragment key={s.id}>
            <div className="clickable" onClick={() => onOpen(s)} style={{ padding: "10px 0", borderBottom: "1.5px dashed var(--ink-soft)" }}>
              <div style={{ fontFamily: "var(--hand-bold)", fontSize: 17 }}>{i + 1}. {s.name}</div>
              <div className="label-mono">{s.loc}</div>
            </div>
            <div style={{ padding: "10px 0", borderBottom: "1.5px dashed var(--ink-soft)" }}><TierPill tier={s.tier} /></div>
            <div style={{ padding: "10px 0", borderBottom: "1.5px dashed var(--ink-soft)" }}><Radar scores={s.scores} size={56} showLabels={false} showRings={false} /></div>
            <div style={{ padding: "10px 0", borderBottom: "1.5px dashed var(--ink-soft)", fontFamily: "var(--hand-bold)" }}>#{s.rank}</div>
            <div style={{ padding: "10px 0", borderBottom: "1.5px dashed var(--ink-soft)", fontFamily: "var(--mono)" }}>{(s.biglaw*100).toFixed(0)}%</div>
            <div style={{ padding: "10px 0", borderBottom: "1.5px dashed var(--ink-soft)", fontFamily: "var(--mono)" }}>{(s.clerk*100).toFixed(0)}%</div>
            <div style={{ padding: "10px 0", borderBottom: "1.5px dashed var(--ink-soft)", fontFamily: "var(--mono)" }}>{(s.bar*100).toFixed(0)}%</div>
            <div style={{ padding: "10px 0", borderBottom: "1.5px dashed var(--ink-soft)", fontFamily: "var(--hand-bold)" }}>{s.debt}</div>
            <div style={{ padding: "10px 0", borderBottom: "1.5px dashed var(--ink-soft)", fontFamily: "var(--hand-bold)", fontSize: 20 }}>
              <span className="sk-hi">{Math.round(s.scores.reduce((a,b)=>a+b,0)/6)}</span>
            </div>
          </React.Fragment>
        ))}
      </div>
      {anno && (<>
        <Anno style={{ position: "absolute", top: 60, right: 30 }} rot={1.5} color="var(--marker-blue)">tiny inline radar keeps the visual</Anno>
        <Anno style={{ position: "absolute", bottom: 16, left: 40 }} rot={-1.5}>compare 2+ → opens detail diff</Anno>
      </>)}
    </div>
  );
}

// Narrowed to chosen direction (D). Other variations kept above for reference.
window.ResultsVariations = [
  { key: "D", title: "Sortable table + inline radars", Comp: ResultsVarD },
];
