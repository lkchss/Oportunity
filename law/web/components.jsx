/* Shared presentational components and constants. Plain style. */

const SCORE_NAMES = ["Admiss.", "Prestige", "Career", "Location", "Schol.", "Financial"];
const SCORE_NAMES_LONG = ["Admissibility", "Prestige", "Career Fit", "Location Fit", "Scholarship", "Financial"];

const STATES = [
  "AL","AK","AZ","AR","CA","CO","CT","DC","DE","FL","GA","HI","ID","IL",
  "IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE",
  "NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD",
  "TN","TX","UT","VT","VA","WA","WV","WI","WY",
];

const GOALS = [
  "BigLaw", "Federal Clerkship", "Government", "Public Interest",
  "Solo/Small Firm", "In-house", "Academia", "Unsure",
];

const INCOME_OPTIONS = [
  ["under_65k", "Under $65K"],
  ["65k_130k", "$65K – $130K"],
  ["130k_200k", "$130K – $200K"],
  ["over_200k", "Over $200K"],
  ["prefer_not", "Prefer not to say"],
];

const TIER_CLASS = { safety: "safety", target: "target", reach: "reach", "hard reach": "hard" };
const TIER_LABEL = { safety: "Safety", target: "Target", reach: "Reach", "hard reach": "Hard Reach" };

function fmtMoney(n) {
  if (n == null) return "—";
  return "$" + Math.round(n).toLocaleString();
}
function fmtMoneyShort(n) {
  if (n == null) return "—";
  if (Math.abs(n) >= 1000) return "$" + Math.round(n / 1000) + "k";
  return "$" + Math.round(n);
}
function fmtPct(frac) {
  if (frac == null) return "—";
  return Math.round(frac * 100) + "%";
}
/* USNWR rank — the 999 sentinel means Rank-Not-Published; show N/A. */
function fmtRank(rank) {
  if (rank == null || rank >= 999) return "N/A";
  return "#" + rank;
}

/* Clean 6-axis radar chart (SVG, no hand-drawn jitter). */
function Radar({ scores, size = 200, color = "var(--accent)", showLabels = true, showRings = true, fill = true }) {
  const cx = size / 2, cy = size / 2;
  const r = size * 0.36;
  const axes = 6;
  const rings = [0.33, 0.66, 1.0];

  const point = (v, i) => {
    const angle = (Math.PI * 2 / axes) * i - Math.PI / 2;
    const rad = (Math.max(0, Math.min(100, v)) / 100) * r;
    return [cx + Math.cos(angle) * rad, cy + Math.sin(angle) * rad];
  };
  const axisEnd = (i) => {
    const angle = (Math.PI * 2 / axes) * i - Math.PI / 2;
    return [cx + Math.cos(angle) * r, cy + Math.sin(angle) * r];
  };

  const poly = scores.map((v, i) => point(v, i).join(",")).join(" ");

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ overflow: "visible" }}>
      {showRings && rings.map((s, ri) => {
        const pts = Array.from({ length: axes }, (_, i) => {
          const angle = (Math.PI * 2 / axes) * i - Math.PI / 2;
          return `${cx + Math.cos(angle) * r * s},${cy + Math.sin(angle) * r * s}`;
        }).join(" ");
        return <polygon key={ri} points={pts} fill="none" stroke="var(--line)" strokeWidth="1" />;
      })}
      {Array.from({ length: axes }, (_, i) => {
        const [x, y] = axisEnd(i);
        return <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke="var(--line)" strokeWidth="1" />;
      })}
      <polygon
        points={poly}
        fill={fill ? color : "none"}
        fillOpacity={fill ? 0.15 : 0}
        stroke={color}
        strokeWidth="2"
        strokeLinejoin="round"
      />
      {scores.map((v, i) => {
        const [x, y] = point(v, i);
        return <circle key={i} cx={x} cy={y} r="2.5" fill={color} />;
      })}
      {showLabels && Array.from({ length: axes }, (_, i) => {
        const [x, y] = axisEnd(i);
        const dx = (x - cx) * 1.22;
        const dy = (y - cy) * 1.25;
        return (
          <text key={i} x={cx + dx} y={cy + dy + 4} textAnchor="middle"
            fontFamily="var(--font)" fontSize="11" fill="var(--ink-soft)">
            {SCORE_NAMES[i]}
          </text>
        );
      })}
    </svg>
  );
}

