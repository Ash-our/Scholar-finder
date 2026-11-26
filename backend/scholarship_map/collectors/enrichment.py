import json
import re
import unicodedata
from datetime import UTC, datetime
from pathlib import Path

import httpx

from ..models import Placement, Scholarship
from ..settings import ROOT

ROR_API = "https://api.ror.org/v2/organizations"
INSTITUTION_WORDS = re.compile(
    r"universit|universidad|universidade|institut|istituto|college|academy|academie|école|school|library|bibliothek|centre|center",
    re.IGNORECASE,
)
UNSPECIFIED_HOST = re.compile(
    r"not (?:individually )?(?:named|specified)|institutions? (?:selected|not specified)|"
    r"eligible (?:administering|swiss)|suitable academic host|universities (?:in|and|funded)|"
    r"state.recognized university|accredited (?:four.year|colleges)|a university in|"
    r"a french host|french higher education|eight SENSS|multiple (?:universities|higher)|"
    r"participating (?:dutch|master)|relevant centres|piedmont universities|u\.s\. institutions|"
    r"a consortium of|several leading european|the TCCM consortium",
    re.IGNORECASE,
)


def _read_json(path, default=None):
    return json.loads(path.read_text("utf8")) if path.exists() else ({} if default is None else default)


def _normalize(value):
    """Compare spelling, punctuation and accents, never similarity or token overlap."""
    value = re.sub(r"^the\s+", "", value.strip(), flags=re.IGNORECASE)
    value = value.translate(str.maketrans({"ł": "l", "Ł": "L", "ø": "o", "Ø": "O"}))
    value = "".join(c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c))
    return re.sub(r"[^\w]", "", value).casefold()


def _split_hosts(text):
    # Parenthetic acronyms/countries are qualifiers, not separate organizations.
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"^.*?(?:coordinated by|partner universities:|including)\s+", "", text, flags=re.IGNORECASE)
    # A comma in "Royal Holloway, University of London" belongs to one name.
    text = re.sub(r"(?<![\w])([^;,]+),\s*(University of [^;,]+)",
                  lambda m: m[0] if INSTITUTION_WORDS.search(m[1]) else m[1] + " " + m[2], text)
    parts = re.split(r";|,|\s+(?:and|or|&)\s+(?=(?:(?:the|a)\s+)?(?:[\w’'-]+\s+){0,4}"
                     r"(?:University|Universit\w*|Institute|College|Library|Academy|School)\b)", text)
    result = []
    for part in parts:
        part = re.sub(r"^(?:and|or|the)\s+", "", part.strip(" .–—"), flags=re.IGNORECASE)
        part = re.split(r"\s+(?:for the first|for a second|is the degree|and thesis|and an eligible|"
                        r"and partner|depending on|for the return)", part, flags=re.IGNORECASE)[0].strip()
        if (part and part[0].isupper() and (INSTITUTION_WORDS.search(part) or re.search(r"\b[A-Z]{2,}\b", part))
                and not UNSPECIFIED_HOST.search(part)):
            result.append(part)
    return result


