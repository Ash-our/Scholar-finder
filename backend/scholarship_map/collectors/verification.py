"""Conservative, reviewed call-specific rules checked against live official HTML."""
from hashlib import sha256
from datetime import datetime
import json
import re
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
from kafka import KafkaProducer

from ..events import content_hash, make_event
from ..models import Scholarship, utcnow
from ..repository import MongoRepository
from ..settings import ROOT, settings
from .http import PublicClient


def rules():
    path = ROOT / "data" / "verification-rules.json"
    return json.loads(path.read_text("utf8")) if path.exists() else {}


def matches_record(record, rule):
    return all(getattr(record, key) in (value if isinstance(value, list) else [value])
               for key, value in rule["match"].items())


def verified_from_html(record, rule, html, checked_at):
    if not matches_record(record, rule):
        return record
    soup = BeautifulSoup(html, "html.parser")
    for node in soup.select("script,style,nav,header,footer"):
        node.decompose()
    text = " ".join(soup.stripped_strings)
    expired_rule = rule.get("review_until") and checked_at > datetime.fromisoformat(rule["review_until"])
    closed = re.search(r"\bapplications? (?:are |is |have )?(?:now |currently )?(?:closed|ended)\b", text, re.I)
    if expired_rule or closed or not all(re.search(pattern, text, re.I) for pattern in rule["patterns"]):
        return record.model_copy(update={"official_verified_at": None, "open_evidence": None, "reported_status": "unknown",
            "verification_note": "القراءة الرسمية الأحدث لم تؤكد أدلة هذه الدورة؛ يرجى مراجعة البرنامج مباشرة."})
    values = record.model_dump() | rule.get("updates", {})
    values.update(official_url=rule["url"], official_verified_at=checked_at,
                  identity_resolved=True, reported_status="open", open_evidence=rule.get("open_evidence", "accepting_applications"),
                  verification_note="تمت قراءة صفحة الجهة الرسمية مباشرة ومطابقة أدلة البرنامج والدورة والموعد. "
                    + rule.get("note", "راجع شروط الأهلية الكاملة قبل التقديم.")
                    + " بصمة دليل الصفحة: " + sha256(html.encode()).hexdigest())
    return Scholarship(**values)


def verify_one(record, client, on_error=None):
    rule = rules().get(record.id)
    if not rule or not matches_record(record, rule):
        return record
    try:
        verified = verified_from_html(record, rule, client.get(rule["url"]), utcnow())
        if verified.official_verified_at == record.official_verified_at:
            raise ValueError("Official call proof changed; retained prior verification date, manual review needed")
        return verified
    except Exception as error:
        if on_error:
            on_error(rule["url"], error)
        return record


def verify_catalogue():
    config = settings()
    repo = MongoRepository(config)
    known_rules = rules()
    client = PublicClient([urlsplit(rule["url"]).hostname for rule in known_rules.values()], config.request_delay)
    producer = KafkaProducer(bootstrap_servers=config.kafka_bootstrap, acks="all", enable_idempotence=True,
        value_serializer=lambda value: json.dumps(value, ensure_ascii=False).encode(), key_serializer=lambda value: value.encode())
    published, errors = 0, []
    try:
        for record in repo.records({"id": {"$in": list(known_rules)}}):
            verified = verify_one(record, client, lambda url,error: errors.append({"url":url,"error":str(error)[:200]}))
            if verified.official_verified_at == record.official_verified_at:
                continue
            event = make_event(verified, utcnow(), "updated", mode="live")
            producer.send(config.kafka_topic, key=verified.id, value=event.model_dump(mode="json")).get(timeout=30)
            repo.db.collector_state.update_one({"_id": f"{record.source_id}:{record.source_record_id}"},
                {"$set": {"content_hash": content_hash(verified), "last_observed_at": utcnow()}}, upsert=True)
            published += 1
        report = {"verified_and_published": published, "errors": errors, "checked_at": utcnow().isoformat()}
        repo.db.verification_runs.insert_one(report.copy())
        print(json.dumps(report, ensure_ascii=False), flush=True)
        return report
    finally:
        producer.close()
        client.close()
        repo.close()
