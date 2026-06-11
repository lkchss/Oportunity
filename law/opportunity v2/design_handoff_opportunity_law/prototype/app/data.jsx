/* data.jsx — canned dataset (24 plausible schools) + client-side matcher
   so the prototype actually responds to profile edits and what-ifs.
   Numbers are realistic but illustrative — this is a design deliverable. */

const STATES = ["AL","AK","AZ","AR","CA","CO","CT","DC","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY"];

const GOALS = ["Unsure", "BigLaw / In-house", "Federal Clerkship", "Government", "Public Interest", "Solo/Small Firm", "Academia"];

const INCOME_OPTIONS = [
  ["under_65k", "Under $65K"], ["65k_130k", "$65K – $130K"],
  ["130k_200k", "$130K – $200K"], ["over_200k", "Over $200K"],
  ["prefer_not", "Prefer not to say"],
];

const TIERS = {
  safety: { label: "Safety", cls: "t-safety", color: "var(--safety-dot)" },
  target: { label: "Target", cls: "t-target", color: "var(--target-dot)" },
  reach:  { label: "Reach",  cls: "t-reach",  color: "var(--reach-dot)" },
  hard:   { label: "Hard reach", cls: "t-hard", color: "var(--hard-dot)" },
};
const TIER_ORDER = ["safety", "target", "reach", "hard"];

/* id, name, loc, state, public, rank, accept,
   l25,l50,l75, g25,g50,g75,
   biglaw, clerk, gov, pi, solo, bar, barUlt, emp,
   tuitRes, tuitNon, living, grantRate, medGrant, cond,
   trIn, trOutRate, attr, salPriv, size, feeds, scDebt, scEarn */
