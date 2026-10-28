# Preregistration

**Does Retrieval Know When Evidence Is Missing? A Baseline-Aware, Time-Valid Evaluation of RAG for Evidence-Based Clinical QA**

| | |
|---|---|
| Version | 1.5 (draft; lock target 30 Oct 2026) |
| Author | Hooman Soleymani, Islamic Azad University, Tehran North Branch |
| Supervisor | Dr. Nava Eslami, Islamic Azad University, North Tehran Branch |
| Registered at | git tag `prereg-v1` and OSF Registries (TODO(lock): OSF link) |
| Code | https://github.com/Hooman-Jericho/medal-ne-prereg |
| Data | MEDAL, Cochrane subset. Wang & Chen, *Patterns* 7:101519 (2026) |

---

## 0. What I have and haven't seen

I have read the MEDAL paper, including its Table 1 (per-class results) and Table 6 (context ablations). The class counts and baseline figures quoted below come from there. I have not run any model on the study sample, and I have not looked at any model output for it.

I have inspected the structure of the Cochrane file (columns, labels, review identifiers, versions, the `notes` field of the no-evidence items). That touches the data, not model behaviour. What I found is summarised in section 3 and the registration log, and it changed the design in two places: the public file's `abstract` and `publication_year` columns are empty for every row, so abstracts and years are fetched from PubMed by DOI; and the file has one question per DOI, with many reviews appearing in several versions, so I sample at most one question per review.

Still to do before lock, again without any model: fetch the PubMed metadata, and check my search-date extraction by hand on 50 abstracts (section 4). The results go into the registration log. Nothing else happens before lock.

One thing I did look at is how the generator's own supporting notes read for the no-evidence items (about a third say that no eligible studies were found). I describe it in section 10 because it shapes one planned analysis.

After lock, and before the main run, I will run a 50-question pilot drawn separately from the main sample. It tests the pipeline and feeds the power simulation. Pilot questions are excluded from the 900.

If any of this turns out to be untrue by the time I lock, I will say so here.

## 1. Why I'm doing this

MEDAL reports that giving GPT-4o-mini PubMed abstracts lifts answer accuracy from 60.3% to 79.9%. That is one number for three very different classes of question. In the Cochrane file, 5,167 of 8,530 questions (60.6%) are "yes", so a model that always says yes already scores 60.6% and has a macro-F1 of about 0.25. The paper doesn't report this baseline. It also reports that "no evidence" is the hardest class (F1 0.18 for GPT-4o-mini, 0.33 for GPT-5), and then never asks what retrieval does to it.

That second point is the one I care about. When a model reads retrieved abstracts, does it get better at noticing that the literature can't answer the question, or does it just find something to lean on? I don't know, and I suspect the answer depends on how the evidence is selected, so I want to measure it class by class.

There is a second problem. A MEDAL label of "no evidence" means the review's authors, at the time they wrote it, found nothing conclusive. PubMed today contains studies published after that. A model that retrieves one of them and answers "yes" is scored wrong, but may be scientifically right. I call an evaluation *time-valid* when retrieval is limited to what the review authors could have seen. I'll test how much of any apparent harm from retrieval disappears when it is.

I'm aware that parts of this have been touched by others: harm from retrieval has been shown before, and noise controls exist. I don't claim novelty for those. What I think is open is the baseline-aware re-evaluation of MEDAL and the temporal control. The search behind that statement was limited, and the related-work table will be completed by reading the papers in full (section 14).

## 2. Hypotheses

The primary outcome is the AUROC of P(no evidence), defined in section 7. All hypotheses are about one model, M1. The same analysis is repeated on M2 as a replication, not as extra tests.

| ID | Hypothesis | Comparison | Supported if |
|---|---|---|---|
| H1 | With retrieval restricted to evidence available at review time (MedCPT, k = 10), the model gets worse at identifying "no evidence" questions than with no context. | C10 vs C0 | $\Delta\text{AUROC}_{NE} < 0$, Holm-adjusted p < 0.05 |
| H2 | The opposite: retrieval helps the model recognise missing evidence. This is the other tail of the H1 test, not a separate test. | C10 vs C0 | $\Delta\text{AUROC}_{NE} > 0$, Holm-adjusted p < 0.05 |
| H3 | If H1 holds, it holds because of what the context says, not because it is long or noisy: a hard-negative context of matched length (section 5) does not produce the same drop. | C10 vs C14 | $\text{AUROC}_{NE}(C10) < \text{AUROC}_{NE}(C14)$, Holm-adjusted p < 0.05 |
| H4 | Retrieval without a date limit hurts "no evidence" detection more than date-limited retrieval, because newer studies resolve questions the review left open. | C15 vs C9 (k = 5) | $\Delta\text{AUROC}_{NE} < 0$, Holm-adjusted p < 0.05 |
| H4b | The H4 effect grows with the time between the review's search date and today. Secondary. | C15 vs C9 | $\beta_1 < 0$ in the model in section 8.4 |

