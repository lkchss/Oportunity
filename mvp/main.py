"""Streamlit entry point for Opportunity MVP."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import io

import pypdf
import streamlit as st
from dotenv import load_dotenv

from mvp.search import find_opportunities

load_dotenv()

CATEGORIES = [
    "Jobs",
    "Internships",
    "Graduate school",
    "Fellowships / Scholarships",
    "Gap year programs",
    "Travel / Volunteer",
]


def run() -> None:
    st.set_page_config(page_title="Opportunity Finder", layout="wide")
    st.title("Opportunity Finder")
    st.caption("Tell us about you. We'll search for matching opportunities.")

    category = st.selectbox("What are you looking for?", CATEGORIES)

    resume_file = st.file_uploader("Resume (optional PDF)", type=["pdf"])
    resume_text: str = ""
    if resume_file is not None:
        reader = pypdf.PdfReader(io.BytesIO(resume_file.read()))
        resume_text = "\n".join(page.extract_text() or "" for page in reader.pages)
        st.success(f"Resume loaded — {len(reader.pages)} page(s)")

    background = st.text_area(
        "Your background",
        height=180,
        placeholder="Education, work experience, skills, location, anything relevant.",
    )
    goals = st.text_area(
        "What you want",
        height=120,
        placeholder="What kind of opportunity, ideal outcome, constraints (timing, location, compensation).",
    )

    ready = bool(goals and (background or resume_text))
    if st.button("Find opportunities", type="primary", disabled=not ready):
        with st.spinner("Searching..."):
            results = find_opportunities(
                category=category,
                background=background,
                goals=goals,
                resume_text=resume_text,
            )
        st.session_state["results"] = results

    results = st.session_state.get("results")
    if results:
        st.subheader(f"Top {len(results)} matches")
        for r in results:
            with st.container(border=True):
                st.markdown(f"### [{r['title']}]({r['url']})")
                st.write(r.get("summary", ""))
                if r.get("why_match"):
                    st.markdown(f"**Why this fits:** {r['why_match']}")
    elif results is not None:
        st.warning("No results found. Try adding more detail to your background or goals.")


if __name__ == "__main__":
    run()
