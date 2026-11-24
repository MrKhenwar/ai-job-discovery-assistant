import csv, json, re, sys
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                Image, PageBreak, KeepTogether)

R = Path(__file__).resolve().parent.parent
OUT = R / "docs"
ss = getSampleStyleSheet()
B = ParagraphStyle("B", parent=ss["BodyText"], fontSize=9.5, leading=13)
H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontSize=17, spaceAfter=8)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12, spaceBefore=8, spaceAfter=4)
H3 = ParagraphStyle("H3", parent=ss["Heading3"], fontSize=10, spaceBefore=6, spaceAfter=2)
C = ParagraphStyle("C", parent=B, fontName="Courier", fontSize=7, leading=8.6)
T = ParagraphStyle("T", parent=B, fontSize=8, leading=10)
FILL = lambda s: f'<font color="#C00000"><b>[FILL: {escape(s)}]</b></font>'

TEAM_NAME = "Wadit"
TEAM_ID = "WADIT"
BATCH = "2"
FACULTY_NAME = "Sonal"
MEMBERS = "S24CSEU0178 - Vidit Raj Khenwar (leader)<br/>S24CSEU0229 - Wafiq Ahsan"
PROTOTYPE_LINK = "https://ai-job-discovery-wadit.streamlit.app/"
REPO_LINK = "https://github.com/MrKhenwar/ai-job-discovery-assistant"

def P(t, st=B): return Paragraph(t, st)
def code(text):
    return Paragraph(escape(text).replace("\n", "<br/>").replace("  ", "&nbsp;&nbsp;"), C)
def table(rows, widths, head=True):
    data = [[Paragraph(c if isinstance(c, str) else str(c), T) for c in r] for r in rows]
    t = Table(data, colWidths=[w * cm for w in widths], repeatRows=1 if head else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.4, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP")]
    if head: st.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EDF7")))
    t.setStyle(TableStyle(st)); return t
def img(name, w=16.5):
    from PIL import Image as PI
    p = R / "docs" / name; iw, ih = PI.open(p).size
    return Image(str(p), width=w * cm, height=w * cm * ih / iw)

def split(path):
    t = (R / path).read_text(encoding="utf-8")
    parts = re.split(r"^\[(SETTINGS|SYSTEM|USER)\]\s*$", t, flags=re.M)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}

def footer(c, d):
    c.setFont("Helvetica", 7.5); c.drawString(2 * cm, 1.2 * cm, "SCSE4041 Mini Project - Milestone 2"); c.drawRightString(19 * cm, 1.2 * cm, f"Page {d.page}")

def doc(path, story): SimpleDocTemplate(str(path), pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=1.8*cm, bottomMargin=1.8*cm).build(story, onFirstPage=footer, onLaterPages=footer)

TITLE = "AI Job Discovery Assistant"
cases = json.loads((R / "test-data/inputs.json").read_text(encoding="utf-8"))

# ---------- parse real results.md into {id: (actual, pass_fail)} ----------
def load_results():
    out = {}
    path = R / "test-data/results.md"
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines()[2:]:
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 6:
            continue
        try:
            rid = int(cells[0])
        except ValueError:
            continue
        out[rid] = (cells[4], cells[5])
    return out

results = load_results()
n_pass = sum(1 for a, pf in results.values() if pf == "Pass")
n_total = len(results)

# ---------- parse real version_comparison.csv ----------
def load_versions():
    path = R / "test-data/version_comparison.csv"
    if not path.exists():
        return {}
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return {r["version"]: r for r in rows}

versions = load_versions()
def vfmt(v, key):
    r = versions.get(v)
    return FILL("run --versions 10") if not r else r[key] + ("%" if "pct" in key else "")