H1/H2, H3 and H4 are the three primary tests. Holm correction is applied across these three. Everything else is exploratory and will be labelled that way in the paper.

H3 is only interpreted if H1 is supported. If H1 is not supported I'll still report the H3 estimate, with a note that it has no hypothesis behind it.

**Why k = 10 for H1 and k = 5 for H4.** Neither value was chosen by looking at results; no results exist. For H1 my working idea is that the more retrieved material the model reads, the more it has to lean on, so the largest k should show the biggest effect and give the test its best power. For H4 I use k = 5 for a different reason: the date-restricted pool shrinks for older reviews, and at k = 10 some restricted contexts may be shorter than the unrestricted ones, which would confound the contrast with context size. Five is the largest k at which I expect nearly every question to get a full context in both conditions. I'll report the share of questions with a full k-document context in each condition, and if C9 falls below 90% I'll say so next to the H4 result. The other values of k are exploratory (section 10).

Section 11 lays out in advance what I will conclude under each combination of outcomes.

## 3. Data and sampling

**Source.** The Cochrane subset of MEDAL (`QA-systematic-review.jsonl`, Hugging Face `cwang271/MEDAL`), covering reviews from 2010 to May 2025. The paper reports 8,530 questions: yes 5,167, no 2,309, no evidence 1,054. The file I hold has 8,533 rows (yes 5,168, no 2,309, no evidence 1,054, and 2 rows with an empty answer), which is within three rows of the paper. Every row has its own DOI, so there is exactly one question per DOI. The class proportions $\pi_c$ used for prevalence weighting are computed from the eligible rows below, and are about 0.606, 0.271 and 0.124.

**Eligibility.** A question is eligible if it has a label in {yes, no, no evidence}; a DOI containing a Cochrane CD number; and a PubMed record, found by DOI, with a non-empty abstract and a publication year. The second rule removes 43 rows: Cochrane methodology reviews (MR numbers) and HTA monographs, which are not intervention reviews. That leaves 8,488 rows before the PubMed step (yes 5,138, no 2,301, no evidence 1,049), spread over 7,111 distinct CD numbers. The PubMed step then removes 41 more rows (8,450 of 8,490 CD-DOIs were found; 8,447 of the eligible rows have a non-empty abstract), leaving yes 5,115, no 2,288, no evidence 1,044. The exact count after the year rule goes in the registration log.

**Versions.** 1,223 CD numbers appear under more than one DOI (.pub2, .pub3 and so on), often with near-identical questions, and 158 questions are repeated verbatim across versions. A review and its updates are the same unit for my purposes. The unit of independence is therefore the CD number, and every exclusion rule in section 4.2 removes all versions of the review.

**Draw.** 300 questions per class, 900 in total.

- Stratified by class and by tertile of review year (nine strata of about 100). The tertile cut points are computed on all eligible rows pooled, before the draw. This matters: no-evidence reviews are newer in the file (median year 2018, against 2016 for yes and no), and without the stratification year would be tangled up with class.
- At most 1 question per review (CD number) across the whole sample. When a review has several eligible rows, the seeded draw picks one. A dry run on the real file with a throwaway seed reaches 300 per class from 900 distinct reviews, so the cap is feasible; the no-evidence class has 964 distinct reviews.
- If 300 no-evidence questions can't be reached under that cap after the PubMed step, I relax it to 2 per review, then 3. If that still fails, I take every eligible no-evidence question and shrink the other two classes to match. Whatever happens gets reported.
- Seed: 20261028, the planned lock date as an integer (YYYYMMDD), fixed before the draw. The sample was drawn on 26 Oct 2026, before any model run. If the lock slips by a day or two, the seed and the manifest stay as they are; I will not redraw. I chose it this way so nobody, me included, can say I shopped for a draw.
- The sampled question IDs are written to `manifest.csv`, and its SHA-256 hash goes in the registration log before any model run.

**Reduced design.** If at the second gate (10 Nov) the pipeline isn't ready for 900, I drop to 200 per class. I keep all 17 conditions; I do not drop conditions to save time. This is the only pre-approved change to the sample.

## 4. Review date and retrieval

### 4.1 The cutoff date

Each question gets a cutoff date $T_i$, the date after which evidence was not available to the review's authors.

