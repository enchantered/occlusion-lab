"""Evidence-first scoring for venture opportunity hypotheses."""
from __future__ import annotations

from datetime import date
from urllib.parse import urlsplit

_SCORE_WEIGHTS = {
    "pain": 25,
    "demand": 20,
    "payment_likelihood": 20,
    "feasibility": 15,
    "differentiation": 10,
    "distribution": 10,
}
_EVIDENCE_KINDS = {"demand", "engineering", "competition"}


def _nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate(data: dict) -> list[dict]:
    if not isinstance(data, dict):
        raise ValueError("manifest must be a JSON object")
    opportunities = data.get("opportunities")
    if not isinstance(opportunities, list) or not opportunities:
        raise ValueError("opportunities must be a nonempty list")
    if len(opportunities) > 100:
        raise ValueError("opportunities may contain at most 100 records")
    seen: set[str] = set()
    for i, record in enumerate(opportunities):
        where = f"opportunities[{i}]"
        if not isinstance(record, dict):
            raise ValueError(f"{where} must be an object")
        for field in ("id", "title", "buyer", "problem"):
            if not _nonempty_string(record.get(field)):
                raise ValueError(f"{where}.{field} must be a nonempty string")
        if record["id"] in seen:
            raise ValueError(f"duplicate opportunity id: {record['id']}")
        seen.add(record["id"])
        evidence = record.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise ValueError(f"{where}.evidence must be a nonempty list")
        for j, item in enumerate(evidence):
            ew = f"{where}.evidence[{j}]"
            if not isinstance(item, dict):
                raise ValueError(f"{ew} must be an object")
            url = item.get("url")
            if not _nonempty_string(url):
                raise ValueError(f"{ew}.url must be an HTTPS URL")
            try:
                parts = urlsplit(url)
                valid_url = parts.scheme == "https" and bool(parts.hostname)
            except ValueError:
                valid_url = False
            if not valid_url:
                raise ValueError(f"{ew}.url must be an HTTPS URL")
            published = item.get("published_on")
            if not _nonempty_string(published):
                raise ValueError(f"{ew}.published_on must be an ISO date")
            try:
                parsed = date.fromisoformat(published)
            except ValueError:
                parsed = None
            if parsed is None or parsed.isoformat() != published:
                raise ValueError(f"{ew}.published_on must be an ISO date (YYYY-MM-DD)")
            if not _nonempty_string(item.get("finding")):
                raise ValueError(f"{ew}.finding must be a nonempty string")
            if item.get("kind") not in _EVIDENCE_KINDS:
                raise ValueError(f"{ew}.kind must be one of {', '.join(sorted(_EVIDENCE_KINDS))}")
        scores = record.get("scores")
        if not isinstance(scores, dict) or set(scores) != set(_SCORE_WEIGHTS):
            raise ValueError(f"{where}.scores must contain exactly: {', '.join(_SCORE_WEIGHTS)}")
        for field in _SCORE_WEIGHTS:
            value = scores[field]
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 5:
                raise ValueError(f"{where}.scores.{field} must be an integer from 0 to 5")
    return opportunities


def rank_opportunities(data: dict) -> list[dict]:
    """Validate, score and sort records; scores are hypotheses, not investibility."""
    opportunities = _validate(data)
    results = []
    for record in opportunities:
        kinds = {item["kind"] for item in record["evidence"]}
        missing = [kind for kind in ("demand", "engineering") if kind not in kinds]
        eligible = not missing
        reasons = [] if eligible else [f"Missing required {kind} evidence" for kind in missing]
        weighted = sum(record["scores"][field] * weight for field, weight in _SCORE_WEIGHTS.items())
        score = weighted / 5
        results.append({**record, "eligible": eligible, "reasons": reasons, "score": score})
    results.sort(key=lambda item: (not item["eligible"], -item["score"], item["id"]))
    return results
