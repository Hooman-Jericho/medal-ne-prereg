"""Run with:  python tests/test_dates.py   (or pytest)."""
import os, sys
from datetime import date
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src")); sys.path.insert(0, os.path.join(ROOT, "scripts"))
from dates import extract_search_date as ext
import audit_medal

CASES = [
    # (abstract text, pub_year, expected date, expected precision)
    ("Search methods: We searched CENTRAL to March 2014.", 2014, date(2014, 3, 31), "month"),
    ("Search methods: MEDLINE (1966 to August Week 1 2008), EMBASE (1980 to 2008 Week 28).", 2010, date(2008, 8, 7), "week"),
    ("Search methods: Embase (1980 to 2018 week 39); MEDLINE (1946 to 25 September 2018).", 2019, date(2018, 9, 30), "week"),
    ("Search methods: CENTRAL (2013, Issue 5) and MEDLINE (1966 to June 2013).", 2014, date(2013, 6, 30), "month"),
    ("Search methods: Register (Issue 3, 2008). MEDLINE (1966 to 2008).", 2010, date(2008, 3, 31), "issue"),
    # a later search that was NOT incorporated must not set the cutoff (CD013030, CD012583)
    ("Search methods: We conducted the most recent searches on 1 June 2020. A further search was run in October 2021, but studies were not fully incorporated.", 2022, date(2020, 6, 1), "day"),
    ("Search methods: In March 2017 we searched the Register. We updated this search in March 2018; as a result several studies are awaiting classification.", 2018, date(2017, 3, 31), "month"),
    # latest of several dates
    ("Search methods: We last searched databases on November 16, 2018, and Chinese databases on November 19, 2018.", 2020, date(2018, 11, 19), "day"),
]

def test_cases():
    for text, y, d, p in CASES:
        got = ext("OBJECTIVES: x. " + text, y)
        assert got[0] == d and got[1] == p, (text[:60], got[:2], d, p)

def test_same_as_audit_script():
    for text, y, _, _ in CASES:
        a = ext("OBJECTIVES: x. " + text, y)[:2]
        b = audit_medal.extract_search_date("OBJECTIVES: x. " + text, y)[:2]
        assert a == b, (text[:60], a, b)

def test_no_abstract():
    assert ext("", 2015)[0] is None and ext(None, 2015)[0] is None

if __name__ == "__main__":
    test_cases(); test_same_as_audit_script(); test_no_abstract(); print("dates: all tests passed")
