"""One-off: add fit_grade + deadline columns, populate, re-export sorted CSV."""
import sqlite3, csv
from pathlib import Path

DB = Path(__file__).parent / "opportunities.db"
CSV = Path(__file__).parent / "opportunities.csv"

# title -> (fit_grade, estimated_deadline). Grades: A+ A A- B+ B B- C+ C C- (9 sub-tiers)
DATA = {
    # --- A+ : bullseyes, read first ---
    "Anthropic Fellows Program - The Anthropic Institute (Economics & Policy)": ("A+", "Rolling (cohorts from Jul 2026)"),
    "Emergent Ventures (Mercatus Center, Tyler Cowen)": ("A+", "Rolling (decisions in weeks)"),
    "Contrary Research Fellowship": ("A+", "Quarterly 2026: Jun 17, Oct 23, Dec 9"),
    "Luce Scholars Program": ("A+", "Sep 7, 2026"),

    # --- A : top-tier fit + actionable ---
    "Bridgewater Associates - Investment Associate Program": ("A", "Dec 1 - Jan 31 (annual)"),
    "Schwarzman Scholars (Tsinghua University, Beijing)": ("A", "Sep 9, 2026"),
    "Knight-Hennessy Scholars (Stanford)": ("A", "Oct 6, 2026 (+ GSB app ~Dec 1)"),
    "Susa Venture Fellows": ("A", "Open now: ~Jun-Jul 31"),
    "FAS Day One - Policy Entrepreneurship Fellowship": ("A", "Rolling open call"),

    # --- A- : strong fit, slightly more friction ---
    "Antler": ("A-", "Rolling (city cohorts)"),
    "Asterisk Magazine AI Blogging Fellowship": ("A-", "Rolling / per-cohort"),
    "Citadel - Global Fixed Income & Macro (Analyst)": ("A-", "Rolling (intern/analyst cycles)"),
    "Contrary Venture Partner Program": ("A-", "Rolling cohorts"),
    "Entrepreneur First (EF)": ("A-", "Rolling (city cohorts)"),
    "First Round Capital - Angel Track": ("A-", "Periodic cohorts"),
    "Gates Cambridge Scholarship": ("A-", "~Oct-Dec (annual, US round)"),
    "German Marshall Memorial Fellowship (GMF)": ("A-", "~Jul 15, 2026"),
    "Kleiner Perkins Fellows Program": ("A-", "~Jan 31 (annual)"),
    "Mansfield Fellowship Program (US-Japan)": ("A-", "Annual (~spring)"),
    "New America National Fellows Program": ("A-", "~Feb 2 (annual)"),
    "O'Shaughnessy Fellowships & Grants (OSV)": ("A-", "Passed (~Apr 30; annual)"),
    "Point72 Academy": ("A-", "Passed (annual; watch next cycle)"),
    "Roots of Progress Blog-Building Intensive Fellowship": ("A-", "Passed (~Jun 1; annual)"),
    "Sohn Investment Idea Contest": ("A-", "Annual (~spring)"),
    "South Park Commons Founder Fellowship": ("A-", "Spring ~Feb 1; Fall opens this summer"),
    "Substack - Independent Writer Fellowship": ("A-", "Rolling / announced periodically"),
    "Works in Progress Writing Fellowship": ("A-", "Rolling"),
    "Y Combinator": ("A-", "Rolling (multiple batches/year)"),
    "Yenching Academy of Peking University": ("A-", "Annual (~fall-winter)"),
    "German Chancellor Fellowship (Humboldt Foundation)": ("A-", "~Oct 15 (annual)"),
    "Center for AI Safety - AI and Society Fellowship": ("A-", "Passed (cohort Jun-Aug 2026; annual ~winter)"),
    "Stripe Economics of AI Fellowship": ("B", "Passed (1st cohort Apr 2025; watch next). Academic-research-oriented"),
    "Constellation - Astra Fellowship (AI safety/governance)": ("B", "Passed (~May 3; begins Sep 2026). AI-safety research"),
    "Prediction-Market Companies - Strategy / Markets / BizOps (Kalshi, Polymarket)": ("B", "Rolling (fintech+markets; CFTC-regulated)"),
    "BizOps / Strategy & Operations at High-Growth Tech (Stripe, Ramp, DoorDash, Uber)": ("B", "Rolling (non-eng strategy/ops at high-growth tech)"),
    "Experimentation / Causal-Inference Data Science at Tech (Netflix, Uber, Amazon)": ("B", "Rolling (uses causal-inference thesis skill; some PhD/ML-leaning)"),
    "Management Consulting (McKinsey, Bain, BCG)": ("B", "Annual recruiting cycles; maximal optionality, springboard not endpoint"),
    "Corporate Development / Strategic Finance at Tech": ("B", "Rolling (deal teams at tech; IB/PE/consulting feeder)"),
    "Stablecoin / Payments-Infrastructure Roles (Circle, Stripe, Bridge, payment fintechs)": ("B", "Rolling (Fed financial-reg edge post-GENIUS Act)"),
    "GovAI - DC Summer Fellowship": ("A-", "Passed (cohort Jun-Aug 2026; annual ~Feb)"),

    # --- B+ : good fit, a notch below ---
    "Accel Starters (Scout Program)": ("B+", "Varies by geography / seasonal"),
    "Cambridge ERA:AI Fellowship": ("B+", "Passed (cohort Jul 2026; reopens ~winter)"),
    "Coro Fellows Program in Public Affairs": ("B+", "~Jan 11 (written app) + Selection Day"),
    "Founders, Inc. (f.inc)": ("B+", "Rolling"),
    "Good Judgment Open -> Superforecaster track": ("B+", "Ongoing (open platform)"),
    "Hustle Fund - Angel Squad": ("B+", "Rolling (membership)"),
    "Institute for AI Policy and Strategy (IAPS) Fellowship": ("B+", "Annual (summer cohort ~Jun-Aug)"),
    "Interact Fellowship": ("B+", "~Feb 9 (annual)"),
    "Metaculus x Bridgewater Forecasting Contest": ("B+", "Passed (ran early 2026; watch next)"),
    "Obama Foundation Leaders Program (USA)": ("B+", "Annual (cohort-based)"),
    "On Deck Angel Fellowship (ODA)": ("B+", "~3x/year (~6-week windows)"),
    "On Deck Founder Fellowship (ODF)": ("B+", "Rolling (ODF27 Feb, ODF28 Q3 2026)"),
    "Schmidt Futures - International Strategy Forum (ISF)": ("B+", "~Aug (annual); ages 25-35"),
    "Sequoia Arc": ("B+", "Bi-annual open call"),
    "Soma Capital Fellows": ("B+", "~Apr 1, 2026"),
    "SumZero Top Idea / Value Investing Challenge": ("B+", "Periodic contests"),
    "VC Scout Programs (Bessemer, Bain Capital Ventures, Chapter One via AngelList)": ("B+", "Varies / seasonal by fund"),
    "Z Fellows": ("B+", "Rolling cohorts"),
    "a16z Speedrun Accelerator": ("B+", "Rolling (SR007 starts Jul 2026)"),
    "OECD Young Associates Programme (YAP)": ("B+", "Passed (~Dec 14; biennial 2-yr, Paris). Bachelor-only"),
    "Economic Consulting (Brattle, Cornerstone, Analysis Group, Compass Lexecon)": ("B+", "Rolling + annual analyst cycles"),
    "Chief of Staff / BizOps at Frontier AI Labs & Startups": ("B+", "Rolling (role postings come and go)"),
    "Venture Capital Analyst / Pre-MBA Associate (early-career VC roles)": ("B", "Rolling (scarce; network-driven, no on-cycle)"),
    "Perplexity Business Fellowship": ("B+", "Rolling (part-time; no coding required)"),
    "Berggruen Prize Essay Competition": ("B+", "Aug 17, 2026 ($50k prize)"),
    "OpenAI Grove (pre-idea founder program)": ("B+", "Rolling (2nd cohort); pre-idea + OpenAI talent network"),
    "Inflection Fellowship (Edge City x Long Journey VC)": ("B+", "Cohorts ~late May-Jun 2026 (full-ride, builders <25)"),

    # --- B : solid with a real caveat ---
    "Google Associate Product Manager (APM) Program": ("B", "~late Sep-Oct (annual)"),
    "Meta Rotational Product Manager (RPM) Program": ("B", "~Fall (annual)"),
    "Chevening Scholarship (UK)": ("B", "~Aug-early Nov (annual)"),
    "Brookings - David M. Rubenstein Fellowship": ("B", "Annual; 2-year term"),
    "Aspen Ideas Festival - Fellows Program": ("B", "Annual (~winter)"),
    "Aspen Science & Technology Policy Fellowship (Aspen Policy Academy)": ("B", "Passed (~Dec-Feb; annual)"),
    "Atlantic Council Millennium Fellowship": ("B", "Passed (~Dec-Jan; annual). Age 25+"),
    "Forbes 30 Under 30": ("B", "Nominations ~autumn (annual)"),
    "Fulbright U.S. Student Program - Japan (Open Study/Research)": ("B", "Annual (campus ~Sep-Oct)"),
    "Google Public Policy Fellowship": ("B", "Annual (~winter/spring)"),
    "Hertog Foundation - Political Studies / Humanities Programs": ("B", "Passed (summer); reopens ~winter"),
    "Horizon Institute for Public Service Fellowship": ("B", "~Oct 1-Dec 1 (next cycle)"),
    "Included VC Fellowship": ("B", "Annual"),
    "Marshall Scholarship (UK study)": ("B", "~Oct natl; campus ~summer. Needs nomination"),
    "Mercatus Center - Oskar Morgenstern Fellowship": ("B", "Passed (annual)"),
    "OpenAI - Economic Research Team": ("B", "Rolling (roles; senior-skewed)"),
    "Palladium Magazine (contributor / writing)": ("B", "Rolling (pitch-based)"),
    "RAND Center on AI, Security, and Technology (CAST) Fellowship": ("B", "Rolling / varies"),
    "Rhodes Scholarship (Oxford)": ("B", "~Oct 1. Needs nomination (reach)"),
    "Sell-Side Equity Research Analyst Programs (Morgan Stanley, Goldman Sachs)": ("B", "Annual (student-pipeline timing)"),
    "Tech Policy Press Reporting Fellowship": ("B", "~Oct 15 (annual)"),
    "TechCongress - Congressional Innovation Fellowship": ("B", "~Jun 25, 2026 (next cohort)"),
    "The New Atlantis (contributor / writing)": ("B", "Rolling (pitch-based)"),
    "16VC Founder Fellowship": ("B", "Open now (Summer 2026)"),
    "Berkman Klein Center Fellowship (Harvard)": ("B", "Annual open call (~fall)"),
    "AI Grant (Nat Friedman & Daniel Gross)": ("B", "Rolling / periodic cohorts"),
    "Cosmos Institute - Cosmos Fellowship (Philosopher-Builder)": ("B", "Rolling (express interest)"),
    "U.S. Treasury Junior Fellowships (Domestic Finance / FSOC / Intl Affairs)": ("B", "~Oct 31, 2026 (2-yr; new-grad targeted)"),

    # --- B- : decent, multiple caveats / secondary ---
    "East-West Center in Washington - Young Professionals Program": ("B-", "Passed (~Mar-Apr; annual)"),
    "Humanity in Action - Democracy Fellowship": ("B-", "Spring 2026 (date TBD)"),
    "JET Programme (Japan Exchange and Teaching)": ("B-", "2027 apps open Fall 2026"),
    "One Young World Summit": ("B-", "Annual (delegate applications)"),
    "Princeton in Asia (PiA) Fellowship": ("B-", "Passed (~fall open; annual). 1-2 yr"),
    "Tarbell Fellowship (AI Journalism)": ("B-", "Passed (~Jan 7; 2027 cycle next)"),
    "Techstars Accelerator": ("B-", "Rolling cohorts (Spring 2026 open)"),
    "The OpEd Project - Public Voices Fellowship": ("B-", "Varies by cohort (often needs affiliation)"),
    "US-Japan Leadership Program (USJLP)": ("B-", "Recruiting opens fall 2026"),
    "Village Global - Network Catalyst": ("B-", "Rolling"),
    "WEF Global Shapers Community": ("B-", "Rolling (city-hub applications)"),
    "U.S. Digital Corps": ("B-", "Annual (~fall-winter). 2-year term"),
    "FASPE - Design & Technology Fellowship": ("B-", "~Jan (annual); summer program"),
    "Alumni Ventures - Venture Fellow Program": ("B-", "Opens ~May 1, 2026 (July cohort)"),
    "Mercatus Center - Don Lavoie Fellowship": ("B-", "~Apr 15 (annual)"),
    "Google Creative Fellowship": ("B-", "~late Mar (annual)"),
    "Fintech VC Scout / Emerging-Investor Programs (QED, Fin VC, BTV)": ("B-", "Varies by fund / rolling"),
    "Roosevelt Institute - Think Tank Fellows": ("B-", "Annual (cohort-based)"),
    "Notable Capital - NextGen AI Fellowship": ("B-", "~spring (cohort Jun-Jul 2026)"),
    "Primary VC - Operator in Residence": ("B-", "Varies (cohort-based)"),
    "Founder University Japan (JETRO x LAUNCH)": ("B-", "Passed (~Jun 7; annual). Japan-focused startups"),
    "Founder-in-Residence (Atomic, Afore & venture studios)": ("B-", "Rolling (co-found; in-person ~6mo)"),
    "Growth Equity / Private Equity Analyst (Adams Street, Norwest, Hamilton Lane)": ("B-", "Rolling (analyst programs; IB/consulting feeder)"),
    "Proptech / Location-Intelligence Roles (geospatial real-estate tech)": ("B-", "Rolling (roles; leverages geospatial + land-VC edge)"),
    "Operator Roles via VC Talent Networks (Greylock, a16z, Seedcamp)": ("B-", "Rolling (fund matches you into portfolio startups)"),
    "Agtech / Farmland Investing Roles (ag-focused VC/PE & farmland funds)": ("B-", "Rolling (direct match to PLB ag-land VC background)"),
    "Defense Tech / Frontier Hardware Strategy & Ops (Anduril, etc.)": ("B-", "Rolling (hot sector; non-eng strategy/ops; defense-specific)"),
    "Space Economy / Earth-Observation Roles (strategy, BizOps, geospatial analytics)": ("B-", "Rolling (booming sector; geospatial/EO analytics edge)"),
    "Japan / Asia Tech & VC Roles (English-speaking; Tokyo / Singapore)": ("B-", "Rolling (JETRO/CareerCross/Japan Dev; Japanese an asset)"),
    "World Economic Forum Early Careers Programme (Geneva / Tokyo / Mumbai / Beijing)": ("B-", "~late Nov (Spring 2026); paid 6-mo; entry-level placement"),
    "In-House Economist / Economic Data-Storyteller at Tech & Fintech (Ramp, LinkedIn, Redfin, Carta)": ("B-", "Rolling (econ + writing brand role; many variants PhD)"),
    "Search Funds / Entrepreneurship Through Acquisition (ETA)": ("B-", "Rolling (searcher path; capital-intensive, usually post-MBA)"),
    "Institute for Progress (IFP) - innovation & science policy think tank": ("B-", "Rolling (pitch hiring@ifp.org; create-your-role; DC)"),
    "Behavioural Insights Team / ideas42 (Applied Behavioral Economics)": ("B-", "Rolling (advisor/analyst roles)"),
    "Institute for Progress (IFP)": ("B-", "Rolling (pitch essays / watch for roles)"),

    # --- C+ : marginal-but-relevant / future-soon ---
    "Aspen Institute - Socrates Program": ("C+", "Seminars Feb & Jul 2026. Age 28+; ~$2.5k"),
    "Milken Institute - Young Leaders Circle (YLC)": ("C+", "Rolling membership. Age 25+"),
    "On Deck VC Fellowship (ODV)": ("C+", "Periodic cohorts"),
    "TEDx Speaker (local events, e.g., TEDxLogan Circle DC)": ("C+", "Varies by event (e.g. ~Mar 15)"),
    "500 Global Accelerator": ("C+", "Rolling cohorts"),
    "1517 Fund - Medici Project (micro-grants)": ("C+", "Rolling (5-min Loom)"),
    "Autodesk Research Residency (Technology Centers)": ("C+", "Apps ~Jun 1 (annual). Fabrication/hardware-leaning"),
    "Design Technologist / Product Designer at AI Startups": ("C+", "Rolling (needs design portfolio/craft)"),
    "Humba Ventures Fellowship (deep-tech VC)": ("C+", "Rolling (part-time; beta)"),
    "VC Lab / Emerging-Manager Fund Accelerators (launch your own VC fund)": ("C+", "Rolling (free 14-wk); future - needs deal track record + LPs"),
    "Yale Prospect Fellowship (investment-management entrepreneurs)": ("C+", "Annual (2nd cohort); ~5 spots; needs an investment thesis"),
    "Palantir Startup Fellowship": ("C+", "Rolling (Cohort 001); needs a startup; Palantir ecosystem, equity-free"),
    "X $1M Article Prize (long-form writing on X)": ("C+", "Recurring (free to enter; long-form on X; low odds, high visibility)"),
    "Sports Strategy & Analytics Roles (NBA / MLB teams & leagues)": ("C+", "Rolling (personal-passion fit; tangential to finance/tech core)"),

    # --- C : weak / aspirational / future ---
    "a16z Scout Program": ("C", "Rolling/invite. Best once already angel-active"),
    "NEXUS Global": ("C", "Membership / summits"),
    "World Bank Group - Young Professionals Program (YPP)": ("C", "~Sep (annual). Needs master's + 2-6 yrs (future)"),
    "Boren Fellowship (Asia language study)": ("C", "~Jan-Feb (annual). Needs grad enrollment"),
    "Emerson Collective Fellowship": ("C", "Invitation-only"),
    "Foundation for American Innovation - AI Policy Fellowship": ("C", "Passed (~Apr 6; annual). Conservative-framed"),
    "Neo (Accelerator + Scholars)": ("C", "Rolling. Tech/eng-skewed"),
    "Open Philanthropy - Career Development & Transition Funding": ("C", "Rolling. EA/GCR-oriented"),
    "Rotary Global Grant Scholarship": ("C", "Rolling via local clubs. Mission-constrained"),
    "TOMODACHI Emerging Leaders Program (US-Japan Council)": ("C", "Annual. Confirm eligibility fit"),
    "White House Fellowship": ("C", "~Apr (annual). INELIGIBLE while at the Fed"),

    # --- C- : weakest / heavily gated, lowest priority ---
    "MEXT Japanese Government Scholarship (Research Students)": ("C-", "Passed (~May 21; annual). 2+ yr degree in Japan"),
    "Hayek Essay Contest (Mont Pelerin Society)": ("C-", "Biennial (~spring). Ideological (classical-liberal)"),
    "Spearhead (Angel Investing Program)": ("C-", "Rolling (by class). Requires founder status - future"),
    "CFR Stephen M. Kellen Term Member Program": ("C-", "Annual (~Dec). Min age 30 (future)"),
    "Kauffman Fellows": ("C-", "Rolling (~Dec early). ~$80k tuition; needs VC role"),
    "Asia Society - Asia 21 Next Generation Fellowship": ("C-", "Annual; nomination-only (5-10 yrs exp) - future"),
}

