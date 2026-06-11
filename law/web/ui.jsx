/* ui.jsx — shared presentational components. */

const SCORE_NAMES = ["Admiss.", "Prestige", "Career", "Location", "Schol.", "Financial"];
const SCORE_NAMES_LONG = ["Admissibility", "Prestige", "Career fit", "Location fit", "Scholarship", "Financial"];
const SERIES_COLORS = ["#1e4d35", "#b45309", "#1e3a5f", "#8c3120", "#6a3aa0", "#0e7490"];

/* grade color: driven by the score itself, not the admit tier */
function gradeColor(score) {
  return score >= 85 ? "#1f6b3d" : score >= 70 ? "#4e8a66" : score >= 55 ? "#b45309" : "#9a3324";
}

function TierTag({ tier }) {
  const t = TIERS[tier];
  return (
    <span className={`tier-tag ${t.cls}`}>
      <span className="dot"></span>{t.label}
    </span>);

}
function TierPill({ tier }) {
  const t = TIERS[tier];
  return <span className={`tier-pill ${t.cls}`}>{t.label}</span>;
}

function ScoreRing({ value, color = "var(--accent)", size = 52 }) {
  const r = size / 2 - 4;
  const circ = 2 * Math.PI * r;
  return (
    <div className="sc-ring" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--line)" strokeWidth="4.5"></circle>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth="4.5"
        strokeDasharray={`${clamp(value) / 100 * circ} ${circ}`} strokeLinecap="round"
        transform={`rotate(-90 ${size / 2} ${size / 2})`}></circle>
      </svg>
      <span className="ring-num">{Math.round(value)}</span>
    </div>);

}

function Bar({ value, label, color = "var(--accent)" }) {
  const v = Math.round(value);
  return (
    <div className="bar-wrap">
      {label && <div className="bar-head"><span>{label}</span><span className="v">{v}</span></div>}
      <div className="bar-track">
        <div className="bar-fill" style={{ width: `${clamp(v)}%`, background: color }}></div>
      </div>
    </div>);

}

function CellBar({ frac, color = "var(--accent)" }) {
  return (
    <span className="cellbar">
      <span className="track"><span className="fill" style={{ width: `${Math.round(clamp((frac || 0) * 100))}%`, background: color, display: "block" }}></span></span>
      <span className="pv">{fmtPct(frac)}</span>
    </span>);

}

function Radar({ scores, size = 230, color = "var(--accent)", showLabels = true }) {
  const cx = size / 2,cy = size / 2,r = size * 0.36,axes = 6;
  const pt = (v, i) => {
    const a = Math.PI * 2 / axes * i - Math.PI / 2;
    const rad = clamp(v) / 100 * r;
    return [cx + Math.cos(a) * rad, cy + Math.sin(a) * rad];
  };
  const end = (i) => {
    const a = Math.PI * 2 / axes * i - Math.PI / 2;
    return [cx + Math.cos(a) * r, cy + Math.sin(a) * r];
  };
  const ringPts = (s) => Array.from({ length: axes }, (_, i) => {
    const a = Math.PI * 2 / axes * i - Math.PI / 2;
    return `${cx + Math.cos(a) * r * s},${cy + Math.sin(a) * r * s}`;
  }).join(" ");
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ overflow: "visible" }}>
      {[0.33, 0.66, 1].map((s) =>
      <polygon key={s} points={ringPts(s)} fill="none" stroke="var(--line)" strokeWidth="1"></polygon>
      )}
      {Array.from({ length: axes }, (_, i) => {
        const [x, y] = end(i);
        return <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke="var(--line)" strokeWidth="1"></line>;
      })}
      <polygon points={scores.map((v, i) => pt(v, i).join(",")).join(" ")}
      fill={color} fillOpacity="0.14" stroke={color} strokeWidth="2" strokeLinejoin="round"></polygon>
      {scores.map((v, i) => {
        const [x, y] = pt(v, i);
        return <circle key={i} cx={x} cy={y} r="2.5" fill={color}></circle>;
      })}
      {showLabels && Array.from({ length: axes }, (_, i) => {
        const [x, y] = end(i);
        return (
          <text key={i} x={cx + (x - cx) * 1.24} y={cy + (y - cy) * 1.26 + 4} textAnchor="middle"
          fontFamily="var(--sans)" fontSize="11" fill="var(--soft)">{SCORE_NAMES[i]}</text>);

      })}
    </svg>);

}

