#!/usr/bin/env python3
"""
fetch_pubmed_meta.py -- fetch abstracts, years and entry dates for the MEDAL
Cochrane DOIs from PubMed (NCBI E-utilities).

The public MEDAL file has empty `abstract` and `publication_year` columns, so
this step is needed before the search-date check, year stratification and the
oracle condition.

Usage (needs internet access to eutils.ncbi.nlm.nih.gov):
    pip install requests
    python fetch_pubmed_meta.py QA-systematic-review.jsonl --out pubmed_meta.jsonl \
        --email you@example.com [--api-key YOUR_NCBI_KEY]

It is resumable: rerun the same command and it skips DOIs already saved.
Only DOIs that contain a Cochrane CD number are fetched.
Without an API key NCBI allows about 3 requests/second; this script stays below it.

Output, one JSON object per DOI that was found in PubMed:
    doi, pmid, title, year, pubdate, entry_date, abstract, n_sections
`abstract` keeps the section labels ("SEARCH METHODS: ...") so that the
search-date extractor can use them.
"""
import argparse, json, os, re, sys, time
import xml.etree.ElementTree as ET

try:
    import requests
except ImportError:
    sys.exit("requests is required: pip install requests")

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

def text_of(el):
    return "".join(el.itertext()).strip() if el is not None else ""

def ymd(node):
    if node is None:
        return None
    y = text_of(node.find("Year")); m = text_of(node.find("Month")) or "01"; d = text_of(node.find("Day")) or "01"
    if not y:
        return None
    try:
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    except ValueError:
        return None

def parse_pubmed_xml(xml_bytes):
    """Return a list of dicts, one per PubmedArticle."""
    root = ET.fromstring(xml_bytes)
    out = []
    for art in root.iter("PubmedArticle"):
        mc = art.find("MedlineCitation")
        if mc is None:
            continue
        pmid = text_of(mc.find("PMID"))
        article = mc.find("Article")
        title = text_of(article.find("ArticleTitle")) if article is not None else ""
        secs = []
        if article is not None and article.find("Abstract") is not None:
            for at in article.find("Abstract").findall("AbstractText"):
                lab = (at.get("Label") or "").strip().upper()
                body = text_of(at)
                if body:
                    secs.append(f"{lab}: {body}" if lab else body)
        pd_node = None
        if article is not None:
            pd_node = article.find("Journal/JournalIssue/PubDate")
        year = text_of(pd_node.find("Year")) if pd_node is not None else ""
        if not year and pd_node is not None:
            m = re.search(r"(19|20)\d{2}", text_of(pd_node.find("MedlineDate")))
            year = m.group(0) if m else ""
        pubdate = " ".join(x for x in [year, text_of(pd_node.find("Month")) if pd_node is not None else "",
                                       text_of(pd_node.find("Day")) if pd_node is not None else ""] if x)
        entry = None
        doi = None
        pdata = art.find("PubmedData")
        if pdata is not None:
            for h in pdata.findall("History/PubMedPubDate"):
                if h.get("PubStatus") in ("entrez", "pubmed") and entry is None:
                    entry = ymd(h)
            for aid in pdata.findall("ArticleIdList/ArticleId"):
                if aid.get("IdType") == "doi":
                    doi = text_of(aid).lower()
        if not doi and article is not None:
            for e in article.findall("ELocationID"):
                if e.get("EIdType") == "doi":
                    doi = text_of(e).lower()
        out.append(dict(doi_pubmed=doi, pmid=pmid, title=title, year=int(year) if year.isdigit() else None,
                        pubdate=pubdate, entry_date=entry, abstract=" ".join(secs), n_sections=len(secs)))
    return out

class Client:
    def __init__(self, email, api_key, pause):
        self.s = requests.Session()
        self.base = {"tool": "medal_prereg_meta", "email": email}
        if api_key:
            self.base["api_key"] = api_key
        self.pause = pause
        self.last = 0.0

    def _wait(self):
        dt = time.time() - self.last
        if dt < self.pause:
            time.sleep(self.pause - dt)
        self.last = time.time()

    def post(self, endpoint, data, tries=4):
        for k in range(tries):
            self._wait()
            try:
                r = self.s.post(EUTILS + endpoint, data={**self.base, **data}, timeout=60)
                if r.status_code == 200:
                    return r
                if r.status_code in (429, 500, 502, 503):
                    time.sleep(2 ** (k + 1)); continue
                r.raise_for_status()
            except requests.RequestException as e:
                if k == tries - 1:
                    raise
                time.sleep(2 ** (k + 1))
        raise RuntimeError("request failed")

    def pmids_for_dois(self, dois):
        term = " OR ".join(f'"{d}"[AID]' for d in dois)
        r = self.post("esearch.fcgi", {"db": "pubmed", "term": term, "retmax": 500, "retmode": "json"})
        return r.json()["esearchresult"].get("idlist", [])

    def fetch(self, pmids):
        r = self.post("efetch.fcgi", {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"})
        return parse_pubmed_xml(r.content)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("medal_jsonl")
    ap.add_argument("--out", default="pubmed_meta.jsonl")
    ap.add_argument("--email", required=True, help="NCBI asks for a contact email")
    ap.add_argument("--api-key", default=None)
    ap.add_argument("--batch", type=int, default=40)
    a = ap.parse_args()

    dois = []
    with open(a.medal_jsonl, encoding="utf-8") as f:
        for line in f:
            try:
                d = json.loads(line).get("doi", "")
            except json.JSONDecodeError:
                continue
            if re.search(r"CD\d{6}", d or "", re.I):
                dois.append(d.strip())
    dois = list(dict.fromkeys(dois))
    done = set()
    if os.path.exists(a.out):
        with open(a.out, encoding="utf-8") as f:
            for line in f:
                try:
                    done.add(json.loads(line)["doi"].lower())
                except Exception:
                    pass
    todo = [d for d in dois if d.lower() not in done]
    print(f"{len(dois)} CD-DOIs in file; {len(done)} already saved; {len(todo)} to fetch")

    cl = Client(a.email, a.api_key, 0.11 if a.api_key else 0.40)
    missing = []
    with open(a.out, "a", encoding="utf-8") as w:
        for i in range(0, len(todo), a.batch):
            chunk = todo[i:i + a.batch]
            try:
                pmids = cl.pmids_for_dois(chunk)
                recs = cl.fetch(pmids) if pmids else []
            except Exception as e:
                print(f"batch {i}: {e}"); missing += chunk; continue
            by_doi = {r["doi_pubmed"]: r for r in recs if r["doi_pubmed"]}
            for d in chunk:
                r = by_doi.get(d.lower())
                if r is None:
                    missing.append(d); continue
                r = {"doi": d, **{k: v for k, v in r.items() if k != "doi_pubmed"}}
                w.write(json.dumps(r, ensure_ascii=False) + "\n")
            w.flush()
            print(f"{min(i + a.batch, len(todo))}/{len(todo)}  not found so far: {len(missing)}")
    with open(a.out + ".missing.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(missing))
    print(f"Done. Not found in PubMed: {len(missing)} (listed in {a.out}.missing.txt)")

if __name__ == "__main__":
    main()