# Titles that are POSITIONS (actual jobs/roles), kept in a separate vault folder.
# Everything else is an "opportunity" (fellowship / scholarship / grant / competition / program).
POSITIONS = {
    "Bridgewater Associates - Investment Associate Program",
    "Point72 Academy",
    "Citadel - Global Fixed Income & Macro (Analyst)",
    "Sell-Side Equity Research Analyst Programs (Morgan Stanley, Goldman Sachs)",
    "OpenAI - Economic Research Team",
    "Google Associate Product Manager (APM) Program",
    "Meta Rotational Product Manager (RPM) Program",
    "Economic Consulting (Brattle, Cornerstone, Analysis Group, Compass Lexecon)",
    "Behavioural Insights Team / ideas42 (Applied Behavioral Economics)",
    "OECD Young Associates Programme (YAP)",
    "U.S. Treasury Junior Fellowships (Domestic Finance / FSOC / Intl Affairs)",
    "U.S. Digital Corps",
    "World Bank Group - Young Professionals Program (YPP)",
    "Chief of Staff / BizOps at Frontier AI Labs & Startups",
    "Venture Capital Analyst / Pre-MBA Associate (early-career VC roles)",
    "Design Technologist / Product Designer at AI Startups",
    "Prediction-Market Companies - Strategy / Markets / BizOps (Kalshi, Polymarket)",
    "Growth Equity / Private Equity Analyst (Adams Street, Norwest, Hamilton Lane)",
    "Proptech / Location-Intelligence Roles (geospatial real-estate tech)",
    "BizOps / Strategy & Operations at High-Growth Tech (Stripe, Ramp, DoorDash, Uber)",
    "Operator Roles via VC Talent Networks (Greylock, a16z, Seedcamp)",
    "Stablecoin / Payments-Infrastructure Roles (Circle, Stripe, Bridge, payment fintechs)",
    "Sports Strategy & Analytics Roles (NBA / MLB teams & leagues)",
    "Agtech / Farmland Investing Roles (ag-focused VC/PE & farmland funds)",
    "Experimentation / Causal-Inference Data Science at Tech (Netflix, Uber, Amazon)",
    "Defense Tech / Frontier Hardware Strategy & Ops (Anduril, etc.)",
    "Space Economy / Earth-Observation Roles (strategy, BizOps, geospatial analytics)",
    "Management Consulting (McKinsey, Bain, BCG)",
    "Corporate Development / Strategic Finance at Tech",
    "Japan / Asia Tech & VC Roles (English-speaking; Tokyo / Singapore)",
    "World Economic Forum Early Careers Programme (Geneva / Tokyo / Mumbai / Beijing)",
    "In-House Economist / Economic Data-Storyteller at Tech & Fintech (Ramp, LinkedIn, Redfin, Carta)",
    "Search Funds / Entrepreneurship Through Acquisition (ETA)",
    "Institute for Progress (IFP) - innovation & science policy think tank",
}