1. **Search date.** Cochrane abstracts have a "Search methods" section with the date of the last search. The abstract and year come from PubMed, fetched by DOI with the released script, because the public MEDAL file leaves both empty. I extract the date with a fixed regular expression (in `src/dates.py`, frozen at lock) and take the latest date in that section. If only a month and year are given, I use the last day of that month. A Cochrane "Issue n, year" is read as that issue's month. If only a bare year is found ("1966 to 2008"), I use 31 December of that year and mark `date_precision = year`; a bare year never outranks a month-level date in the same year. Week formats ("August Week 3 2014", "2018 week 39") are read as that week's date. A sentence that says a later search was not used ("not fully incorporated", "awaiting classification", "will be incorporated") is ignored, because the review's evidence stops before that search. The extraction code is released with the paper (the same functions as in the audit script).
2. **Fallback.** If no search date can be extracted, I use the review's publication date from its PubMed record and set `date_fallback = 1`.
3. **Check.** I verify the extraction by hand on 50 abstracts before lock. I need at least 45 correct (same month). If I get fewer, I revise the regex and check a fresh 50. If it still fails, every question uses the publication date and H4b is demoted to descriptive.
4. **Sensitivity.** All primary analyses are repeated without the `date_fallback = 1` questions.

**Coverage as fetched (25 Oct 2026).** Of the 8,447 eligible rows with an abstract, 8,377 (99.2%) carry a "SEARCH METHODS" or "SEARCH STRATEGY" heading, 62 more are read from sentences that mention a search, and 8 have nothing. The extractor finds a search date for 8,294 (98.2%). By precision: day 4,147, month 3,703, issue 367, week 45, bare year 32. The other 153 rows will use the fallback and be flagged. The median gap between publication year and search year is one year, and 10.8% of reviews have a gap of two years or more, which is the stretch of time I'm trying to protect with the restricted conditions. The hand check on 50 random rows gave 48 correct. The two misses (CD013030, CD012583) had a later search whose studies were not incorporated into the review; I added the rule above for exactly this. The two texts now give the right date, and the audit was rerun with the final rule (coverage unchanged). I did not draw a fresh 50 after the change.

### 4.2 Retrieval pipeline

Retrieval runs against live PubMed through E-utilities. Every query and every returned PMID list is cached with a timestamp, and the cache is released with the paper. I'm not freezing a full PubMed snapshot; that is too heavy for this project, and I'll say in the limitations that PubMed drifts.

1. **Query.** M1 writes one Boolean PubMed query per question, from the prompt in Appendix A.4, at temperature 0. If the date-restricted search returns fewer than 10 records, a pre-set fallback query is used (the question text with stop words removed).
2. **Pool.** Top 100 records in PubMed Best Match order that have an abstract. In restricted conditions the pool is filtered to entry date ≤ $T_i$. In unrestricted conditions there is no date filter.
3. **Exclusions.** Remove the source review (every version, protocol and update of the same CD number), any record with the same DOI, and near-duplicates (MinHash over 5-word shingles, Jaccard ≥ 0.8 against the review abstract).
4. **Ranking.** Plain conditions use Best Match order. MedCPT conditions re-rank the 100 with the MedCPT cross-encoder.
5. **Context.** The top k abstracts, each as title plus abstract truncated to 400 tokens, in rank order.
6. **Leakage test.** A hard assertion in the pipeline: in any restricted condition, no retrieved record has an entry date after $T_i$. Separately, I audit 50 random retrieved documents by hand for date or source-review leakage and report the result.

The cutoff uses PubMed entry date, not publication date, because publication dates are often set to a future issue.

**Who writes the queries, and what that means.** The retrieval step runs once per question. M1 writes the query, and the resulting pools and contexts are then shared with M2, so both models read exactly the same text in every condition. The cost is a coupling I can't remove: retrieval quality is tied to how well M1 writes queries, and M1 is also one of the models being evaluated. To limit this, the query is generated from the question text alone (no label, no answer, no context) at temperature 0. I also run a small check (section 10): on 150 random questions, M2 writes the queries instead, and I compare the retrieved sets and the direction of the C10 effect.

**C2 is different.** C2 mimics the MEDAL setup as closely as I can infer: the question text as the query, Best Match, top 3, no date limit, source review excluded. It is a replication check against Table 6, not a controlled comparison with the other conditions.

## 5. Conditions

Seventeen conditions, each run on all 900 questions for both models.

