"""Checks that manifest/manifest.csv matches the registered hash and the design in section 3."""
import csv, hashlib, os, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
M = os.path.join(ROOT, "manifest")

def test_hash():
    h = hashlib.sha256(open(os.path.join(M, "manifest.csv"), "rb").read()).hexdigest()
    reg = open(os.path.join(M, "manifest.sha256")).read().split()[0]
    assert h == reg, (h, reg)

def test_design():
    rows = list(csv.DictReader(open(os.path.join(M, "manifest.csv"), encoding="utf-8")))
    assert len(rows) == 900
    assert collections.Counter(r["label"] for r in rows) == {"yes": 300, "no": 300, "ne": 300}
    assert len({r["cd"] for r in rows}) == 900                     # 1 question per review
    assert len({r["doi"] for r in rows}) == 900
    c = collections.Counter((r["label"], r["tert"]) for r in rows)
    assert all(v == 100 for v in c.values()) and len(c) == 9      # nine strata of 100

if __name__ == "__main__":
    test_hash(); test_design(); print("manifest: all tests passed")
