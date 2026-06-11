/* tweaks-panel.jsx — User-adjustable score-weight sliders for the results screen.
   Ported from law/mock up/tweaks-panel.jsx prototype shell; visuals follow the
   prototype; data flow follows the app's existing submit path (fetchMatch /
   buildPayload) so what-if, pure-fit, and transfer tabs stay consistent.

   Design:
   - Floating panel, fixed bottom-right, draggable header, marigold glass look.
   - Six sliders: Admissibility, Prestige, Career, Location, Scholarship, Financial.
     Each slider is a "relative importance" multiplier (0–3 in 0.1 steps).
     Default = 1.0 (no change to backend defaults). The backend normalizes.
   - Reset button restores all to 1.0.
   - Changes debounce 400 ms before re-submitting.
   - A trigger button ("Adjust weights") appears in the results toolbar.
   - When no weights differ from default (all 1.0), the payload key is omitted
     so backend responses are byte-identical to the no-TweaksPanel path.
*/

// ── Styles (injected once, scoped by .twp- prefix) ──────────────────────────
const _TWP_STYLE = `
  .twp-trigger{
    display:flex;align-items:center;gap:5px;
    height:30px;padding:0 12px;
    background:var(--surface);
    border:1px solid var(--line2);border-radius:8px;
    font:500 12.5px/1 var(--sans);color:var(--ink);cursor:pointer;
    transition:border-color .12s,background .12s;
  }
  .twp-trigger:hover{background:var(--bg2,#f0ede6);border-color:var(--line,#ccc);}
  .twp-trigger.active{
    background:var(--accent,#2f7a50);color:#fff;border-color:transparent;
  }
  .twp-trigger .dot{
    width:6px;height:6px;border-radius:50%;
    background:currentColor;opacity:.6;flex-shrink:0;
  }

  .twp-panel{
    position:fixed;right:16px;bottom:16px;z-index:999;width:290px;
    max-height:calc(100vh - 32px);display:flex;flex-direction:column;
    background:rgba(250,249,247,.82);color:#29261b;
    -webkit-backdrop-filter:blur(24px) saturate(160%);
    backdrop-filter:blur(24px) saturate(160%);
    border:.5px solid rgba(255,255,255,.65);border-radius:14px;
    box-shadow:0 1px 0 rgba(255,255,255,.5) inset,0 12px 40px rgba(0,0,0,.2);
    font:11.5px/1.4 var(--sans,ui-sans-serif,system-ui,sans-serif);
    overflow:hidden;
  }
  .twp-hd{
    display:flex;align-items:center;justify-content:space-between;
    padding:10px 10px 10px 14px;cursor:move;user-select:none;
    border-bottom:.5px solid rgba(0,0,0,.07);
  }
  .twp-hd-left{display:flex;align-items:center;gap:7px;}
  .twp-hd b{font-size:12px;font-weight:600;letter-spacing:.01em;color:#29261b;}
  .twp-hd-sub{font-size:10.5px;color:rgba(41,38,27,.45);}
  .twp-x{
    appearance:none;border:0;background:transparent;color:rgba(41,38,27,.5);
    width:22px;height:22px;border-radius:6px;cursor:pointer;
    font-size:14px;line-height:22px;text-align:center;
  }
  .twp-x:hover{background:rgba(0,0,0,.07);color:#29261b;}

  .twp-body{
    padding:12px 14px 14px;display:flex;flex-direction:column;gap:11px;
    overflow-y:auto;overflow-x:hidden;min-height:0;
    scrollbar-width:thin;scrollbar-color:rgba(0,0,0,.12) transparent;
  }
  .twp-body::-webkit-scrollbar{width:6px;}
  .twp-body::-webkit-scrollbar-thumb{background:rgba(0,0,0,.12);border-radius:3px;}

  .twp-row{display:flex;flex-direction:column;gap:4px;}
  .twp-lbl{
    display:flex;justify-content:space-between;align-items:baseline;
    font-size:11px;color:rgba(41,38,27,.65);
  }
  .twp-lbl span:first-child{font-weight:500;color:#29261b;}
  .twp-lbl span:last-child{
    font-variant-numeric:tabular-nums;color:rgba(41,38,27,.45);
    font-size:10.5px;
  }
  .twp-lbl span.changed{color:var(--accent,#2f7a50);font-weight:600;}

  .twp-slider-wrap{position:relative;}
  .twp-slider{
    appearance:none;-webkit-appearance:none;
    width:100%;height:4px;border-radius:999px;
    background:rgba(0,0,0,.1);outline:none;cursor:pointer;
    margin:5px 0;
  }
  .twp-slider::-webkit-slider-thumb{
    -webkit-appearance:none;appearance:none;
    width:14px;height:14px;border-radius:50%;
    background:#fff;border:.5px solid rgba(0,0,0,.14);
    box-shadow:0 1px 3px rgba(0,0,0,.22);cursor:pointer;
  }
  .twp-slider::-moz-range-thumb{
    width:14px;height:14px;border-radius:50%;
    background:#fff;border:.5px solid rgba(0,0,0,.14);
    box-shadow:0 1px 3px rgba(0,0,0,.22);cursor:pointer;
  }
  .twp-slider.changed::-webkit-slider-thumb{
    background:var(--accent,#2f7a50);border-color:var(--accent,#2f7a50);
  }
  .twp-slider.changed::-moz-range-thumb{
    background:var(--accent,#2f7a50);border-color:var(--accent,#2f7a50);
  }

  .twp-foot{
    display:flex;align-items:center;justify-content:space-between;
    padding:9px 14px;border-top:.5px solid rgba(0,0,0,.07);
  }
  .twp-reset{
    appearance:none;border:0;background:transparent;
    font:500 11.5px/1 var(--sans,sans-serif);
    color:rgba(41,38,27,.5);cursor:pointer;padding:0;
  }
  .twp-reset:hover{color:#29261b;text-decoration:underline;}
  .twp-reset:disabled{opacity:.3;cursor:default;text-decoration:none;}
  .twp-status{font-size:10.5px;color:rgba(41,38,27,.4);}
  .twp-status.pending{color:var(--accent,#2f7a50);}
`;