conn = sqlite3.connect(DB)
cols = {r[1] for r in conn.execute("PRAGMA table_info(opportunities)")}
if "fit_grade" not in cols:
    conn.execute("ALTER TABLE opportunities ADD COLUMN fit_grade TEXT")
if "deadline" not in cols:
    conn.execute("ALTER TABLE opportunities ADD COLUMN deadline TEXT")
if "kind" not in cols:
    conn.execute("ALTER TABLE opportunities ADD COLUMN kind TEXT DEFAULT 'opportunity'")

missing = []
all_titles = {r[0] for r in conn.execute("SELECT title FROM opportunities")}
for title in all_titles:
    if title not in DATA:
        missing.append(title)
for title, (grade, dl) in DATA.items():
    if title not in all_titles:
        missing.append("KEY-NOT-IN-DB: " + title)
        continue
    kind = "position" if title in POSITIONS else "opportunity"
    conn.execute("UPDATE opportunities SET fit_grade=?, deadline=?, kind=? WHERE title=?", (grade, dl, kind, title))
conn.commit()

if missing:
    print("!! UNMATCHED:")
    for m in missing:
        print("   ", m)
else:
    print("All 100 graded, no mismatches.")

# export sorted by 9-tier priority, then category, title
order = {"A+": 0, "A": 1, "A-": 2, "B+": 3, "B": 4, "B-": 5, "C+": 6, "C": 7, "C-": 8}
rows = conn.execute(
    "SELECT fit_grade, deadline, category, title, url, summary, why_match, found_at FROM opportunities"
).fetchall()
rows.sort(key=lambda r: (order.get(r[0], 9), r[2], r[3]))
with open(CSV, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["Fit grade", "Est. deadline", "Category", "Title", "URL", "Summary", "Why it matches", "Found at"])
    w.writerows(rows)

print("CSV rows:", len(rows))
print(" / ".join(f"{g} {sum(1 for r in rows if r[0]==g)}"
                 for g in ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-"]))
