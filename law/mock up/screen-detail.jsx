/* screen-detail.jsx — Single school detail variations (3) */

function FinBreakdown() {
  const rows = [
    ["Annual tuition (effective)", "$72,755"],
    ["Est. 3-yr cost",            "$314k"],
    ["Est. aid (3-yr)",           "−$72k"],
    ["Net debt",                  "$242k"],
    ["Starting salary",           "$215k"],
    ["Monthly payment (10-yr, 7%)", "$2,810"],
    ["Debt/income",               "1.13×"],
  ];
  return (
    <div className="sk-box" style={{ padding: 12 }}>
      <div className="label-tiny" style={{ marginBottom: 6 }}>Standard repayment — 10-yr @ 7%</div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: "4px 16px" }}>
        {rows.map(([k, v]) => (
          <React.Fragment key={k}>
            <span style={{ fontSize: 14 }}>{k}</span>
            <span style={{ fontFamily: "var(--mono)", fontSize: 14 }}>{v}</span>
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}
function PSLFCard() {
  return (
    <div className="sk-box" style={{ padding: 12, background: "var(--hi-yellow-soft)" }}>
      <div className="label-tiny" style={{ marginBottom: 6 }}>PSLF / IDR path — gov + nonprofit only</div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: "4px 16px" }}>
        {[
          ["IDR monthly (gross)", "$415"],
          ["LRAP reduction",      "−$400"],
          ["Your monthly (net)",  "$15"],
          ["Forgiven at year 10", "$241k"],
          ["Total paid (10 yr)",  "$1.8k"],
        ].map(([k, v]) => (
          <React.Fragment key={k}>
            <span style={{ fontSize: 14 }}>{k}</span>
            <span style={{ fontFamily: "var(--mono)", fontSize: 14 }}>{v}</span>
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

function StatBlock({ label, value, sub }) {
  return (
    <div className="sk-box" style={{ padding: 10, textAlign: "center" }}>
      <div className="label-tiny">{label}</div>
      <div style={{ fontFamily: "var(--hand-bold)", fontSize: 24 }}>{value}</div>
      {sub && <div className="label-mono">{sub}</div>}
    </div>
  );
}

/* === Variation A — Hero radar + financial breakdown stack === */
function DetailVarA({ school, anno, onBack }) {
  const s = school || SAMPLE_SCHOOLS[3];
  return (
    <div className="sk-card" style={{ padding: 22, position: "relative" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
        <div>
          <button className="sk-btn sm ghost" onClick={onBack}>← back to results</button>
          <h2 style={{ marginTop: 8 }}>{s.name}</h2>
          <div className="label-mono">{s.loc} · USNWR #{s.rank} · acceptance 12.8%</div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8, alignItems: "flex-end" }}>
          <TierPill tier={s.tier} />
          <button className="sk-btn sm">+ add to compare</button>
          <a className="label-mono" href="#">visit website ↗</a>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 22 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 12, alignItems: "center" }}>
          <Radar scores={s.scores} size={300} color="var(--marker-blue)" />
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, width: "100%" }}>
            {SCORE_NAMES_LONG.map((n, i) => (
              <Bar key={n} value={s.scores[i]} label={n} color={["var(--marker-blue)","var(--marker-purple)","var(--marker-green)","var(--marker-red)","#b8860b","var(--marker-blue)"][i]} />
            ))}
          </div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 8 }}>
            <StatBlock label="LSAT 50" value="168" sub="25/75: 162/169" />
            <StatBlock label="GPA 50"  value="3.83" sub="25/75: 3.67/3.90" />
            <StatBlock label="BigLaw"  value={`${(s.biglaw*100).toFixed(0)}%`} />
            <StatBlock label="Clerk"   value={`${(s.clerk*100).toFixed(0)}%`} />
            <StatBlock label="Bar"     value={`${(s.bar*100).toFixed(0)}%`} />
          </div>
          <FinBreakdown />
          <PSLFCard />
        </div>
      </div>
      {anno && (<>
        <Anno style={{ position: "absolute", top: 20, left: 360 }} rot={-2}>hero radar = single takeaway</Anno>
        <Anno style={{ position: "absolute", bottom: 100, right: 24 }} rot={2} color="var(--marker-green)">PSLF path optional — only for PI/gov goals</Anno>
      </>)}
    </div>
  );
}

/* === Variation B — Story columns (Admissions / Career / Money) === */
function DetailVarB({ school, anno, onBack }) {
  const s = school || SAMPLE_SCHOOLS[3];
  return (
    <div className="sk-card" style={{ padding: 22, position: "relative" }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 14 }}>
        <button className="sk-btn sm ghost" onClick={onBack}>← back</button>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="sk-btn sm ghost">share</button>
          <button className="sk-btn sm">+ compare</button>
        </div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 22, marginBottom: 18 }}>
        <div>
          <h2>{s.name}</h2>
          <div className="label-mono" style={{ marginTop: 4 }}>{s.loc} · USNWR #{s.rank}</div>
          <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
            <TierPill tier={s.tier} />
            <span className="sk-pill hi">Composite {Math.round(s.scores.reduce((a,b)=>a+b,0)/6)}</span>
          </div>
        </div>
        <Radar scores={s.scores} size={170} color="var(--marker-purple)" />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14 }}>
        <div className="sk-box" style={{ padding: 14, display: "flex", flexDirection: "column", gap: 10 }}>
          <div className="label-tiny" style={{ borderBottom: "2px solid var(--ink)", paddingBottom: 4 }}>Admissions</div>
          <div>
            <div className="label-mono">your LSAT vs school</div>
            <div style={{ position: "relative", height: 40, marginTop: 6 }}>
              <div style={{ position: "absolute", left: 0, right: 0, top: 18, height: 4, background: "var(--ink-soft)", borderRadius: 2 }} />
              <div style={{ position: "absolute", left: "20%", top: 10, fontFamily: "var(--mono)", fontSize: 11 }}>162</div>
              <div style={{ position: "absolute", left: "50%", top: 10, fontFamily: "var(--mono)", fontSize: 11 }}>168</div>
              <div style={{ position: "absolute", left: "80%", top: 10, fontFamily: "var(--mono)", fontSize: 11 }}>169</div>
              <div style={{ position: "absolute", left: "65%", top: 24, transform: "translateX(-50%)" }}>
                <div style={{ width: 14, height: 14, borderRadius: "50%", background: "var(--marker-red)", border: "2px solid var(--ink)" }} />
                <div className="label-mono" style={{ textAlign: "center", marginTop: 2, color: "var(--marker-red)" }}>you 169</div>
              </div>
            </div>
          </div>
          <StatBlock label="Acceptance" value="12.8%" />
          <Bar value={s.scores[0]} label="Admissibility score" color="var(--marker-blue)" />
        </div>

        <div className="sk-box" style={{ padding: 14, display: "flex", flexDirection: "column", gap: 10 }}>
          <div className="label-tiny" style={{ borderBottom: "2px solid var(--ink)", paddingBottom: 4 }}>Career</div>
          <div style={{ fontSize: 15 }}>Goal: <strong>BigLaw</strong> · school strength → <span className="sk-hi">strong</span></div>
          <Bar value={Math.round(s.biglaw*100)}     label="BigLaw"        color="var(--marker-blue)" />
          <Bar value={Math.round(s.clerk*100*4)}    label="Fed. Clerkship" color="var(--marker-purple)" />
          <Bar value={42}                            label="Government"    color="var(--marker-green)" />
          <Bar value={28}                            label="Public Interest" color="var(--marker-red)" />
          <div className="label-mono">target states: MA · NY · DC · CA · CT</div>
        </div>

        <div className="sk-box" style={{ padding: 14, display: "flex", flexDirection: "column", gap: 10 }}>
          <div className="label-tiny" style={{ borderBottom: "2px solid var(--ink)", paddingBottom: 4 }}>Money</div>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <div>
              <div className="label-mono">net debt</div>
              <div style={{ fontFamily: "var(--hand-bold)", fontSize: 28 }}>{s.debt}</div>
            </div>
            <div>
              <div className="label-mono">starting</div>
              <div style={{ fontFamily: "var(--hand-bold)", fontSize: 28 }}>$215k</div>
            </div>
          </div>
          <Bar value={s.scores[5]} label="Financial score" color="var(--marker-green)" />
          <div className="sk-box" style={{ background: "var(--hi-yellow-soft)", padding: 8 }}>
            <div className="label-tiny">PSLF if you go gov / nonprofit</div>
            <div style={{ fontSize: 14, marginTop: 2 }}>$15/mo · forgiven at yr 10</div>
          </div>
        </div>
      </div>
      {anno && (<>
        <Anno style={{ position: "absolute", top: 30, left: 230 }} rot={-2}>three story columns: get in / what next / can I afford</Anno>
      </>)}
    </div>
  );
}