/* Distinct colors for overlaying multiple schools on one radar. */
const SERIES_COLORS = ["#2563eb", "#dc2626", "#15803d", "#b45309", "#7c3aed", "#0891b2"];

/* Multi-series radar: several schools' six-axis profiles drawn on ONE chart. */
function RadarOverlay({ series, size = 280 }) {
  const cx = size / 2, cy = size / 2;
  const r = size * 0.36;
  const axes = 6;
  const rings = [0.33, 0.66, 1.0];

  const point = (v, i) => {
    const angle = (Math.PI * 2 / axes) * i - Math.PI / 2;
    const rad = (Math.max(0, Math.min(100, v)) / 100) * r;
    return [cx + Math.cos(angle) * rad, cy + Math.sin(angle) * rad];
  };
  const axisEnd = (i) => {
    const angle = (Math.PI * 2 / axes) * i - Math.PI / 2;
    return [cx + Math.cos(angle) * r, cy + Math.sin(angle) * r];
  };

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ overflow: "visible" }}>
      {rings.map((s, ri) => {
        const pts = Array.from({ length: axes }, (_, i) => {
          const angle = (Math.PI * 2 / axes) * i - Math.PI / 2;
          return `${cx + Math.cos(angle) * r * s},${cy + Math.sin(angle) * r * s}`;
        }).join(" ");
        return <polygon key={ri} points={pts} fill="none" stroke="var(--line)" strokeWidth="1" />;
      })}
      {Array.from({ length: axes }, (_, i) => {
        const [x, y] = axisEnd(i);
        return <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke="var(--line)" strokeWidth="1" />;
      })}
      {series.map((ser, si) => {
        const color = ser.color || SERIES_COLORS[si % SERIES_COLORS.length];
        const poly = ser.scores.map((v, i) => point(v, i).join(",")).join(" ");
        return (
          <g key={si}>
            <polygon points={poly} fill={color} fillOpacity="0.08"
              stroke={color} strokeWidth="2" strokeLinejoin="round" />
            {ser.scores.map((v, i) => {
              const [x, y] = point(v, i);
              return <circle key={i} cx={x} cy={y} r="2.5" fill={color} />;
            })}
          </g>
        );
      })}
      {Array.from({ length: axes }, (_, i) => {
        const [x, y] = axisEnd(i);
        const dx = (x - cx) * 1.22;
        const dy = (y - cy) * 1.25;
        return (
          <text key={i} x={cx + dx} y={cy + dy + 4} textAnchor="middle"
            fontFamily="var(--font)" fontSize="11" fill="var(--ink-soft)">
            {SCORE_NAMES[i]}
          </text>
        );
      })}
    </svg>
  );
}

function Bar({ value, label, color = "var(--accent)" }) {
  const v = Math.round(value);
  return (
    <div className="bar-wrap">
      {label && (
        <div className="bar-head"><span>{label}</span><span className="v">{v}</span></div>
      )}
      <div className="bar-track">
        <div className="bar-fill" style={{ width: `${Math.max(0, Math.min(100, v))}%`, background: color }} />
      </div>
    </div>
  );
}

function TierPill({ tier }) {
  const cls = TIER_CLASS[tier] || "neutral";
  return <span className={`pill ${cls}`}>{TIER_LABEL[tier] || tier}</span>;
}

/* Small "?" affordance — reveals explanatory text on hover/focus/click. */
function InfoTip({ text, label = "More info" }) {
  const [open, setOpen] = React.useState(false);
  return (
    <span className="infotip"
      onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
      <button type="button" className="infotip-btn" aria-label={label}
        aria-expanded={open} onClick={() => setOpen((v) => !v)}
        onFocus={() => setOpen(true)} onBlur={() => setOpen(false)}>?</button>
      {open && <span className="infotip-pop" role="tooltip">{text}</span>}
    </span>
  );
}

Object.assign(window, {
  SCORE_NAMES, SCORE_NAMES_LONG, STATES, GOALS, INCOME_OPTIONS, SERIES_COLORS,
  TIER_LABEL, TIER_CLASS, fmtMoney, fmtMoneyShort, fmtPct, fmtRank,
  Radar, RadarOverlay, Bar, TierPill, InfoTip,
});
