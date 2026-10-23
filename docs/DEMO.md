# GearMatch demonstration and live defence

Target: 3-6 minutes. Use a real running class proxy. Do not replace live answers with recorded JSON.

1. 0:00-0:40 - Explain the user problem,21-SKU mouse-domain corpus and USD reference-price limitation. The drawings are schematic, not product photography.
2. 0:40-1:30 - Ask in Thai for a quiet office Bluetooth mouse under USD30. Set the explicit filters. Show the real answer, tool trace, Pebble76g fact and manufacturer source links. Explain the optional Bolt receiver is not included.
3. 1:30-2:10 - Add Pebble and another mouse to Compare. Show price, connection and unknown attributes. Avoid claiming unknown means false.
4. 2:10-3:00 - Show an impossible requirement: left-handed, Bluetooth, <=80g and <=USD100. A valid result is an explicit abstention. This is a deliberate negative case, not the pre-fix software failure.
5. 3:00-4:00 - Show evaluation/RESULTS.md and run python -m evaluation.run. Explain baseline0.438 versus hybrid0.969 held-out Recall@3, the filtered-BM25 ablation, and why this is not a model-faithfulness score.
6. 4:00-4:50 - Show live-before-fix.json: source IDs and product IDs were confused. Explain the single citation namespace, separate router instruction and bounded validation. Show the latest3/3 live smoke results without claiming broad reliability.
7. 4:50-5:30 - Take a new instructor question, run it and explain one design choice and one evaluation number. State one real limitation.

## Questions to be ready for

- Why are filters applied before ranking? They encode explicit user constraints; unknown values cannot satisfy a required constraint.
- Why RRF instead of averaging raw scores? BM25 and cosine scores have different scales; RRF combines ranks with constant60.
- Is TF-IDF a neural embedding? No. This is a local lexical-vector index and hand-built bilingual expansion, with limitations stated in the report.
- Why is Recall@3 below1 for one fully relevant ranking? That case has4 relevant products, while only3 can be returned.
- Does valid citation ID prove every sentence true? No. It prevents non-retrieved IDs and links to real catalog sources, but free-text faithfulness needs additional review.
- What stops the agent? Validated final output, or a maximum of5 model turns. Repeated queries, disallowed tools and invalid arguments are rejected.
- What did the failed live run teach you? The evidence format exposed two namespaces. Deterministic validation caught the error; a clearer observation contract was more effective than repeated vague repair prompts.