class LocationEnricher:
    """Resolve explicit hosts only; every decision is available for a dry-run audit.

    ROR points describe an institution's city. They never establish a programme
    campus. Reviewed exceptions must therefore identify the actual study host.
    """

    def __init__(self, root=None, *, allow_network=True, max_requests=300):
        self.root = Path(root) if root is not None else ROOT
        self.cache_path = self.root / ".runtime" / "ror-institutions-v2.json"
        self.cache = _read_json(self.cache_path)
        self.references = _read_json(self.root / "data" / "institution-locations.json")
        self.legacy_hosts = _read_json(self.root / "data" / "host-institutions.json")
        self.geography = _read_json(self.root / "data" / "countries.json", {"countries": {}})
        self.allow_network, self.max_requests = allow_network, max_requests
        self.requests = self.cache_hits = 0
        self.failures = []

    def _query(self, name, ror_id=None):
        if ror_id and not re.fullmatch(r"https://ror\.org/[a-z0-9]{9}", ror_id):
            return None, "invalid_reviewed_ror_id"
        identifier = ror_id.rsplit("/", 1)[-1] if ror_id else None
        key = "id:" + identifier if identifier else _normalize(name)
        entry = self.cache.get(key)
        if entry is not None:
            self.cache_hits += 1
            if entry["number_of_results"] <= len(entry["items"]):
                return entry, None
        if not self.allow_network:
            return entry, "incomplete_search_cache_only" if entry else "cache_miss"
        # Literal phrase searches avoid Elasticsearch syntax in names and keep
        # broad fuzzy candidates out of the acceptance decision below. Resume
        # the ORIGINAL cached query, even when normalized spellings share a key.
        query = entry.get("query", name) if entry else name
        phrase = '"' + re.sub(r'([+\-=!(){}\[\]^"~*?:\\/<>|&])', r"\\\1", query) + '"'
        while True:
            if self.requests >= self.max_requests:
                return entry, "incomplete_search_request_budget_exhausted" if entry else "request_budget_exhausted"
            # Existing cache entries contain only their first API page. New
            # entries retain the last successfully retrieved page explicitly.
            page = entry.get("pages_fetched", 1) + 1 if entry else 1
            if page > 500:
                return entry, "incomplete_search_api_page_limit"
            params = None if identifier else {"query": phrase}
            if params is not None and page > 1:
                params["page"] = page
            self.requests += 1
            try:
                response = httpx.get(ROR_API + "/" + identifier if identifier else ROR_API,
                                     params=params, timeout=25)
                response.raise_for_status()
                payload = response.json()
                if ror_id:
                    if payload.get("id") != ror_id:
                        raise ValueError("ROR identity response does not match the reviewed identifier")
                    payload = {"items": [payload], "number_of_results": 1}
                if payload.get("errors") or not isinstance(payload.get("items"), list):
                    raise ValueError("ROR response does not contain a valid result page")
                items = payload["items"]
                total = payload.get("number_of_results", payload.get("metadata", {}).get("number_of_results",
                                                                                         len(items)))
                if not isinstance(total, int) or total < 0 or any(not org.get("id") for org in items):
                    raise ValueError("ROR result count or organization identity is invalid")
                if entry and total != entry["number_of_results"]:
                    raise ValueError("ROR result count changed while retrieving pages; retry after cache review")
                combined = {org["id"]: org for org in (entry["items"] if entry else [])}
                previous_count = len(combined)
                combined.update({org["id"]: org for org in items})
                if entry and len(combined) == previous_count:
                    raise ValueError("ROR pagination made no progress; result set remains incomplete")
                url = str(response.request.url)
                entry = {"query": query, "query_url": entry["query_url"] if entry else url,
                         "page_urls": [*(entry.get("page_urls", [entry["query_url"]]) if entry else []), url],
                         "fetched_at": datetime.now(UTC).isoformat(), "pages_fetched": page,
                         "number_of_results": total, "items": list(combined.values())}
            except (httpx.HTTPError, ValueError) as error:
                self.failures.append({"name": name, "page": page, "error": str(error)[:200]})
                # Partial pages remain cached for an explicit, bounded retry;
                # neither outages nor incomplete results establish identity.
                return entry, "incomplete_search_request_failed" if entry else "request_failed"
            self.cache[key] = entry
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.cache_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(self.cache, ensure_ascii=False), encoding="utf8")
            temporary.replace(self.cache_path)
            if total <= len(entry["items"]):
                return entry, None

    def _hosts(self, record):
        reviewed = self.references.get("records", {}).get(record.id, {})
        if (reviewed.get("match") and
                all(getattr(record, key) == value for key, value in reviewed["match"].items())):
            if reviewed.get("blocked_reason"):
                return [], reviewed["blocked_reason"]
            if reviewed.get("evidence_url") and "hosts" in reviewed:
                return [{"name": item} if isinstance(item, str) else item for item in reviewed["hosts"]], None
        text = record.provider
        if "university of the people" in (text + " " + record.title).casefold():
            return [], "online_programme_no_physical_study_location"
        if re.search(r"\bcampus\b", text, re.IGNORECASE):
            return [], "programme_campus_requires_review"
        if UNSPECIFIED_HOST.search(text):
            # Some lists contain named hosts followed by a generic thesis host.
            named = [] if UNSPECIFIED_HOST.search(text).start() == 0 else _split_hosts(text)
            if not named:
                return [], "host_institutions_not_specified"
        aliases = self.references.get("aliases", {})
        names = _split_hosts(text)
        if text in aliases:
            names = [text]
        elif not text.strip():
            title = re.split(r"\s[–—]\s|\s(?:Scholarships?|Fellowships?|Full Funding|Excellence)\b",
                             record.title, flags=re.IGNORECASE)[0]
            names = _split_hosts(title)
        legacy = self.legacy_hosts.get(record.id)
        if isinstance(legacy, str):
            names = [legacy]
        hosts = []
        for name in names:
            alias = aliases.get(name)
            if alias and alias.get("evidence_url"):
                hosts.append({"name": alias["name"], "mention": name, "evidence_url": alias["evidence_url"]})
            else:
                hosts.append({"name": name})
        return list({host["name"]: host for host in hosts}.values()), None

    def enrich(self, record, *, use_ror=True):
        places, countries, decisions = list(record.placements), list(record.countries), []
        if use_ror:
            hosts, blocked = self._hosts(record)
            if blocked:
                decisions.append({"status": "unresolved", "reason": blocked, "mention": record.provider})
            if not hosts and not blocked:
                decisions.append({"status": "unresolved", "reason": "no_explicit_host_extracted",
                                  "mention": record.provider or record.title})
            for host in hosts:
                name = host["name"]
                decision = {"mention": host.get("mention", name), "query": name,
                            "evidence_url": host.get("evidence_url", record.official_url or record.source_url)}
                if host.get("city"):
                    decision["required_city"] = host["city"]
                if host.get("blocked_reason"):
                    decisions.append(decision | {"status": "unresolved", "reason": host["blocked_reason"]})
                    continue
                existing = [p for p in places if p.precision != "country" and _normalize(p.name) == _normalize(name)]
                if existing:
                    decisions.append(decision | {"status": "existing", "ror_ids": [p.source_url for p in existing]})
                    continue
                entry, error = self._query(name, host.get("ror_id"))
                if error:
                    decisions.append(decision | {"status": "unresolved", "reason": error})
                    continue
                exact = {org["id"]: org for org in entry["items"]
                         if org.get("status", "active") == "active" and
                         (not host.get("ror_id") or org["id"] == host["ror_id"]) and
                         _normalize(name) in {_normalize(n["value"]) for n in org.get("names", [])}}
                matches = {key: org for key, org in exact.items() if not record.countries or any(
                    loc.get("geonames_details", {}).get("country_code") in record.countries
                    for loc in org.get("locations", []))}
                if entry["number_of_results"] > len(entry["items"]):
                    reason = "incomplete_search_requires_review"
                elif not exact:
                    reason = "no_exact_ror_name_or_reviewed_alias"
                elif not matches:
                    reason = "destination_country_conflict"
                elif len(matches) != 1:
                    reason = "ambiguous_ror_identity"
                else:
                    reason = None
                if reason:
                    decisions.append(decision | {"status": "unresolved", "reason": reason,
                        "exact_ror_ids": list(exact), "candidate_names": [n["value"] for o in entry["items"][:3]
                            for n in o.get("names", []) if "ror_display" in n.get("types", [])]})
                    continue
                org = next(iter(matches.values()))
                added = []
                for loc in org.get("locations", []):
                    geo = loc.get("geonames_details", {})
                    country = geo.get("country_code")
                    if (not country or (record.countries and country not in record.countries)
                            or geo.get("lat") is None or geo.get("lng") is None):
                        continue
                    # Institution-level coordinates cannot disambiguate a named
                    # campus elsewhere. Explicit reviewed city constraints can.
                    if host.get("city") and _normalize(geo.get("name", "")) != _normalize(host["city"]):
                        continue
                    identifier = org["id"].rsplit("/", 1)[-1]
                    if not any(p.source_url == org["id"] and p.lat == geo["lat"] and p.lon == geo["lng"]
                               for p in places):
                        places.append(Placement(id=identifier, name=name, country=country, lat=geo["lat"],
                                                lon=geo["lng"], precision="city", source_url=org["id"]))
                    added.append(country)
                    if not record.countries and country not in countries:
                        countries.append(country)
                decisions.append(decision | ({"status": "resolved", "ror_id": org["id"], "countries": added}
                    if added else {"status": "unresolved", "reason": "no_compatible_city_coordinates"}))
        for country in countries:
            if not any(place.country == country for place in places) and country in self.geography["countries"]:
                geo = self.geography["countries"][country]
                places.append(Placement(id=f"country-{country}", name=geo["name"], country=country,
                                        lat=geo["lat"], lon=geo["lon"], precision="country",
                                        source_url=self.geography["source_url"]))
        return record.model_copy(update={"placements": places, "countries": sorted(countries)}), decisions


def attach_locations(record: Scholarship, use_ror=False) -> Scholarship:
    return LocationEnricher().enrich(record, use_ror=use_ror)[0]


def apply_curation(record: Scholarship) -> Scholarship:
    path = ROOT / "data" / "curation.json"
    if not path.exists():
        return record
    values = json.loads(path.read_text("utf8")).get(record.id)
    if not values:
        return record
    expected = values.pop("_match", {})
    # Reviewed evidence belongs to one specific source call. A reused URL or
    # changed source deadline must not inherit a previous cycle's verification.
    if not expected or any(getattr(record, key) not in (value if isinstance(value, list) else [value])
                           for key, value in expected.items()):
        return record
    return Scholarship(**(record.model_dump() | values))
