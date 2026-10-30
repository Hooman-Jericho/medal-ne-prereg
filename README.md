# Does Retrieval Know When Evidence Is Missing?

A baseline-aware, time-valid evaluation of retrieval-augmented generation (RAG) for evidence-based clinical QA. The study builds on the Cochrane subset of MEDAL (Wang & Chen, *Patterns* 7:101519, 2026).

**Status:** preregistration v1.6, locked 30 Oct 2026 (git tag `prereg-v1`; OSF link and commit hash in [`AMENDMENTS.md`](AMENDMENTS.md)). No model has been run on the study sample. A second phase (a learned retrieval-side component) will be registered separately before the main run.

Hooman Soleymani (Islamic Azad University, Tehran North Branch), supervised by Dr. Nava Eslami (Islamic Azad University, North Tehran Branch).

## The question

When a model reads retrieved PubMed abstracts, does it get better or worse at noticing that the literature cannot answer the question ("no evidence")? And how much of any apparent harm disappears when retrieval is limited to what the review's authors could have seen at the time? The full design, hypotheses and analysis plan are in [`PREREGISTRATION.md`](PREREGISTRATION.md).

## Layout

| Path | What it is |
|---|---|
| `PREREGISTRATION.md` | The registered plan (the official, English version) |
| `AMENDMENTS.md` | Log of any change after lock |
| `manifest/` | The 900-question sample: `manifest.csv`, its SHA-256, and the draw report |
| `src/dates.py` | Search-date extraction (frozen at lock) |
| `scripts/audit_medal.py` | Data-only structure audit and manual date-check sample |
| `scripts/fetch_pubmed_meta.py` | Fetches abstracts, years and entry dates from PubMed by DOI |
| `scripts/make_manifest.py` | Draws the sample (seed = lock date) |
| `tests/` | Tests for date extraction and manifest integrity |

## Reproducing the sample

The MEDAL file is not redistributed here. Download `QA-systematic-review.jsonl` from Hugging Face (`cwang271/MEDAL`), then:

```bash
pip install pandas requests
python scripts/fetch_pubmed_meta.py QA-systematic-review.jsonl --out pubmed_meta.jsonl --email you@example.com
python scripts/make_manifest.py QA-systematic-review.jsonl --meta pubmed_meta.jsonl --out manifest_out
python tests/test_dates.py
python tests/test_manifest.py
```

PubMed changes over time, so a fresh fetch may give slightly different abstracts. The registered sample is `manifest/manifest.csv`; check it against `manifest/manifest.sha256`.

## Licence

Code: MIT. The MEDAL data keep their own licence.
