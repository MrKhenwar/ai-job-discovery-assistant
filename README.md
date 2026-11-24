# AI Job Discovery Assistant (SCSE4041 Mini Project, Milestone 2)

A 3-prompt pipeline that turns a free-text self-description into 5 ranked job roles and a 7-day search plan.

- Team ID: [FILL]
- Team name: Wadit
- Team members: S24CSEU0178 - Vidit Raj Khenwar (leader), S24CSEU0229 - Wafiq Ahsan
- Repository: https://github.com/MrKhenwar/ai-job-discovery-assistant
- Prototype link: https://ai-job-discovery-wadit.streamlit.app/
- Reel link: [FILL]

## How it works
P1 extracts a profile (JSON) -> P2 recommends 5 roles (JSON) -> P3 writes a search plan (text). If P1 finds too little information, the app asks a follow-up question instead of guessing.

## Run it
```
pip install -r requirements.txt
export GEMINI_API_KEY=your_key      # never commit this
streamlit run code/app.py
```

## Run the tests
```
python code/run_tests.py                 # all inputs once -> test-data/outputs, test-data/results.md
python code/run_tests.py --versions 10   # compare P2 v1/v2/v3 -> test-data/version_comparison.csv
```

## Folders
- `prompts/` v1-v3 (P2 versions) and `final/` (P1, P2, P3)
- `code/` app, pipeline, LLM wrapper, test runner
- `test-data/` test inputs and saved outputs
- `docs/` diagrams and the Milestone 2 PDF
- `CHANGELOG.md` dated changes since Milestone 1