# ---------- supporting document (technical report) ----------
def tech_report():
    s = [P("Technical Report: " + TITLE, H1),
         P(f"Team: {TEAM_NAME} &nbsp; Project: SCSE4041 Mini Project", B),
         P("1. Architecture", H2),
         P("A browser user types free text into a Streamlit app (code/app.py). The pipeline (code/pipeline.py) loads three prompt files from prompts/final/ and calls an LLM through a small wrapper (code/llm.py). A test runner (code/run_tests.py) feeds saved inputs through the same pipeline and stores outputs in test-data/. API keys are read from environment variables and are not stored in the repository."),
         img("architecture.png", 16.5),
         P("2. Tools and models", H2),
         P("Gemini 3.5 Flash-Lite (Google AI Studio API) is the default provider for all three prompts in the shipped app (deployed prototype). Gemini 2.5 Flash was the original target, but it was deprecated (shutdown Oct 16 2026) and its free-tier quota fell to 20 requests/day on this account, which is too low to run a 13-case suite plus a 180-call version comparison. code/llm.py therefore supports an LLM_PROVIDER env var (gemini, groq, openrouter, or auto, which falls back across providers on rate limits/errors): the Section 4 test results were collected via Groq (openai/gpt-oss-120b), and the P2 version-comparison numbers via the auto-fallback chain across Groq and OpenRouter free-tier models, since a single free-tier model's daily token cap was not enough for the full 180-call comparison; the deployed app still defaults to Gemini. Python 3, Streamlit for the interface, Graphviz for diagrams."),
         P("3. Prompt design", H2),
         P("The task is split into three prompts so each has one job and a checkable output. P1 turns free text into a profile JSON and refuses when information is insufficient (guards against empty input, gibberish and prompt injection by treating the user text as data). P2 ranks exactly 5 roles with a fixed scoring rubric and JSON schema. P3 writes a plain-text search plan from the first two outputs. P2 was iterated through three versions: v1 one-line prompt, v2 rubric plus JSON schema, v3 one worked example, explicit constraints and temperature 0.2 (full text in Milestone 2 PDF, Section 3)."),
         P("4. Test results", H2),
         P(f"13 test inputs (6 normal, 4 edge, 3 invalid) were run through the pipeline. Passed: {n_pass} of {n_total}. P2 version comparison (10 runs per profile): valid JSON v1 {vfmt('v1','valid_json_pct')}, v2 {vfmt('v2','valid_json_pct')}, v3 {vfmt('v3','valid_json_pct')}; schema-compliant v3 {vfmt('v3','schema_ok_pct')}. Source: test-data/results.md and test-data/version_comparison.csv."),
         P("5. Limitations", H2),
         P("(a) Role suggestions come from the model's general knowledge, not live job listings, so availability is not verified. (b) Fit scores are model-estimated and vary a little between runs and between providers even at low temperature (observed when cross-checking Gemini vs Groq outputs for the same input). (c) A very long skill list with no stated target role or education (Test 8) was correctly treated by P1 as insufficient information and met with a follow-up question rather than a guess -- safer behaviour, but it does not satisfy a test case whose literal expectation was '5 roles, no crash'. Next: connect a live job-search source, add a resume upload, and loosen P1's insufficiency bar when the profile already contains a long, specific skill list even without an explicit stated role."),
         ]
    return s

# ---------- Milestone 2 PDF ----------
s = []
s += [P("1. Cover page", H1), Spacer(1, 6), P(TITLE, ParagraphStyle("t", parent=H1, fontSize=22)), P("Prompt Design and Demonstration - Milestone 2", H2)]
s.append(table([["Team ID", TEAM_ID], ["Team name", TEAM_NAME],
    ["Project title", TITLE], ["Batch", BATCH],
    ["Faculty name", FACULTY_NAME], ["Members", MEMBERS],
    ["Prototype link", PROTOTYPE_LINK], ["Repository link", REPO_LINK], ["Reel link", FILL("link") + " (length " + FILL("seconds, 90-150") + ")"]], [3.5, 13.5], head=False))
s.append(PageBreak())

s += [P("2. Prompt and solution design", H1), P("(a) Overview", H2)]
s += [P("<b>Problem and users.</b> Students and early-career job seekers in India often do not know which roles fit their skills or where to start searching. The tool takes a short free-text description and returns matching roles and a concrete search plan."),
      P("<b>Input and output.</b> Input: free text (skills, education, experience, location, goal). Output: profile JSON, 5 ranked roles with fit score, reasons, search keywords and skill gaps, then a 180-word search plan."),
      P("<b>Prompts and why.</b> 3 prompts in a chain. One prompt doing everything gave long, unchecked answers; splitting gives a JSON checkpoint after each step, lets us stop early on invalid input, and lets us improve one step at a time."),
      P("<b>Tool and model.</b> Gemini 3.5 Flash-Lite via Google AI Studio API is the default for the deployed app; fast, free tier, follows JSON-only instructions well at low temperature. code/llm.py also supports Groq and OpenRouter (LLM_PROVIDER=groq/openrouter/auto) as interchangeable free-tier providers, with auto mode falling back to the next provider on a rate limit or error; this was used to gather the test results below after Gemini 2.5 Flash's Oct 2026 deprecation cut its free-tier quota to 20 requests/day."),
      P("<b>What changed since Milestone 1.</b> Added the P1 profile extractor with an insufficient-information follow-up path, the P3 search-plan writer, a fixed JSON schema and scoring rubric for P2, a Streamlit prototype, a test runner that saves real outputs for 13 inputs plus a P2 version comparison, and deployed the app publicly."),
      P("(b) Diagrams", H2), P("Prompt workflow", H3), img("workflow.png"), P("Task decomposition", H3), img("decomposition.png", 11),
      P("Input-output flow", H3), img("io_flow.png"), P("System architecture", H3), img("architecture.png"),
      P("No agent loop or retrieval is used, so no agent/RAG diagram is included.", T), PageBreak(), P("(c) Prompt sheets", H2)]

