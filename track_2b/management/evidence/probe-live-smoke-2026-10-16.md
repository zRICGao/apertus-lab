# Probe live smoke test: 2026-10-16

This is a transport and workflow smoke test against the configured CSCS OpenAI-compatible endpoint. It is not a safety finding and does not estimate model behavior prevalence.

## Configuration

- Model: `swiss-ai/Apertus-v1.5-70B`
- Endpoint: `https://api.inference.cscs.ch/v1`
- Credential: present locally; value omitted
- Store: temporary local `WORKBENCH_DATA`; ignored by Git
- Prompt: synthetic counterfactual nationality-label comparison with fictional applicants
- Languages: `zh`, `en`, `de`

## Results

1. Direct connectivity request returned HTTP 200, model `swiss-ai/Apertus-v1.5-70B`, `finish_reason=stop`, and the expected sentinel response.
2. Probe translation created three independent calls. All three returned HTTP 200 and valid text.
3. After explicit batch confirmation, all three target-model calls completed successfully. The job reached `completed` with 6 calls total and no failed or unknown calls.
4. The result was saved to the local record store.
5. A separately confirmed analysis call completed and was linked to the saved job.
6. The records endpoint and model endpoint did not expose `api_key`.

## Quality observation

The English translation introduced additional concrete details that were absent from the source prompt, including academic transcripts, work experience, and recommendation letters. Chinese and German stayed closer to the source. This is translation semantic drift, not a network or worker failure. For multilingual fairness comparisons, the translation protocol should later add a preservation check or a human review step before dispatching the translated prompt.

## Operational notes

- Worker heartbeat was healthy during the run.
- No automatic retry was observed.
- The live smoke used only one small synthetic job and did not exercise high concurrency.
- Raw responses and the local key remain outside Git; this report intentionally contains no raw model output or credential material.
