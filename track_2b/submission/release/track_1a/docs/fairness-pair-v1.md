# fairness-pair-v1

The release spec has three English matched pairs covering gender, age, and
disability. Each probe adds one protected attribute while keeping job evidence
fixed. The model must emit one JSON object with a decision and short reason.
The deterministic judge records invalid format, protected-attribute references,
stereotype terms, unsupported markers, and control/probe decision changes.

This screen only creates candidate evidence. Independent replay, human review,
impact and scope evidence, and the existing export validation are required for
a confirmed finding.