// ── Constants ───────────────────────────────────────────────────────────────

const TWP_DEFAULT = 1.0;    // multiplier default
const TWP_MIN     = 0.0;
const TWP_MAX     = 3.0;
const TWP_STEP    = 0.1;
const TWP_DEBOUNCE_MS = 400;

const TWP_AXES = [
  { key: "admissibility", label: "Admissibility",  tip: "How well your LSAT/GPA fit the school's profile" },
  { key: "prestige",      label: "Prestige",        tip: "US News rank on a top-heavy curve" },
  { key: "career_fit",    label: "Career fit",      tip: "Placement into your stated career goal" },
  { key: "location_fit",  label: "Location fit",    tip: "How strongly the school feeds your target market" },
  { key: "scholarship",   label: "Scholarship",     tip: "Merit likelihood and need-based aid signal" },
  { key: "financial",     label: "Financial",       tip: "Net debt vs. expected starting salary" },
];

function _defaultWeights() {
  return Object.fromEntries(TWP_AXES.map(({ key }) => [key, TWP_DEFAULT]));
}

function _isDefault(weights) {
  return TWP_AXES.every(({ key }) => weights[key] === TWP_DEFAULT);
}

// Build the weights object to send in the API payload.
// Returns null when all values are at default so the API skips the key entirely
// (byte-identical to no-TweaksPanel baseline).
function buildWeightsPayload(weights) {
  if (_isDefault(weights)) return null;
  return { ...weights };
}

Object.assign(window, { buildWeightsPayload });

// ── ScoreWeightsPanel component ──────────────────────────────────────────────