/* === Variation C — Long-scroll narrative w/ pinned radar === */
function DetailVarC({ school, anno, onBack }) {
  const s = school || SAMPLE_SCHOOLS[3];
  const Section = ({ title, children }) => (
    <div style={{ borderTop: "2.5px solid var(--ink)", paddingTop: 14, marginTop: 14 }}>
      <h3 style={{ marginBottom: 8 }}>{title}</h3>
      {children}
    </div>
  );
  return (
    <div className="sk-card" style={{ padding: 22, position: "relative", display: "grid", gridTemplateColumns: "1fr 260px", gap: 22 }}>
      <div>
        <button className="sk-btn sm ghost" onClick={onBack}>← back</button>
        <h2 style={{ marginTop: 8 }}>{s.name}</h2>
        <div className="label-mono">{s.loc} · USNWR #{s.rank}</div>

        <Section title="Will you get in?">
          <p style={{ fontSize: 16, lineHeight: 1.4 }}>
            Your <strong>173 LSAT / 3.21 GPA</strong> is a classic splitter. LSAT clears their 75th (169);
            GPA is below their 25th (3.67). Schools protect both medians → tier reads as <strong>reach</strong>.
          </p>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            <Bar value={94} label="LSAT percentile" color="var(--marker-blue)" />
            <Bar value={11} label="GPA percentile" color="var(--marker-red)" />
          </div>
        </Section>

        <Section title="Will you get the job?">
          <p style={{ fontSize: 16, lineHeight: 1.4 }}>
            BigLaw placement <strong>{(s.biglaw*100).toFixed(0)}%</strong> — strong pipeline into your target market (NYC).
            Federal clerkship pipeline modest at {(s.clerk*100).toFixed(0)}%.
          </p>
          <div style={{ display: "flex", gap: 10 }}>
            <span className="sk-pill">corporate</span>
            <span className="sk-pill">litigation</span>
            <span className="sk-pill">ip</span>
            <span className="sk-pill">tax</span>
          </div>
        </Section>

        <Section title="Can you afford it?">
          <p style={{ fontSize: 16, lineHeight: 1.4 }}>
            On standard repayment: <strong>{s.debt} net debt</strong> against $215k starting salary →
            DTI 1.13×. Manageable but tight in years 1–3.
          </p>
          <FinBreakdown />
        </Section>
      </div>

      <aside style={{ position: "sticky", top: 0, alignSelf: "start", display: "flex", flexDirection: "column", gap: 10 }}>
        <Radar scores={s.scores} size={240} color="var(--marker-blue)" />
        <TierPill tier={s.tier} />
        <button className="sk-btn sm">+ compare</button>
        <button className="sk-btn sm ghost">save ♡</button>
      </aside>
      {anno && (<>
        <Anno style={{ position: "absolute", top: 80, right: 290 }} rot={2}>plain-English questions, radar pinned right</Anno>
      </>)}
    </div>
  );
}

