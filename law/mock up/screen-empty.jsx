/* screen-empty.jsx — No-match / edge case states (2) */

function EmptyVarA({ anno, onAdjust }) {
  return (
    <div className="sk-card" style={{ padding: 40, position: "relative", display: "flex", flexDirection: "column", alignItems: "center", gap: 16, minHeight: 380 }}>
      {/* Sad radar — all low */}
      <Radar scores={[12, 8, 15, 10, 18, 9]} size={220} color="var(--marker-red)" />
      <h2 style={{ marginTop: 4 }}>No matches above the threshold</h2>
      <p style={{ fontSize: 17, textAlign: "center", maxWidth: 520, lineHeight: 1.4 }}>
        Your filter combo (LSAT 173 + must be in <strong>WY</strong> + scholarship critical) is too narrow.
        Loosen one of these to see results.
      </p>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", justifyContent: "center" }}>
        <button className="sk-btn" onClick={onAdjust}>↺ widen state to whole region</button>
        <button className="sk-btn">↺ relax scholarship priority</button>
        <button className="sk-btn">↺ include reach schools</button>
      </div>
      <div style={{ display: "flex", gap: 14, marginTop: 8 }}>
        <StickyNote rot={-3} color="var(--hi-pink)">last action that emptied it: <strong>filter: state = WY</strong></StickyNote>
      </div>
      {anno && (<>
        <Anno style={{ position: "absolute", top: 30, right: 30 }} rot={2}>show WHY it's empty + one-tap unstuck</Anno>
      </>)}
    </div>
  );
}

function EmptyVarB({ anno }) {
  // "No LSAT yet" partial-info state
  return (
    <div className="sk-card" style={{ padding: 30, position: "relative" }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 280px", gap: 24, alignItems: "center" }}>
        <div>
          <h2>Showing GPA-only matches</h2>
          <p style={{ fontSize: 16, lineHeight: 1.4, maxWidth: 560 }}>
            You haven't taken the LSAT yet — results are <span className="sk-hi">capped at "target"</span> and admissibility scores stop at 65.
            Estimate your LSAT to unlock safety bucket + financial projections.
          </p>
          <div style={{ display: "flex", gap: 10, marginTop: 12 }}>
            <button className="sk-btn primary">⌨︎ estimate my LSAT</button>
            <button className="sk-btn ghost">continue with GPA only</button>
          </div>
          <div style={{ marginTop: 16, display: "flex", gap: 10 }}>
            <span className="sk-pill target">8 target matches</span>
            <span className="sk-pill reach">14 reach matches</span>
            <span className="sk-pill" style={{ opacity: 0.4 }}>safety — locked</span>
          </div>
        </div>
        <div className="sk-box" style={{ padding: 14, background: "var(--paper-2)" }}>
          <div className="label-tiny">If LSAT = 160</div>
          <Radar scores={[55, 60, 70, 65, 55, 50]} size={170} showLabels={false} color="var(--marker-blue)" />
          <div className="label-tiny" style={{ marginTop: 8 }}>If LSAT = 170</div>
          <Radar scores={[88, 82, 80, 75, 72, 68]} size={170} showLabels={false} color="var(--marker-green)" />
        </div>
      </div>
      {anno && (<>
        <Anno style={{ position: "absolute", top: 30, left: 20 }} rot={-2}>partial-info state — show range, not nothing</Anno>
      </>)}
    </div>
  );
}

window.EmptyVariations = [
  { key: "A", title: "Zero matches — why + unstick", Comp: EmptyVarA },
  { key: "B", title: "No LSAT yet — show range",     Comp: EmptyVarB },
];
