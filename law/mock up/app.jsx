/* app.jsx — shell, screen+variation routing, click-through wiring, Tweaks */

const { useState, useMemo } = React;

const SCREENS = [
  { id: "sitemap", label: "Sitemap",          variations: () => [{ key: "—", title: "User flow", Comp: null }] },
  { id: "profile", label: "Profile Dashboard", variations: () => window.ProfileVariations },
  { id: "results", label: "Results",           variations: () => window.ResultsVariations },
  { id: "detail",  label: "School Detail",     variations: () => window.DetailVariations },
  { id: "compare", label: "Compare",           variations: () => window.CompareVariations },
  { id: "empty",   label: "Edge States",       variations: () => window.EmptyVariations },
];

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "profile": "splitter",
  "annotations": true,
  "stickyNav": true,
  "density": "regular"
}/*EDITMODE-END*/;

function VarBar({ variations, varKey, setVarKey }) {
  return (
    <div className="var-bar">
      <span className="label">Variation</span>
      {variations.map(v => (
        <button
          key={v.key}
          className={`var-btn ${varKey === v.key ? "active" : ""}`}
          onClick={() => setVarKey(v.key)}
        >
          <span style={{ fontWeight: 700, marginRight: 6 }}>{v.key}</span>
          <span style={{ fontWeight: 400, fontSize: 15, color: "var(--ink-soft)" }}>{v.title}</span>
        </button>
      ))}
    </div>
  );
}

function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [screen, setScreen] = useState("sitemap");
  const [varKeyByScreen, setVarKeyByScreen] = useState({
    profile: "A", results: "A", detail: "A", compare: "A", empty: "A",
  });
  const [openedSchool, setOpenedSchool] = useState(SAMPLE_SCHOOLS[3]);

  const profile = SAMPLE_PROFILES[t.profile] || SAMPLE_PROFILES.splitter;
  const screenDef = SCREENS.find(s => s.id === screen);
  const variations = useMemo(() => screenDef.variations(), [screen]);
  const varKey = varKeyByScreen[screen] || variations[0]?.key;
  const variation = variations.find(v => v.key === varKey) || variations[0];

  const setVarKey = (k) => setVarKeyByScreen(prev => ({ ...prev, [screen]: k }));

  const goToScreen = (id) => {
    setScreen(id);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const onOpenSchool = (s) => { setOpenedSchool(s); goToScreen("detail"); };
  const onProfileSubmit = () => goToScreen("results");
  const onDetailBack = () => goToScreen("results");

  // Render the chosen variation
  let body;
  if (screen === "sitemap") {
    body = <Sitemap onJumpTo={goToScreen} />;
  } else {
    const Comp = variation?.Comp;
    const commonProps = {
      profile,
      anno: t.annotations,
    };
    if (screen === "profile") body = <Comp {...commonProps} onSubmit={onProfileSubmit} />;
    else if (screen === "results") body = <Comp {...commonProps} onOpen={onOpenSchool} />;
    else if (screen === "detail")  body = <Comp {...commonProps} school={openedSchool} onBack={onDetailBack} />;
    else if (screen === "compare") body = <Comp anno={t.annotations} />;
    else if (screen === "empty")   body = <Comp anno={t.annotations} onAdjust={() => goToScreen("profile")} />;
  }

  return (
    <div className="app" style={{ paddingBottom: 120 }}>
      <div className="topbar">
        <div>
          <h1 style={{ fontSize: 38, lineHeight: 1 }}>Law School Matcher</h1>
          <div className="subtitle">Wireframe exploration · whiteboard fidelity · {variations.length > 1 ? `${variations.length} variations per screen` : "single flow view"}</div>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <span className="label-mono">demo profile:</span>
          <span className="sk-pill hi" style={{ transform: "rotate(-1.5deg)" }}>{profile.name}</span>
        </div>
      </div>

      <div style={{ position: t.stickyNav ? "sticky" : "static", top: 0, zIndex: 30, background: "var(--paper)", paddingTop: 6 }}>
        <div className="screen-tabs">
          {SCREENS.map(s => {
            const count = s.variations().length;
            return (
              <button
                key={s.id}
                className={`screen-tab ${screen === s.id ? "active" : ""}`}
                onClick={() => goToScreen(s.id)}
              >
                {s.label}
                {count > 1 && <span className="count">{count}</span>}
              </button>
            );
          })}
        </div>
        {variations.length > 1 && (
          <VarBar variations={variations} varKey={varKey} setVarKey={setVarKey} />
        )}
      </div>

      <div className="stage" style={{
        fontSize: t.density === "compact" ? 14 : t.density === "comfy" ? 17 : 15,
      }}>
        <div style={{ marginBottom: 12 }}>
          {variation && screen !== "sitemap" && (
            <ScreenHeader
              title={variations.length > 1 ? `${screenDef.label} — Variation ${variation.key}` : screenDef.label}
              sub={variation.title}
            />
          )}
        </div>
        {body}

        {t.annotations && screen !== "sitemap" && (
          <div style={{ marginTop: 30, display: "flex", gap: 18, alignItems: "flex-start", flexWrap: "wrap" }}>
            <StickyNote rot={-2}>
              click-through: forms → results, results → detail.
              <br />no real algorithm wired — visuals only.
            </StickyNote>
            <StickyNote rot={2} color="#bbdefb">
              all variations share the editable-sidebar pattern + 6-axis radar.
            </StickyNote>
          </div>
        )}
      </div>

      <TweaksPanel>
        <TweakSection label="Demo profile" />
        <TweakRadio
          label="Persona"
          value={t.profile}
          options={["splitter", "pi", "t14", "unsure"]}
          onChange={(v) => setTweak("profile", v)}
        />
        <div style={{ fontFamily: "var(--label)", fontSize: 11, color: "var(--ink-soft)", padding: "2px 4px 6px" }}>
          {profile.blurb}
        </div>
        <TweakSection label="Display" />
        <TweakToggle label="Annotations" value={t.annotations} onChange={(v) => setTweak("annotations", v)} />
        <TweakToggle label="Sticky nav"  value={t.stickyNav}   onChange={(v) => setTweak("stickyNav", v)} />
        <TweakRadio
          label="Density"
          value={t.density}
          options={["compact", "regular", "comfy"]}
          onChange={(v) => setTweak("density", v)}
        />
        <TweakSection label="Jump to" />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, padding: "0 4px" }}>
          {SCREENS.map(s => (
            <TweakButton key={s.id} label={s.label} onClick={() => goToScreen(s.id)} />
          ))}
        </div>
      </TweaksPanel>
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);
