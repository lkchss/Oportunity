/* screen-profile.jsx — Profile Dashboard variations (4)
   All implement "Dashboard with editable sidebar of filters" — varied layout. */

const _STATES = ["NY","CA","TX","FL","DC","MA","IL","PA","GA","WA"];

function FilterGroup({ title, children }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <div className="label-tiny" style={{ borderBottom: "2px solid var(--ink)", paddingBottom: 3 }}>{title}</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>{children}</div>
    </div>
  );
}
function Field({ label, value, type = "text" }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
      <span className="label-tiny" style={{ textTransform: "none", fontSize: 11 }}>{label}</span>
      <div className="sk-input" style={{ minHeight: 36, fontSize: 16 }}>{value}</div>
    </div>
  );
}
function Slider({ label, value, max = 10 }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <span className="label-tiny" style={{ textTransform: "none", fontSize: 11 }}>{label}</span>
        <span className="label-mono">{value}/{max}</span>
      </div>
      <div style={{ height: 8, border: "2px solid var(--ink)", borderRadius: 6, background: "var(--paper)", position: "relative" }}>
        <div style={{ position: "absolute", left: `${value/max*100}%`, top: -5, width: 18, height: 18, background: "var(--hi-yellow)", border: "2px solid var(--ink)", borderRadius: "50%", transform: "translateX(-50%)" }} />
      </div>
    </div>
  );
}

