#!/usr/bin/env python3
"""
make_manifest.py -- draw the 900-question study sample and write manifest.csv.

Implements section 3 and section 4.1 of PREREGISTRATION.md. It reads DATA ONLY
(the MEDAL file and the PubMed metadata). It never loads or runs a model.

Usage (same folder as audit_medal.py):
    python make_manifest.py 1-QA-systematic-review.jsonl --meta pubmed_meta.jsonl --out manifest_out

The seed is the planned lock date as an integer (YYYYMMDD), 20261028, fixed before
the draw. The seed does not change if the lock slips. Do not try several seeds:
the first run that you register is the one that counts.

Writes, in --out:
    manifest.csv         the sample (one row per question), sorted by doi
    manifest.sha256      SHA-256 of manifest.csv (goes into section 17 of the prereg)
    manifest_report.md   counts per class / stratum, the cap used, feasibility notes
The file is written with UTF-8 and "\\n" line endings so that the hash is the same on
Windows, Linux and macOS.
"""
import argparse, csv, hashlib, os, random, re, sys
from collections import defaultdict

try:
    import pandas as pd
except ImportError:
    sys.exit("pandas is required: pip install pandas")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from audit_medal import load, pick, LABELS, extract_search_date
except ImportError:
    sys.exit("audit_medal.py must be in the same folder as make_manifest.py")

CLASSES = ("ne", "no", "yes")          # scarcest class first


def build_table(path, meta_path):
    df = load(path)
    c_doi = pick(df, ["doi"]); c_q = pick(df, ["question"]); c_ans = pick(df, ["answer", "label"])
    d = pd.DataFrame({
        "doi": df[c_doi].astype(str).str.strip(),
        "question": df[c_q].astype(str),
        "label": df[c_ans].astype(str).str.strip().str.lower().map(LABELS),
    })
    m = pd.read_json(meta_path, lines=True)
    m["k"] = m["doi"].astype(str).str.lower().str.strip()
    m = m.drop_duplicates("k").set_index("k")
    key = d["doi"].str.lower()
    d["abstract"] = key.map(m["abstract"])
    d["year"] = key.map(m["year"])
    d["entry_date"] = key.map(m["entry_date"]) if "entry_date" in m else None
    d["pubdate"] = key.map(m["pubdate"]) if "pubdate" in m else None
    d["cd"] = d["doi"].str.extract(r"(CD\d{6})", flags=re.I)[0].str.upper()
    n_all = len(d)
    # eligibility (section 3): label, CD number, PubMed record with abstract and year
    d = d[d["label"].notna() & d["cd"].notna()].copy()
    d["abstract"] = d["abstract"].fillna("").astype(str)
    d = d[(d["abstract"].str.strip() != "") & d["year"].notna()].copy()
    d["year"] = d["year"].astype(int)
    d = d.sort_values("doi").reset_index(drop=True)
    return d, n_all


def add_cutoff(d):
    """Cutoff date T_i (section 4.1): last search date, else PubMed publication date."""
    sd, prec, fb, src = [], [], [], []
    for _, r in d.iterrows():
        dt, pr, _, how = extract_search_date(r["abstract"], r["year"])
        if dt is not None:
            sd.append(dt.isoformat()); prec.append(pr); fb.append(0); src.append("search_date")
            continue
        alt = None
        try:
            alt = pd.to_datetime(str(r["pubdate"]), errors="raise").date().isoformat()
        except Exception:
            alt = None
        if alt is None and isinstance(r["entry_date"], str) and r["entry_date"]:
            alt = r["entry_date"][:10]
        if alt is None:
            alt = f"{int(r['year'])}-12-31"
        sd.append(alt); prec.append("fallback"); fb.append(1); src.append("pubmed_date")
    d["cutoff_date"] = sd; d["date_precision"] = prec; d["date_fallback"] = fb; d["cutoff_source"] = src
    return d


