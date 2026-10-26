#!/usr/bin/env python3
"""
audit_medal.py  --  structure audit of the MEDAL Cochrane file.

Looks at the DATA ONLY. It never loads or runs a model, so it does not touch
the preregistration rule about not seeing model outputs.

Usage:
    python audit_medal.py path/to/cochrane_file.{jsonl,json,csv,parquet}

Writes (next to the input, or in --out):
    audit_report.md          summary, safe to paste into a chat
    date_check_sample.csv    50 random rows for the manual search-date check
                             (fill the last column with y / n by hand)

The dry-run draw below uses a THROWAWAY seed (1). The real seed is the lock
date (YYYYMMDD) and is used only once, in the real sampling script.
"""
import argparse, json, math, os, random, re, sys
from collections import Counter, defaultdict
from datetime import date
import calendar

try:
    import pandas as pd
except ImportError:
    sys.exit("pandas is required: pip install pandas")

# ---------------------------------------------------------------- loading
def load(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".jsonl":
        return pd.read_json(path, lines=True)
    if ext == ".json":
        try:
            return pd.read_json(path)
        except ValueError:
            return pd.read_json(path, lines=True)
    if ext == ".csv":
        return pd.read_csv(path)
    if ext in (".parquet", ".pq"):
        return pd.read_parquet(path)
    sys.exit(f"Unknown file type: {ext}")

def pick(df, names):
    low = {c.lower().replace("_", "").replace("-", ""): c for c in df.columns}
    for n in names:
        k = n.lower().replace("_", "").replace("-", "")
        if k in low:
            return low[k]
    return None

LABELS = {"yes": "yes", "no": "no", "no evidence": "ne", "noevidence": "ne"}

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

# ----------------------------------------------------------------- drawing
def tertile_labels(years):
    s = pd.Series(years)
    q1, q2 = s.quantile([1 / 3, 2 / 3])
    return [0 if y <= q1 else (1 if y <= q2 else 2) for y in years], (q1, q2)

def dry_run_draw(df, per_class=300, cap=2, seed=1):
    rng = random.Random(seed)
    d = df.copy()
    d["tert"], _ = tertile_labels(d["year"].fillna(d["year"].median()).tolist())
    remaining = defaultdict(lambda: cap)
    picked = defaultdict(int)
    chosen = []
    target = per_class // 3
    for cls in ("ne", "no", "yes"):                 # scarcest class first
        for t in (0, 1, 2):
            pool = d[(d["label"] == cls) & (d["tert"] == t)].index.tolist()
            rng.shuffle(pool)
            n = 0
            for i in pool:
                r = d.at[i, "review"]
                if remaining[r] > 0 and n < target:
                    remaining[r] -= 1; picked[cls] += 1; n += 1; chosen.append(i)
        # top up this class from any stratum if a stratum fell short
        if picked[cls] < per_class:
            pool = [i for i in d[d["label"] == cls].index if i not in set(chosen)]
            rng.shuffle(pool)
            for i in pool:
                r = d.at[i, "review"]
                if remaining[r] > 0 and picked[cls] < per_class:
                    remaining[r] -= 1; picked[cls] += 1; chosen.append(i)
    return dict(picked), len(set(d.loc[chosen, "review"]))

# -------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--out", default=None)
    ap.add_argument("--meta", default=None,
                    help="pubmed_meta.jsonl from fetch_pubmed_meta.py (adds abstracts, years, entry dates)")
    a = ap.parse_args()
    out = a.out or os.path.dirname(os.path.abspath(a.path))
    os.makedirs(out, exist_ok=True)

    df = load(a.path)
    L = []
    P = lambda s="": L.append(s)

    P("# MEDAL Cochrane file: structure audit")
    P(f"\nFile: `{os.path.basename(a.path)}`  |  rows: **{len(df)}**  |  columns: {list(df.columns)}")

    c_doi = pick(df, ["doi"]); c_q = pick(df, ["question"])
    c_ans = pick(df, ["answer", "label", "ground_truth_answer"])
    c_abs = pick(df, ["abstract"]); c_yr = pick(df, ["publication_year", "year", "pub_year"])
    P(f"\nColumn mapping: doi={c_doi}, question={c_q}, answer={c_ans}, abstract={c_abs}, year={c_yr}")
    missing = [n for n, c in [("doi", c_doi), ("question", c_q), ("answer", c_ans)] if c is None]
    if missing:
        P(f"\n**STOP: required columns not found: {missing}**")
        open(os.path.join(out, "audit_report.md"), "w", encoding="utf-8").write("\n".join(L))
        print("\n".join(L)); return

    c_notes = pick(df, ["notes"])
    d = pd.DataFrame({
        "doi": df[c_doi].astype(str).str.strip(),
        "question": df[c_q].astype(str),
        "label": df[c_ans].astype(str).str.strip().str.lower().map(LABELS),
        "abstract": df[c_abs] if c_abs else None,
        "year": pd.to_numeric(df[c_yr], errors="coerce") if c_yr else float("nan"),
        "notes": df[c_notes].fillna("").astype(str) if c_notes else "",
    })
    if c_abs is None:
        d["abstract"] = None
    if a.meta:
        m = pd.read_json(a.meta, lines=True)
        m["k"] = m["doi"].astype(str).str.lower().str.strip()
        m = m.drop_duplicates("k").set_index("k")
        key = d["doi"].str.lower()
        d["abstract"] = key.map(m["abstract"]) if "abstract" in m else d["abstract"]
        d["year"] = key.map(m["year"]) if "year" in m else d["year"]
        d["edat"] = key.map(m["entry_date"]) if "entry_date" in m else None
        P(f"\nMerged PubMed metadata: {int(d['abstract'].notna().sum())} of {len(d)} rows now have an abstract.")
        c_abs, c_yr = "abstract", "year"
    else:
        c_abs = c_abs if (c_abs and df[c_abs].notna().any()) else None
        c_yr = c_yr if (c_yr and df[c_yr].notna().any()) else None
        if c_abs is None or c_yr is None:
            P("\n> **The file's `abstract` and/or `publication_year` columns are empty for every row.** "
              "Abstracts, years and dates must be fetched from PubMed by DOI (fetch_pubmed_meta.py), "
              "then rerun with `--meta pubmed_meta.jsonl`.")

    # 1. labels
    P("\n## 1. Labels")
    raw = df[c_ans].astype(str).str.strip().value_counts().to_dict()
    P(f"Raw label values: {raw}")
    cnt = d["label"].value_counts(dropna=False).to_dict()
    exp = {"yes": 5167, "no": 2309, "ne": 1054}
    P("\n| class | found | expected (paper) |\n|---|---|---|")
    for k in ("yes", "no", "ne"):
        P(f"| {k} | {cnt.get(k, 0)} | {exp[k]} |")
    P(f"\nUnmapped / missing labels: {int(d['label'].isna().sum())}. "
      f"Total rows {len(d)} (paper: 8530).")
    if len(d) != 8530:
        P("**Note: row count differs from 8,530. Say whether this is the Cochrane file only.**")

    # 1b. eligibility
    P("\n## 1b. Eligibility")
    has_cd = d["doi"].str.contains(r"CD\d{6}", case=False, regex=True)
    P(f"Rows with an empty / unmapped label: {int(d['label'].isna().sum())}")
    P(f"Rows whose DOI has no Cochrane CD number: {int((~has_cd).sum())} "
      f"(examples: {d.loc[~has_cd, 'doi'].head(4).tolist()}). These are not standard Cochrane intervention reviews "
      f"(methodology reviews MR..., HTA monographs) and are excluded by rule.")
    d = d[d["label"].notna() & has_cd].copy().reset_index(drop=True)
    P(f"Eligible rows before any abstract requirement: **{len(d)}**; "
      f"by class: {d['label'].value_counts().to_dict()}")

    # 2. review ids
    P("\n## 2. Review identifiers")
    d["cd"] = d["doi"].str.extract(r"(CD\d{6})", flags=re.I)[0].str.upper()
    P(f"DOIs with a parseable CD number: {int(d['cd'].notna().sum())} / {len(d)}. "
      f"Example DOI: `{d['doi'].iloc[0]}`")
    d["review"] = d["cd"].fillna(d["doi"])
    per = d.groupby("review").size()
    P(f"Unique reviews: **{len(per)}**. Questions per review: "
      f"min {per.min()}, median {per.median()}, mean {per.mean():.2f}, max {per.max()}. "
      f"Distribution: {per.value_counts().sort_index().to_dict()}")
    dup = d.duplicated(subset=["review", "question"]).sum()
    P(f"Duplicate (review, question) pairs: {int(dup)}")

    # 3. abstracts and years
    P("\n## 3. Abstracts and years")
    if c_abs:
        d["abstract"] = d["abstract"].astype(object).where(d["abstract"].notna(), "").astype(str)
        has = d["abstract"].str.strip().str.len() > 0
        P(f"Rows with a non-empty abstract: {int(has.sum())} / {len(d)} ({100*has.mean():.1f}%)")
        L_ = d.loc[has, "abstract"].str.len()
        if len(L_):
            P(f"Abstract length (chars): median {int(L_.median())}, 5th pct {int(L_.quantile(.05))}, 95th pct {int(L_.quantile(.95))}")
        sec = d["abstract"].fillna("").str.contains(SEC_START)
        P(f"Abstracts containing a 'SEARCH METHODS/STRATEGY' heading: {int(sec.sum())} ({100*sec.mean():.1f}%)")
    else:
        P("**No usable abstracts in the file.** They must be fetched from PubMed by DOI.")
    if c_yr:
        y = d["year"].dropna()
        P(f"Year coverage: {int(y.notna().sum())} rows" + (f"; range {int(y.min())} to {int(y.max())}" if len(y) else ""))
        P(f"Per-class median year: " + ", ".join(f"{k}: {d.loc[d.label==k,'year'].median()}" for k in ("yes","no","ne")))
    else:
        P("**No usable publication years in the file.**")

    # 4. search-date extraction
    P("\n## 4. Search-date extraction")
    if c_abs:
        res = [extract_search_date(a_, y_) for a_, y_ in zip(d["abstract"], d["year"])]
        d["sdate"] = [r[0] for r in res]; d["sprec"] = [r[1] for r in res]
        d["ssnip"] = [r[2] for r in res]; d["show"] = [r[3] for r in res]
        found = d["sdate"].notna()
        P(f"Search date found: **{int(found.sum())} / {len(d)} ({100*found.mean():.1f}%)**")
        P(f"By source: {d['show'].value_counts().to_dict()}")
        P(f"By precision: {d.loc[found,'sprec'].value_counts().to_dict()}")
        if c_yr:
            gap = (d.loc[found, "year"] - d.loc[found, "sdate"].map(lambda x: x.year)).dropna()
            P(f"Publication year minus search year: median {gap.median()}, "
              f"share >= 2 years: {100*(gap>=2).mean():.1f}%, negative: {int((gap<0).sum())}")
        by_cls = d.groupby("label")["sdate"].apply(lambda s: round(100 * s.notna().mean(), 1)).to_dict()
        P(f"Coverage by class (%): {by_cls}")
        sample = d[found | ~found].sample(n=min(50, len(d)), random_state=1)[
            ["doi", "year", "label", "sdate", "sprec", "show", "ssnip"]].copy()
        sample["correct_y_or_n"] = ""
        sample.to_csv(os.path.join(out, "date_check_sample.csv"), index=False, encoding="utf-8-sig")
        P("\nWrote `date_check_sample.csv` (50 random rows). Check each by hand against the "
          "abstract. For rows WITH an extracted date, 'y' = same month as the true last-search date. "
          "For rows WITHOUT one, 'y' = the abstract really has no usable date, 'n' = it has one we missed. "
          "Preregistration threshold: **at least 45 of 50 'y'**.")
    else:
        P("Skipped (no abstracts).")

    # 5. dry-run draw
    P("\n## 5. Dry-run draw (throwaway seed 1; NOT the real sample)")
    dd = d[d["label"].notna()].copy()
    if c_abs and (dd["abstract"].fillna("").str.strip().str.len() > 0).any():
        dd = dd[dd["abstract"].fillna("").str.strip().str.len() > 0]
    if dd["year"].notna().sum() == 0:
        dd["year"] = 0.0
        P("(No years yet, so the draw is not stratified by year tertile here.)")
    P(f"Eligible rows (label + abstract): {len(dd)}; by class: {dd['label'].value_counts().to_dict()}")
    for cap in (1, 2, 3):
        picked, nrev = dry_run_draw(dd.reset_index(drop=True), cap=cap)
        short = {k: 300 - picked.get(k, 0) for k in ("ne", "no", "yes")}
        P(f"- cap {cap} per review: picked {picked}, shortfall {short}, distinct reviews {nrev}")
    for cap in (1, 2):
        ub = {k: int(sum(min(cap, n) for n in dd[dd.label == k].groupby('review').size())) for k in ("ne", "no", "yes")}
        P(f"- Upper bound on questions per class with cap {cap} (ignoring the cross-class limit): {ub}")

    # 6. what the NE labels look like (notes field only; no model involved)
    P("\n## 6. What the no-evidence labels look like (from the `notes` field)")
    ne = d[d["label"] == "ne"]
    if len(ne) and (ne["notes"].str.len() > 0).any():
        n = ne["notes"].str.lower()
        t1 = n.str.contains(r"\bno (?:randomi[sz]ed|eligible|relevant|studies|trials|rcts?|included|published|clinical|controlled|evidence from|data)|\bnone of the|no .{0,40}(?:were|was) (?:identified|found|included|available)|not identified|no study|no trial|did not (?:identify|find)|lack of|absence of", regex=True)
        t2 = n.str.contains(r"insufficient|inconclusive|unclear|limited|low[- ]quality|low[- ]certainty|poor quality|very low|too few|small|imprecis|uncertain|cannot be|not possible|no clear|no firm|no significant|not significant|no difference|includes 1|crosses", regex=True)
        N1 = t1 & ~t2; N2 = t2 & ~t1; N3 = ~t1 & ~t2; NB = t1 & t2
        P("Keyword typing of the generator's own supporting note (rough, descriptive, not a labelling of truth):")
        P(f"- N1, no eligible studies / trials identified: {int(N1.sum())} ({100*N1.mean():.1f}%)")
        P(f"- N2, evidence inconclusive / low certainty / not significant: {int(N2.sum())} ({100*N2.mean():.1f}%)")
        P(f"- both patterns: {int(NB.sum())} ({100*NB.mean():.1f}%); neither: {int(N3.sum())} ({100*N3.mean():.1f}%)")
        d.loc[ne.index, "ne_type"] = ["N1" if x1 else "N2" if x2 else "NB" if xb else "N3" for x1, x2, xb in zip(N1, N2, NB)]
        d.loc[ne.index, ["doi", "question", "notes", "ne_type"]].sample(n=min(30, len(ne)), random_state=1).to_csv(
            os.path.join(out, "ne_notes_sample.csv"), index=False, encoding="utf-8-sig")
        P("Wrote `ne_notes_sample.csv` (30 random no-evidence items, for a quick read).")

    rep = "\n".join(L)
    open(os.path.join(out, "audit_report.md"), "w", encoding="utf-8").write(rep)
    print(rep)

if __name__ == "__main__":
    main()
