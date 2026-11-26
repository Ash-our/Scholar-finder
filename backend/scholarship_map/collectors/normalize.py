from datetime import datetime
import re

from dateutil import parser
import pycountry

FIELD_WORDS = {
    "computer_science": ["computer science", "computing", "informatics", "data science", "software"],
    "engineering": ["engineering", "engineer"], "business": ["business", "management", "mba", "finance"],
    "medicine": ["medicine", "medical", "health", "dentistry", "nursing", "pharmacy"],
    "natural_sciences": ["biology", "physics", "chemistry", "mathematics", "natural sciences"],
    "social_sciences": ["social sciences", "global studies", "african studies", "politics", "economics"],
    "arts": ["arts", "humanities", "history", "literature", "design"], "law": ["law", "legal"],
    "education": ["education", "teaching"], "agriculture": ["agriculture", "agricultural", "forestry"],
}
ALIASES = {"Palestine": "PS", "Palestinian": "PS", "Occupied Palestinian Territory": "PS",
           "Palestinian Territories": "PS", "United States": "US", "USA": "US", "UK": "GB",
           "United Kingdom": "GB", "South Korea": "KR", "Russia": "RU", "Turkey": "TR"}


def countries_in(text: str) -> list[str]:
    names = dict(ALIASES)
    for country in pycountry.countries:
        for attr in ["name", "official_name", "common_name"]:
            if name := getattr(country, attr, None):
                names[name] = country.alpha_2
    occupied, found = [], set()
    for name, code in sorted(names.items(), key=lambda item: len(item[0]), reverse=True):
        for match in re.finditer(r"(?<!\w)" + re.escape(name) + r"(?!\w)", text, re.I):
            if not any(match.start() < end and match.end() > start for start, end in occupied):
                found.add(code)
                occupied.append(match.span())
    return sorted(found)


def degrees_in(text: str) -> list[str]:
    text = re.sub(r"\bpost[\s-]*doctoral\b", "postdoc", text, flags=re.I)
    pairs = [("bachelor", r"undergraduate|bachelor|associate"), ("master", r"master|\bmba\b|\bmsc\b"),
             ("phd", r"\bph\.?d\b|\bdoctoral\b|\bdoctorate\b"), ("postdoc", r"\bpostdoc\b|post-doc"),
             ("research", r"research fellowship")]
    return [key for key, pattern in pairs if re.search(pattern, text, re.I)]


def fields_in(text: str) -> list[str]:
    if text.strip().lower() in {"unrestricted", "all", "all disciplines", "all subjects"}:
        return ["all"]
    return [field for field, words in FIELD_WORDS.items()
            if any(re.search(r"\b" + re.escape(word) + r"\b", text, re.I) for word in words)]


def funding_in(text: str) -> str:
    text = text.lower()
    if "fully funded" in text or "full funding" in text:
        return "full"
    if "partial" in text:
        return "partial"
    if "tuition" in text:
        return "tuition"
    if "stipend" in text:
        return "stipend"
    return "unknown"


def parse_deadline(text: str) -> tuple[str | None, str]:
    if not text or text.lower().strip() in {"not specified", "not confirmed", "unknown", "not stated"}:
        return None, "unknown"
    if re.search(r"estimat|usually|approximately", text, re.I):
        return None, "estimated"
    if not re.search(r"\b(?:19|20)\d{2}\b", text):
        return None, "recurring" if re.search(r"\d", text) else "unknown"
    date_text = text.split("·")[0].strip()
    try:
        result = parser.parse(date_text, fuzzy=False, default=datetime(2000, 1, 1))
        return result.date().isoformat(), "confirmed"
    except (ValueError, OverflowError):
        return None, "unknown"


def extract_gpa(text: str):
    match = re.search(r"(?:minimum\s+)?c?gpa\s*(?:of\s*)?([0-9.]+)\s*(?:on\s*(?:a\s*)?|/)([0-9.]+)\s*(?:scale)?", text, re.I)
    if match:
        try:
            value, scale = float(match[1]), float(match[2])
            if 0 <= value <= scale:
                return value, scale
        except ValueError:
            pass
    return None, None


def fact_pairs(soup):
    return {dt.get_text(" ", strip=True).casefold(): dd.get_text(" ", strip=True)
            for dt in soup.select("dt") if (dd := dt.find_next_sibling("dd"))}
