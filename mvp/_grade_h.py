"""Grade the HORIZONS list (broad, horizon-expanding programs) by SPRINGBOARD VALUE.

Separate DB (horizons.db) from the career list. Grades A+..C- answer "how much
does this open doors / diversify lived experience?" - NOT career fit. Every row
is kind='horizon' (single vault tree). Re-export sorted CSV + print distribution.
"""
import sqlite3, csv
from pathlib import Path

DB = Path(__file__).parent / "horizons.db"
CSV = Path(__file__).parent / "horizons.csv"

# title -> (springboard_grade, deadline/timing). 9 sub-tiers: A+ A A- B+ B B- C+ C C-
DATA = {
    "Fulbright U.S. Student Program (study / research / English-teaching abroad)": ("A", "~Oct (annual); 1 academic year abroad"),
    "Schwarzman Scholars (one-year master's at Tsinghua, Beijing)": ("A", "~Sept (annual); fully funded; age <=28"),
    "Mitchell Scholarship (US -> Ireland, one year postgrad)": ("A-", "~Oct (annual); fully funded year in Ireland"),
    "Knight-Hennessy Scholars (funds any Stanford graduate degree)": ("A-", "~Oct (annual); needs Stanford grad admit too"),
    "National Geographic Young Explorers / Early Career Grant": ("B+", "Rolling pre-apps; ~6-8mo before field dates"),
    "Princeton in Asia (yearlong fellowships across Asia)": ("B+", "~Nov/Dec (annual); year+ placement in Asia"),
    "JET Programme (Japan Exchange & Teaching)": ("B+", "~Nov (annual); salaried 1-5 yr in Japan"),
    "Congress-Bundestag Youth Exchange for Young Professionals (CBYX)": ("B+", "~Dec (annual); funded year in Germany"),
    "TED Fellows Program": ("B+", "Annual cohorts; needs a visible body of work"),
    "Rhodes Scholarship (two years at Oxford)": ("A", "~Oct (annual); univ endorsement; age limits"),
    "Marshall Scholarship (two years, any UK university)": ("A-", "~late Sept (annual); univ endorsement"),
    "Gates Cambridge Scholarship (postgrad at Cambridge, any subject)": ("A-", "US round ~mid-Oct; no endorsement needed"),
    "Yenching Academy (Peking University, China Studies master's)": ("B+", "~Dec/Jan (annual); funded MA in Beijing"),
    "The Arctic Circle Expeditionary Residency (Svalbard tall-ship)": ("B", "Annual cohorts; self-funded berth"),
    "Coro Fellows Program in Public Affairs": ("B", "~Jan 11 written app + Selection Day; tuition-free + stipend"),
    "Ember Fellowship (startup placement in emerging US cities)": ("B", "Annual cohort (summer start); new/unproven program"),
    "Wilderness Leadership Expeditions (NOLS / Outward Bound)": ("B-", "Rolling sessions; adults 18/23+; self-funded"),
    "Tall-Ship / Ocean Sailing Semesters (SEA Semester, Sea-mester)": ("B-", "Rolling terms; self-funded / for-credit"),
    "Art Omi: Writers (international writing residency, NY)": ("B-", "~Jul 1 deadline; ~1-month, funded ex-travel"),
    "Antarctic Artists & Writers Program (NSF / Polar STEAM)": ("B+", "2027/28 round ~through Jul 1, 2026; US 21+; arts/letters record"),
    "Erasmus Mundus Joint Master's (multi-country Europe, funded)": ("B+", "Apply ~Oct-Jan; EUR1,400/mo; full degree"),
    "Expedition Grants (Explorers Club, RGS, American Alpine Club)": ("B", "Rolling/annual; fund a self-designed expedition"),
    "MacDowell Fellowship (premier US arts residency)": ("B", "Next app opens ~Aug 15, 2026; free; project-based"),
    "Yaddo (artists' community residency, Saratoga Springs)": ("B-", "~Jul deadline cycle; free; competitive; project-based"),
    "Djerassi Resident Artists Program (California ranch)": ("B-", "Annual (competitive); free; several-week sessions"),
    "Banff Centre for Arts and Creativity (themed programs, Canada)": ("B-", "Rolling themed programs; aid varies; Alberta"),
    "Pioneer Works Residency (art / science / technology, Brooklyn)": ("B-", "Open call ~Aug-Sep; Brooklyn; project-based; honorarium"),
    "Cosmos Institute Fellowship (philosophy x AI, human flourishing)": ("B+", "Rolling; multi-yr unrestricted; very high bar"),
    "Bogliasco Foundation Fellowship (Genoa, Italy)": ("B", "~Mar 7 deadline; 1-mo fully funded; arts/humanities"),
    "Middlebury Language Schools - Japanese Immersion (8 weeks)": ("B", "~May 15 deadline; 8-wk immersion; tuition + some aid"),
    "Vermont Studio Center Residency (writers & artists)": ("B-", "Multiple deadlines; partial-full fellowships; 2-4 wk"),
    "Virginia Center for the Creative Arts (VCCA) Residency": ("B-", "Jan 15 / May 15 / Oct 15; funded fellowships; 2-wk"),
    "Edge Esmeralda / Edge City pop-up villages": ("B-", "May 30-Jun 27, 2026; paid attendance; Healdsburg CA"),
    "Clipper Round the World Yacht Race (crew a leg or the circumnavigation)": ("B-", "2027-28 edition; pay-to-crew; full training"),
    "Logan Nonfiction Program (narrative-nonfiction residency)": ("B", "Apply Oct 15 (spring) / Jun 15 (fall); free; 5-10 wk"),
    "Interintellect (global salon community + Fellows)": ("B-", "Rolling; salon community + Fellows; membership"),
    "Zen Monastic Residencies (Zen Mountain Monastery, Tassajara)": ("B-", "Rolling; 1-mo residential / work-practice; low-cost"),
    "Plum Village (France) - mindfulness immersion + Happy Farm work-practice": ("B-", "Summer 2026 retreats + work-practice; low-cost"),
    "Earthwatch Expeditions (citizen-science fieldwork)": ("C+", "Rolling 2026 trips; pay-to-join; days-weeks"),
    "Headlands Center for the Arts - Artist in Residence (AIR)": ("B", "2027 cycle apps Apr 1-Jun 1, 2026; fully sponsored; 4-10 wk"),
    "Ucross Foundation Residency (Wyoming ranch)": ("B-", "Two cycles/yr; free; remote; competitive"),
    "Mesa Refuge Residency (writers on money, the commons, the environment)": ("B-", "~Oct 4 deadline; 2-wk; no fee (travel/food on you)"),
    "Newspeak House - London College of Political Technology": ("B-", "Rolling; 1-yr; London; ~GBP1100/mo if resident; mid-career-leaning"),
    "Schmidt Ocean Institute - Artist-at-Sea": ("B+", "Apply (online app opening); free berth+travel; unpaid; portfolio req"),
    "PLAYA Arts & Science Residency (remote Oregon)": ("B-", "~Jun 30 deadline; free cabin; remote Oregon"),
    "Sitka Center for Art & Ecology Residency (Oregon coast)": ("B-", "Annual juried; free; 2wk-3mo; some stipends"),
    "Antikythera (philosophy of planetary computation studio)": ("B+", "Cohort studio (check dates); philosophy x computation; competitive"),
    "Hawthornden Castle Literary Retreat (Scotland)": ("B-", "~Jun 30 deadline (following yr); free 4-wk; no travel/stipend"),
    "Working Holiday Year abroad (New Zealand / Ireland - US-eligible)": ("B", "12-mo; US-eligible via NZ & Ireland (not AUS/Japan)"),
    "Antarctic Support Jobs (US Antarctic Program / USAP)": ("B", "Seasonal contracts; support roles; extraordinary"),
    "Folk & Craft Schools (WoodenBoat, North House, The Apprenticeshop)": ("B-", "Short courses + apprenticeships; pay-to-attend"),
    "Seasonal Adventure Jobs (National Parks / CoolWorks)": ("B-", "Apply Oct-Feb for summer; paid; live in parks/resorts"),
    "EPIK - Teach English in South Korea": ("B", "Gov program; ~$1.75-2.5k/mo + housing + airfare; TEFL"),
    "Princeton in Africa (yearlong fellowship across Africa)": ("B-", "~Oct/Nov deadline; pro roles; dev/social-leaning"),
    "Fine-Craft Workshops (Penland, Haystack, Anderson Ranch, Arrowmont)": ("B-", "1-2 wk summer; apply early; fellowships ~25%"),
    "Thru-hike a Long Trail (Appalachian / Pacific Crest)": ("B-", "Self-directed 4-6 mo; ~$8-11k; PCT permit"),
    "Work-Exchange Travel (Workaway / WWOOF / Worldpackers)": ("B-", "~$50/yr; room+board for ~5 hrs/day; 150+ countries"),
    "Pro Skill Courses Abroad (Divemaster / Ski / Sailing Instructor)": ("B-", "4-8 wk courses; pay; then seasonal work-travel"),
    "Where There Be Dragons (immersive travel-study)": ("C+", "Pay-to-go; deep immersion (Nepal/Peru/Senegal); weeks"),
    "Language Immersion Schools Abroad (homestay; Spanish/Italian/French)": ("B-", "~$420-800/wk; homestay; 2-24 wks; flexible"),
    "Maine Media Workshops (film / photography / writing intensives)": ("B-", "Year-round; 1-day to multi-week; tuition-based"),
    "10-Day Vipassana Meditation Course (Goenka, free)": ("B-", "Free (donation); 10-day silent; worldwide; apply online"),
    "Recurse Center (self-directed programming retreat, NYC - free)": ("B-", "Free; 6/12-wk batches 2026; must already code"),
    "Crew an Ocean Crossing (OceanCrewLink / ARC rally)": ("B-", "Atlantic Nov-Jan; free working or paid crew; vet the boat"),
    "Writers' Conferences (Bread Loaf, Sewanee, Tin House)": ("B-", "~1-1.5 wk summer; competitive; some scholarships"),
    "Regenerative Farming Apprenticeships (MESA, Quivira New Agrarian)": ("B-", "Season-long; stipend + room/board; rural"),
    "Ideas Festivals (Aspen Ideas, Chautauqua, Sun Valley Writers')": ("B-", "Summer; paid attendance (some scholarships)"),
    "Analog Astronaut Missions (MDRS, HI-SEAS, LunAres)": ("B-", "Apply (LunAres 20+); ~2-wk; pay; extraordinary"),
    "Camino de Santiago (long-distance pilgrimage walk)": ("B-", "5 days-8 wks; cheap; well-supported; reset + community"),
    "Culinary Immersion Abroad (short cooking courses)": ("B-", "Short courses (Le Cordon Bleu/Florence/Bangkok); no exp"),
    "Mountaineering Courses (Alpine Ascents / glacier skills)": ("B-", "1-13 day courses; glacier/alpine skills + summit; pay"),
    "Wine Harvest / Vendange (seasonal vineyard work abroad)": ("C+", "1-3 wk seasonal; board incl.; US needs WHV (NZ) - visa caveat"),
    "Improv / Comedy Intensives (iO, UCB, BATS)": ("C+", "1-5 wk; stage presence/quick thinking; cheap-ish"),
}

