"""Bounded discovery of individual public award articles, excluding listicles."""
from hashlib import sha256
import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from ..models import Scholarship
from .normalize import countries_in, degrees_in, fields_in, funding_in, parse_deadline

BASE="https://www.scholars4dev.com"
LABELS={"brief description","host institution(s)","level/field(s) of study","number of awards","target group",
        "scholarship value/inclusions/duration","scholarship value/duration","scholarship value/inclusions",
        "eligibility","application instructions","website"}


def sections_in(article):
    result={}; label=""
    for node in article.find_all(recursive=False):
        text=node.get_text(" ",strip=True)
        candidate=text.rstrip(":").strip().casefold()
        if candidate in LABELS:
            label=candidate; result.setdefault(label,[])
        elif label and text:
            result[label].append(text)
    return {key:" ".join(values) for key,values in result.items()}


def parse_detail(html,url,fetched_at):
    soup=BeautifulSoup(html,"html.parser")
    title=soup.select_one(".band-in h1") or soup.select_one("h1")
    article=soup.select_one("main article.entry-scholarship")
    if not title or not article:
        raise ValueError("No individual scholarship article")
    facts={item.dt.get_text(" ",strip=True).casefold():item.dd.get_text(" ",strip=True)
           for item in soup.select("dl.facts>div") if item.dt and item.dd}
    sections=sections_in(article)
    raw_deadline=facts.get("deadline") or facts.get("annual deadline","")
    dates=re.findall(r"\b\d{1,2}\s+[A-Za-z]{3,9}\s+20\d{2}\b",raw_deadline)
    deadline,confidence=parse_deadline(dates[0] if len(dates)==1 else raw_deadline)
    instructions=sections.get("application instructions","")
    degrees=degrees_in(facts.get("degree","").replace("’","'"))
    if (re.search(r"scholarship deadline.{0,50}(?:not |not yet |unannounced)",instructions,re.I)
            or len(degrees)>1 or len(dates)>1):
        deadline,confidence=None,"unknown"
    links=[]
    for paragraph in article.select("p"):
        if paragraph.get_text(" ",strip=True).casefold().startswith("official scholarship website"):
            links.extend(a["href"] for a in paragraph.select("a[href]")
                         if urlsplit(a["href"]).scheme=="https" and "scholars4dev.com" not in (urlsplit(a["href"]).hostname or ""))
    links=list(dict.fromkeys(links))
    funding_text=" ".join(value for key,value in sections.items() if key.startswith("scholarship value"))
    funding=funding_in(funding_text)
    if re.search(r"full scholarships?.{0,30}cover.{0,50}tuition.{0,50}living",funding_text,re.I):
        funding="full"
    elif re.search(r"tuition.{0,25}(?:not included|not covered)|(?:does not|not).{0,15}cover.{0,20}tuition",funding_text,re.I):
        funding="partial"
    fields_text=sections.get("level/field(s) of study","")
    fields=["all"] if re.search(r"any subject|any field|all fields|all disciplines",fields_text,re.I) else fields_in(fields_text)
    post=re.search(r"\bpost-(\d+)\b"," ".join(article.get("class",[])))
    key=post[1] if post else sha256(url.encode()).hexdigest()[:24]
    eligibility=sections.get("eligibility","")
    return Scholarship(id="scholars4dev-"+key,source_id="scholars4dev",source_record_id=key,
        title=title.get_text(" ",strip=True),provider=facts.get("offered by",""),source_url=url,
        official_url=links[0] if len(links)==1 else None,cycle=facts.get("course starts") or None,
        countries=countries_in(facts.get("study in","")),degrees=degrees,fields=fields,funding=funding,
        description=(sections.get("brief description","")+"\n"+funding_text)[:1000],
        eligibility_text=(sections.get("target group","")+"\n"+eligibility+"\n"+instructions)[:2800],
        extra_requirements=["راجع مسار الدراسة وشروط الجنسية والإقامة ومواعيد القبول والمنحة في المصدر الرسمي"],
        deadline=deadline,deadline_text=raw_deadline+("؛ تفاصيل الموعد في تعليمات التقديم" if not deadline else ""),
        deadline_confidence=confidence,fetched_at=fetched_at)


def collect(client,limit,fetched_at,on_error=None):
    records=[];seen=set();url=BASE+"/"
    for _ in range(2):
        if not url or len(records)>=limit:break
        soup=BeautifulSoup(client.get(url),"html.parser")
        for card in soup.select("main article.row-scholarship"):
            anchor=card.select_one("h2.row-title a[href]")
            if not anchor:continue
            detail=urljoin(BASE,anchor["href"])
            if detail in seen or len(records)>=limit:continue
            seen.add(detail)
            try:records.append(parse_detail(client.get(detail),detail,fetched_at))
            except Exception as error:
                if on_error:on_error(detail,error)
        next_link=soup.select_one("nav.pages a.next[href]")
        url=urljoin(BASE,next_link["href"]) if next_link else None
    return records
