"""Made-up data for the Nimbus Robotics "launch in Germany?" question. Nothing to do here.

Two sources, each reachable only through its own tools:
- news articles   -> search_news()                       (news_researcher agent)
- internal docs   -> list_internal_docs(), read_internal_doc()  (doc_analyst agent)

Every record carries metadata (source_id, title, date, page) separate from its
content, so findings can keep their attribution all the way to the report.
"""

import json

NEWS = [
    {"source_id": "N1", "title": "Kestrel Logistics unveils KX-9 picking robot for EU market",
     "outlet": "RoboTrade Weekly", "date": "2026-08-14",
     "text": "Kestrel Logistics will ship its KX-9 autonomous picking robot to German "
             "warehouses from Q1 2027 at a list price of EUR 48,000, undercutting most rivals."},
    {"source_id": "N2", "title": "German warehouse automation spending to grow 18% in 2027",
     "outlet": "Logistik Heute", "date": "2026-07-02",
     "text": "Analysts expect German warehouse automation spending to grow 18% in 2027 "
             "to EUR 2.4 billion, driven by e-commerce and a shortage of pickers."},
    {"source_id": "N3", "title": "New EU Machinery Regulation applies from January 2027",
     "outlet": "EU Compliance Brief", "date": "2026-05-20",
     "text": "Regulation (EU) 2023/1230 replaces the Machinery Directive on 20 January 2027. "
             "Autonomous mobile robots sold after that date need a new conformity assessment."},
    {"source_id": "N4", "title": "Germany reports 63,000 unfilled warehouse jobs",
     "outlet": "Handelsblatt Logistics", "date": "2026-09-01",
     "text": "The German logistics association counts 63,000 unfilled warehouse positions, "
             "up from 41,000 a year earlier."},
    {"source_id": "N5", "title": "Nimbus Robotics CEO: 'Europe is next'",
     "outlet": "TechCrunch-ish", "date": "2026-06-11",
     "text": "Nimbus Robotics CEO Dana Okafor said Germany is the company's top expansion "
             "priority for 2027, but gave no launch date for the Stratus robot."},
]

DOCS = {
    "D1": {"title": "Stratus pilot report: Hamburg (Nordhafen Logistik GmbH)", "date": "2026-08-30",
           "pages": {
               1: "Six-month pilot of 12 Stratus units at Nordhafen Logistik, Hamburg. "
                  "Average 410 picks/hour per unit against a target of 300. Uptime 97.2%.",
               2: "Open issues: no German-language operator UI; local service technicians "
                  "needed within 4 hours (currently flown in from Rotterdam). The customer "
                  "intends to order 40 more units if both are fixed.",
           }},
    "D2": {"title": "FY2026 Q2 sales by region", "date": "2026-07-15",
           "pages": {
               1: "EU revenue USD 3.1M (Netherlands 2.2M, Belgium 0.9M). Germany USD 0: "
                  "no German sales entity yet; pilot units were loaned, not sold.",
           }},
    "D3": {"title": "Compliance memo: Stratus CE marking", "date": "2026-06-03",
           "pages": {
               1: "Stratus is CE-marked under the old Machinery Directive 2006/42/EC. "
                  "Recertification under Regulation 2023/1230 is estimated at 5 months "
                  "and USD 220,000. Work has not started.",
           }},
    "D4": {"title": "Stratus unit economics", "date": "2026-04-22",
           "pages": {
               1: "Stratus list price EUR 52,000 per unit; gross margin 38%. A price cut "
                  "to EUR 47,000 would bring the margin to 31%.",
           }},
}

ALL_SOURCE_IDS = {n["source_id"] for n in NEWS} | set(DOCS)
NEWS_IDS = {n["source_id"] for n in NEWS}
DOC_IDS = set(DOCS)


def search_news(query: str) -> str:
    """Keyword search over the news. Returns the top 3 articles as JSON."""
    words = [w for w in query.lower().split() if len(w) > 2]
    scored = []
    for art in NEWS:
        hay = (art["title"] + " " + art["text"]).lower()
        score = sum(w in hay for w in words)
        if score:
            scored.append((score, art))
    scored.sort(key=lambda x: -x[0])
    return json.dumps([a for _, a in scored[:3]]) if scored else "[]"


def list_internal_docs() -> str:
    return json.dumps([{"doc_id": k, "title": d["title"], "date": d["date"],
                        "pages": len(d["pages"])} for k, d in DOCS.items()])


def read_internal_doc(doc_id: str, page: int = 1) -> str:
    doc = DOCS.get(doc_id)
    if not doc:
        raise KeyError(f"No document {doc_id!r}. Call list_internal_docs first.")
    if page not in doc["pages"]:
        raise KeyError(f"{doc_id} has pages {sorted(doc['pages'])}, not {page}")
    return json.dumps({"source_id": doc_id, "title": doc["title"], "date": doc["date"],
                       "page": page, "text": doc["pages"][page]})
