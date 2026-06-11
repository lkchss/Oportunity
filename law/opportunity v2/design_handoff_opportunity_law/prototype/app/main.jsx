/* main.jsx — app shell: routing, state, tweaks. */

const DEFAULT_FORM = {
  lsat: 167, noLsat: false, gpa: 3.72, goal: "BigLaw / In-house",
  practice: [{ state: "NY", weight: 100 }], instate: ["NY"],
  income: "prefer_not", cash: "", debt: "",
  careerW: 7, locW: 6, costW: 5, transfer: true
};

/* One color drives both accent + highlight — a single voice, not two. */
const PALETTE = {
  "#a3791a": { deep: "#7d5c12", soft: "#f3ead0", border: "#e5d6a9" }, /* marigold */
  "#ffa494": { deep: "#b14a37", soft: "#ffe7e2", border: "#f6c9c0" }, /* salmon */
  "#f0c5ef": { deep: "#973f92", soft: "#f9e9f8", border: "#e9c6e8" }, /* orchid */
  "#d6c5f0": { deep: "#6b4ba6", soft: "#efe9f9", border: "#d9cbef" }, /* lavender */
  "#c9d4ff": { deep: "#3d51b5", soft: "#e9eeff", border: "#c9d4f0" } /* periwinkle */
};

function relLum(hex) {
  const n = parseInt(hex.slice(1), 16);
  const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
  return 0.2126 * f(n >> 16 & 255) + 0.7152 * f(n >> 8 & 255) + 0.0722 * f(n & 255);
}

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "color": "#a3791a",
  "display": "serif",
  "density": "compact"
} /*EDITMODE-END*/;

const STORE_KEY = "oplaw-v2-profile";

function loadStoredForm() {
  try {
    const raw = localStorage.getItem(STORE_KEY);
    if (raw) return { ...DEFAULT_FORM, ...JSON.parse(raw) };
  } catch (e) {/* ignore */}
  return DEFAULT_FORM;
}

function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [screen, setScreen] = React.useState("intake");
  const [form, setForm] = React.useState(loadStoredForm);
  const [profile, setProfile] = React.useState(null); // submitted snapshot
  const [whatIf, setWhatIf] = React.useState(0);
  const [compareIds, setCompareIds] = React.useState([]);
  const [openedId, setOpenedId] = React.useState(null);
  const [rview, setRview] = React.useState("guided");
  const [modal, setModal] = React.useState(null);

  /* apply tweaks to the document */
  React.useEffect(() => {
    const root = document.documentElement;
    const hex = PALETTE[t.color] ? t.color : "#a3791a";
    const p = PALETTE[hex];
    root.style.setProperty("--accent", hex);
    root.style.setProperty("--accent-deep", p.deep);
    root.style.setProperty("--accent-soft", p.soft);
    root.style.setProperty("--accent-contrast", relLum(hex) > 0.45 ? "#1c1917" : "#f5f1e6");
    root.style.setProperty("--amber", hex);
    root.style.setProperty("--amber-soft", p.soft);
    root.style.setProperty("--amber-border", p.border);
    document.body.classList.toggle("sans-display", t.display === "sans");
    document.body.classList.toggle("compact", t.density === "compact");
  }, [t.color, t.display, t.density]);

  const baseResults = React.useMemo(
    () => profile ? computeResults(profile) : null, [profile]);
  const results = React.useMemo(() => {
    if (!profile || !baseResults) return null;
    if (whatIf <= 0 || profile.noLsat) return baseResults;
    return computeResults(profile, Math.min(profile.lsat + whatIf, 180));
  }, [profile, baseResults, whatIf]);

  const submit = () => {
    const p = { ...form, lsat: form.noLsat ? null : Number(form.lsat), gpa: Number(form.gpa) };
    setProfile(p);
    setWhatIf(0);
    setCompareIds([]);
    setScreen("results");
    try {localStorage.setItem(STORE_KEY, JSON.stringify(form));} catch (e) {/* ignore */}
    window.scrollTo({ top: 0 });
  };

  const nav = (where) => {
    if (where === "methodology") {setModal("how");return;}
    if (where === "home") {setScreen("intake");} else
    if (where === "matches") {setScreen(profile ? "results" : "intake");} else
    if (where === "rankings") {setScreen("rankings");}
    window.scrollTo({ top: 0 });
  };

  const openSchool = (m) => {setOpenedId(m.id);setScreen("detail");window.scrollTo({ top: 0 });};
  const toggleCompare = (id) =>
  setCompareIds((ids) => ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id]);

  const opened = results && openedId ? results.find((m) => m.id === openedId) : null;
  const compareSchools = results ? results.filter((m) => compareIds.includes(m.id)) : [];

  const mastView = screen === "rankings" ? "rankings" :
  screen === "results" || screen === "detail" || screen === "compare" ? "matches" : "";

  return (
    <div className="shell">
      <Masthead view={mastView} onNav={nav} />

      {screen === "intake" &&
      <ProfileScreen form={form} setForm={setForm} onSubmit={submit} />
      }
      {screen === "results" && results &&
      <ResultsScreen results={results} baseResults={baseResults} profile={profile}
      whatIf={whatIf} setWhatIf={setWhatIf}
      onOpen={openSchool} onEditProfile={() => setScreen("intake")}
      compareIds={compareIds} onToggleCompare={toggleCompare}
      onClearCompare={() => setCompareIds([])}
      rview={rview} setRview={setRview}
      onCompare={() => {setScreen("compare");window.scrollTo({ top: 0 });}} />
      }
      {screen === "detail" && opened &&
      <DetailScreen m={opened} profile={profile}
      onBack={() => {setScreen("results");}} />
      }
      {screen === "compare" && results &&
      <CompareScreen schools={compareSchools} profile={profile}
      onBack={() => setScreen("results")} onRemove={toggleCompare} />
      }
      {screen === "rankings" &&
      <RankingsScreen onBack={() => nav("matches")} />
      }

      <div className="footer-note">
        <span className="mono">None of your data is saved.
        </span>
        <span className="mono">
          <a href="mailto:lukechaussee119@gmail.com?subject=[Opportunity: Law] feedback">Report a bug / request a feature</a>
        </span>
      </div>

      {modal === "how" && <Methodology onClose={() => setModal(null)} />}

      <TweaksPanel>
        <TweakSection label="Theme" />
        <TweakColor label="Color" value={t.color}
        options={["#a3791a", "#ffa494", "#f0c5ef", "#d6c5f0", "#c9d4ff"]}
        onChange={(v) => setTweak("color", v)} />
        <TweakRadio label="Display type" value={t.display}
        options={["serif", "sans"]}
        onChange={(v) => setTweak("display", v)} />
        <TweakSection label="Layout" />
        <TweakRadio label="Density" value={t.density}
        options={["comfortable", "compact"]}
        onChange={(v) => setTweak("density", v)} />
      </TweaksPanel>
    </div>);

}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);