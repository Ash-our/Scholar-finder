"""Public ScholarPal collection/detail pages; no account or private API."""
import json
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from ..models import Scholarship
from .normalize import countries_in, degrees_in, funding_in, parse_deadline

BASE = "https://scholarpal.io"
INDEXES = ["/scholarships-for-palestinians", "/scholarships/fully-funded", "/scholarships/deadlines/next-30-days"]


def structured(soup):
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            value = json.loads(script.get_text())
        except (ValueError, TypeError):
            continue
        yield from value if isinstance(value, list) else [value]


def parse_index(html):
    urls = []
    for value in structured(BeautifulSoup(html, "html.parser")):
        if value.get("@type") == "CollectionPage":
            for entry in value.get("itemListElement", []):
                url = entry.get("url", "")
                if urlsplit(url).hostname == "scholarpal.io" and urlsplit(url).path.startswith("/scholarships/"):
                    urls.append(url)
    return list(dict.fromkeys(urls))


def parse_detail(html, url, fetched_at):
    soup = BeautifulSoup(html, "html.parser")
    programme = next((value for value in structured(soup) if value.get("@type") == "EducationalOccupationalProgram"), None)
    if not programme:
        raise ValueError("No public scholarship structured data")

    def fact(label):
        node = soup.find("p", string=lambda text: text and text.strip() == label)
        value = node.find_next_sibling("p") if node else None
        return value.get_text(" ", strip=True) if value else ""

    deadline_node = soup.select_one('[data-testid="detail-deadline"]')
    deadline_text = deadline_node.get_text(" ", strip=True) if deadline_node else ""
    deadline, confidence = parse_deadline(deadline_text)
    if deadline_node and deadline_node.get("data-deadline-state") in {"unconfirmed", "estimated"}:
        deadline, confidence = None, "estimated" if deadline_node["data-deadline-state"] == "estimated" else "unknown"
    official = next((a for a in soup.select("main a[href]")
                     if a.get_text(" ", strip=True).casefold() in {"apply on official website", "visit official website", "official scholarship page", "apply on official site", "apply now"}
                     and urlsplit(urljoin(BASE, a["href"])).scheme == "https"
                     and urlsplit(urljoin(BASE, a["href"])).hostname not in {"scholarpal.io", "www.google.com"}), None)
    provider = soup.select_one('[data-testid="detail-institution"]')
    slug = urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1]
    # Stable short source identities; retain the full source URL and title.
    from hashlib import sha256
    key = sha256(slug.encode()).hexdigest()[:24]
    return Scholarship(id=f"scholarpal-{key}", source_id="scholarpal", source_record_id=slug[:150],
        title=programme.get("name") or soup.h1.get_text(" ", strip=True),
        provider=provider.get_text(" ", strip=True) if provider else "",
        source_url=url, official_url=urljoin(BASE, official["href"]) if official else None,
        countries=countries_in(fact("Country")), degrees=degrees_in(programme.get("occupationalCategory", "")),
        funding=funding_in(programme.get("offers", {}).get("description", "")),
        description=programme.get("description", "")[:900],
        eligibility_text=programme.get("description", "")[:1500],
        extra_requirements=["راجع شروط الجنسية والإقامة واللغة والدورة في المصدر الرسمي"],
        deadline=deadline, deadline_text=deadline_text, deadline_confidence=confidence, fetched_at=fetched_at)


def collect(client, limit, fetched_at, on_error=None):
    urls, records = [], []
    for path in INDEXES:
        try:
            urls.extend(parse_index(client.get(BASE + path)))
        except Exception as error:
            if on_error:
                on_error(BASE + path, error)
    for url in list(dict.fromkeys(urls))[:limit]:
        try:
            records.append(parse_detail(client.get(url), url, fetched_at))
        except Exception as error:
            if on_error:
                on_error(url, error)
    return records
