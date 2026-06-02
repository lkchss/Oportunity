/* shared.jsx — sketch primitives + hand-drawn radar + sample profiles */

const SAMPLE_PROFILES = {
  splitter: {
    name: "Maya — Splitter",
    lsat: 173, gpa: 3.21, goal: "BigLaw", state: "NY",
    income: "65k_130k", scholarship: 7,
    blurb: "High LSAT, low GPA. Wants NYC BigLaw.",
  },
  pi: {
    name: "Jordan — Public Interest",
    lsat: 164, gpa: 3.78, goal: "Public Interest", state: "DC",
    income: "under_65k", scholarship: 9,
    blurb: "Cares about LRAP + PSLF. Wants gov / nonprofit.",
  },
  t14: {
    name: "Sam — T14 Hopeful",
    lsat: 169, gpa: 3.85, goal: "Federal Clerkship", state: "CA",
    income: "130k_200k", scholarship: 5,
    blurb: "Reaching for top-10. Clerkship pipeline matters.",
  },
  unsure: {
    name: "Alex — Undecided",
    lsat: null, gpa: 3.62, goal: "Unsure", state: "",
    income: "prefer_not", scholarship: 6,
    blurb: "Hasn't taken LSAT. Still exploring goals.",
  },
};

/* Sample ranked schools — illustrative wireframe data only */
const SAMPLE_SCHOOLS = [
  { id: 1, name: "Yale Law School",        loc: "New Haven, CT", rank: 1,  tier: "reach",  scores: [62, 99, 82, 70, 45, 38], biglaw: 0.76, clerk: 0.32, bar: 0.99, debt: "$248k" },
  { id: 2, name: "NYU School of Law",       loc: "New York, NY",  rank: 9,  tier: "target", scores: [78, 91, 89, 95, 68, 55], biglaw: 0.69, clerk: 0.14, bar: 0.97, debt: "$215k" },
  { id: 3, name: "Columbia Law",            loc: "New York, NY",  rank: 8,  tier: "reach",  scores: [66, 92, 88, 94, 52, 50], biglaw: 0.77, clerk: 0.13, bar: 0.97, debt: "$232k" },
  { id: 4, name: "Cornell Law",             loc: "Ithaca, NY",    rank: 14, tier: "target", scores: [82, 86, 81, 78, 71, 64], biglaw: 0.72, clerk: 0.09, bar: 0.96, debt: "$198k" },
  { id: 5, name: "Fordham Law",             loc: "New York, NY",  rank: 35, tier: "safety", scores: [94, 68, 72, 90, 85, 78], biglaw: 0.41, clerk: 0.04, bar: 0.92, debt: "$165k" },
  { id: 6, name: "Boston College Law",      loc: "Newton, MA",    rank: 20, tier: "target", scores: [80, 79, 71, 64, 76, 68], biglaw: 0.45, clerk: 0.08, bar: 0.94, debt: "$182k" },
  { id: 7, name: "Notre Dame Law",          loc: "South Bend, IN",rank: 20, tier: "reach",  scores: [58, 80, 76, 42, 82, 71], biglaw: 0.41, clerk: 0.16, bar: 0.92, debt: "$155k" },
  { id: 8, name: "George Washington Law",   loc: "Washington, DC",rank: 25, tier: "target", scores: [78, 75, 84, 88, 70, 66], biglaw: 0.52, clerk: 0.07, bar: 0.91, debt: "$201k" },
];

const SCORE_NAMES = ["Admiss.", "Prestige", "Career", "Location", "Schol.", "Financial"];
const SCORE_NAMES_LONG = ["Admissibility", "Prestige", "Career Fit", "Location Fit", "Scholarship", "Financial"];

/* tiny seeded jitter so the SVG strokes feel hand-drawn but stable */
function jitter(seed, amp = 1.5) {
  const x = Math.sin(seed * 9301 + 49297) * 233280;
  return ((x - Math.floor(x)) - 0.5) * 2 * amp;
}