const ROWS = [
["yale","Yale University","New Haven, CT","CT",0,1,.057,171,175,178,3.87,3.94,3.99,.28,.33,.04,.18,.01,.98,.99,.95,76000,76000,26000,.65,32000,0,10,.002,.005,215000,200,["NY","DC","CA"],130000,105000],
["harvard","Harvard University","Cambridge, MA","MA",0,4,.10,171,174,176,3.84,3.92,3.97,.55,.14,.04,.10,.01,.98,.99,.96,75000,75000,28000,.50,30000,0,30,.003,.005,215000,560,["NY","DC","MA","CA"],145000,120000],
["penn","University of Pennsylvania","Philadelphia, PA","PA",0,4,.12,168,172,174,3.71,3.89,3.96,.70,.06,.03,.06,.01,.97,.99,.96,74000,74000,26000,.45,25000,0,25,.004,.006,215000,250,["NY","PA","DC"],150000,130000],
["columbia","Columbia University","New York, NY","NY",0,8,.115,170,173,175,3.81,3.90,3.96,.74,.07,.02,.07,.01,.97,.99,.96,78000,78000,27000,.48,28000,0,40,.004,.007,215000,400,["NY","DC","CA"],160000,135000],
["nyu","New York University","New York, NY","NY",0,9,.165,169,172,174,3.74,3.86,3.94,.68,.08,.04,.10,.01,.97,.99,.95,76000,76000,27000,.52,28000,0,45,.005,.006,215000,440,["NY","DC","CA"],155000,130000],
["cornell","Cornell University","Ithaca, NY","NY",0,14,.17,169,172,174,3.73,3.87,3.94,.72,.06,.02,.04,.01,.95,.98,.94,75000,75000,22000,.47,25000,0,30,.006,.007,215000,200,["NY","DC"],150000,128000],
["gtown","Georgetown University","Washington, DC","DC",0,14,.21,166,171,173,3.62,3.85,3.93,.55,.05,.07,.08,.01,.94,.97,.92,73000,73000,25000,.50,24000,0,80,.01,.01,200000,570,["DC","NY","VA"],145000,110000],
["bu","Boston University","Boston, MA","MA",0,27,.25,164,168,170,3.55,3.78,3.89,.36,.04,.05,.07,.02,.93,.96,.91,62000,62000,22000,.78,28000,0,15,.015,.01,180000,230,["MA","NY"],110000,95000],
["bc","Boston College","Newton, MA","MA",0,28,.26,163,167,169,3.52,3.74,3.86,.33,.03,.05,.06,.02,.92,.96,.92,64000,64000,22000,.72,26000,0,12,.013,.01,175000,230,["MA","NY"],105000,92000],
["fordham","Fordham University","New York, NY","NY",0,35,.27,162,166,168,3.48,3.69,3.83,.38,.02,.06,.05,.03,.87,.94,.89,69000,69000,26000,.68,22000,1,35,.02,.015,160000,380,["NY","NJ","CT"],125000,100000],
["gw","George Washington University","Washington, DC","DC",0,41,.30,162,166,168,3.45,3.71,3.84,.30,.03,.10,.06,.03,.86,.93,.88,67000,67000,25000,.70,24000,1,40,.02,.02,150000,470,["DC","VA","MD","NY"],130000,95000],
["villanova","Villanova University","Villanova, PA","PA",0,50,.32,158,162,165,3.40,3.65,3.81,.16,.01,.07,.04,.05,.88,.94,.89,60000,60000,21000,.84,26000,1,8,.025,.015,100000,240,["PA","NJ","NY"],82000,80000],
["uconn","University of Connecticut","Hartford, CT","CT",1,58,.39,156,160,163,3.30,3.56,3.74,.10,.01,.11,.05,.06,.85,.93,.85,32000,48000,19000,.72,15000,0,8,.02,.02,90000,180,["CT","NY","MA"],62000,72000],
["temple","Temple University","Philadelphia, PA","PA",1,60,.36,157,161,164,3.34,3.59,3.77,.12,.01,.09,.05,.06,.85,.93,.87,33000,46000,20000,.74,16000,0,9,.02,.02,92000,350,["PA","NJ","NY"],65000,75000],
["cardozo","Yeshiva University (Cardozo)","New York, NY","NY",0,69,.35,158,163,165,3.36,3.60,3.78,.15,.01,.07,.05,.05,.84,.92,.86,65000,65000,26000,.82,30000,1,25,.03,.02,100000,320,["NY","NJ"],95000,82000],
["setonhall","Seton Hall University","Newark, NJ","NJ",0,70,.40,156,160,162,3.32,3.57,3.74,.14,.01,.08,.04,.06,.83,.92,.86,62000,62000,22000,.86,28000,1,10,.03,.02,95000,290,["NJ","NY"],90000,78000],
["rutgers","Rutgers University","Newark, NJ","NJ",1,75,.34,156,160,163,3.31,3.56,3.74,.12,.01,.10,.05,.05,.80,.90,.85,30000,45000,20000,.60,14000,0,18,.02,.03,95000,350,["NJ","NY","PA"],70000,78000],
["stjohns","St. John's University","Queens, NY","NY",0,84,.38,156,160,163,3.30,3.55,3.76,.10,.01,.09,.03,.08,.83,.92,.85,60000,60000,24000,.88,30000,1,15,.03,.02,88000,300,["NY"],85000,74000],
["brooklyn","Brooklyn Law School","Brooklyn, NY","NY",0,91,.40,155,159,162,3.25,3.50,3.70,.12,.01,.08,.04,.07,.81,.91,.84,58000,58000,25000,.85,27000,1,20,.035,.025,90000,360,["NY","NJ"],92000,76000],
["buffalo","University at Buffalo (SUNY)","Buffalo, NY","NY",1,99,.48,152,156,159,3.20,3.48,3.70,.04,.01,.12,.05,.09,.78,.90,.82,27000,35000,17000,.75,12000,0,5,.03,.03,70000,200,["NY"],58000,66000],
["syracuse","Syracuse University","Syracuse, NY","NY",0,105,.47,152,156,159,3.18,3.45,3.68,.05,.01,.10,.04,.09,.77,.89,.81,58000,58000,20000,.82,22000,1,7,.035,.03,72000,230,["NY","DC"],80000,65000],
["hofstra","Hofstra University","Hempstead, NY","NY",0,112,.45,153,157,160,3.15,3.42,3.65,.06,.004,.08,.03,.10,.76,.88,.80,62000,62000,24000,.80,24000,1,8,.04,.035,75000,280,["NY"],88000,68000],
["albany","Albany Law School","Albany, NY","NY",0,122,.52,151,155,158,3.12,3.40,3.62,.03,.01,.14,.04,.10,.76,.88,.80,50000,50000,18000,.85,20000,1,6,.03,.03,68000,220,["NY"],72000,62000],
["cuny","CUNY School of Law","Queens, NY","NY",1,130,.42,151,155,158,3.10,3.38,3.60,.02,.002,.12,.20,.06,.75,.87,.76,16000,26000,24000,.70,8000,0,4,.02,.04,60000,190,["NY"],45000,58000],
];

const SCHOOLS = ROWS.map((r) => ({
  id: r[0], name: r[1], loc: r[2], state: r[3], isPublic: !!r[4], rank: r[5], accept: r[6],
  l25: r[7], l50: r[8], l75: r[9], g25: r[10], g50: r[11], g75: r[12],
  biglaw: r[13], clerk: r[14], gov: r[15], pi: r[16], solo: r[17],
  bar: r[18], barUlt: r[19], emp: r[20],
  tuitRes: r[21], tuitNon: r[22], living: r[23],
  grantRate: r[24], medGrant: r[25], cond: !!r[26],
  trIn: r[27], trOut: r[28], attr: r[29],
  salPriv: r[30], size: r[31], feeds: r[32], scDebt: r[33], scEarn: r[34],
}));