function ScoreWeightsPanel({ open, onClose, onWeightsChange }) {
  const [weights, setWeights] = React.useState(_defaultWeights);
  const debounceRef = React.useRef(null);
  const dragRef     = React.useRef(null);
  const offsetRef   = React.useRef({ right: 16, bottom: 16 });
  const PAD = 16;

  // ── Debounced notify ────────────────────────────────────────────────────
  const notifyChange = React.useCallback((w) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      onWeightsChange(buildWeightsPayload(w));
    }, TWP_DEBOUNCE_MS);
  }, [onWeightsChange]);

  const setAxis = React.useCallback((key, raw) => {
    const v = Math.round(raw * 10) / 10;  // snap to 0.1 steps
    setWeights((prev) => {
      const next = { ...prev, [key]: v };
      notifyChange(next);
      return next;
    });
  }, [notifyChange]);

  const reset = React.useCallback(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    const def = _defaultWeights();
    setWeights(def);
    onWeightsChange(null);  // null → no weights key → baseline
  }, [onWeightsChange]);

  // ── Drag-to-reposition ──────────────────────────────────────────────────
  const clampPanel = React.useCallback(() => {
    const panel = dragRef.current;
    if (!panel) return;
    const w = panel.offsetWidth, h = panel.offsetHeight;
    offsetRef.current = {
      right:  Math.max(PAD, Math.min(window.innerWidth  - w - PAD, offsetRef.current.right)),
      bottom: Math.max(PAD, Math.min(window.innerHeight - h - PAD, offsetRef.current.bottom)),
    };
    panel.style.right  = offsetRef.current.right  + "px";
    panel.style.bottom = offsetRef.current.bottom + "px";
  }, []);

  React.useEffect(() => {
    if (!open) return;
    clampPanel();
    const ro = typeof ResizeObserver !== "undefined"
      ? new ResizeObserver(clampPanel)
      : null;
    if (ro) ro.observe(document.documentElement);
    else window.addEventListener("resize", clampPanel);
    return () => { if (ro) ro.disconnect(); else window.removeEventListener("resize", clampPanel); };
  }, [open, clampPanel]);

  const onDragStart = React.useCallback((e) => {
    const panel = dragRef.current;
    if (!panel) return;
    const r = panel.getBoundingClientRect();
    const sx = e.clientX, sy = e.clientY;
    const startRight  = window.innerWidth  - r.right;
    const startBottom = window.innerHeight - r.bottom;
    const move = (ev) => {
      offsetRef.current = {
        right:  startRight  - (ev.clientX - sx),
        bottom: startBottom - (ev.clientY - sy),
      };
      clampPanel();
    };
    const up = () => {
      window.removeEventListener("mousemove", move);
      window.removeEventListener("mouseup", up);
    };
    window.addEventListener("mousemove", move);
    window.addEventListener("mouseup", up);
  }, [clampPanel]);

  // ── Cleanup debounce on unmount ─────────────────────────────────────────
  React.useEffect(() => () => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
  }, []);

  if (!open) return null;

  const isDefault = _isDefault(weights);

  return (
    <>
      <style>{_TWP_STYLE}</style>
      <div ref={dragRef} className="twp-panel"
           style={{ right: offsetRef.current.right, bottom: offsetRef.current.bottom }}>

        <div className="twp-hd" onMouseDown={onDragStart}>
          <div className="twp-hd-left">
            <b>Score weights</b>
            <span className="twp-hd-sub">{isDefault ? "defaults" : "customized"}</span>
          </div>
          <button className="twp-x" aria-label="Close score weights" onClick={onClose}>✕</button>
        </div>

        <div className="twp-body">
          {TWP_AXES.map(({ key, label, tip }) => {
            const v = weights[key];
            const changed = v !== TWP_DEFAULT;
            return (
              <div className="twp-row" key={key}>
                <div className="twp-lbl">
                  <span title={tip}>{label}</span>
                  <span className={changed ? "changed" : ""}>
                    {v === TWP_DEFAULT ? "default" : `${v.toFixed(1)}×`}
                  </span>
                </div>
                <input
                  type="range"
                  className={`twp-slider${changed ? " changed" : ""}`}
                  min={TWP_MIN} max={TWP_MAX} step={TWP_STEP}
                  value={v}
                  aria-label={`${label} weight: ${v.toFixed(1)}`}
                  onChange={(e) => setAxis(key, Number(e.target.value))}
                />
              </div>
            );
          })}
        </div>

        <div className="twp-foot">
          <button className="twp-reset" onClick={reset} disabled={isDefault}>
            Reset to defaults
          </button>
          <span className="twp-status">
            {isDefault ? "No changes" : "Re-ranking…"}
          </span>
        </div>
      </div>
    </>
  );
}

Object.assign(window, { ScoreWeightsPanel });
