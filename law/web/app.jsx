/* app.jsx — app shell: routing, state, API calls.
   Scoring happens on the backend: POST /api/match per submitted profile (and
   per what-if LSAT bump); GET /api/schools feeds the raw rankings browser. */

const DEFAULT_FORM = {
  lsat: "", noLsat: false, gpa: "", goal: "Unsure",
  practice: [{ state: "", weight: 100 }], instate: [""],
  income: "", cash: "", debt: "",
  careerW: 5, locW: 5, costW: 5, transfer: false
};

const STORE_KEY = "oplaw-v2-profile";

/* Coerce an untrusted form (share link, old localStorage) back to a safe shape. */
function normalizeForm(f) {
  const out = { ...DEFAULT_FORM, ...f };
  if (!GOALS.includes(out.goal)) out.goal = "Unsure";
  if (!Array.isArray(out.practice) || !out.practice.length ||
      out.practice.some((p) => typeof p !== "object" || p == null)) {
    out.practice = [{ state: "", weight: 100 }];
  }
  if (!Array.isArray(out.instate) || !out.instate.length) out.instate = [""];
  ["careerW", "locW", "costW"].forEach((k) => {
    const n = Number(out[k]);
    out[k] = Number.isNaN(n) ? DEFAULT_FORM[k] : Math.max(0, Math.min(10, n));
  });
  return out;
}

function loadStoredForm() {
  try {
    const raw = localStorage.getItem(STORE_KEY);
    if (raw) return normalizeForm(JSON.parse(raw));
  } catch (e) {/* ignore */}
  return DEFAULT_FORM;
}

/* The submitted form snapshot, viewed the way the screens expect it. */
function profileView(f) {
  return { ...f, lsat: f.noLsat ? null : Number(f.lsat), gpa: Number(f.gpa) };
}

async function fetchMatch(formSnapshot, lsatOverride) {
  const res = await fetch("/api/match", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildPayload(formSnapshot, lsatOverride)),
  });
  // Error bodies aren't always JSON (Basic-Auth 401, proxy 502) — don't let
  // the parse failure mask the real status.
  const json = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(json.error || `Matching failed (${res.status}).`);
  return adaptMatchResponse(json, formSnapshot.goal || "Unsure");
}

