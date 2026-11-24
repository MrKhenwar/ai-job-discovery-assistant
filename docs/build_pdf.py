import json, re, sys
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                Image, PageBreak, KeepTogether)

R = Path("/home/claude/repo")
OUT = Path("/home/claude/out"); OUT.mkdir(exist_ok=True)
ss = getSampleStyleSheet()
B = ParagraphStyle("B", parent=ss["BodyText"], fontSize=9.5, leading=13)
H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontSize=17, spaceAfter=8)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12, spaceBefore=8, spaceAfter=4)
H3 = ParagraphStyle("H3", parent=ss["Heading3"], fontSize=10, spaceBefore=6, spaceAfter=2)
C = ParagraphStyle("C", parent=B, fontName="Courier", fontSize=7, leading=8.6)
T = ParagraphStyle("T", parent=B, fontSize=8, leading=10)
FILL = lambda s: f'<font color="#C00000"><b>[FILL: {escape(s)}]</b></font>'

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

# ---------- supporting document (technical report) ----------
def tech_report():
    s = [P("Technical Report: " + TITLE, H1),
         P("Team: " + FILL("team name") + " &nbsp; Project: SCSE4041 Mini Project", B),
         P("1. Architecture", H2),
         P("A browser user types free text into a Streamlit app (code/app.py). The pipeline (code/pipeline.py) loads three prompt files from prompts/final/ and calls Gemini 3.5 Flash-Lite through a small wrapper (code/llm.py). A test runner (code/run_tests.py) feeds saved inputs through the same pipeline and stores outputs in test-data/. The API key is read from an environment variable and is not stored in the repository."),
         img("architecture.png", 16.5),
         P("2. Tools and models", H2),
         P("Gemini 3.5 Flash-Lite (Google AI Studio API) for all three prompts; Python 3, Streamlit for the interface, Graphviz for diagrams. Flash-Lite was chosen for low latency and free-tier availability; each run makes three short calls. (Originally built against Gemini 2.5 Flash; that model was deprecated Oct 16 2026 and its free-tier quota fell to 20 requests/day on this account, so we moved to Gemini 3.5 Flash-Lite, which had separate, usable quota.)"),
         P("3. Prompt design", H2),
         P("The task is split into three prompts so each has one job and a checkable output. P1 turns free text into a profile JSON and refuses when information is insufficient (guards against empty input, gibberish and prompt injection by treating the user text as data). P2 ranks exactly 5 roles with a fixed scoring rubric and JSON schema. P3 writes a plain-text search plan from the first two outputs. P2 was iterated through three versions: v1 one-line prompt, v2 rubric plus JSON schema, v3 one worked example, explicit constraints and temperature 0.2 (full text in Milestone 2 PDF, Section 3)."),
         P("4. Test results", H2),
         P("13 test inputs (6 normal, 4 edge, 3 invalid) were run through the pipeline. Passed: " + FILL("n of 13") + ". P2 version comparison (" + FILL("N") + " runs per profile): valid JSON v1 " + FILL("%") + ", v2 " + FILL("%") + ", v3 " + FILL("%") + "; schema-compliant v3 " + FILL("%") + ". Source: test-data/results.md and test-data/version_comparison.csv."),
         P("5. Limitations", H2),
         P("(a) Role suggestions come from the model's general knowledge, not live job listings, so availability is not verified. (b) Fit scores are model-estimated and may vary slightly between runs even at low temperature. (c) Hinglish and very long inputs are handled less reliably than plain English. " + FILL("add/replace with limitations you actually observe") + " Next: connect a live job-search source and add a resume upload."),
         ]
    return s

# ---------- Milestone 2 PDF ----------
s = []
s += [P("1. Cover page", H1), Spacer(1, 6), P(TITLE, ParagraphStyle("t", parent=H1, fontSize=22)), P("Prompt Design and Demonstration - Milestone 2", H2)]
s.append(table([["Team ID", FILL("Team ID from Milestone 1")], ["Team name", FILL("exactly as in Milestone 1")],
    ["Project title", TITLE + " " + FILL("must match Milestone 1 title and Form Q3")], ["Batch", FILL("e.g. B13-24")],
    ["Faculty name", FILL("faculty name")], ["Members", FILL("one per line: S24CSEU____ - Name (leader first)")],
    ["Prototype link", FILL("link")], ["Repository link", FILL("link")], ["Reel link", FILL("link") + " (length " + FILL("seconds, 90-150") + ")"]], [3.5, 13.5], head=False))
