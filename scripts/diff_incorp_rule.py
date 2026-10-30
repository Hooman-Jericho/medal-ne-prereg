#!/usr/bin/env python3
"""
diff_incorp_rule.py -- QA for the "later search not incorporated" rule (prereg section 4.1).

For every row, extract the search date twice: with the rule (the frozen src/dates.py) and with the
rule switched off. Rows where the two differ are written to incorp_rule_changes.csv together with
the sentences the rule removed, so that each change can be read by eye. Data only; no model.

Usage (from the repo folder):
    python scripts/diff_incorp_rule.py --meta pubmed_meta.jsonl \
        [--manifest manifest/manifest.csv] --out qa_out
"""
import argparse, os, re, sys
import pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
import dates as D

class _Never:                      # a regex stand-in that never matches
    def search(self, _): return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?"); ap.add_argument("--meta", required=True)
    ap.add_argument("--manifest", default=None); ap.add_argument("--out", default="qa_out")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    m = pd.read_json(a.meta, lines=True)
    if a.manifest:
        keep = set(pd.read_csv(a.manifest)["doi"].str.lower())
        m = m[m["doi"].str.lower().isin(keep)]
    real = D.RE_NOT_INCORP
    rows = []
    for _, r in m.iterrows():
        ab, yr = r.get("abstract"), r.get("year")
        D.RE_NOT_INCORP = real
        with_rule = D.extract_search_date(ab, yr)[:2]
        D.RE_NOT_INCORP = _Never()
        without = D.extract_search_date(ab, yr)[:2]
        D.RE_NOT_INCORP = real
        if with_rule[0] != without[0]:
            text, _ = D.search_section(ab)
            removed = [s for s in re.split(r"(?<=[.!?])\s+", text) if real.search(s)]
            rows.append(dict(doi=r["doi"], year=yr, with_rule=with_rule[0], without_rule=without[0],
                             removed_sentences=" || ".join(removed)[:600]))
    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(a.out, "incorp_rule_changes.csv"), index=False)
    print(f"rows checked: {len(m)}; rows whose date changes because of the rule: {len(out)}")
    print("Read incorp_rule_changes.csv: for each row, is the removed sentence really about a search "
          "whose results were not used? Count how many look WRONG and send me the number and 3 examples.")

if __name__ == "__main__":
    main()