function App() {
  const [screen, setScreen] = React.useState("intake");
  const [form, setForm] = React.useState(loadStoredForm);
  const [submitted, setSubmitted] = React.useState(null); // form snapshot at submit
  const [data, setData] = React.useState(null);           // { schools, plan }
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState(null);
  const [whatIf, setWhatIf] = React.useState({ delta: 0, data: null });
  const [compareIds, setCompareIds] = React.useState([]);
  const [openedId, setOpenedId] = React.useState(null);
  const [rview, setRview] = React.useState("guided");
  const [modal, setModal] = React.useState(null);
  const [rawSchools, setRawSchools] = React.useState(null); // adapted /api/schools | "error"
  // Bumped on every successful submit so in-flight what-if responses from an
  // older profile can be recognized as stale and dropped.
  const submitSeq = React.useRef(0);

  const submit = async (f = form) => {
    setLoading(true);
    setError(null);
    try {
      const adapted = await fetchMatch(f);
      submitSeq.current += 1;
      setData(adapted);
      setSubmitted(f);
      setWhatIf({ delta: 0, data: null });
      setCompareIds([]);
      setScreen("results");
      try {localStorage.setItem(STORE_KEY, JSON.stringify(f));} catch (e) {/* ignore */}
      // Shareable link: profile lives in the URL hash, restored on load.
      try {window.history.replaceState(null, "", "#p=" + encodeShare(f));} catch (e) {/* ignore */}
      window.scrollTo({ top: 0 });
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  // Opened via a share link: restore the profile and run the match once.
  React.useEffect(() => {
    const m = window.location.hash.match(/^#p=(.+)$/);
    if (!m) return;
    try {
      const f = normalizeForm(decodeShare(m[1]));
      setForm(f);
      submit(f);
    } catch (e) {/* malformed share link — start fresh */}
  }, []);

  /* What-if: each LSAT bump re-runs the match server-side and re-tiers live.
     Stale responses are dropped if the user keeps clicking. */
  const setWhatIfDelta = async (d) => {
    if (!submitted || submitted.noLsat) return;
    if (d <= 0) {setWhatIf({ delta: 0, data: null });return;}
    const seq = submitSeq.current;
    setWhatIf((w) => ({ ...w, delta: d }));
    try {
      const adapted = await fetchMatch(submitted, Number(submitted.lsat) + d);
      // Drop if the user kept clicking (delta moved on) or re-submitted the
      // profile while this request was in flight.
      setWhatIf((w) => w.delta === d && seq === submitSeq.current ? { delta: d, data: adapted } : w);
    } catch (e) {/* keep the last good payload */}
  };

  const nav = (where) => {
    if (where === "methodology") {setModal("how");return;}
    if (where === "home") {setScreen("intake");} else
    if (where === "matches") {setScreen(data ? "results" : "intake");} else
    if (where === "rankings") {
      setScreen("rankings");
      if (!rawSchools || rawSchools === "error") {
        setRawSchools(null);
        fetch("/api/schools")
          .then((r) => r.json())
          .then((j) => setRawSchools((j.schools || []).map(adaptRaw)))
          .catch(() => setRawSchools("error"));
      }
    }
    window.scrollTo({ top: 0 });
  };

  const openSchool = (m) => {setOpenedId(m.id);setScreen("detail");window.scrollTo({ top: 0 });};
  const toggleCompare = (id) =>
  setCompareIds((ids) => ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id]);

  const eff = whatIf.delta > 0 && whatIf.data ? whatIf.data : data;
  const results = eff ? eff.schools : null;
  const profile = submitted ? profileView(submitted) : null;
  const opened = results && openedId ? results.find((m) => m.id === openedId) : null;
  const compareSchools = results ? results.filter((m) => compareIds.includes(m.id)) : [];

  const mastView = screen === "rankings" ? "rankings" :
  screen === "results" || screen === "detail" || screen === "compare" ? "matches" : "";

  return (
    <div className="shell">
      <Masthead view={mastView} onNav={nav} />

      {error && <div className="error-banner">{error}</div>}
      {loading && <div className="center-msg"><div className="spinner" />Matching schools…</div>}

      {!loading && screen === "intake" &&
      <ProfileScreen form={form} setForm={setForm} onSubmit={() => submit()} loading={loading} />
      }
      {!loading && screen === "results" && results && profile &&
      <ResultsScreen results={results} plan={eff.plan} profile={profile}
      whatIf={whatIf.delta} setWhatIf={setWhatIfDelta}
      onOpen={openSchool} onEditProfile={() => setScreen("intake")}
      compareIds={compareIds} onToggleCompare={toggleCompare}
      onClearCompare={() => setCompareIds([])}
      rview={rview} setRview={setRview}
      onCompare={() => {setScreen("compare");window.scrollTo({ top: 0 });}} />
      }
      {!loading && screen === "detail" && opened && profile &&
      <DetailScreen m={opened} profile={profile}
      onBack={() => {setScreen("results");}} />
      }
      {!loading && screen === "compare" && results &&
      <CompareScreen schools={compareSchools} profile={profile}
      onBack={() => setScreen("results")} onRemove={toggleCompare} />
      }
      {!loading && screen === "rankings" &&
      <RankingsScreen schools={rawSchools === "error" ? null : rawSchools}
      error={rawSchools === "error"} onRetry={() => nav("rankings")} />
      }

      <div className="footer-note">
        <span className="mono">None of your data is saved.
        </span>
        <span className="mono">
          <button type="button" className="linklike" onClick={() => setModal("report")}>
            Report a bug / request a feature</button>
        </span>
      </div>

      {modal === "how" && <Methodology onClose={() => setModal(null)} />}
      {modal === "report" && <ReportForm onClose={() => setModal(null)} />}
    </div>);

}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
