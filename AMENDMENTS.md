# Amendments

Every change to `PREREGISTRATION.md` after the lock is recorded here: date, what changed, why, and whether any outcome data had been seen when the change was made (section 12 of the preregistration).

## Lock record

| Item | Value |
|---|---|
| Lock date | 30 Oct 2026 |
| Version | 1.6 |
| git tag | `prereg-v1` |
| Commit hash of the tag | `a71f1f572efbcaa710e932a22aec8ce890fdb442` |
| OSF registration | https://osf.io/yxeqv (Open-Ended Registration, 30 Oct 2026; file `PREREGISTRATION.md` v1.6 attached, identical to the tagged file) |
| `manifest.csv` SHA-256 | `ad89017e1fea0ef482497cbc4220e72a9e00cea09b2c82e44a9252a867eb6cd0` |

## Changes after lock

| Date | Change | Reason | Outcome data seen? |
|---|---|---|---|
| 30 Oct 2026 | **Documentation only.** Section 3 says "158 questions are repeated verbatim across versions"; the correct count is **159**. `PREREGISTRATION.md` is not edited (the OSF copy and the tag must stay identical); the corrected figure is recorded here. The count does not enter any rule, sample or analysis. | Counting slip found in the post-lock repository review. | No |
| 30 Oct 2026 | **Documentation only.** Four rules in `src/dates.py` (frozen at the tag) were not spelled out in section 4.1: (1) the search section is the text after "SEARCH METHODS" or "SEARCH STRATEGY" up to the next section heading (else up to 1,500 characters), and if there is no such heading the first four sentences that mention a search are used; (2) a candidate date later than the review's PubMed publication year + 1 is discarded; (3) dates outside 1950 to 2026 are discarded; (4) an issue number 1 to 4 in a year before 2008 is read as a quarter (issue 1 = March, 2 = June, 3 = September, 4 = December), otherwise as that month. The code is unchanged and is what was used to draw the manifest. | Section 4.1 summarised the extraction; the code is the exact specification. | No |
| 30 Oct 2026 | **QA of the "not incorporated" rule (no change to it).** `scripts/diff_incorp_rule.py` compares the extracted cutoff with and without the rule on the 900 manifest rows: 3 of 900 rows differ, and in all 3 the rule gives the correct (earlier) date. The manifest and its SHA-256 are unchanged. | Check that the rule added after the 50-abstract audit does not distort the sample. | No |
| 30 Oct 2026 | **Docstring only.** `scripts/make_manifest.py` still said "If the lock date changes, pass --seed with the new lock date". Section 3 says the seed stays 20261028 even if the lock slips. The docstring now says that. No code line changed; the manifest is unaffected. Also added `scripts/diff_incorp_rule.py`, and `qa_out/` to `.gitignore`. | The docstring contradicted the preregistration. | No |
| Planned | The physician audit (section 9, stage 2) is coordinated by Dr. Eslami and runs after the main results; the design does not depend on it. This restates section 9 and is not a change. | Clarification for readers of the log. | No |
