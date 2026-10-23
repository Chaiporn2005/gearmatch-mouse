# Retrieval evaluation results

These are real offline retrieval measurements, not LLM answer scores.

| System | Split | Recall@3 | MRR@3 | Constraint violations | Empty-answer accuracy |
|---|---|---:|---:|---:|---:|
| bm25 | dev | 1.000 | 0.938 | 32 | 0.250 |
| bm25 | test | 0.438 | 0.438 | 11 | 0.000 |
| bm25 | all | 0.812 | 0.771 | 43 | 0.167 |
| filtered_bm25 | dev | 1.000 | 1.000 | 0 | 1.000 |
| filtered_bm25 | test | 0.500 | 0.500 | 0 | 1.000 |
| filtered_bm25 | all | 0.833 | 0.833 | 0 | 1.000 |
| hybrid | dev | 1.000 | 1.000 | 0 | 1.000 |
| hybrid | test | 0.969 | 1.000 | 0 | 1.000 |
| hybrid | all | 0.990 | 1.000 | 0 | 1.000 |

## Interpretation and limits

30 author-curated cases (24 answerable, 6 unanswerable), based on this 21-SKU convenience sample. Relevance IDs and rationales are committed before evaluation. They have not been independently annotated. Test contains Thai paraphrases and specific filters. Recall@3 excludes unanswerable cases; their empty-result correctness is scored separately. One test case has 4 relevant products, so its best possible recall@3 is0.75. MRR is truncated at3. No faithfulness, Thai fluency or user preference metric is inferred from these numbers.

Author-curated 20 dev / 10 held-out examples. No tuning on held-out labels. Corpus-sized lexical-vector evaluation, not LLM answer quality. Baseline intentionally ignores metadata filters; filtered BM25 isolates this factor. No claim of statistical significance.

## Per-case failures

- t02: น้ำหนักเบา เล่นเกม -> ['keychron-m3-mini-8k', 'keychron-m2-4k', 'razer-cobra']; expected ['keychron-m2-4k', 'keychron-m2-mini-8k', 'keychron-m3-mini-8k', 'razer-cobra']
