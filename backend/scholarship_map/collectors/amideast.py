"""Official West Bank programme pages; never treat an old closed call as open."""
from hashlib import sha256
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..models import Scholarship
from .normalize import countries_in, degrees_in, parse_deadline

BASE="https://www.amideast.org"
CATEGORIES=["/west-bank/find-a-scholarship/graduate-study","/west-bank/find-a-scholarship/undergraduate-study"]
SGFP=BASE+"/west-bank/find-a-scholarship/graduate-study/sousou-graduate-fellows-program-sgfp"


def parse_detail(html,url,fetched_at):
    soup=BeautifulSoup(html,"html.parser")
    title=soup.select_one("main#content h1.page-title") or soup.select_one("h1")
    body=soup.select_one("main#content .field--name-body")
    if not title or not body:raise ValueError("No official programme content")
    name=title.get_text(" ",strip=True);text=body.get_text(" ",strip=True)
    if not re.search(r"scholarship|fellow|fulbright|hope fund|SGFP",name,re.I):
        raise ValueError("Reference page is not an individual funding programme")
    opens=re.search(r"Opens:\s*([A-Za-z]+\s+\d{1,2},?\s+20\d{2})",text,re.I)
    closes=re.search(r"Closes:\s*([A-Za-z]+\s+\d{1,2},?\s+20\d{2})",text,re.I)
    opening=parse_deadline(opens[1])[0] if opens else None
    deadline,confidence=parse_deadline(closes[1]) if closes else (None,"unknown")
    closed=bool(re.search(r"(?:applications?|application period|competition).{0,90}(?:are now closed|is now closed|has closed|are closed|is closed)",text,re.I))
    closed_on=re.search(r"\bapplications?\s+closed\s+on\s+([A-Za-z]+\s+\d{1,2},?\s+20\d{2})",text,re.I)
    if closed_on:
        closed=True
        deadline,confidence=parse_deadline(closed_on[1])
    funding="partial" if re.search(r"tuition gap|supplemental|supplementary",text,re.I) else "unknown"
    key=sha256(url.encode()).hexdigest()[:20]
    sgfp="SGFP" in name and bool(opening and deadline) and "Fall 2027" in text
    # Reviewed programme destinations, never the applicants' nationality or residence.
    destinations=["GB","US"] if "SGFP" in name else ["IE"] if "ireland" in name.casefold() else ["US"] if re.search(r"fulbright|hope fund",name,re.I) else []
    return Scholarship(id="amideast-"+key,source_id="amideast",source_record_id=key,title=name,
        title_ar="برنامج سوسو لزملاء الدراسات العليا" if "SGFP" in name else None,
        provider="Amideast",source_url=url,official_url=url,countries=destinations,
        degrees=degrees_in(text[:900].replace("’","'")),fields=[],funding=funding,
        description=text[:800],eligibility_text=text[:2800],
        nationalities=[],extra_requirements=["الأهلية قد تعتمد على الهوية الفلسطينية أو الأصل الفلسطيني، إضافة إلى القبول والحاجة المالية؛ راجع الشروط كاملة"],
        cycle="Fall 2027" if "Fall 2027" in text else None,opens_at=opening,deadline=deadline,
        deadline_text=("Opens: "+opens[1]+"; closes: "+closes[1]) if opens and closes else "راجع إعلان الدورة وحالة التقديم في الصفحة الرسمية",
        deadline_confidence=confidence,reported_status="closed" if closed else "open" if sgfp else "unknown",
        open_evidence="date_window" if sgfp else None,official_verified_at=fetched_at if sgfp else None,
        identity_resolved=True,verification_note="قراءة مباشرة لإعلان الجهة الرسمية؛ دعم SGFP يسد فجوة الرسوم ولا يعد تمويلًا كاملًا." if sgfp else "",
        fetched_at=fetched_at)


def collect(client,limit,fetched_at,on_error=None):
    urls=[SGFP];records=[]
    for path in CATEGORIES:
        try:
            soup=BeautifulSoup(client.get(BASE+path),"html.parser")
            urls.extend(urljoin(BASE,a["href"]) for a in soup.select("main#content h2.sublanding-header2 a[href]"))
        except Exception as error:
            if on_error:on_error(BASE+path,error)
    for url in list(dict.fromkeys(urls))[:limit]:
        try:records.append(parse_detail(client.get(url),url,fetched_at))
        except Exception as error:
            if on_error:on_error(url,error)
    return records