| ID | Context | k | Purpose |
|---|---|---|---|
| C0 | None | n/a | Baseline |
| C1 | The review's own abstract | n/a | Oracle. Control only; labels were generated from this text, so it is close to leakage |
| C2 | PubMed Best Match, unrestricted, question text as query | 3 | Replication of the MEDAL setting |
| C3 to C6 | PubMed Best Match, restricted to $T_i$ | 1, 3, 5, 10 | Plain retrieval |
| C7 to C10 | MedCPT re-ranking, restricted to $T_i$ | 1, 3, 5, 10 | Main retrieval condition (C10 for H1) |
| C11, C12 | Random abstracts, total length matched (±10%) to the question's restricted MedCPT context of the same k (C8 for k = 3, C10 for k = 10), drawn from other questions' retrieved pools | 3, 10 | Length control |
| C13, C14 | Hard negatives: records ranked 51 to 50+k in the restricted MedCPT list, length-matched to C8 (k = 3) and C10 (k = 10) as described below | 3, 10 | Same topic, low relevance, same length. Content control for H3 |
| C15, C16 | MedCPT re-ranking, unrestricted | 5, 10 | Temporal contrast (H4: C15 vs C9) |

C11/C12 draw from a fixed seed. For C13/C14, the k hard-negative abstracts are taken in rank order and then truncated, each in proportion, so that their total token count does not exceed that of the matched MedCPT context. If the hard-negative total is already shorter, it is left alone. I report the mean length ratio (hard-negative over MedCPT) for each condition, and repeat the H3 test adjusting for the per-question length difference as a sensitivity analysis. The H3 result is read together with that ratio. If a question has fewer than k records in a condition, it gets what exists and `n_docs` is recorded; if there are none, the prompt carries the line "No articles were retrieved." and the question stays in the analysis.

## 6. Models, prompts and scoring

**Models.** Two open-weight, instruction-tuned models of 7 to 8 billion parameters. Required: logits accessible, context window of at least 16k tokens, and a training cutoff documented. M1 = `meta-llama/Llama-3.1-8B-Instruct`, revision `0e9e39f249a16976918f6564b8830bc894c89659`. M2 = `Qwen/Qwen2.5-7B-Instruct`, revision `a09a35458c702b33eeacc393d103063234e8bc28`. Both read from the Hugging Face API on 26 Oct 2026. Qwen does not publish an exact training cutoff; I note this in section 14. M1 also writes the retrieval queries for both models (section 4.2). The choice is made at lock and not changed after.

**Prompts.** The primary prompt P1, the paraphrases P2 and P3, the query prompt and the screening prompt are in Appendix A. They are frozen at lock. P2 and P3 are run only on C0, C10 and C16.

C0 and the retrieval conditions differ only by the context block and its one-line instruction. I note this because the instruction itself could move predictions.

**What "no evidence" means in the prompt.** I read MEDAL's public code before writing this. Questions were generated by GPT-4o (temperature 0.2) from a PubMed abstract (the script asks for two to four questions per abstract; the released Cochrane file has one per DOI), with the answer constrained to Yes / No / No Evidence and no definition of any of the three. A second GPT-4o pass then "refined" each item and attached a short supporting quote. MEDAL's own evaluation prompt also lists the three values without defining them and asks for a JSON object with extra fields. Two consequences. First, the definitions in my prompt are mine, not MEDAL's, and my prompt is not a replication of theirs (it asks for the label only). I define "no evidence" as a statement about the literature and tell the model explicitly not to use it just because the supplied text is silent. Second, and more important, "No Evidence" in MEDAL has no operational meaning beyond what GPT-4o decided, and it may sometimes mean "this abstract does not address the question" rather than "the review found the evidence insufficient". Those are different things, and retrieval could affect them differently. That is why section 9 sorts the no-evidence questions by type and section 10 repeats the main tests on the clean type. MEDAL's retrieval experiments are not in the public repository, which is why C2 is an approximation.

**Scoring.** No free generation. For each question I compute the log-probability of each of the three label strings (followed by the end-of-turn token, since "no" is a prefix of "no evidence") and normalise with a softmax across the three. This gives $p(\text{yes}), p(\text{no}), p(\text{NE})$. The predicted label is the argmax. I will not tune thresholds on the study data. I'll report the share of probability mass the three strings capture; if it is under 0.9 for more than 5% of outputs in a condition, I flag the condition.

## 7. Outcomes

**Primary.** $\text{AUROC}_{NE}$: the AUROC of $p(\text{NE})$ for separating the 300 no-evidence questions from the 600 yes/no questions. It does not depend on a decision threshold, which is why I chose it: retrieval can shift how often a model says "no evidence" without changing how well it ranks the questions.

**Secondary (all conditions).**

- Per-class precision, recall and F1; macro-F1; the majority-class baseline.
- Prevalence-weighted accuracy, $\text{Acc}_\pi = \sum_c \pi_c \, \text{Recall}_c$, using the full-Cochrane proportions above, so it is comparable with the paper's 60.3%.
- Rescue/harm transition counts against C0, by class (Appendix B).
- False-abstention rate: yes/no questions predicted as "no evidence".
- Mean $p(\text{NE})$ among no-evidence questions and among the other two classes, separately. This shows where a change in AUROC comes from.

