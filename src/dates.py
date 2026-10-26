"""
dates.py -- search-date extraction for Cochrane abstracts (preregistration section 4.1).

Frozen at lock. The functions are the same as in scripts/audit_medal.py; the test in
tests/test_dates.py checks that the two give identical output.

extract_search_date(abstract, pub_year) -> (date | None, precision | None, snippet, source)
"""
import calendar, math, re
from datetime import date

# ------------------------------------------------- search-date extraction
MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
MONTHS.update({m.lower(): i for i, m in enumerate(calendar.month_abbr) if m})
MONTHS["sept"] = 9
MON = r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
YEAR = r"((?:19|20)\d{2})"

RE_DMY = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+{MON}\.?,?\s+{YEAR}\b", re.I)
RE_MDY = re.compile(rf"\b{MON}\.?\s+(\d{{1,2}}),?\s+{YEAR}\b", re.I)
RE_MY = re.compile(rf"\b{MON}\.?,?\s+{YEAR}\b", re.I)
RE_MWY = re.compile(rf"\b{MON}\.?\s+Week\s*(\d)\s*,?\s*{YEAR}\b", re.I)   # "August Week 3 2014"
RE_YW = re.compile(rf"\b{YEAR}\s+Week\s*(\d{{1,2}})\b", re.I)               # "2018 week 39"
RE_ISSUE = re.compile(rf"{YEAR}\s*,?\s*Issue\s+(\d{{1,2}})", re.I)
RE_ISSUE2 = re.compile(rf"Issue\s+(\d{{1,2}})\s*,?\s*{YEAR}\b", re.I)
RE_YEAR_TO = re.compile(rf"(?:\bto|\buntil|\bthrough|\bup to|\bcurrent to|[-–])\s*(?:the\s+)?{YEAR}\b", re.I)

SEC_START = re.compile(r"\bSEARCH\s+(?:METHODS|STRATEGY)\b\s*:?", re.I)
SEC_END = re.compile(r"\b(?:SELECTION\s+CRITERIA|DATA\s+COLLECTION|MAIN\s+RESULTS|AUTHORS['’]?\s+CONCLUSIONS|DATA\s+SOURCES)\b\s*:?")

def mon(s):
    s = s.lower().rstrip(".")
    return MONTHS[s] if s in MONTHS else MONTHS[s[:3]]

def eom(y, m):
    return date(y, m, calendar.monthrange(y, m)[1])

def dates_in(text):
    """Return list of (date, precision) found in text."""
    out, used = [], []
    def free(span):
        return all(span[1] <= u[0] or span[0] >= u[1] for u in used)
    for m in RE_DMY.finditer(text):
        d, mo, y = int(m.group(1)), mon(m.group(2)), int(m.group(3))
        try:
            out.append((date(y, mo, d), "day")); used.append(m.span())
        except ValueError:
            pass
    for m in RE_MDY.finditer(text):
        if not free(m.span()): continue
        mo, d, y = mon(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            out.append((date(y, mo, d), "day")); used.append(m.span())
        except ValueError:
            pass
    for m in RE_MWY.finditer(text):
        if not free(m.span()): continue
        mo, wk, y = mon(m.group(1)), int(m.group(2)), int(m.group(3))
        day = min(7 * wk, calendar.monthrange(y, mo)[1])
        out.append((date(y, mo, day), "week")); used.append(m.span())
    for m in RE_YW.finditer(text):
        if not free(m.span()): continue
        y, wk = int(m.group(1)), int(m.group(2))
        if 1 <= wk <= 53:
            from datetime import timedelta
            out.append((min(date(y, 1, 1) + timedelta(days=7 * wk - 1), date(y, 12, 31)), "week")); used.append(m.span())
    for m in RE_MY.finditer(text):
        if not free(m.span()): continue
        mo, y = mon(m.group(1)), int(m.group(2))
        out.append((eom(y, mo), "month")); used.append(m.span())
    for m in RE_ISSUE.finditer(text):
        if not free(m.span()): continue
        y, iss = int(m.group(1)), int(m.group(2))
        mo = iss * 3 if (iss <= 4 and y < 2008) else min(iss, 12)
        out.append((eom(y, mo), "issue")); used.append(m.span())
    for m in RE_ISSUE2.finditer(text):
        if not free(m.span()): continue
        iss, y = int(m.group(1)), int(m.group(2))
        mo = iss * 3 if (iss <= 4 and y < 2008) else min(iss, 12)
        out.append((eom(y, mo), "issue")); used.append(m.span())
    for m in RE_YEAR_TO.finditer(text):
        if not free(m.span()): continue
        y = int(m.group(1))
        out.append((date(y, 12, 31), "year")); used.append(m.span())
    return out

def search_section(abstract):
    m = SEC_START.search(abstract)
    if m:
        rest = abstract[m.end():]
        e = SEC_END.search(rest)
        return rest[: e.start()] if e else rest[:1500], "section"
    sents = re.split(r"(?<=[.!?])\s+", abstract)
    hits = [s for s in sents if re.search(r"\bsearch(?:ed|es|ing)?\b", s, re.I)]
    if hits:
        return " ".join(hits[:4]), "sentence"
    return "", "none"

# a later search whose results were NOT incorporated into the review must not set the cutoff
RE_NOT_INCORP = re.compile(r"(not\s+(?:been\s+|yet\s+|fully\s+)*(?:incorporated|included|integrated|assessed|analy[sz]ed)"
                           r"|awaiting\s+(?:classification|assessment)|will\s+be\s+(?:incorporated|included|integrated)"
                           r"|to\s+be\s+(?:incorporated|included|integrated)|studies\s+(?:are|were)\s+ongoing)", re.I)
def _kept_text(text):
    sents = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(x for x in sents if not RE_NOT_INCORP.search(x))

PREC_RANK = {"day": 3, "week": 2, "month": 2, "issue": 2, "year": 1}

def extract_search_date(abstract, pub_year=None):
    if not isinstance(abstract, str) or not abstract.strip():
        return None, None, "", "no_abstract"
    text, how = search_section(abstract)
    if not text:
        return None, None, "", "none"
    cands = dates_in(_kept_text(text)) or dates_in(text)
    if pub_year is not None and not (isinstance(pub_year, float) and math.isnan(pub_year)):
        try:
            cands = [c for c in cands if c[0].year <= int(pub_year) + 1]
        except (TypeError, ValueError):
            pass
    cands = [c for c in cands if 1950 <= c[0].year <= 2026]
    # a bare year ("1966 to 2008") must not outrank a month-level date in the same or a later year
    fine_years = [c[0].year for c in cands if c[1] != "year"]
    if fine_years:
        cands = [c for c in cands if c[1] != "year" or c[0].year > max(fine_years)]
    if not cands:
        return None, None, text[:300], how
    best = max(cands, key=lambda c: (c[0], PREC_RANK[c[1]]))
    return best[0], best[1], text[:300], how