/* === Variation A — Left sidebar, live preview on right === */
function ProfileVarA({ profile, anno, onSubmit }) {
  return (
    <div className="sk-card" style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 0, overflow: "hidden", position: "relative" }}>
      {/* Sidebar */}
      <aside style={{ borderRight: "3px solid var(--ink)", padding: 22, display: "flex", flexDirection: "column", gap: 18, background: "var(--paper-2)" }}>
        <div>
          <h3 style={{ fontSize: 24 }}>Your Profile</h3>
          <div className="label-mono">edits update results →</div>
        </div>
        <FilterGroup title="Academic">
          <Field label="LSAT" value={profile.lsat ?? "— not taken —"} />
          <Field label="GPA" value={profile.gpa.toFixed(2)} />
        </FilterGroup>
        <FilterGroup title="Career">
          <Field label="Primary goal" value={profile.goal} />
          <Field label="Practice state" value={profile.state || "—"} />
        </FilterGroup>
        <FilterGroup title="Location & residency">
          <Field label="In-state for" value={profile.state ? `[${profile.state}]` : "[ none ]"} />
        </FilterGroup>
        <FilterGroup title="Financial">
          <Field label="Income bracket" value={profile.income.replace(/_/g, " ")} />
          <Slider label="Scholarship priority" value={profile.scholarship} />
        </FilterGroup>
        <button className="sk-btn primary" onClick={onSubmit}>Update matches →</button>
      </aside>

      {/* Live preview */}
      <section style={{ padding: 22, display: "flex", flexDirection: "column", gap: 14 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <h3>Live preview — top 3</h3>
          <span className="label-mono">{SAMPLE_SCHOOLS.length} schools · re-ranking…</span>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
          {SAMPLE_SCHOOLS.slice(0, 3).map((s, i) => (
            <div key={s.id} className="sk-box" style={{ padding: 12, display: "flex", flexDirection: "column", gap: 8, transform: `rotate(${i === 1 ? 0 : (i % 2 ? 0.4 : -0.4)}deg)` }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <strong style={{ fontSize: 16 }}>{s.name.replace(" School of Law", "").replace(" Law School", "").replace(" Law", "")}</strong>
                <TierPill tier={s.tier} />
              </div>
              <div style={{ display: "flex", justifyContent: "center" }}>
                <Radar scores={s.scores} size={150} showLabels={false} />
              </div>
              <div className="label-mono" style={{ textAlign: "center" }}>#{s.rank} · {s.loc}</div>
            </div>
          ))}
        </div>
        <div className="sk-box" style={{ padding: 12, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ fontFamily: "var(--hand-bold)", fontSize: 18 }}>+ {SAMPLE_SCHOOLS.length - 3} more matches</span>
          <button className="sk-btn sm" onClick={onSubmit}>See all results →</button>
        </div>
      </section>

      {anno && (<>
        <Anno style={{ position: "absolute", top: 14, left: 200 }} rot={-3}>edits = instant re-rank</Anno>
        <Anno style={{ position: "absolute", bottom: 70, right: 18 }} rot={2} color="var(--marker-blue)">radar at-a-glance</Anno>
      </>)}
    </div>
  );
}

/* === Variation B — Right inspector rail, main = full list === */
function ProfileVarB({ profile, anno, onSubmit }) {
  return (
    <div className="sk-card" style={{ display: "grid", gridTemplateColumns: "1fr 300px", overflow: "hidden", position: "relative" }}>
      <section style={{ padding: 22, display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <h3>Ranked schools</h3>
          <span className="label-mono">drag sliders → list reorders</span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {SAMPLE_SCHOOLS.slice(0, 5).map((s, i) => (
            <div key={s.id} className="sk-box" style={{ padding: "10px 14px", display: "grid", gridTemplateColumns: "30px 1fr auto 90px", gap: 14, alignItems: "center" }}>
              <strong style={{ fontSize: 22 }}>#{i + 1}</strong>
              <div>
                <div style={{ fontSize: 17, fontFamily: "var(--hand-bold)", fontWeight: 600 }}>{s.name}</div>
                <div className="label-mono">{s.loc} · USNWR #{s.rank}</div>
              </div>
              <TierPill tier={s.tier} />
              <Radar scores={s.scores} size={70} showLabels={false} showRings={false} />
            </div>
          ))}
        </div>
      </section>

      <aside style={{ borderLeft: "3px solid var(--ink)", padding: 20, background: "var(--paper-2)", display: "flex", flexDirection: "column", gap: 14 }}>
        <div>
          <h3 style={{ fontSize: 22 }}>Filter inspector</h3>
          <div className="label-mono">tweak to re-rank</div>
        </div>
        <FilterGroup title="Stats">
          <Field label="LSAT" value={profile.lsat ?? "—"} />
          <Field label="GPA" value={profile.gpa.toFixed(2)} />
        </FilterGroup>
        <FilterGroup title="Weights">
          <Slider label="Career fit" value={7} />
          <Slider label="Location" value={6} />
          <Slider label="Scholarship" value={profile.scholarship} />
        </FilterGroup>
        <FilterGroup title="Filters">
          <Field label="Goal" value={profile.goal} />
          <Field label="State" value={profile.state || "any"} />
        </FilterGroup>
        <button className="sk-btn primary" onClick={onSubmit}>Open full results →</button>
      </aside>

      {anno && (<>
        <Anno style={{ position: "absolute", top: 80, right: 320 }} rot={2}>inspector pattern — main canvas always shows results</Anno>
      </>)}
    </div>
  );
}

/* === Variation C — Top horizontal filter bar, dashboard grid below === */
function ProfileVarC({ profile, anno, onSubmit }) {
  const groups = [
    { name: "Academic", items: [["LSAT", profile.lsat ?? "—"], ["GPA", profile.gpa.toFixed(2)]] },
    { name: "Career",   items: [["Goal", profile.goal], ["State", profile.state || "any"]] },
    { name: "Money",    items: [["Income", profile.income.replace(/_/g," ")], ["Schol", `${profile.scholarship}/10`]] },
    { name: "Weights",  items: [["Career", "7/10"], ["Location", "6/10"]] },
  ];
  return (
    <div className="sk-card" style={{ padding: 22, display: "flex", flexDirection: "column", gap: 18, position: "relative" }}>
      {/* Top bar */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr) auto", gap: 12, alignItems: "stretch" }}>
        {groups.map(g => (
          <div key={g.name} className="sk-box" style={{ padding: 10 }}>
            <div className="label-tiny" style={{ marginBottom: 6 }}>{g.name}</div>
            {g.items.map(([k, v]) => (
              <div key={k} style={{ display: "flex", justifyContent: "space-between", fontSize: 14, fontFamily: "var(--hand)" }}>
                <span style={{ color: "var(--ink-soft)" }}>{k}</span>
                <span style={{ fontWeight: 600 }}>{v}</span>
              </div>
            ))}
          </div>
        ))}
        <button className="sk-btn primary" style={{ alignSelf: "stretch" }} onClick={onSubmit}>Re-rank →</button>
      </div>

      {/* Dashboard grid */}
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
          <h3>Match dashboard</h3>
          <span className="label-mono">grouped by tier</span>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
          {[
            { tier: "safety", label: "Safety", count: 1 },
            { tier: "target", label: "Target", count: 3 },
            { tier: "reach",  label: "Reach",  count: 3 },
            { tier: "hard reach", label: "Hard Reach", count: 1 },
          ].map(col => (
            <div key={col.tier} className="sk-box" style={{ padding: 12, display: "flex", flexDirection: "column", gap: 10, minHeight: 280 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <TierPill tier={col.tier} />
                <span className="label-mono">{col.count}</span>
              </div>
              {SAMPLE_SCHOOLS.filter(s => s.tier === col.tier || (col.tier === "hard reach" && s.tier === "hard reach")).slice(0, 2).map(s => (
                <div key={s.id} style={{ borderBottom: "1.5px dashed var(--ink-soft)", paddingBottom: 6 }}>
                  <div style={{ fontFamily: "var(--hand-bold)", fontSize: 15 }}>{s.name.replace(" School of Law", "")}</div>
                  <div className="label-mono">#{s.rank} · {s.loc}</div>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
      {anno && (<>
        <Anno style={{ position: "absolute", top: 18, left: 110 }}>edits in-place — no modal</Anno>
        <Anno style={{ position: "absolute", bottom: 16, right: 22 }} color="var(--marker-blue)" rot={1.5}>kanban-style tier columns</Anno>
      </>)}
    </div>
  );
}

/* === Variation D — Split: profile L, score-weight knobs + preview R === */
function ProfileVarD({ profile, anno, onSubmit }) {
  return (
    <div className="sk-card" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", overflow: "hidden", position: "relative" }}>
      {/* Left — facts */}
      <section style={{ padding: 22, display: "flex", flexDirection: "column", gap: 16, borderRight: "3px solid var(--ink)" }}>
        <h3>Who you are</h3>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <Field label="LSAT" value={profile.lsat ?? "Not yet"} />
          <Field label="GPA" value={profile.gpa.toFixed(2)} />
          <Field label="Career goal" value={profile.goal} />
          <Field label="Target state" value={profile.state || "—"} />
          <Field label="In-state" value={profile.state ? `[${profile.state}]` : "—"} />
          <Field label="Income" value={profile.income.replace(/_/g," ")} />
        </div>
        <div className="sk-box" style={{ padding: 12, background: "var(--hi-yellow-soft)" }}>
          <div className="label-tiny">Tier you'll see most</div>
          <div style={{ fontSize: 26, fontFamily: "var(--hand-bold)" }}>Target → Reach</div>
          <div className="label-mono">based on LSAT vs school medians</div>
        </div>
      </section>

      {/* Right — what matters */}
      <section style={{ padding: 22, display: "flex", flexDirection: "column", gap: 14 }}>
        <h3>What matters to you</h3>
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Slider label="Career fit"        value={7} />
          <Slider label="Location"          value={6} />
          <Slider label="Scholarship"       value={profile.scholarship} />
          <Slider label="Prestige"          value={5} />
          <Slider label="Admissibility"     value={8} />
        </div>
        <div className="sk-box" style={{ padding: 12, background: "var(--paper-2)" }}>
          <div className="label-tiny">How matches respond</div>
          <div style={{ fontSize: 15, marginTop: 4, lineHeight: 1.35 }}>
            Higher <strong>scholarship</strong> + <strong>financial</strong> weight pushes
            in-state &amp; high-aid schools up the list. Drop <strong>prestige</strong> to surface safer bets.
          </div>
        </div>
        <button className="sk-btn primary" onClick={onSubmit}>See all 20 →</button>
      </section>

      {anno && (<>
        <Anno style={{ position: "absolute", top: 14, left: 18 }} rot={-2}>facts vs weights — split brain</Anno>
        <Anno style={{ position: "absolute", top: 200, right: 16 }} rot={2} color="var(--marker-blue)">sliders re-weight composite → list re-ranks</Anno>
      </>)}
    </div>
  );
}

// Narrowed to chosen direction (D), with the top-match preview card removed.
// Other variations kept above for reference.
window.ProfileVariations = [
  { key: "D", title: "Facts L / Weights R", Comp: ProfileVarD },
];