/* Year-by-year repayment mini table (the "more detailed" financial content) */
function YearByYear({ pslf }) {
  const std = [
    ["1", "$242k", "$33.7k", "$208k"],
    ["3", "$208k", "$33.7k", "$140k"],
    ["5", "$140k", "$33.7k", "$66k"],
    ["8", "$66k",  "$33.7k", "$11k"],
    ["10","$11k",  "$33.7k", "$0"],
  ];
  const idr = [
    ["1", "$242k", "$5.0k",  "$251k"],
    ["3", "$251k", "$5.2k",  "$258k"],
    ["5", "$258k", "$5.4k",  "$262k"],
    ["8", "$262k", "$5.6k",  "$258k"],
    ["10","$258k", "$5.6k",  "forgiven"],
  ];
  const rows = pslf ? idr : std;
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "2px 14px" }}>
      {["Year", "Balance start", pslf ? "Paid (IDR)" : "Paid", "Balance end"].map(h => (
        <div key={h} className="label-tiny" style={{ borderBottom: "2px solid var(--ink)", paddingBottom: 4 }}>{h}</div>
      ))}
      {rows.map(r => r.map((c, ci) => (
        <div key={r[0] + ci} style={{ fontFamily: "var(--mono)", fontSize: 13, padding: "5px 0", borderBottom: "1.5px dashed var(--ink-soft)" }}>{c}</div>
      )))}
    </div>
  );
}