**Descriptive.** Brier score and negative log-likelihood (prevalence-weighted), and expected calibration error with 10 equal-mass bins. ECE on a balanced sample is noisy and I won't lean on it.

## 8. Analysis plan

**8.1 Primary tests.** For each of H1/H2, H3, H4 the statistic is the paired difference $\hat\Delta$ in $\text{AUROC}_{NE}$ between the two conditions. Uncertainty comes from a cluster bootstrap over reviews: $B = 10{,}000$ resamples, each drawing reviews with replacement, keeping all their sampled questions, and recomputing both AUROCs on the same draw (ties in $p(\text{NE})$ count as half). That gives replicates $\Delta^*_1, \dots, \Delta^*_B$. The two-sided p-value is

$$p = \min\Big\{1,\; 2\cdot\min\Big(\tfrac{1 + \#\{b:\Delta^*_b \le 0\}}{B+1},\; \tfrac{1 + \#\{b:\Delta^*_b \ge 0\}}{B+1}\Big)\Big\}.$$

This is the usual percentile-bootstrap inversion, so the 95% percentile interval excludes zero exactly when p < 0.05 before correction. The three p-values are then Holm-adjusted at family-wise level 0.05 (compare the smallest to 0.05/3, the next to 0.05/2, the largest to 0.05). A hypothesis counts as supported only if its adjusted p is below 0.05 and the sign of $\hat\Delta$ matches the hypothesis. I report the unadjusted 95% interval with each estimate. A resample in which either class lacks observations is discarded and redrawn; I'll report how often that happens (it shouldn't).

**8.2 Floor rules.** Two, fixed now.
(a) If $\text{AUROC}_{NE}(C0) < 0.55$ for a model, the model has little ability to detect the class without help, and a "drop" under H1 is uninformative. H1 is then reported as uninformative for that model, and only the H2 direction is discussed.
(b) If argmax recall for no-evidence in C0 is under 0.10, all recall-based statements about that class are descriptive.

**8.3 Binary and per-class comparisons.** Exact McNemar tests on paired correct/incorrect outcomes, exploratory, no multiplicity correction, reported as such.

**8.4 H4b.** For each no-evidence question $i$, let $d_i = p_{C15}(\text{NE}) - p_{C9}(\text{NE})$. Fit $d_i = \beta_0 + \beta_1 g_i + \varepsilon_i$ with $g_i = 2026 - \text{year}(T_i)$, by GEE with an exchangeable working correlation clustered on review. H4b is supported if $\beta_1 < 0$ at the 0.05 level. A log-transformed $g_i$ is a sensitivity analysis.

**8.5 Replication on M2.** Same tests. A result is called *replicated* if M2 has the same sign and Holm-adjusted p < 0.05; *same direction* if the sign agrees but p doesn't pass; *not replicated* otherwise.

**8.6 Power.** With 300 no-evidence and 600 other questions, my rough expectation is a standard error for a paired $\Delta\text{AUROC}$ of 0.015 to 0.02, so a minimum detectable difference near 0.05 at the Holm-adjusted level. This is a back-of-envelope figure. I'll check it by simulation using the pilot and write the result into the amendment log; if it says 900 is underpowered, the only allowed response is to report that fact, not to enlarge the sample after seeing outcomes.

**8.7 Invalid outputs.** Scoring is by log-probability, so malformed outputs shouldn't occur. Retrieval failures and truncation are logged per condition and per question and reported.

## 9. Checking the labels

MEDAL's labels were produced by an LLM, and the oracle result suggests they follow the abstract closely. I don't want my conclusions to rest on labels I haven't looked at.

**Stage 1 (automatic, before the physician).** A strong model, different from M1, M2 and GPT-4o (which generated MEDAL), reads each sampled question, its source review abstract and its label, and answers whether the abstract supports the label (prompt A.5). This is a screen, not ground truth. Questions it flags are removed in a sensitivity analysis. For no-evidence questions it also records why: (a) the abstract says the evidence is insufficient or absent, (b) the abstract doesn't address the question, (c) something else. This matters because MEDAL never defined the label (section 6) and (b) is not the same thing as (a). Judge: `claude-sonnet-5-5` through the Anthropic API, temperature 0, run date logged (TODO(lock): confirm model string on the run date). It is from a different family than M1, M2 and GPT-4o. I disclose in the paper that the judge is a commercial model and was used only as a screen.

**Stage 2 (physician).** A physician arranged through Dr. Eslami labels 60 questions blind to the dataset label and to every model output, using the review abstract only. For items the dataset calls no-evidence, the physician also notes whether the abstract says the evidence is insufficient or is simply silent on the question.

- 30 *transition* questions: dataset label is no-evidence, M1 predicts "no evidence" in C9, and M1 predicts something else in C15. If there are more than 30, 30 are drawn at random (seeded). If fewer, I take all of them and fill the rest at random.
- 30 *random* questions, 10 per class.
- The list is hashed and frozen before the physician sees it.

I report Cohen's κ between the physician and the dataset label with a confidence interval, overall and per class. With 60 items and agreement near 0.8, the 95% interval is about ±0.10. If the physician agrees with the dataset on fewer than 60% of the no-evidence items, label quality becomes a main result of the paper and conclusions about the no-evidence class are stated as conditional on it.

**Stage 2b, if the physician has time.** For the transition questions, the physician is shown the post-cutoff abstracts that appeared in C15 but not in C9 and asked whether they change the answer. This is the most direct test of the temporal story, but it is optional and secondary.

Dr. Eslami told me (25 Oct 2026) that a physician colleague can't be arranged soon and that I should plan around the small set available now; she will coordinate the physician for the final evaluation. So the audit runs after the main results, and the design does not depend on it. If the physician audit isn't finished before I submit, I will say so in the paper, report only stage 1, and state it as a limitation. It will not be described as validated.

## 10. Exploratory analyses

All labelled exploratory in the paper, no correction.

- Trend in $\text{AUROC}_{NE}$ against $\log k$ for C3 to C6 and C7 to C10.
- C2 against C0: raw accuracy and $\text{Acc}_\pi$, shown next to MEDAL's 60.3% to 79.9%.
- Rate of "no evidence" predictions by decile of top-1 re-ranker score. This is my attempt to separate "retrieval failed" from "the evidence doesn't exist".
- A descriptive typing of the no-evidence items by the generator's own supporting note, with a fixed keyword rule (section 6 of `audit_medal.py`, frozen at lock): N1, the note says no eligible studies were found (34.5% of the 1,049 eligible items in the file I inspected); N2, the note describes an inconclusive, low-certainty or non-significant result (43.5%); the rest are mixed or unclear. N1 are reviews with nothing to find, which is where newer studies are most likely to change the answer, so I expect H4 to be strongest there. H1 and H4 are repeated within N1 and within N2. This is exploratory and I'm writing the expectation down so it can't be claimed afterwards.
- H1 and H4 repeated on the no-evidence questions the stage-1 screen types as (a) only, together with the share of each type. If most no-evidence labels turn out to be type (b), the main analysis stays as registered and I say plainly what it measures.
- Prompt sensitivity and prompt tuning: P1 vs P2 vs P3 on C0, C10 and C16; do the signs of the primary effects hold? Added after Dr. Eslami's suggestion (28 Oct 2026, before lock): a fourth prompt P4 is P1 plus three worked examples (one per class). The examples come from eligible questions outside the manifest and outside the pilot, chosen by a seeded draw (seed 20261028) and frozen at G2 (10 Nov), before any main run. P4 runs on the same three conditions. I report how much P4 moves $\text{AUROC}_{NE}$ in C0 and C10, and whether the sign of the C10 vs C0 difference changes. This is exploratory and does not enter the three primary tests. Trained (soft) prompt tuning is not part of this study (see the last item of section 14).
- Review search year against each model's training cutoff (before vs after), for contamination.
- The sensitivity analyses named above: without `date_fallback`, without stage-1 flags.
- Query-author swap: on 150 randomly chosen questions, M2 writes the queries instead of M1. I report the overlap of the top-10 retrieved records (Jaccard) and whether the sign of the C10 effect on those questions is the same.
- The H3 length-difference adjustment described in section 5, and the share of questions with a full k-document context in each condition.
- C1 is reported but excluded from every inference.

## 11. How I'll read the results

Fixed in advance so I can't reinterpret later.

| H1 | H3 | H4 | What I will say |
|---|---|---|---|
| Supported | Supported | Supported | Retrieval hurts no-evidence detection because of its content, and part of that is an evaluation artifact from newer evidence. |
| Supported | Supported | Not supported | The harm is real and not explained by newer evidence. |
| Supported | Not supported | any | The drop is explained by context size or noise, not by relevant content. |
| Not supported (H2 supported) | n/a | any | Retrieval helps the model recognise missing evidence. |
| Not supported, no difference | n/a | Supported | Date-limited retrieval is harmless, but unrestricted retrieval hurts, and likely mismeasures. |
| Not supported, no difference | n/a | Not supported | No detectable effect on this class with these models. Reported as a null result with the interval. |
| Uninformative (floor rule) | n/a | any | The models can't detect the class unaided. I report what retrieval does to the other classes and stop short of claiming anything about this one. |

A null is a result. The paper is worth writing in every row of this table.

## 12. Changes after lock

Every change goes in `AMENDMENTS.md` with the date, the reason, and whether I had seen any outcome data when I made it. Anything affecting a primary hypothesis after the first main run is labelled post hoc in the paper. The one pre-approved change is the reduced design in section 3.

## 13. Reproducibility

- A single config file defines each run; `run_id` is its hash. Every number in the paper comes from a script and a `run_id`.
- Fixed seeds everywhere. Model revisions, inference library version and hardware are recorded.
- Tests that must pass before the main run: date filter and leakage assertion, label scoring (including the prefix case), probability-mass check, de-duplication, regex extraction.
- I use AI coding assistants to draft code. Nothing goes into the pipeline unless I've read it and a test covers it. AI assistance will be declared in the paper.
- Retrieval cache (queries, PMIDs, timestamps), the manifest, prompts and analysis code will be released. The dataset licence is listed as "other"; TODO(lock): check what I'm allowed to redistribute.

## 14. Limits I already know about

- The labels come from an LLM, were never defined, and were "refined" by the same model family that generated them. I check them, but only on a small sample.
- The abstracts I fetch now may differ slightly from the ones MEDAL's authors used (PubMed records get corrected), and the public file doesn't ship its abstracts, so I can't compare them.
- One benchmark, one document source (Cochrane), and two small open models. A second dataset (PubMedQA, same design) is the condition for aiming higher than a workshop paper.
- M1 writes the queries that both models read, so retrieval quality is coupled to one of the models under test (section 4.2). The swap check on 150 questions looks at this, but doesn't remove it.
- Length matching for the control conditions is approximate (±10% for random abstracts, truncation for hard negatives), so H3 is read alongside the reported length ratio.
- Retrieval depends on the query, and PubMed changes over time. The cache makes it auditable, not reproducible from scratch.
- Cochrane reviews are almost certainly in the models' pretraining data. C0 may partly measure memory.
- Search-date extraction can be wrong. That's why there is a check and a sensitivity analysis.
- Qwen2.5 has no officially published training cutoff, and Llama-3.1's (December 2023) falls before some of the reviews. Memorisation of post-cutoff reviews is therefore possible for either model. The no-context condition C0 shows how much the models already know, and I report it next to every result.
- The stage-1 judge is a commercial model I can't inspect. It is a screen only, and its flags are tested in a sensitivity analysis.
- The physician audit may not finish in time.
- My novelty search was a skim of about eight papers. The related-work table will not be final until I've read at least ten in full (target: 3 Nov). The table link is added to this file as a documentation-only amendment, since it changes nothing in the design.
- A second phase is planned: a learned retrieval-side component (for example an auto-encoder over retrieved-context features that feeds no-evidence detection, suggested by Dr. Eslami on 28 Oct 2026), and possibly trained (soft) prompt tuning and adaptive choice of k. None of it is part of the present study. Its protocol is written and registered separately by 10 Nov (G2), before the main run starts, so it is written without seeing any primary result. It would train only on questions outside the manifest and the pilot (and outside the manifest's review numbers) and be evaluated on the manifest. Only its training and evaluation runs come after Phase 1, and the paper will say so.

## 15. Timeline

| Gate | Date | Condition |
|---|---|---|
| G1 | 30 Oct | This file locked (git tag and OSF); prompts frozen |
| G1b | 3 Nov | Related-work table finished (at least 10 papers read in full); link added by amendment |
| G2 | 10 Nov | MEDAL baseline reproduced (C0, C2 on M1); search-date accuracy ≥ 90%; manifest hashed; leakage tests pass; pilot and power simulation done; P4 examples frozen; **Phase 2 protocol written and registered separately, before the main run** |
| G3 | 24 Nov | 17 conditions × 900 questions on M1; P2, P3 on three conditions |
| G4 | 1 Dec | Primary tests; M2 replication; transition tables; stage-1 screen; physician list frozen |
| G5 | 8 Dec | 4 to 6 page draft to Dr. Eslami |
| Phase 2 | Dec to Jan | Run the separately registered Phase 2 (learned component), then the full paper |
| P | with Dr. Eslami | Physician audit, ideally before submission |

## 16. Roles

Hooman Soleymani: design, code, analysis, writing; first author. Dr. Eslami: supervision, review, correspondence with the journal. Dr. Eslami confirmed on 25 Oct 2026 (message) that I am first author, that she handles the journal, and that she will arrange a physician colleague for the final evaluation, not in the short term. The physician rater and anyone else who contributes will be named in the paper. Funding: none (TODO(lock): confirm). Competing interests: none declared.

## 17. Registration log

| Item | Value |
|---|---|
| Lock date | TODO(lock) |
| git commit and tag | TODO(lock) |
| OSF registration | TODO(lock) |
| `manifest.csv` SHA-256 | `ad89017e1fea0ef482497cbc4220e72a9e00cea09b2c82e44a9252a867eb6cd0` (seed 20261028; 900 questions from 900 distinct reviews, 300 per class, 100 per stratum, cap 1 per review; 9 with `date_fallback = 1`; drawn 26 Oct 2026 before any model run). no redraw if the lock date moves (section 3) |
| Dataset structure check (25 Oct 2026) | 8,533 rows; 2 empty labels; 43 non-CD DOIs; 8,488 eligible (yes 5,138 / no 2,301 / NE 1,049); 7,111 CD numbers; `abstract` and `publication_year` empty in the file; dry-run draw feasible with 1 per review |
| PubMed fetch (25 Oct 2026) | 8,450 of 8,490 CD-DOIs found (99.5%); 40 not found; 8,447 eligible rows with an abstract (yes 5,115 / no 2,288 / NE 1,044) |
| Search-date coverage (26 Oct 2026, final rule) | 8,294 of 8,447 extracted (98.2%); day 4,147 / month 3,703 / issue 367 / week 45 / year 32; 153 to fallback |
| Search-date check (n correct / 50) | 48 / 50 (threshold 45). Both misses were "later search not incorporated"; rule added, those two re-extracted correctly. No fresh 50 drawn after the rule change |
| M1, M2, judge model, revisions | M1 Llama-3.1-8B-Instruct, M2 Qwen2.5-7B-Instruct, judge claude-sonnet-5-5 (API); revisions Llama `0e9e39f249a16976918f6564b8830bc894c89659`, Qwen `a09a35458c702b33eeacc393d103063234e8bc28` (Hugging Face, 26 Oct 2026) |
| Supervisor suggestions (28 Oct 2026) | Prompt tuning: P4 added to section 10. Learned retrieval-side component (auto-encoder): Phase 2, registered separately before the main run (section 14). |
| Supervisor feedback | 25 Oct 2026, by message: she reviewed my plan, called the path complete and good and the hypotheses realistic. She had not yet seen this file. Approval of this version: TODO(lock): date |

---

## Appendix A. Prompts

### A.1 Primary prompt (P1)

```
You are a clinician-researcher answering a question the way a systematic
reviewer would at the time the evidence was assessed.

Answer with exactly one of:
  yes          the evidence indicates the answer to the question is yes
  no           the evidence indicates the answer to the question is no
  no evidence  the evidence is too sparse, too weak or too inconsistent to
               answer the question either way

Judge the state of the published literature.

{CONTEXT BLOCK, retrieval conditions only}

Question: {question}
Answer:
```

The context block, when present:

```
Articles retrieved from PubMed. They may or may not be relevant; use them as
you see fit. Do not answer "no evidence" merely because the articles do not
mention the answer.

[1] {title}. {abstract}
[2] ...
```

For C1 the block holds the single review abstract. If nothing was retrieved it holds "No articles were retrieved."

### A.2 Paraphrase P2

```
Below is a clinical question. Decide which of three statements best describes
the published evidence at the time a systematic review would have been written:
  - no evidence: the evidence cannot settle the question
  - yes: the evidence supports "yes"
  - no: the evidence supports "no"

{CONTEXT BLOCK}

Question: {question}
Answer:
```

### A.3 Paraphrase P3

```
Imagine you are writing the conclusion of a Cochrane review on the question
below. Your options are "yes", "no", or "no evidence" (the available evidence
is insufficient to conclude). Choose the one that fits the evidence in the
literature.

{CONTEXT BLOCK}

Question: {question}
Conclusion:
```

### A.4 Query prompt

```
Write one PubMed search query that would find primary studies and systematic
reviews relevant to the question below. You may use Boolean operators, MeSH
terms and title/abstract field tags. Do not add any date limit. Return only the
query.

Question: {question}
```

### A.5 Label screening prompt (stage 1)

```
Below are a clinical question, the abstract of the systematic review it was
generated from, and a proposed answer (yes / no / no evidence).

Does the abstract's conclusion support the proposed answer?
Reply with one word: supported, unsupported, or unclear.

If the proposed answer is "No Evidence", add a second line with one letter:
  a  the abstract says the evidence is insufficient, absent or inconclusive
  b  the abstract does not address the question
  c  something else

Question: {question}
Abstract: {review abstract}
Proposed answer: {label}
```

## Appendix B. Transition definitions

For a condition $c$ against C0, using argmax labels and the dataset label as truth:

- **Rescue:** wrong in C0, right in $c$.
- **Harm:** right in C0, wrong in $c$.
- **Net:** rescues minus harms.

Reported per dataset class (yes, no, no evidence), each as counts out of the 300 in that class, together with a McNemar exact p-value (exploratory).