/* Hand-drawn 6-axis radar chart */
function Radar({ scores, size = 220, color = "var(--marker-blue)", showLabels = true, showRings = true, fill = true }) {
  const cx = size / 2, cy = size / 2;
  const r = size * 0.38;
  const axes = 6;
  const ringSteps = [0.33, 0.66, 1.0];
  const pts = scores.map((v, i) => {
    const angle = (Math.PI * 2 / axes) * i - Math.PI / 2;
    const rad = (Math.max(0, Math.min(100, v)) / 100) * r;
    const jx = jitter(i * 7 + 1, 2);
    const jy = jitter(i * 7 + 2, 2);
    return [cx + Math.cos(angle) * rad + jx, cy + Math.sin(angle) * rad + jy];
  });
  const polyStr = pts.map(p => p.join(",")).join(" ");

  const axisPts = Array.from({ length: axes }, (_, i) => {
    const angle = (Math.PI * 2 / axes) * i - Math.PI / 2;
    return [cx + Math.cos(angle) * r, cy + Math.sin(angle) * r];
  });

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ overflow: "visible" }}>
      {showRings && ringSteps.map((s, ri) => {
        const ringPts = Array.from({ length: axes }, (_, i) => {
          const angle = (Math.PI * 2 / axes) * i - Math.PI / 2;
          const j1 = jitter(ri * 31 + i * 3, 1.4);
          const j2 = jitter(ri * 31 + i * 3 + 1, 1.4);
          return `${cx + Math.cos(angle) * r * s + j1},${cy + Math.sin(angle) * r * s + j2}`;
        }).join(" ");
        return <polygon key={ri} points={ringPts} fill="none" stroke="rgba(0,0,0,0.18)" strokeWidth="1.3" strokeLinejoin="round" />;
      })}
      {axisPts.map(([x, y], i) => (
        <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke="rgba(0,0,0,0.18)" strokeWidth="1.2" />
      ))}
      <polygon
        points={polyStr}
        fill={fill ? color : "none"}
        fillOpacity={fill ? 0.18 : 0}
        stroke={color}
        strokeWidth="3"
        strokeLinejoin="round"
      />
      {pts.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r="3.5" fill={color} stroke="var(--ink)" strokeWidth="1" />
      ))}
      {showLabels && axisPts.map(([x, y], i) => {
        const dx = (x - cx) * 1.18;
        const dy = (y - cy) * 1.22;
        return (
          <text
            key={i}
            x={cx + dx} y={cy + dy + 4}
            textAnchor="middle"
            fontFamily="Architects Daughter, Kalam, sans-serif"
            fontSize="11"
            fill="var(--ink)"
          >{SCORE_NAMES[i]}</text>
        );
      })}
    </svg>
  );
}

/* Hand-drawn arrow that points from (x1,y1) to (x2,y2). Coords relative to parent. */
function Arrow({ from, to, color = "var(--marker-red)", curve = 0.3, dashed = false }) {
  const [x1, y1] = from;
  const [x2, y2] = to;
  const mx = (x1 + x2) / 2 + (y2 - y1) * curve;
  const my = (y1 + y2) / 2 - (x2 - x1) * curve;
  const d = `M ${x1} ${y1} Q ${mx} ${my} ${x2} ${y2}`;
  // arrowhead
  const ang = Math.atan2(y2 - my, x2 - mx);
  const ah = 10;
  const ax1 = x2 - Math.cos(ang - 0.5) * ah;
  const ay1 = y2 - Math.sin(ang - 0.5) * ah;
  const ax2 = x2 - Math.cos(ang + 0.5) * ah;
  const ay2 = y2 - Math.sin(ang + 0.5) * ah;
  return (
    <svg className="anno-arrow" style={{ left: 0, top: 0, width: "100%", height: "100%", position: "absolute" }} viewBox={`0 0 1000 1000`} preserveAspectRatio="none">
      <path d={d} stroke={color} strokeWidth="2.5" fill="none" strokeLinecap="round" strokeDasharray={dashed ? "6 4" : ""} />
      <polygon points={`${x2},${y2} ${ax1},${ay1} ${ax2},${ay2}`} fill={color} />
    </svg>
  );
}

/* Hand-drawn progress bar */
function Bar({ value, color = "var(--marker-blue)", height = 10, label }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
      {label && <div className="label-tiny" style={{ display: "flex", justifyContent: "space-between" }}>
        <span>{label}</span><span className="label-mono">{value}</span>
      </div>}
      <div style={{
        height, border: "2px solid var(--ink)", borderRadius: 6,
        background: "var(--paper)", overflow: "hidden", position: "relative",
      }}>
        <div style={{
          width: `${value}%`, height: "100%",
          background: color,
          borderRight: "2px solid var(--ink)",
        }} />
      </div>
    </div>
  );
}

/* "tier dot" */
function TierPill({ tier }) {
  const map = { safety: "Safety", target: "Target", reach: "Reach", "hard reach": "Hard Reach", hard: "Hard Reach" };
  const cls = tier === "hard reach" ? "hard" : tier;
  return <span className={`sk-pill ${cls}`}>{map[tier] || tier}</span>;
}

/* Sticky-note annotation */
function StickyNote({ children, color = "var(--hi-yellow)", rot = -2, style = {} }) {
  return (
    <div style={{
      background: color,
      border: "2.5px solid var(--ink)",
      padding: "8px 12px",
      fontFamily: "var(--hand-bold)",
      fontSize: 16,
      transform: `rotate(${rot}deg)`,
      boxShadow: "3px 3px 0 rgba(0,0,0,0.15)",
      borderRadius: "8px 12px 7px 11px / 9px 8px 13px 7px",
      ...style,
    }}>{children}</div>
  );
}

/* Annotation callout w/ arrow */
function Anno({ children, color = "var(--marker-red)", rot = -1.5, style = {} }) {
  return (
    <div className="anno-callout" style={{ borderColor: color, color, transform: `rotate(${rot}deg)`, ...style }}>
      {children}
    </div>
  );
}

/* Section title above a wireframe */
function ScreenHeader({ title, sub }) {
  return (
    <div style={{ display: "flex", alignItems: "baseline", gap: 14, marginBottom: 14 }}>
      <h3 style={{ fontSize: 22 }}>{title}</h3>
      {sub && <span className="label-mono">{sub}</span>}
    </div>
  );
}

Object.assign(window, {
  SAMPLE_PROFILES, SAMPLE_SCHOOLS, SCORE_NAMES, SCORE_NAMES_LONG,
  Radar, Arrow, Bar, TierPill, StickyNote, Anno, ScreenHeader, jitter,
});
