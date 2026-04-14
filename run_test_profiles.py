"""
Run test profiles through the matcher to verify algorithm quality.
"""

from app.data_loader import load_law_schools
from app.matcher import rank_schools

# Load schools
schools = load_law_schools()

# Define test profiles
test_profiles = [
    {
        "name": "Profile 1: Strong T14 Candidate",
        "profile": {
            "lsat": 177,
            "gpa": 3.95,
            "goal": "BigLaw",
            "practice_areas": ["Corporate", "Litigation"],
            "geography": [],
            "scholarship": "Prefer but not required",
            "reach_preference": "Want a balanced list",
        },
    },
    {
        "name": "Profile 2: Splitter (High LSAT, Lower GPA)",
        "profile": {
            "lsat": 172,
            "gpa": 3.3,
            "goal": "BigLaw",
            "practice_areas": ["Corporate"],
            "geography": ["Northeast"],
            "scholarship": "Must have significant scholarship",
            "reach_preference": "Willing to apply to reaches",
        },
    },
    {
        "name": "Profile 3: Reverse Splitter (Lower LSAT, High GPA)",
        "profile": {
            "lsat": 160,
            "gpa": 3.98,
            "goal": "Public Interest",
            "practice_areas": ["Constitutional", "Environmental"],
            "geography": ["West Coast"],
            "scholarship": "Prefer but not required",
            "reach_preference": "Want a balanced list",
        },
    },
    {
        "name": "Profile 4: Academia Goal",
        "profile": {
            "lsat": 175,
            "gpa": 3.92,
            "goal": "Academia",
            "practice_areas": ["Constitutional", "IP"],
            "geography": [],
            "scholarship": "Prefer but not required",
            "reach_preference": "Willing to apply to reaches",
        },
    },
    {
        "name": "Profile 5: Regional Focus",
        "profile": {
            "lsat": 165,
            "gpa": 3.7,
            "goal": "Government",
            "practice_areas": ["Criminal", "Constitutional"],
            "geography": ["Southeast"],
            "scholarship": "Must have significant scholarship",
            "reach_preference": "Only schools where I'm a strong candidate",
        },
    },
    {
        "name": "Profile 6: Weak Candidate",
        "profile": {
            "lsat": 155,
            "gpa": 3.2,
            "goal": "Unsure",
            "practice_areas": [],
            "geography": ["Midwest"],
            "scholarship": "Must have significant scholarship",
            "reach_preference": "Only schools where I'm a strong candidate",
        },
    },
]

# Run each profile
output_lines = []
output_lines.append("=" * 80)
output_lines.append("ALGORITHM TEST RESULTS (AFTER ADMISSIBILITY FIX)")
output_lines.append("=" * 80)
output_lines.append("")

for test in test_profiles:
    output_lines.append(f"\n{'=' * 80}")
    output_lines.append(f"{test['name']}")
    output_lines.append(f"{'=' * 80}")
    profile = test["profile"]
    output_lines.append(f"LSAT: {profile['lsat']} | GPA: {profile['gpa']} | Goal: {profile['goal']}")
    output_lines.append("")

    try:
        ranked = rank_schools(profile, schools, top_n=10)

        output_lines.append(f"Top 10 Matches:")
        output_lines.append(f"{'-' * 80}")

        for idx, school in enumerate(ranked, 1):
            output_lines.append(
                f"{idx:2}. {school['name']:45} "
                f"| Composite: {school['composite_score']:5.1f} "
                f"| Tier: {school['admissibility_tier']:12} "
                f"| Admit: {school['admissibility_score']:5.1f} "
                f"| Goal: {school['goal_fit_score']:5.1f}"
            )

        output_lines.append("")
        output_lines.append(f"Analysis:")
        output_lines.append(f"  - Top school: {ranked[0]['name']}")
        output_lines.append(f"  - Admissibility score range: {ranked[-1]['admissibility_score']:.1f} - {ranked[0]['admissibility_score']:.1f}")
        output_lines.append(f"  - Tier breakdown: {', '.join(set(s['admissibility_tier'] for s in ranked))}")

    except Exception as e:
        output_lines.append(f"ERROR: {e}")

    output_lines.append("")

# Write to file
output_text = "\n".join(output_lines)
with open("algorithm_test_results_v2.txt", "w", encoding="utf-8") as f:
    f.write(output_text)

print(output_text)
print("\nResults saved to algorithm_test_results_v2.txt")
