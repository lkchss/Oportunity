/* screen-scenarios.jsx — Saved Scenarios panel on the intake form.
   Lets users name, save, load, and delete up to 10 form profiles in localStorage.
   Storage key: "oplaw-v2-scenarios"  →  { [name: string]: profile object }
   No backend changes; no auto-submit on load. */

const SCENARIOS_KEY = "oplaw-v2-scenarios";
const MAX_SCENARIOS = 10;

/* ---------- persistence helpers ---------- */

function loadScenarios() {
  try {
    const raw = localStorage.getItem(SCENARIOS_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) return {};
    return parsed;
  } catch (e) {
    return {};
  }
}

function saveScenarios(map) {
  try {
    localStorage.setItem(SCENARIOS_KEY, JSON.stringify(map));
  } catch (e) {/* ignore quota errors */}
}

/* ---------- ScenariosPanel ---------- */

function ScenariosPanel({ form, onLoad }) {
  const [scenarios, setScenarios] = React.useState(loadScenarios);
  const [open, setOpen] = React.useState(false);
  const [saving, setSaving] = React.useState(false);   // inline save-name mode
  const [nameInput, setNameInput] = React.useState("");
  const nameRef = React.useRef(null);

  /* Focus the name input whenever we enter save mode. */
  React.useEffect(() => {
    if (saving && nameRef.current) nameRef.current.focus();
  }, [saving]);

  const count = Object.keys(scenarios).length;

  /* Persist a new or updated scenario. */
  const commitSave = () => {
    const name = nameInput.trim();
    if (!name) { setSaving(false); setNameInput(""); return; }
    const existing = loadScenarios();                // re-read for freshness
    let next = { ...existing };

    /* If at cap and it's a new name, evict the oldest entry. */
    if (Object.keys(next).length >= MAX_SCENARIOS && !(name in next)) {
      const oldest = Object.keys(next)[0];
      delete next[oldest];
    }
    next[name] = { ...form };
    saveScenarios(next);
    setScenarios(next);
    setSaving(false);
    setNameInput("");
    setOpen(true);   // show list after saving so user sees their new entry
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") { e.preventDefault(); commitSave(); }
    if (e.key === "Escape") { setSaving(false); setNameInput(""); }
  };

  const loadScenario = (name) => {
    const s = scenarios[name];
    if (!s) return;
    onLoad(normalizeForm(s));   // normalizeForm is defined in app.jsx (global)
  };

  const deleteScenario = (name) => {
    const next = { ...scenarios };
    delete next[name];
    saveScenarios(next);
    setScenarios(next);
  };

  return (
    <div className="sc-panel">
      <div className="sc-bar">
        {/* Left: toggle list (only shown when there are saved scenarios) */}
        {count > 0 && (
          <button type="button" className="btn xs ghost sc-toggle"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}>
            <span className="sc-toggle-arrow">{open ? "▾" : "▸"}</span>
            Scenarios
            <span className="sc-count">{count}</span>
          </button>
        )}
        {count === 0 && (
          <span className="sc-label">Scenarios</span>
        )}

        {/* Right: save control */}
        <div className="sc-save-area">
          {saving ? (
            <span className="sc-name-row">
              <input
                ref={nameRef}
                type="text"
                className="sc-name-input"
                value={nameInput}
                placeholder="Name this scenario…"
                maxLength={48}
                onChange={(e) => setNameInput(e.target.value)}
                onKeyDown={handleKeyDown}
              />
              <button type="button" className="btn xs primary" onClick={commitSave}
                disabled={!nameInput.trim()}>Save</button>
              <button type="button" className="btn xs ghost" onClick={() => { setSaving(false); setNameInput(""); }}>✕</button>
            </span>
          ) : (
            <button type="button" className="btn xs ghost sc-save-btn"
              onClick={() => setSaving(true)}
              title="Save current form as a named scenario">
              + Save scenario
            </button>
          )}
        </div>
      </div>

      {/* Scenario list (collapsible) */}
      {open && count > 0 && (
        <ul className="sc-list" role="list">
          {Object.keys(scenarios).map((name) => (
            <li key={name} className="sc-item">
              <button type="button" className="sc-load-btn"
                onClick={() => loadScenario(name)}
                title={`Load "${name}" into the form`}>
                {name}
              </button>
              <button type="button" className="btn xs ghost sc-del"
                onClick={() => deleteScenario(name)}
                aria-label={`Delete scenario "${name}"`}
                title="Delete">
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

window.ScenariosPanel = ScenariosPanel;