SAMPLE_INPUT = "Final year BCA student, know Python, SQL and Power BI. Looking for data analyst jobs in Pune."
sample = None
try:
    sample = json.loads((R / "test-data/outputs/test_01.json").read_text(encoding="utf-8"))["result"]
except Exception:
    pass

sheets = [
 ("P1", "Profile Extractor", "prompts/final/P1_profile_extractor.txt", "Step 1 of 3", "Convert free text into a structured profile or ask for missing information.", "candidate_text", "The user's raw text, wrapped in &lt;candidate_text&gt; tags", "2", "Single JSON object (profile or insufficient)", lambda: sample.get("p1_raw", "") if sample else ""),
 ("P2", "Role Recommender", "prompts/final/P2_role_recommender.txt", "Step 2 of 3", "Rank 5 realistic roles for the profile with scores, reasons, keywords and gaps.", "profile_json", "The JSON profile produced by P1", "1 (first role shown)", "Single JSON object {roles:[5 items]}", lambda: sample.get("p2_raw", "") if sample else ""),
 ("P3", "Search Plan Writer", "prompts/final/P3_search_plan.txt", "Step 3 of 3", "Turn profile and roles into a short, actionable 7-day plan.", "profile_json, roles_json", "profile_json: P1 output. roles_json: P2 output", "0 (layout template given)", "Plain text, fixed layout, max 180 words", lambda: sample.get("plan", "") if sample else ""),
]
for pid, name, path, step, purpose, var, varhold, nex, fmt, getout in sheets:
    sec = split(path)
    temp = sec["SETTINGS"].split("=")[1]
    s.append(KeepTogether([P(f"Prompt sheet {pid}: {name}", H3), table([
        ["Prompt ID and name", f"{pid} {name}"], ["Step in workflow", step], ["Purpose", purpose],
        ["Tool and model", "Gemini 3.5 Flash-Lite, Google AI Studio API (deployed app)"], ["Settings", f"temperature {temp}, other settings default"],
        ["Variables", f"{{{var}}}: {varhold}"], ["Examples included", nex], ["Output format", fmt]], [4, 13], head=False)]))
    out_text = getout()
    s += [P("<b>Full system prompt</b>", T), code(sec["SYSTEM"]), Spacer(1, 4), P("<b>Full user prompt template</b>", T), code(sec["USER"]), Spacer(1, 4),
          P(f"<b>Sample run</b> -- real input: “{escape(SAMPLE_INPUT)}”", T),
          code(out_text if out_text else "(no saved output -- run code/run_tests.py first)"), Spacer(1, 8)]
s.append(PageBreak())

s += [P("3. Implementation", H1), P("What is built: a Streamlit web app that runs the 3-prompt pipeline, a pipeline module that loads prompt files and validates JSON between steps, and a test runner that saves real outputs.", B), P("Module status", H2)]
s.append(table([["Module", "What it does", "Status", "Notes"],
 ["P1 Profile Extractor", "Free text to profile JSON; refuses insufficient input", "Working", f"{n_pass}/{n_total} suite tests pass; insufficient-info path confirmed on Tests 10-13"],
 ["P2 Role Recommender", "Ranks 5 roles as JSON", "Working", "Schema-valid 5-role output confirmed across normal and edge cases"],
 ["P3 Search Plan Writer", "Writes 7-day plan", "Working", "TOP PICK plan produced for every case that reached P3"],
 ["Streamlit UI", "Input box, results display, error handling", "Working", f"Deployed and tested live at {PROTOTYPE_LINK}"],
 ["Test runner", "Runs 13 inputs, writes outputs and results.md", "Working", "test-data/results.md and test-data/outputs/*.json generated by a real run"]], [3.6, 6, 3.4, 4]))
s.append(P("Prompt iteration log (prompt P2)", H2))
s.append(table([["Version", "What changed", "Why it was changed", "Result after the change"],
 ["v1", "One-line prompt: suggest suitable job roles, no system prompt, default settings", "Starting point",
  f"valid JSON {vfmt('v1','valid_json_pct')}, schema-ok {vfmt('v1','schema_ok_pct')} ({versions.get('v1',{}).get('runs','?')} runs)"],
 ["v2", "Added system prompt, fixed 5 roles, scoring rubric, JSON schema", "v1 output was free text with no fixed structure and varied between runs",
  f"valid JSON {vfmt('v2','valid_json_pct')}, schema-ok {vfmt('v2','schema_ok_pct')} ({versions.get('v2',{}).get('runs','?')} runs)"],
 ["v3", "Added one worked example, explicit constraints (no fences, realistic level, no companies), temperature 0.2", "v2 sometimes wrapped JSON in markdown fences or picked an unrealistic seniority level",
  f"valid JSON {vfmt('v3','valid_json_pct')}, schema-ok {vfmt('v3','schema_ok_pct')} ({versions.get('v3',{}).get('runs','?')} runs), top-score stdev {versions.get('v3',{}).get('avg_top_score_stdev','?')}"]], [1.4, 5.6, 4.4, 5.6]))