/* === MERGED — B's story columns + bigger A-style hero + tabbed financial detail === */
function DetailMerged({ school, anno, onBack }) {
  const s = school || SAMPLE_SCHOOLS[3];
  const [finTab, setFinTab] = React.useState("standard");
  const composite = Math.round(s.scores.reduce((a, b) => a + b, 0) / 6);
  const barColors = ["var(--marker-blue)","var(--marker-purple)","var(--marker-green)","var(--marker-red)","#b8860b","var(--marker-blue)"];

  const finTabs = [
    { k: "standard", label: "Standard 10-yr" },
    { k: "pslf",     label: "PSLF / IDR path" },
    { k: "schedule", label: "Year-by-year" },
  ];

  return (
    <div className="sk-card" style={{ padding: 22, position: "relative" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
        <div>
          <button className="sk-btn sm ghost" onClick={onBack}>← back to results</button>
          <h2 style={{ marginTop: 8 }}>{s.name}</h2>
          <div className="label-mono">{s.loc} · USNWR #{s.rank} · acceptance 12.8%</div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8, alignItems: "flex-end" }}>
          <div style={{ display: "flex", gap: 8 }}>
            <TierPill tier={s.tier} />
            <span className="sk-pill hi">Composite {composite}</span>
          </div>
          <button className="sk-btn sm">+ add to compare</button>
          <a className="label-mono" href="#">visit website ↗</a>
        </div>
      </div>

      {/* HERO BAND — bigger radar (like A) + stat blocks + score bars */}
      <div style={{ display: "grid", gridTemplateColumns: "330px 1fr", gap: 24, alignItems: "center", paddingBottom: 18, borderBottom: "3px solid var(--ink)" }}>
        <div style={{ display: "flex", justifyContent: "center" }}>
          <Radar scores={s.scores} size={300} color="var(--marker-blue)" />
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 8 }}>
            <StatBlock label="LSAT 50" value="168" sub="25/75 162·169" />
            <StatBlock label="GPA 50"  value="3.83" sub="25/75 3.67·3.90" />
            <StatBlock label="BigLaw"  value={`${(s.biglaw*100).toFixed(0)}%`} />
            <StatBlock label="Clerk"   value={`${(s.clerk*100).toFixed(0)}%`} />
            <StatBlock label="Bar"     value={`${(s.bar*100).toFixed(0)}%`} />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
            {SCORE_NAMES_LONG.map((n, i) => (
              <Bar key={n} value={s.scores[i]} label={n} color={barColors[i]} />
            ))}
          </div>
        </div>
      </div>

      {/* THREE STORY COLUMNS */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14, marginTop: 18 }}>
        <div className="sk-box" style={{ padding: 14, display: "flex", flexDirection: "column", gap: 10 }}>
          <div className="label-tiny" style={{ borderBottom: "2px solid var(--ink)", paddingBottom: 4 }}>Will you get in?</div>
          <div>
            <div className="label-mono">your LSAT vs school</div>
            <div style={{ position: "relative", height: 44, marginTop: 6 }}>
              <div style={{ position: "absolute", left: 0, right: 0, top: 18, height: 4, background: "var(--ink-soft)", borderRadius: 2 }} />
              <div style={{ position: "absolute", left: "20%", top: 10, fontFamily: "var(--mono)", fontSize: 11 }}>162</div>
              <div style={{ position: "absolute", left: "50%", top: 10, fontFamily: "var(--mono)", fontSize: 11 }}>168</div>
              <div style={{ position: "absolute", left: "80%", top: 10, fontFamily: "var(--mono)", fontSize: 11 }}>169</div>
              <div style={{ position: "absolute", left: "65%", top: 24, transform: "translateX(-50%)" }}>
                <div style={{ width: 14, height: 14, borderRadius: "50%", background: "var(--marker-red)", border: "2px solid var(--ink)" }} />
                <div className="label-mono" style={{ textAlign: "center", marginTop: 2, color: "var(--marker-red)" }}>you</div>
              </div>
            </div>
          </div>
          <Bar value={s.scores[0]} label="Admissibility score" color="var(--marker-blue)" />
          <div className="label-mono">tier: {s.tier} · protects both medians</div>
        </div>

        <div className="sk-box" style={{ padding: 14, display: "flex", flexDirection: "column", gap: 10 }}>
          <div className="label-tiny" style={{ borderBottom: "2px solid var(--ink)", paddingBottom: 4 }}>Will you get the job?</div>
          <div style={{ fontSize: 15 }}>Goal: <strong>BigLaw</strong> · strength → <span className="sk-hi">strong</span></div>
          <Bar value={Math.round(s.biglaw*100)}     label="BigLaw"          color="var(--marker-blue)" />
          <Bar value={Math.round(s.clerk*100*4)}    label="Fed. Clerkship"  color="var(--marker-purple)" />
          <Bar value={42}                            label="Government"      color="var(--marker-green)" />
          <Bar value={28}                            label="Public Interest" color="var(--marker-red)" />
          <div className="label-mono">feeder markets: NY · DC · MA · CA · CT</div>
        </div>

        <div className="sk-box" style={{ padding: 14, display: "flex", flexDirection: "column", gap: 10 }}>
          <div className="label-tiny" style={{ borderBottom: "2px solid var(--ink)", paddingBottom: 4 }}>Can you afford it?</div>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <div>
              <div className="label-mono">net debt</div>
              <div style={{ fontFamily: "var(--hand-bold)", fontSize: 28 }}>{s.debt}</div>
            </div>
            <div>
              <div className="label-mono">starting</div>
              <div style={{ fontFamily: "var(--hand-bold)", fontSize: 28 }}>$215k</div>
            </div>
          </div>
          <Bar value={s.scores[5]} label="Financial score" color="var(--marker-green)" />
          <div className="label-mono">debt-to-income 1.13× · see full detail below ↓</div>
        </div>
      </div>

      {/* TABBED FINANCIAL DETAIL */}
      <div className="sk-box" style={{ marginTop: 18, padding: 0, overflow: "hidden" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 14px 0" }}>
          <h3 style={{ fontSize: 20 }}>Financial detail</h3>
          <span className="label-mono">click a tab ↓</span>
        </div>
        {/* Tabs */}
        <div style={{ display: "flex", gap: 8, padding: "10px 14px 0", borderBottom: "3px solid var(--ink)" }}>
          {finTabs.map(tab => (
            <button
              key={tab.k}
              onClick={() => setFinTab(tab.k)}
              className="clickable"
              style={{
                border: "3px solid var(--ink)", borderBottom: "none",
                background: finTab === tab.k ? "var(--hi-yellow)" : "var(--paper-2)",
                color: finTab === tab.k ? "var(--ink)" : "var(--ink-soft)",
                padding: "7px 16px", marginBottom: -3,
                borderRadius: "10px 12px 0 0 / 9px 11px 0 0",
                fontFamily: "var(--hand-bold)", fontWeight: 600, fontSize: 17,
                cursor: "pointer",
                transform: finTab === tab.k ? "translateY(-1px)" : "none",
              }}
            >{tab.label}</button>
          ))}
        </div>
        {/* Tab content */}
        <div style={{ padding: 16 }}>
          {finTab === "standard" && (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, alignItems: "start" }}>
              <FinBreakdown />
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <StickyNote rot={-1.5}>Standard federal repayment — what you pay if you take a private-sector job and just pay it down.</StickyNote>
                <Bar value={62} label="Affordability vs cohort" color="var(--marker-green)" />
              </div>
            </div>
          )}
          {finTab === "pslf" && (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, alignItems: "start" }}>
              <PSLFCard />
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <StickyNote rot={1.5} color="#c8e6c9">Only if you work gov / 501(c)(3). 120 qualifying payments → remaining balance forgiven, tax-free.</StickyNote>
                <div className="label-mono">requires: full-time qualifying employer · IDR plan enrollment · LRAP from school covers most of the IDR payment.</div>
              </div>
            </div>
          )}
          {finTab === "schedule" && (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, alignItems: "start" }}>
              <div>
                <div className="label-tiny" style={{ marginBottom: 8 }}>Standard 10-yr schedule</div>
                <YearByYear pslf={false} />
              </div>
              <div>
                <div className="label-tiny" style={{ marginBottom: 8 }}>PSLF / IDR schedule</div>
                <YearByYear pslf={true} />
              </div>
            </div>
          )}
        </div>
      </div>

      {anno && (<>
        <Anno style={{ position: "absolute", top: 70, left: 360 }} rot={-2}>bigger hero radar = instant read</Anno>
        <Anno style={{ position: "absolute", top: 320, right: 24 }} rot={2} color="var(--marker-green)">tabs unfold the financial story on demand</Anno>
      </>)}
    </div>
  );
}

// Narrowed to chosen direction: merged B + A-hero + tabbed financials.
// DetailVarA / B / C kept above for reference.
window.DetailVariations = [
  { key: "★", title: "Story columns + big hero + financial tabs", Comp: DetailMerged },
];