s.append(PageBreak())

s += [P("2. Prompt and solution design", H1), P("(a) Overview", H2)]
s += [P("<b>Problem and users.</b> Students and early-career job seekers in India often do not know which roles fit their skills or where to start searching. The tool takes a short free-text description and returns matching roles and a concrete search plan."),
      P("<b>Input and output.</b> Input: free text (skills, education, experience, location, goal). Output: profile JSON, 5 ranked roles with fit score, reasons, search keywords and skill gaps, then a 180-word search plan."),
      P("<b>Prompts and why.</b> 3 prompts in a chain. One prompt doing everything gave long, unchecked answers; splitting gives a JSON checkpoint after each step, lets us stop early on invalid input, and lets us improve one step at a time."),
      P("<b>Tool and model.</b> Gemini 3.5 Flash-Lite via Google AI Studio API: fast, free tier, follows JSON-only instructions well at low temperature."),
      P("<b>What changed since Milestone 1.</b> " + FILL("write what really changed, e.g. added P1/P3, insufficient-info path, JSON schema, test runner, Streamlit prototype")),
      P("(b) Diagrams", H2), P("Prompt workflow", H3), img("workflow.png"), P("Task decomposition", H3), img("decomposition.png", 11),
      P("Input-output flow", H3), img("io_flow.png"), P("System architecture", H3), img("architecture.png"),
      P("No agent loop or retrieval is used, so no agent/RAG diagram is included.", T), PageBreak(), P("(c) Prompt sheets", H2)]

sheets = [
 ("P1", "Profile Extractor", "prompts/final/P1_profile_extractor.txt", "Step 1 of 3", "Convert free text into a structured profile or ask for missing information.", "candidate_text", "The user's raw text, wrapped in &lt;candidate_text&gt; tags", "2", "Single JSON object (profile or insufficient)"),
 ("P2", "Role Recommender", "prompts/final/P2_role_recommender.txt", "Step 2 of 3", "Rank 5 realistic roles for the profile with scores, reasons, keywords and gaps.", "profile_json", "The JSON profile produced by P1", "1 (first role shown)", "Single JSON object {roles:[5 items]}"),
 ("P3", "Search Plan Writer", "prompts/final/P3_search_plan.txt", "Step 3 of 3", "Turn profile and roles into a short, actionable 7-day plan.", "profile_json, roles_json", "profile_json: P1 output. roles_json: P2 output", "0 (layout template given)", "Plain text, fixed layout, max 180 words"),
]
for pid, name, path, step, purpose, var, varhold, nex, fmt in sheets:
    sec = split(path)
    temp = sec["SETTINGS"].split("=")[1]
    s.append(KeepTogether([P(f"Prompt sheet {pid}: {name}", H3), table([
        ["Prompt ID and name", f"{pid} {name}"], ["Step in workflow", step], ["Purpose", purpose],
        ["Tool and model", "Gemini 3.5 Flash-Lite, Google AI Studio API"], ["Settings", f"temperature {temp}, other settings default"],
        ["Variables", f"{{{var}}}: {varhold}"], ["Examples included", nex], ["Output format", fmt]], [4, 13], head=False)]))
    s += [P("<b>Full system prompt</b>", T), code(sec["SYSTEM"]), Spacer(1, 4), P("<b>Full user prompt template</b>", T), code(sec["USER"]), Spacer(1, 4),
          P("<b>Sample run</b> (real input and actual output): " + FILL(f"run the app, paste the exact input and the exact {pid} output as text"), T), Spacer(1, 8)]
s.append(PageBreak())

s += [P("3. Implementation", H1), P("What is built: a Streamlit web app that runs the 3-prompt pipeline, a pipeline module that loads prompt files and validates JSON between steps, and a test runner that saves real outputs. Status values below must be set honestly after you test each module.", B), P("Module status", H2)]
s.append(table([["Module", "What it does", "Status", "Notes"],
 ["P1 Profile Extractor", "Free text to profile JSON; refuses insufficient input", FILL("Working / Partly working / Not started"), FILL("notes")],
 ["P2 Role Recommender", "Ranks 5 roles as JSON", FILL("status"), FILL("notes")],
 ["P3 Search Plan Writer", "Writes 7-day plan", FILL("status"), FILL("notes")],
 ["Streamlit UI", "Input box, results display, error handling", FILL("status"), FILL("notes")],
 ["Test runner", "Runs 13 inputs, writes outputs and results.md", FILL("status"), FILL("notes")]], [3.6, 6, 3.4, 4]))
