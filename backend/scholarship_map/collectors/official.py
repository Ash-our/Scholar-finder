"""Reviewed discovery seeds; every record still requires a successful live read."""
import json

from ..models import Scholarship
from ..settings import ROOT
from .verification import rules, verified_from_html


def programmes():
    return json.loads((ROOT / "data" / "official-programmes.json").read_text("utf8"))


def collect(client, limit, fetched_at, on_error=None):
    records = []
    known = rules()
    for values in programmes()[:limit]:
        try:
            record = Scholarship(**(values | {"fetched_at": fetched_at}))
            html = client.get(record.source_url)
            verified = verified_from_html(record, known[record.id], html, fetched_at)
            if not verified.official_verified_at:
                if on_error:
                    on_error(record.source_url, ValueError("Current official call no longer matches the reviewed evidence"))
            records.append(verified)
        except Exception as error:
            if on_error:
                on_error(values["source_url"], error)
    return records