def draw(d, per_class, cap, seed):
    """One seeded draw. Returns list of row indices."""
    rng = random.Random(seed)
    per_stratum = per_class // 3
    remaining = defaultdict(lambda: cap)
    chosen, count = [], defaultdict(int)
    for cls in CLASSES:
        for t in (0, 1, 2):
            pool = d[(d["label"] == cls) & (d["tert"] == t)].index.tolist()
            rng.shuffle(pool)
            n = 0
            for i in pool:
                r = d.at[i, "cd"]
                if n < per_stratum and remaining[r] > 0:
                    remaining[r] -= 1; n += 1; count[cls] += 1; chosen.append(i)
        if count[cls] < per_class:                 # top up from any stratum
            taken = set(chosen)
            pool = [i for i in d[d["label"] == cls].index if i not in taken]
            rng.shuffle(pool)
            for i in pool:
                r = d.at[i, "cd"]
                if count[cls] < per_class and remaining[r] > 0:
                    remaining[r] -= 1; count[cls] += 1; chosen.append(i)
    return chosen, dict(count)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--meta", required=True)
    ap.add_argument("--out", default="manifest_out")
    ap.add_argument("--seed", type=int, default=20261028, help="lock date as YYYYMMDD")
    ap.add_argument("--per-class", type=int, default=300, help="300 (main) or 200 (reduced design)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    d, n_all = build_table(a.path, a.meta)
    d = add_cutoff(d)
    # tertile cut points on all eligible rows pooled, before the draw (section 3)
    q1, q2 = d["year"].quantile([1 / 3, 2 / 3])
    d["tert"] = d["year"].apply(lambda y: 0 if y <= q1 else (1 if y <= q2 else 2))

    notes, cap_used, chosen, count = [], None, None, None
    for cap in (1, 2, 3):
        ch, ct = draw(d, a.per_class, cap, a.seed)
        short = {c: a.per_class - ct.get(c, 0) for c in CLASSES}
        notes.append(f"cap {cap} per review: picked {ct}, shortfall {short}")
        chosen, count, cap_used = ch, ct, cap
        if all(v == 0 for v in short.values()):
            break
    if any(a.per_class - count.get(c, 0) > 0 for c in CLASSES):
        # last resort of section 3: take every eligible NE question, shrink the other classes
        ne_n = int((d["label"] == "ne").sum())
        notes.append(f"FALLBACK: could not reach {a.per_class} per class; shrinking to {ne_n} per class")
        ch, ct = draw(d, ne_n, 3, a.seed)
        chosen, count = ch, ct

    s = d.loc[chosen].copy()
    s["qid"] = [f"Q{n:04d}" for n in range(1, len(s) + 1)]
    s = s.sort_values("doi")
    s["qid"] = [f"Q{n:04d}" for n in range(1, len(s) + 1)]
    cols = ["qid", "doi", "cd", "label", "year", "tert", "cutoff_date", "date_precision",
            "date_fallback", "cutoff_source", "question"]
    path = os.path.join(a.out, "manifest.csv")
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(cols)
        for _, r in s[cols].iterrows():
            w.writerow([r[c] for c in cols])
    h = hashlib.sha256(open(path, "rb").read()).hexdigest()
    open(os.path.join(a.out, "manifest.sha256"), "w").write(f"{h}  manifest.csv\n")

    L = ["# Manifest report", "",
         f"Seed: **{a.seed}**   |   per class: {a.per_class}   |   cap used: **{cap_used} per review**",
         f"SHA-256 of manifest.csv: `{h}`", "",
         f"Rows in file: {n_all}; eligible (label, CD number, abstract, year): {len(d)}",
         f"Year tertile cut points (pooled, eligible): {q1:.1f}, {q2:.1f}", "",
         "Draw attempts:"] + [f"- {n}" for n in notes] + [
         "", f"Sample size: **{len(s)}**; distinct reviews: **{s['cd'].nunique()}**", "",
         "Class x year tertile:", "", "| class | t0 | t1 | t2 | total |", "|---|---|---|---|---|"]
    for c in CLASSES:
        x = [int(((s.label == c) & (s.tert == t)).sum()) for t in (0, 1, 2)]
        L.append(f"| {c} | {x[0]} | {x[1]} | {x[2]} | {sum(x)} |")
    L += ["", f"date_fallback = 1: {int(s['date_fallback'].sum())} of {len(s)} questions",
          f"date precision: {s['date_precision'].value_counts().to_dict()}",
          f"median year by class: {s.groupby('label')['year'].median().to_dict()}", "",
          "Register `manifest.csv` SHA-256 in section 17 of the preregistration BEFORE any model run."]
    open(os.path.join(a.out, "manifest_report.md"), "w", encoding="utf-8").write("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
