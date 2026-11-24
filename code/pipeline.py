"""3-step prompt pipeline: P1 profile extractor -> P2 role recommender -> P3 search plan."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "prompts"


def load_prompt(path: Path) -> dict:
    """Parse a prompt file with [SETTINGS], [SYSTEM], [USER] sections."""
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"^\[(SETTINGS|SYSTEM|USER)\]\s*$", text, flags=re.M)
    sections = {parts[i]: parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}
    temp = None
    for line in sections.get("SETTINGS", "").splitlines():
        k, _, v = line.partition("=")
        if k.strip() == "temperature" and v.strip().lower() != "default":
            temp = float(v)
    return {"system": sections.get("SYSTEM", ""), "user": sections.get("USER", ""), "temperature": temp}


def fill(template: str, **variables) -> str:
    # str.replace (not str.format) so JSON braces in prompts are safe
    for k, v in variables.items():
        template = template.replace("{" + k + "}", v)
    return template


def parse_json(raw: str, strict: bool = True):
    """strict=True is used for measurement: the model must return bare JSON."""
    raw = raw.strip()
    if not strict:
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
    return json.loads(raw)


def run_prompt(call_llm, prompt_file: Path, **variables) -> str:
    p = load_prompt(prompt_file)
    return call_llm(p["system"], fill(p["user"], **variables), p["temperature"])


def run_pipeline(call_llm, candidate_text: str, p2_file: Path = None, strict: bool = True) -> dict:
    """Returns a dict with raw/parsed outputs of each step. Stops after P1 if info is insufficient."""
    final = PROMPTS / "final"
    p2_file = p2_file or final / "P2_role_recommender.txt"
    out = {"input": candidate_text, "stopped_at": None, "errors": []}

    raw1 = run_prompt(call_llm, final / "P1_profile_extractor.txt", candidate_text=candidate_text)
    out["p1_raw"] = raw1
    try:
        profile = parse_json(raw1, strict)
    except json.JSONDecodeError as e:
        out["stopped_at"] = "P1"
        out["errors"].append(f"P1 invalid JSON: {e}")
        return out
    out["profile"] = profile
    if profile.get("status") != "ok":
        out["stopped_at"] = "P1"
        return out

    profile_json = json.dumps(profile, ensure_ascii=False)
    raw2 = run_prompt(call_llm, p2_file, profile_json=profile_json)
    out["p2_raw"] = raw2
    try:
        roles = parse_json(raw2, strict)
    except json.JSONDecodeError as e:
        out["stopped_at"] = "P2"
        out["errors"].append(f"P2 invalid JSON: {e}")
        return out
    out["roles"] = roles

    raw3 = run_prompt(
        call_llm, final / "P3_search_plan.txt",
        profile_json=profile_json, roles_json=json.dumps(roles, ensure_ascii=False),
    )
    out["plan"] = raw3
    return out


def roles_schema_ok(roles) -> bool:
    try:
        items = roles["roles"]
        if len(items) != 5:
            return False
        for r in items:
            if not (isinstance(r["title"], str) and isinstance(r["fit_score"], int)
                    and 0 <= r["fit_score"] <= 100 and isinstance(r["why"], str)
                    and len(r["search_keywords"]) == 3 and len(r["skill_gaps"]) <= 3):
                return False
        return True
    except (KeyError, TypeError):
        return False
