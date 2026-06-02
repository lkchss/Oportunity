/* screen-sitemap.jsx — high-level flow overview */

function Node({ x, y, w = 160, h = 80, title, sub, color = "var(--paper-2)", onJump }) {
  return (
    <div
      onClick={onJump}
      style={{
        position: "absolute",
        left: x, top: y, width: w, height: h,
        background: color,
        border: "3px solid var(--ink)",
        borderRadius: "12px 8px 14px 7px / 8px 13px 7px 11px",
        boxShadow: "3px 3px 0 rgba(0,0,0,0.12)",
        padding: 10,
        display: "flex", flexDirection: "column", justifyContent: "center",
        cursor: onJump ? "pointer" : "default",
        transform: `rotate(${(x % 7 - 3) * 0.1}deg)`,
      }}
    >
      <div style={{ fontFamily: "var(--hand-bold)", fontSize: 17, lineHeight: 1.05 }}>{title}</div>
      {sub && <div className="label-mono" style={{ marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

function FlowArrow({ x1, y1, x2, y2, color = "var(--ink)", label }) {
  const mx = (x1 + x2) / 2;
  const my = (y1 + y2) / 2 + (Math.abs(x2 - x1) > 100 ? 0 : -20);
  const d = `M ${x1} ${y1} Q ${mx} ${my} ${x2} ${y2}`;
  const ang = Math.atan2(y2 - my, x2 - mx);
  const ah = 12;
  const ax1 = x2 - Math.cos(ang - 0.4) * ah;
  const ay1 = y2 - Math.sin(ang - 0.4) * ah;
  const ax2 = x2 - Math.cos(ang + 0.4) * ah;
  const ay2 = y2 - Math.sin(ang + 0.4) * ah;
  return (
    <g>
      <path d={d} stroke={color} strokeWidth="3" fill="none" strokeLinecap="round" />
      <polygon points={`${x2},${y2} ${ax1},${ay1} ${ax2},${ay2}`} fill={color} />
      {label && <text x={mx} y={my - 6} textAnchor="middle" fontFamily="Architects Daughter" fontSize="13" fill={color}>{label}</text>}
    </g>
  );
}

function Sitemap({ onJumpTo }) {
  // Coordinate system inside an absolute-positioned canvas
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <ScreenHeader title="User flow" sub="lightly interactive — click any node to jump" />
      <div className="sk-card" style={{ padding: 22, position: "relative" }}>
        <div style={{ position: "relative", height: 520, width: "100%", maxWidth: 1100, margin: "0 auto" }} className="gridlines">
          {/* SVG arrows layer */}
          <svg style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none" }}>
            <FlowArrow x1={170} y1={90}  x2={250} y2={90}  label="fill profile" />
            <FlowArrow x1={490} y1={90}  x2={580} y2={90}  label="see matches" />
            <FlowArrow x1={820} y1={90}  x2={900} y2={150} label="drill in" />
            <FlowArrow x1={680} y1={150} x2={680} y2={300} label="pick 2-3" />
            <FlowArrow x1={680} y1={380} x2={900} y2={330} label="diff them" />
            <FlowArrow x1={400} y1={150} x2={400} y2={300} label="filter too tight" color="var(--marker-red)" />
            <FlowArrow x1={490} y1={350} x2={400} y2={150} label="loosen" color="var(--marker-red)" />
          </svg>

          <Node x={10}  y={60}  w={150} h={70}  title="Landing"        sub="optional"        onJump={() => onJumpTo && onJumpTo("profile")} />
          <Node x={250} y={50}  w={240} h={90}  title="Profile Dashboard" sub="editable sidebar" color="var(--hi-yellow-soft)" onJump={() => onJumpTo && onJumpTo("profile")} />
          <Node x={580} y={50}  w={240} h={90}  title="Results"        sub="ranked + radar"  color="var(--hi-yellow-soft)" onJump={() => onJumpTo && onJumpTo("results")} />
          <Node x={900} y={150} w={190} h={90}  title="School Detail"  sub="financial + PSLF" color="#bbdefb"               onJump={() => onJumpTo && onJumpTo("detail")} />

          <Node x={580} y={300} w={240} h={90}  title="Compare (2-3)"  sub="overlay radar"   color="#c8e6c9"               onJump={() => onJumpTo && onJumpTo("compare")} />
          <Node x={250} y={300} w={240} h={90}  title="Empty / partial" sub="why + unstick"  color="#ffcdd2"               onJump={() => onJumpTo && onJumpTo("empty")} />

          <StickyNote style={{ position: "absolute", left: 20, top: 240, maxWidth: 200 }} rot={-3}>
            Sidebar lives on every screen → any field tweak re-ranks live
          </StickyNote>
          <StickyNote style={{ position: "absolute", right: 30, top: 410, maxWidth: 220 }} rot={2} color="#bbdefb">
            Save / share comes off the detail + compare views, not from results.
          </StickyNote>
        </div>
      </div>

      <div className="sk-card" style={{ padding: 18, display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 12 }}>
        {[
          ["1", "Open dashboard", "LSAT / GPA / goal / state"],
          ["2", "See live preview", "top 3 mini radars"],
          ["3", "Run full match", "ranked top 20"],
          ["4", "Skim radars", "shape ≈ trade-offs"],
          ["5", "Open 2-3 details", "PSLF / financial / fit"],
          ["6", "Compare + decide", "overlay or table"],
        ].map(([n, t, d]) => (
          <div key={n} className="sk-box" style={{ padding: 10 }}>
            <div className="label-mono">step {n}</div>
            <div style={{ fontFamily: "var(--hand-bold)", fontSize: 17 }}>{t}</div>
            <div className="label-mono">{d}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

window.Sitemap = Sitemap;