function RadarOverlay({ series, size = 290 }) {
  const cx = size / 2,cy = size / 2,r = size * 0.36,axes = 6;
  const pt = (v, i) => {
    const a = Math.PI * 2 / axes * i - Math.PI / 2;
    const rad = clamp(v) / 100 * r;
    return [cx + Math.cos(a) * rad, cy + Math.sin(a) * rad];
  };
  const end = (i) => {
    const a = Math.PI * 2 / axes * i - Math.PI / 2;
    return [cx + Math.cos(a) * r, cy + Math.sin(a) * r];
  };
  const ringPts = (s) => Array.from({ length: axes }, (_, i) => {
    const a = Math.PI * 2 / axes * i - Math.PI / 2;
    return `${cx + Math.cos(a) * r * s},${cy + Math.sin(a) * r * s}`;
  }).join(" ");
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ overflow: "visible" }}>
      {[0.33, 0.66, 1].map((s) =>
      <polygon key={s} points={ringPts(s)} fill="none" stroke="var(--line)" strokeWidth="1"></polygon>
      )}
      {Array.from({ length: axes }, (_, i) => {
        const [x, y] = end(i);
        return <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke="var(--line)" strokeWidth="1"></line>;
      })}
      {series.map((ser, si) => {
        const color = ser.color || SERIES_COLORS[si % SERIES_COLORS.length];
        return (
          <g key={si}>
            <polygon points={ser.scores.map((v, i) => pt(v, i).join(",")).join(" ")}
            fill={color} fillOpacity="0.08" stroke={color} strokeWidth="2" strokeLinejoin="round"></polygon>
            {ser.scores.map((v, i) => {
              const [x, y] = pt(v, i);
              return <circle key={i} cx={x} cy={y} r="2.5" fill={color}></circle>;
            })}
          </g>);

      })}
      {Array.from({ length: axes }, (_, i) => {
        const [x, y] = end(i);
        return (
          <text key={i} x={cx + (x - cx) * 1.24} y={cy + (y - cy) * 1.26 + 4} textAnchor="middle"
          fontFamily="var(--sans)" fontSize="11" fill="var(--soft)">{SCORE_NAMES[i]}</text>);

      })}
    </svg>);

}

function InfoTip({ text, label = "More info" }) {
  const [open, setOpen] = React.useState(false);
  return (
    <span className="infotip" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
      <button type="button" className="infotip-btn" aria-label={label} aria-expanded={open}
      onClick={() => setOpen((v) => !v)} onFocus={() => setOpen(true)} onBlur={() => setOpen(false)}>?</button>
      {open && <span className="infotip-pop" role="tooltip">{text}</span>}
    </span>);

}

function Stat({ label, value, sub }) {
  return (
    <div className="stat">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>);

}

function Seg({ options, value, onChange }) {
  return (
    <div className="seg">
      {options.map((o) =>
      <button key={o.k} className={value === o.k ? "active" : ""}
      onClick={() => onChange(o.k)}>{o.label}</button>
      )}
    </div>);

}

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
    </div>);

}

function Methodology({ onClose }) {
  return (
    <Modal title="Methodology" onClose={onClose}>
      <div className="prose">
        <p>Every ABA-accredited school is scored against your profile on six 0–100 axes:</p>
        <ul>
          <li><strong>Admissibility</strong> : how your LSAT/GPA sit against the school's 25/50/75 percentiles, mapped to a tier (Safety / Target / Reach / Hard reach). Not your odds of admission.
          </li>
          <li><strong>Prestige</strong> : US News ranking, scaled linearly from 100 at rank 1.</li>
          <li><strong>Career fit</strong> : placement into your stated goal, discounted by employment
            and bar-passage outcomes.</li>
          <li><strong>Location fit</strong> : how strongly the school feeds your target market(s).</li>
          <li><strong>Scholarship</strong> : merit likelihood from the school's aid grid, net of
            conditional-scholarship risk.</li>
          <li><strong>Financial</strong> : projected net debt against your goal's typical starting salary.</li>
        </ul>
        <p>The composite is a weighted blend of the six; your sliders set the weights. It is then scaled
          by admit tier so unrealistic reaches don't top the list.</p>
        <p className="mono">All 196 ABA-accredited schools, scored from ABA 509 disclosures,
          ABA employment summaries, and College Scorecard data.</p>
      </div>
    </Modal>);

}

function Masthead({ view, onNav }) {
  return (
    <header className="masthead">
      <button type="button" className="brand" onClick={() => onNav("home")}
      aria-label="Opportunity: Law — back to start">
        Opportunity<span className="colon">:</span> Law
      </button>
      <nav>
        <button className={`nav-link ${view === "matches" ? "active" : ""}`}
        onClick={() => onNav("matches")}>your matches</button>
        <button className={`nav-link ${view === "rankings" ? "active" : ""}`}
        onClick={() => onNav("rankings")}>all schools</button>
        <button className="nav-link" onClick={() => onNav("methodology")}>methodology</button>
      </nav>
    </header>);

}

Object.assign(window, {
  SCORE_NAMES, SCORE_NAMES_LONG, SERIES_COLORS, gradeColor,
  TierTag, TierPill, ScoreRing, Bar, CellBar, Radar, RadarOverlay,
  InfoTip, Stat, Seg, Modal, Methodology, Masthead
});