const wiki = (n) => "https://en.wikipedia.org/wiki/" + n.replace(/ /g, "_");
const NOTABLE = {
  yale:     { alumni: ["Sonia Sotomayor", "Bill Clinton", "Hillary Clinton", "Clarence Thomas"] },
  harvard:  { alumni: ["Barack Obama", "John Roberts", "Elena Kagan", "Ketanji Brown Jackson"] },
  columbia: { alumni: ["Ruth Bader Ginsburg", "Franklin D. Roosevelt", "Eric Holder"] },
  nyu:      { alumni: ["Fiorello La Guardia", "Judith Sheindlin", "Rudy Giuliani"] },
  cornell:  { alumni: ["Ruth Bader Ginsburg", "Janet Reno"] },
  gtown:    { alumni: ["Antonin Scalia (faculty)", "Dick Durbin"] },
  fordham:  { alumni: ["Geraldine Ferraro", "Andrew Cuomo"] },
  brooklyn: { alumni: ["David Dinkins", "Larry King"] },
};

/* ---------------- formatters ---------------- */
const fmtMoney = (n) => n == null ? "—" : "$" + Math.round(n).toLocaleString();
const fmtMoneyK = (n) => n == null ? "—" : "$" + Math.round(n / 1000) + "k";
const fmtPct = (f) => f == null ? "—" : Math.round(f * 100) + "%";
const fmtPct1 = (f) => f == null ? "—" : Math.round(f * 1000) / 10 + "%";
const fmtRank = (r) => r == null || r >= 999 ? "Unranked" : "#" + r;
const clamp = (v, lo = 0, hi = 100) => Math.max(lo, Math.min(hi, v));

/* ---------------- matcher ---------------- */
const GOAL_METRIC = {
  "BigLaw / In-house": (s) => s.biglaw / 0.74,
  "Federal Clerkship": (s) => s.clerk / 0.33,
  "Government":        (s) => s.gov / 0.14,
  "Public Interest":   (s) => s.pi / 0.20,
  "Solo/Small Firm":   (s) => s.solo / 0.10,
  "Academia":          (s) => s.clerk / 0.33,
  "Unsure":            (s) => 0.5 * (s.biglaw / 0.74) + 0.3 * s.emp + 0.2 * s.bar,
};

function goalSalary(s, goal) {
  if (goal === "Government") return 70000;
  if (goal === "Public Interest") return 62000;
  if (goal === "Federal Clerkship") return 74000;
  if (goal === "Academia") return 85000;
  if (goal === "Solo/Small Firm") return 72000;
  return 70000 + (s.salPriv - 70000) * Math.min(1, s.biglaw / 0.5);
}

function admitRead(s, lsat, gpa) {
  if (lsat == null) {
    const t = gpa >= s.g75 ? "target" : gpa >= s.g50 ? "target" : gpa >= s.g25 ? "reach" : "hard";
    const pG = (gpa - s.g25) / Math.max(s.g75 - s.g25, 0.01);
    return { tier: t, score: clamp(pG * 55 + 18, 2, 92) };
  }
  const pL = (lsat - s.l25) / Math.max(s.l75 - s.l25, 1);
  const pG = (gpa - s.g25) / Math.max(s.g75 - s.g25, 0.01);
  let tier;
  if (lsat >= s.l75 && gpa >= s.g50) tier = "safety";
  else if (lsat >= s.l50 && gpa >= s.g25) tier = "target";
  else if (lsat >= s.l25 - 1) tier = "reach";
  else tier = "hard";
  if (s.accept <= 0.12 && tier === "safety") tier = "target";   // hyper-selective: nothing is safe
  return { tier, score: clamp((pL * 0.65 + pG * 0.35) * 60 + 20, 2, 100) };
}

function whyLine(m, goal) {
  const out = [];
  const goalShort = goal === "BigLaw / In-house" ? "BigLaw" :
    goal === "Federal Clerkship" ? "clerkship" :
    goal === "Public Interest" ? "public-interest" : goal.toLowerCase();
  if (m.career >= 68) out.push(`Strong ${goalShort} pipeline (${fmtPct(m.goalPct)})`);
  if (m.tier === "safety" && m.scholarship >= 70) out.push("strong odds of a large scholarship");
  else if (m.scholarship >= 72) out.push("likely merit aid");
  if (m.location >= 88) out.push("places grads in your market");
  if (m.fin >= 72) out.push("manageable projected debt");
  if ((m.tier === "reach" || m.tier === "hard") && out.length < 2)
    out.push("below their medians — the upside is real");
  if (out.length === 0) out.push("a balanced option for your profile");
  const line = out.slice(0, 2).join(" · ");
  return line.charAt(0).toUpperCase() + line.slice(1);
}

