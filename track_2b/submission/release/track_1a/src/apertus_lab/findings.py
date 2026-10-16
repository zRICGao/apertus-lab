"""Legacy fixture export boundary. Live reviewed export is implemented in review.py."""


def export_findings(records: list[dict]) -> None:
    if not records or len(records) > 5:
        raise ValueError("Expected 1–5 confirmed findings")
    if any(item.get("mode") != "live" or item.get("status") != "confirmed" for item in records):
        raise ValueError("Only independently confirmed live findings may be exported")
    raise NotImplementedError("Use export-live with the persistent human-reviewed registry; arbitrary dictionaries cannot be exported")