s.append(P("Prompt iteration log (prompt P2)", H2))
s.append(table([["Version", "What changed", "Why it was changed", "Result after the change"],
 ["v1", "One-line prompt: suggest suitable job roles, no system prompt, default settings", "Starting point", FILL("observed result with numbers, from run_tests.py --versions")],
 ["v2", "Added system prompt, fixed 5 roles, scoring rubric, JSON schema", "v1 output was free text with no structure and varied between runs " + FILL("confirm"), FILL("observed result with numbers")],
 ["v3", "Added one worked example, explicit constraints (no fences, realistic level, no companies), temperature 0.2", FILL("what failed in v2 that this fixes"), FILL("observed result with numbers")]], [1.4, 5.6, 4.4, 5.6]))
s.append(P("Full text of each version", H2))
for v in ("v1", "v2", "v3"):
    sec = split(f"prompts/{v}/P2_role_recommender.txt")
    s += [P(f"P2 {v}", H3), P("Settings: temperature " + sec["SETTINGS"].split("=")[1], T), P("<b>System:</b>", T), code(sec["SYSTEM"]), P("<b>User:</b>", T), code(sec["USER"]), Spacer(1, 6)]
s.append(PageBreak())

s += [P("4. Demonstration and testing", H1), P("Test table (13 inputs: 6 normal, 4 edge, 3 invalid). Fill Actual and Pass/Fail from test-data/results.md after a real run. Failed tests are fine; do not hide them.", B)]
rows = [["No.", "Input (short)", "Type", "Expected output", "Actual output (short)", "Pass/Fail"]]
for c in cases:
    rows.append([c["id"], escape(c["short"]), c["type"], escape(c["expected_text"]), FILL("actual"), FILL("P/F")])
s.append(table(rows, [0.9, 3.6, 1.4, 4.3, 3.7, 1.6]))
s += [P("Screenshots (2-3 real runs)", H2), P(FILL("insert 2-3 screenshots from the running app; caption each with its test number, e.g. 'Test 1: Data analyst profile'")),
      P("Known limitations and next steps", H2), P(FILL("2-4 limitations you actually saw, each with what you will try next. Example format: 'Hinglish input sometimes returns Hindi words in the plan (Test 7). Next: add an explicit translate-to-English step.'"))]
s.append(PageBreak())

s += [P("5. Repository", H1), P(FILL("insert one screenshot of the GitHub repository or Drive folder showing prompts/, code/, test-data/, docs/, README.md, CHANGELOG.md")),
      P("Changes since Milestone 1", H2), P(FILL("3-5 lines that match the real commit dates or CHANGELOG.md entries, e.g. 'Added P1 extractor and insufficient-info path (date)'")),
      P("Check before submitting: no API key anywhere in the repository; link opens in a private window without requesting access.", T), PageBreak()]

s += [P("6. Supporting document", H1)] + tech_report()[1:] + [PageBreak()]

s += [P("7. Team contribution", H1)]
s.append(table([["Member name", "Enrollment no.", "Role", "Tasks done in Milestone 2", "Evidence", "Contribution (%)"],
  [FILL("name"), FILL("S24CSEU____"), FILL("role"), FILL("specific tasks"), FILL("file, commit or prompt ID"), FILL("%")],
  [FILL("name"), FILL("S24CSEU____"), FILL("role"), FILL("specific tasks"), FILL("file, commit or prompt ID"), FILL("%")],
  [FILL("name"), FILL("S24CSEU____"), FILL("role"), FILL("specific tasks"), FILL("file, commit or prompt ID"), FILL("%")]], [2.6, 2.6, 2.2, 4, 3.4, 2.2]))
s.append(P("Every member owns at least one specific task with evidence. Percentages add up to 100. All members agree to this table.", T))

doc(OUT / "M2_TEAMID_ProjectTitle.pdf", s)
doc(OUT / "TEAMNAME_TechnicalReport.pdf", [P("Technical Report: " + TITLE, H1)] + tech_report()[1:])
print("built")
