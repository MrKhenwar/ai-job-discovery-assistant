"""Streamlit prototype. Run: streamlit run code/app.py"""
import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from llm import call_llm  # noqa: E402
from pipeline import run_pipeline  # noqa: E402

st.set_page_config(page_title="AI Job Discovery Assistant", page_icon="🔎")
st.title("🔎 AI Job Discovery Assistant")
st.caption("Describe your skills and goals. Get 5 matching roles and a 7-day search plan.")

text = st.text_area(
    "About you (skills, education, experience, location, what you want)", height=160,
    placeholder="Final year BCA student, know Python, SQL and Power BI. Looking for data analyst jobs in Pune.",
)

if st.button("Find roles", type="primary"):
    if not text.strip():
        st.warning("Please describe yourself first.")
    else:
        with st.spinner("Working..."):
            try:
                out = run_pipeline(call_llm, text.strip(), strict=False)
            except Exception as e:  # API/network errors
                st.error(f"Could not reach the model: {e}")
                st.stop()
        if out["stopped_at"] == "P1" and out.get("profile", {}).get("status") == "insufficient":
            st.info(out["profile"].get("ask", "Please tell me more about your skills and the job you want."))
        elif out["stopped_at"]:
            st.error("Something went wrong: " + "; ".join(out["errors"]) + " Please try again.")
        else:
            with st.expander("Profile understood", expanded=False):
                st.json(out["profile"])
                if out["profile"].get("flags"):
                    st.warning("Check this: " + "; ".join(out["profile"]["flags"]))
            st.subheader("Recommended roles")
            for r in out["roles"]["roles"]:
                st.markdown(f"**{r['title']}**: fit {r['fit_score']}/100")
                st.write(r["why"])
                st.caption("Search: " + " | ".join(r["search_keywords"]) + "  \nGaps: " + (", ".join(r["skill_gaps"]) or "none"))
            st.subheader("Your search plan")
            st.text(out["plan"])
