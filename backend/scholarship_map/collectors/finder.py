import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..models import Scholarship
from .normalize import countries_in, degrees_in, extract_gpa, fact_pairs, fields_in, funding_in, parse_deadline

BASE = "https://scholarship-finder.fly.dev"


def parse_index(html, fetched_at):
    soup = BeautifulSoup(html, "html.parser")
    records = []
    for item in soup.select("article.item"):
        link = item.select_one("h2 a[href]")
        if not link or not (match := re.fullmatch(r"/s/(\d+)", link["href"])):
            continue
        facts = fact_pairs(item)
        provider_node = item.select_one(".provider")
        provider_text = provider_node.get_text(" ", strip=True) if provider_node else ""
        provider, _, location = provider_text.rpartition(" · ")
        official = item.select_one("a.official[href]")
        deadline_text = facts.get("deadline", "")
        deadline, confidence = parse_deadline(deadline_text)
        checked, _ = parse_deadline(facts.get("last checked", ""))
        nationality = facts.get("who may apply", "")
        records.append(Scholarship(
            id=f"finder-{match[1]}", source_id="finder", source_record_id=match[1],
            title=link.get_text(" ", strip=True), provider=provider or provider_text,
            source_url=urljoin(BASE, link["href"]), official_url=official["href"] if official else None,
            countries=countries_in(location), degrees=degrees_in(facts.get("level", "")),
            funding=funding_in(facts.get("funding", "")), cycle=facts.get("application cycle") or None,
            # 'Who may apply' can describe residence, origin or refugee status;
            # it is not an explicit citizenship column. Keep the text rather
            # than turning every mentioned country into an allowed nationality.
            nationalities=[], eligibility_text=f"Who may apply: {nationality}" if nationality else "",
            deadline=deadline, deadline_text=deadline_text,
            deadline_confidence=confidence, fetched_at=fetched_at,
            source_checked_at=(checked + "T00:00:00Z") if checked else None,
        ))
    return records


def enrich_detail(record, html):
    soup = BeautifulSoup(html, "html.parser")
    main = soup.select_one("article.detail-card") or soup
    facts = fact_pairs(main)
    eligibility = main.select_one("section.action-panel")
    text = eligibility.get_text(" ", strip=True) if eligibility else ""
    minimum, scale = extract_gpa(text)
    values = record.model_dump()
    values.update(fields=fields_in(facts.get("fields of study", "")),
                  description=facts.get("funding details", "")[:1500],
                  eligibility_text=(record.eligibility_text + "\n" + text).strip()[:3000], minimum_gpa=minimum, gpa_scale=scale)
    if facts.get("host institution"):
        values["provider"] = facts["host institution"]
    if facts.get("host country"):
        values["countries"] = countries_in(facts["host country"])
    if facts.get("level of study"):
        values["degrees"] = degrees_in(facts["level of study"])
    if text:
        values["extra_requirements"] = ["راجع متطلبات اللغة والمؤهل والشروط الأخرى في صفحة المنحة"]
    return Scholarship(**values)


def collect(client, limit, fetched_at, on_error=None):
    results, url, visited = [], BASE + "/lite", set()
    while url and len(results) < limit and url not in visited:
        visited.add(url)
        html = client.get(url)
        soup = BeautifulSoup(html, "html.parser")
        page_records = parse_index(html, fetched_at)
        # Use the provider's Arabic titles where they are available.
        arabic = {}
        try:
            arabic_url = url.replace(BASE + "/lite", BASE + "/ar/lite")
            ar_soup = BeautifulSoup(client.get(arabic_url), "html.parser")
            for a in ar_soup.select("article.item h2 a[href]"):
                match = re.search(r"/s/(\d+)", a["href"])
                if match:
                    arabic[match[1]] = a.get_text(" ", strip=True)
        except Exception as exc:
            if on_error:
                on_error("Arabic titles", exc)
        for record in page_records:
            if len(results) >= limit:
                break
            try:
                record = enrich_detail(record, client.get(record.source_url))
            except Exception as exc:
                if on_error:
                    on_error(record.source_url, exc)
            if record.source_record_id in arabic:
                record.title_ar = arabic[record.source_record_id]
            results.append(record)
        next_link = next((a for a in soup.select("a[href]") if a.get_text(strip=True) == "Next"), None)
        url = urljoin(BASE, next_link["href"]) if next_link else None
    return results