ORDER = ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-"]


def main() -> None:
    conn = sqlite3.connect(DB)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(opportunities)")}
    if "fit_grade" not in cols:
        conn.execute("ALTER TABLE opportunities ADD COLUMN fit_grade TEXT")
    if "deadline" not in cols:
        conn.execute("ALTER TABLE opportunities ADD COLUMN deadline TEXT")
    if "kind" not in cols:
        conn.execute("ALTER TABLE opportunities ADD COLUMN kind TEXT DEFAULT 'horizon'")

    for title, (grade, dl) in DATA.items():
        conn.execute(
            "UPDATE opportunities SET fit_grade=?, deadline=?, kind='horizon' WHERE title=?",
            (grade, dl, title),
        )
    conn.commit()

    order = {g: i for i, g in enumerate(ORDER)}
    rows = conn.execute(
        "SELECT fit_grade, deadline, category, title, url, summary, why_match, found_at "
        "FROM opportunities"
    ).fetchall()
    rows.sort(key=lambda r: (order.get(r[0], 99), r[2] or "", r[3] or ""))

    with open(CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Springboard", "Timing", "Category", "Title", "URL", "Summary", "Why it's worth it", "Found at"])
        w.writerows(rows)

    print(f"CSV rows: {len(rows)}")
    print(" / ".join(f"{g} {sum(1 for r in rows if r[0] == g)}" for g in ORDER))


if __name__ == "__main__":
    main()