s.append(P("Full text of each version", H2))
for v in ("v1", "v2", "v3"):
    sec = split(f"prompts/{v}/P2_role_recommender.txt")
    s += [P(f"P2 {v}", H3), P("Settings: temperature " + sec["SETTINGS"].split("=")[1], T), P("<b>System:</b>", T), code(sec["SYSTEM"]), P("<b>User:</b>", T), code(sec["USER"]), Spacer(1, 6)]
s.append(PageBreak())

s += [P("4. Demonstration and testing", H1), P("Test table (13 inputs: 6 normal, 4 edge, 3 invalid), from a real run of code/run_tests.py.", B)]
rows = [["No.", "Input (short)", "Type", "Expected output", "Actual output (short)", "Pass/Fail"]]
for c in cases:
    actual, pf = results.get(c["id"], (FILL("run code/run_tests.py"), FILL("P/F")))
    rows.append([c["id"], escape(c["short"]), c["type"], escape(c["expected_text"]), escape(actual), pf])
s.append(table(rows, [0.9, 3.6, 1.4, 4.3, 3.7, 1.6]))
s += [P("Screenshots (real runs on the deployed app)", H2),
      img("screenshots/test1_roles.jpg", 16), P("Test 1: Data analyst profile -- profile understood and recommended roles.", T), Spacer(1, 6),
      img("screenshots/test1_searchplan.jpg", 16), P("Test 1: Data analyst profile -- generated 7-day search plan.", T),
      P("Known limitations and next steps", H2),
      P("1) Test 8 (a 30+ skill list with no stated target role or education) was treated as insufficient information by P1 and met with a follow-up question instead of 5 roles -- correct per the 'don't guess' design, but it fails that test's literal expectation. Next: infer a plausible target role from a sufficiently long, specific skill list before asking a follow-up question.", T),
      P("2) Fit scores vary slightly between repeated runs and between model providers (seen when cross-checking Gemini vs Groq outputs for the same profile), even at temperature 0.2. Next: report a score range rather than a single number, or average over a few calls for the final displayed score.", T),
      P(f"3) Gemini 2.5 Flash's free-tier quota dropped to 20 requests/day after its deprecation, making full-suite testing impractical on Gemini alone within a day. Next: request a paid/higher-quota tier for Gemini before relying on it for repeated full-suite runs ({n_pass}/{n_total} pass rate above was measured via the Groq provider).", T)]
s.append(PageBreak())

s += [P("5. Repository", H1), img("screenshots/github_repo.jpg", 16) if (R / "docs/screenshots/github_repo.jpg").exists() else P(FILL("insert one screenshot of the GitHub repository showing prompts/, code/, test-data/, docs/, README.md, CHANGELOG.md")),
      P("Changes since Milestone 1", H2),
      P((R / "CHANGELOG.md").read_text(encoding="utf-8").split("\n\n", 1)[-1].replace("\n", "<br/>")),
      P("Check before submitting: no API key anywhere in the repository; link opens in a private window without requesting access.", T), PageBreak()]

s += [P("6. Supporting document", H1)] + tech_report()[1:] + [PageBreak()]

s += [P("7. Team contribution", H1)]
s.append(table([["Member name", "Enrollment no.", "Role", "Tasks done in Milestone 2", "Evidence", "Contribution (%)"],
  ["Vidit Raj Khenwar", "S24CSEU0178", "Team lead; prompts and pipeline",
   "Designed and iterated P1/P2/P3 prompts (v1-v3 of P2), built the pipeline and LLM wrapper, deployed the app to Streamlit Community Cloud",
   "prompts/final/, code/pipeline.py, code/llm.py, deployed link", "55"],
  ["Wafiq Ahsan", "S24CSEU0229", "Testing and documentation",
   "Wrote the 13-case test suite and inputs, ran the version comparison, wrote README/CHANGELOG and the Milestone 2 report",
   "test-data/inputs.json, test-data/results.md, docs/build_pdf.py, README.md", "45"]], [2.6, 2.6, 2.2, 4, 3.4, 2.2]))
s.append(P("Every member owns at least one specific task with evidence. Percentages add up to 100. All members agree to this table.", T))

doc(OUT / f"M2_{TEAM_NAME}_AIJobDiscoveryAssistant.pdf", s)
doc(OUT / f"{TEAM_NAME}_TechnicalReport.pdf", [P("Technical Report: " + TITLE, H1)] + tech_report()[1:])
print("built")
