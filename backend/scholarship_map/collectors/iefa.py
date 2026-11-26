import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..models import Scholarship
from .normalize import countries_in, degrees_in, fields_in, parse_deadline

BASE = "https://www.iefa.org"


def parse_detail(html, url, fetched_at):
    soup = BeautifulSoup(html, "html.parser")
    title = soup.select_one("h1")
    if not title:
        raise ValueError("Award page has no title")
    facts = {tr.th.get_text(" ", strip=True).casefold(): tr.td.get_text(" ", strip=True)
             for tr in soup.select("tr") if tr.th and tr.td}
    deadline_text = ""
    for box in soup.select(".box-content"):
        heading = box.find("h4")
        if heading and "deadline" in heading.get_text().casefold():
            deadline_text = box.p.get_text(" ", strip=True) if box.p else ""
            break
    deadline, confidence = parse_deadline(deadline_text)
    descriptions = soup.select("section.section-content .description")
    description = "\n".join(node.get_text(" ", strip=True) for node in descriptions)
    sponsor = soup.select_one(".award-description p")
    fields_node = soup.select_one("#award-fieldofstudy")
    nationality = facts.get("nationality required", "")
    award_id = re.search(r"/scholarships/(\d+)", url)[1]
    # Public award contacts may require login. Do not invent official URLs from
    # unrelated footer links or attempt to bypass contact access.
    official = soup.select_one(".award-menu-items a[href^='https://']")
    return Scholarship(
        id=f"iefa-{award_id}", source_id="iefa", source_record_id=award_id,
        title=title.get_text("", strip=True),
        provider=sponsor.get_text(" ", strip=True).removeprefix("Sponsor:").strip() if sponsor else "",
        source_url=url, official_url=official["href"] if official else None,
        countries=countries_in(facts.get("host countries", "")),
        nationalities=["*"] if nationality.lower() == "unrestricted" else countries_in(nationality),
        # A prerequisite degree mentioned in prose is not necessarily the
        # degree being funded. Use the explicit award title, otherwise unknown.
        degrees=degrees_in(title.get_text(" ", strip=True)),
        fields=fields_in(fields_node.get_text(" ", strip=True)) if fields_node else [],
        description=description[:1000], eligibility_text=description[:3000],
        extra_requirements=["تحقق من متطلبات الإقامة والقبول والشروط المذكورة في المصدر"] if description else [],
        deadline=deadline, deadline_text=deadline_text, deadline_confidence=confidence,
        fetched_at=fetched_at,
    )


def collect(client, limit, fetched_at, on_error=None):
    records, visited_pages, visited_awards = [], set(), set()
    page_url = BASE + "/scholarships"
    while page_url and page_url not in visited_pages and len(records) < limit:
        visited_pages.add(page_url)
        soup = BeautifulSoup(client.get(page_url), "html.parser")
        links = list(dict.fromkeys(urljoin(BASE, a["href"]) for a in soup.select("a[href]")
                                 if re.match(r"/scholarships/\d+/", a["href"])))
        for url in links:
            if url in visited_awards or len(records) >= limit:
                continue
            visited_awards.add(url)
            try:
                records.append(parse_detail(client.get(url), url, fetched_at))
            except Exception as exc:
                if on_error:
                    on_error(url, exc)
        next_link = soup.select_one("li.pager-next:not(.disabled) a[href], li.next:not(.disabled) a[href]")
        page_url = urljoin(BASE, next_link["href"]) if next_link else None
    return records
