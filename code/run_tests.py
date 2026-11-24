"""Run the test inputs through the real pipeline and save outputs.

  python code/run_tests.py              # one run of every test input -> test-data/outputs + results.md
  python code/run_tests.py --versions 10  # compare P2 v1/v2/v3, N runs each -> version_comparison.csv

These call the real model, so results are real observations. Nothing here is pre-filled.
"""
import argparse
import csv
import json
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from llm import call_llm  # noqa: E402
from pipeline import PROMPTS, ROOT, fill, load_prompt, parse_json, roles_schema_ok, run_pipeline  # noqa: E402

TESTS = ROOT / "test-data"
HINGLISH = re.compile(r"\b(mujhe|chahiye|hai|hoon|mein|aati|aur|abhi)\b", re.I)


def check(case, out):
    """Return (passed, actual_short)."""
    exp = case["expect"]
    status = out.get("profile", {}).get("status") if "profile" in out else None
    if exp == "insufficient":
        ok = status == "insufficient" and out["stopped_at"] == "P1" and "plan" not in out
        return ok, f"status={status}; ask={out.get('profile', {}).get('ask', '-')[:60]}"
    if out["stopped_at"] and exp == "any" and status == "insufficient":
        return True, f"asked for more info: {out['profile'].get('ask', '')[:60]}"
    if out["stopped_at"] or "roles" not in out:
        return False, "pipeline stopped: " + "; ".join(out["errors"] or [str(status)])
    schema = roles_schema_ok(out["roles"])
    top = out["roles"]["roles"][0] if schema else {}
    ok = schema and "TOP PICK" in out.get("plan", "")
    if case.get("check_flags"):
        ok = ok and bool(out["profile"].get("flags"))
    if case.get("check_english"):
        ok = ok and not HINGLISH.search(out.get("plan", "")) and not re.search(r"[ऀ-ॿ]", out["plan"])
    actual = f"5 roles; top: {top.get('title')} ({top.get('fit_score')})" if schema else "roles schema invalid"
    if case.get("check_flags"):
        actual += f"; flags={out['profile'].get('flags')}"
    return ok, actual


def run_all():
    cases = json.loads((TESTS / "inputs.json").read_text(encoding="utf-8"))
    (TESTS / "outputs").mkdir(exist_ok=True)
    rows = ["| No. | Input | Type | Expected | Actual | Pass/Fail |", "|---|---|---|---|---|---|"]
    for c in cases:
        out = run_pipeline(call_llm, c["text"])
        ok, actual = check(c, out)
        (TESTS / "outputs" / f"test_{c['id']:02d}.json").write_text(
            json.dumps({"case": c, "result": out, "auto_pass": ok}, indent=2, ensure_ascii=False), encoding="utf-8")
        rows.append(f"| {c['id']} | {c['short']} | {c['type']} | {c['expected_text']} | {actual} | {'Pass' if ok else 'Fail'} |")
        print(rows[-1])
    (TESTS / "results.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


def run_versions(n, workers=10):
    from concurrent.futures import ThreadPoolExecutor

    cases = [c for c in json.loads((TESTS / "inputs.json").read_text(encoding="utf-8")) if c["type"] == "Normal"]
    p1 = load_prompt(PROMPTS / "final" / "P1_profile_extractor.txt")
    with ThreadPoolExecutor(max_workers=workers) as ex:
        profiles = list(ex.map(
            lambda c: json.dumps(
                parse_json(call_llm(p1["system"], fill(p1["user"], candidate_text=c["text"]), p1["temperature"]), strict=False),
                ensure_ascii=False),
            cases))

    rows = [["version", "runs", "valid_json_pct", "schema_ok_pct", "avg_top_score_stdev"]]
    for v in ("v1", "v2", "v3"):
        p2 = load_prompt(PROMPTS / v / "P2_role_recommender.txt")
        tasks = [pj for pj in profiles for _ in range(n)]

        def one_call(pj):
            raw = call_llm(p2["system"], fill(p2["user"], profile_json=pj), p2["temperature"])
            try:
                data = parse_json(raw, strict=True)
                return (True, roles_schema_ok(data), data["roles"][0]["fit_score"] if roles_schema_ok(data) else None)
            except json.JSONDecodeError:
                return (False, False, None)

        with ThreadPoolExecutor(max_workers=workers) as ex:
            call_results = list(ex.map(one_call, tasks))

        valid = sum(1 for ok, _, _ in call_results if ok)
        schema = sum(1 for _, ok, _ in call_results if ok)
        total = len(call_results)
        sd = []
        for i, pj in enumerate(profiles):
            tops = [call_results[i * n + k][2] for k in range(n) if call_results[i * n + k][2] is not None]
            if len(tops) > 1:
                sd.append(statistics.pstdev(tops))
        rows.append([v, total, round(100 * valid / total, 1), round(100 * schema / total, 1),
                     round(statistics.mean(sd), 2) if sd else "n/a"])
        print(rows[-1])
    with open(TESTS / "version_comparison.csv", "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--versions", type=int, metavar="N", help="compare P2 v1/v2/v3 with N runs per profile")
    a = ap.parse_args()
    run_versions(a.versions) if a.versions else run_all()
