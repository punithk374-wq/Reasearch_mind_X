# Evaluation with real project data

Run these commands from `researchmind-x/backend`, with your virtual environment
active and the backend running in another terminal. The tools prompt for your
ResearchMind X login password with hidden input. They keep the token in memory;
they never write passwords, tokens or Gemini keys to evaluation output.

## 1. Prepare and freeze a corpus

Use a separate evaluation account for a repeatable experiment. Upload several
related real papers after applying the page-boundary fix. You may add unrelated
distractor papers to make retrieval less trivial. Remove duplicate copies after
checking their contents; record which papers form the corpus. Do not change this
corpus after annotation without exporting and reviewing the labels again.

```powershell
python export_eval_corpus.py
```

This saves `eval/corpus.json`, containing titles, actual paper/chunk IDs, page numbers,
sections and text. It performs no Gemini calls. Read the exported passages while
creating questions. The export intentionally includes all ready papers in that account.
Corpus exports contain document text: share them only where appropriate and retain
them locally for your project evidence. They are ignored by Git.

## 2. Annotate questions before examining retrieval rankings

Copy `retrieval_set.example.json` to `retrieval_set.json`. The example contains
placeholders and is deliberately not runnable. Copy the entire `paper_fingerprints`
object from `corpus.json` and replace every example question and ID with real values.

For each answerable question, list every chunk you judge relevant using
`{"paper_id": <actual ID>, "chunk_id": <actual ID>}` and write a short reference
answer directly from the text. For an unanswerable question, set `answerable` to
`false` and `relevant_chunks` to `[]`, after checking that its answer is absent
from the whole corpus. Do not label results just because a keyword matches or
because the model ranks them highly.

Aim for questions covering methodology, data, findings, limitations and future work
across multiple papers, plus out-of-scope questions. Keep tuning/development questions
separate from the final held-out questions. If you change retrieval settings based on
the final results, describe the run as development rather than a held-out evaluation.
Sparse or incomplete annotations limit the interpretation of precision and recall.

## 3. Run retrieval evaluation

```powershell
python eval_retrieval.py
```

This uses the real `/api/search` endpoint under your account and verifies that the
corpus fingerprints and labelled chunk IDs still match. It reports chunk-level
Hit@1/3/5, Precision@1/3/5, Recall@1/3/5 and MRR@5 for answerable questions only.
Precision uses the requested k as the denominator, even when fewer hits return.
Duplicate hits do not earn extra credit; failed requests count as zero and are
reported. Unanswerable questions are excluded from retrieval relevance averages.

The timestamped `results_retrieval_*.json` contains per-question outputs, dataset
hash, corpus fingerprints, failures and client-side elapsed times. Timing includes
cold-start costs; no warm-up is silently removed. Retrieval calls do not consume
Gemini quota, although the local embedding model must be available.

## 4. Check answers and citations

```powershell
python eval_retrieval.py --with-answers
```

This additionally calls Gemini for every question and consumes API quota. Automatic
checks cover citation indices and the standardized insufficient-evidence response.
They do not establish truth, claim-level coverage or faithfulness. A guarded refusal
after invalid citations is recorded separately from a successful cited answer.

Fill in the generated `human_review_*.csv` yourself against the source passages in
the JSON results. Use a consistent rubric: 1 = mostly unsupported/incorrect,
3 = partly supported/correct, 5 = fully supported/correct. Record reviewer notes
and who rated the outputs. Ratings are blank until a human supplies them. CSV text
is escaped to prevent paper/model text being interpreted as spreadsheet formulas.

## 5. Check candidate gaps

Use actual paper IDs from your corpus (replace 1 and 2 below):

```powershell
python eval_research.py --paper-ids 1 2
```

This runs the real research workflow, saves its evidence and elapsed time, and
creates a blank human gap assessment CSV. Rate evidence support and usefulness,
review every cited paper, and document disagreements with the automated verifier.
A supported gap is still a candidate, not demonstrated novelty. Existing summary
caches may affect latency; the script does not claim to measure cold-cache timing.

Keep the raw outputs and report failed or empty runs honestly. No real project
results can be inferred from the automated regression fixtures in `tests/`.