/* profile: { lsat|null, gpa, goal, practice:[{state,weight}], instate:[],
   cash, careerW, locW, costW } */
function matchSchool(s, profile, lsatOverride) {
  const lsat = lsatOverride !== undefined ? lsatOverride : profile.lsat;
  const { tier, score: admiss } = admitRead(s, lsat, profile.gpa);
  const prestige = clamp(100 - 1.2 * (s.rank - 1));
  const goal = profile.goal || "Unsure";
  const goalPct = goal === "BigLaw / In-house" ? s.biglaw :
    goal === "Federal Clerkship" || goal === "Academia" ? s.clerk :
    goal === "Government" ? s.gov : goal === "Public Interest" ? s.pi :
    goal === "Solo/Small Firm" ? s.solo : s.biglaw;
  const career = clamp(GOAL_METRIC[goal](s) * 100 * (0.75 + 0.25 * s.emp));

  const prac = (profile.practice || []).filter((p) => p.state);
  let location = 50;
  if (prac.length) {
    let tw = 0, acc = 0;
    for (const p of prac) {
      const v = s.state === p.state ? 95 : s.feeds.includes(p.state) ? 72 : 22;
      const w = Math.max(p.weight, 0); acc += v * w; tw += w;
    }
    location = tw > 0 ? acc / tw : 50;
  }

  const merit = lsat == null ? 0.4 : lsat >= s.l75 ? 1 : lsat >= s.l50 ? 0.55 : lsat >= s.l25 ? 0.3 : 0.1;
  const scholarship = clamp(s.grantRate * 55 + merit * 50 - (s.cond ? 10 : 0));

  const instate = s.isPublic && (profile.instate || []).includes(s.state);
  const tuition = instate ? s.tuitRes : s.tuitNon;
  const gross = 3 * (tuition + s.living);
  const aid3 = 3 * s.medGrant * (0.5 + merit) * clamp(s.grantRate + 0.25, 0, 1);
  const cash = Number(profile.cash) || 0;
  const netDebt = Math.max(gross - aid3 - cash, 5000);
  const salary = goalSalary(s, goal);
  const monthly = netDebt * 0.011611;
  const dti = netDebt / salary;
  const fin = clamp(108 - dti * 45, 4, 100);

  const wCar = profile.careerW ?? 5, wLoc = profile.locW ?? 5, wCost = profile.costW ?? 5;
  const wSum = wCar + wLoc + 5 + wCost * 0.7 + wCost;
  const base = (career * wCar + location * wLoc + prestige * 5 + scholarship * wCost * 0.7 + fin * wCost) / Math.max(wSum, 1);
  const tf = { safety: 0.96, target: 1.0, reach: 0.87, hard: 0.6 }[tier];
  const composite = clamp((base * 0.85 + admiss * 0.15) * tf);

  const m = {
    ...s, tier, admiss: Math.round(admiss), prestige: Math.round(prestige),
    career: Math.round(career), location: Math.round(location),
    scholarship: Math.round(scholarship), fin: Math.round(fin),
    goalPct, composite: Math.round(composite * 10) / 10,
    pure: Math.round(base * 10) / 10,
    instate, tuition, gross: Math.round(gross), aid3: Math.round(aid3),
    netDebt: Math.round(netDebt), salary: Math.round(salary),
    monthly: Math.round(monthly), dti: Math.round(dti * 100) / 100,
    pslf: goal === "Government" || goal === "Public Interest",
  };
  m.radar = [m.admiss, m.prestige, m.career, m.location, m.scholarship, m.fin];
  m.why = whyLine(m, goal);
  return m;
}

function computeResults(profile, lsatOverride) {
  const list = SCHOOLS.map((s) => matchSchool(s, profile, lsatOverride))
    .sort((a, b) => b.composite - a.composite);
  return list;
}

function transferPlan(results) {
  const launchpads = results
    .filter((m) => (m.tier === "safety" || m.tier === "target") && m.trOut >= 0.015)
    .sort((a, b) => b.trOut - a.trOut).slice(0, 5);
  const targets = results
    .filter((m) => (m.tier === "reach" || m.tier === "hard") && m.trIn >= 20)
    .sort((a, b) => b.trIn - a.trIn).slice(0, 5);
  return { launchpads, targets };
}

Object.assign(window, {
  STATES, GOALS, INCOME_OPTIONS, TIERS, TIER_ORDER, SCHOOLS, NOTABLE, wiki,
  fmtMoney, fmtMoneyK, fmtPct, fmtPct1, fmtRank, clamp,
  computeResults, matchSchool, transferPlan,
});
