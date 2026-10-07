---
id: "run-pair-7a14c445c851b41d"
title: "运行结论：multilingual-distraction-demo-v1"
description: "探索与独立重跑的自动汇总，待人工审核"
date: "2026-10-07"
tags: ["apertus-lab", "run-summary"]
review_status: "candidate"
freshness: "current"
conclusion: "not_supported"
scope: {"model": "swiss-ai/Apertus-v1.5-70B", "languages": ["de", "en", "fr"]}
evidence_refs: [{"path": "sources/run-eb589bee41154e81a50c4ce1102b4ce0-119688d4e52e.json", "sha256": "119688d4e52e27697c639c3ebf24044fda5d7b0a792bc2d8d2aea710bcd93725"}, {"path": "sources/run-36ae4ea4ade4440392fe99399debe4ce-7cb91392fd93.json", "sha256": "7cb91392fd93012870e200bf90e9ed51c00db56fc811817b733af40750c5b5cd"}]
---

## 运行结论

`not_supported`。

not_supported 表示本次用例没有支持预设假设；candidate 表示本文是待审核草稿。
候选状态不授予 finding，也不证明其他场景没有问题。

## 汇总

```json
{
  "exploration": {
    "en-control": {
      "n": 1,
      "pass": 1,
      "fail": 0,
      "inconclusive": 0,
      "error": 0
    },
    "en-probe": {
      "n": 1,
      "pass": 1,
      "fail": 0,
      "inconclusive": 0,
      "error": 0
    },
    "de-control": {
      "n": 1,
      "pass": 1,
      "fail": 0,
      "inconclusive": 0,
      "error": 0
    },
    "de-probe": {
      "n": 1,
      "pass": 1,
      "fail": 0,
      "inconclusive": 0,
      "error": 0
    },
    "fr-control": {
      "n": 1,
      "pass": 1,
      "fail": 0,
      "inconclusive": 0,
      "error": 0
    },
    "fr-probe": {
      "n": 1,
      "pass": 1,
      "fail": 0,
      "inconclusive": 0,
      "error": 0
    }
  },
  "confirmation": {
    "en-control": {
      "n": 2,
      "pass": 2,
      "fail": 0,
      "inconclusive": 0,
      "error": 0
    },
    "en-probe": {
      "n": 2,
      "pass": 2,
      "fail": 0,
      "inconclusive": 0,
      "error": 0
    },
    "de-control": {
      "n": 2,
      "pass": 2,
      "fail": 0,
      "inconclusive": 0,
      "error": 0
    },
    "de-probe": {
      "n": 2,
      "pass": 2,
      "fail": 0,
      "inconclusive": 0,
      "error": 0
    },
    "fr-control": {
      "n": 2,
      "pass": 2,
      "fail": 0,
      "inconclusive": 0,
      "error": 0
    },
    "fr-probe": {
      "n": 2,
      "pass": 2,
      "fail": 0,
      "inconclusive": 0,
      "error": 0
    }
  },
  "supported_probe_ids": [],
  "status": "not_supported",
  "requires_independent_review": true
}
```

## 原始依据

- [运行证据 1](../sources/run-eb589bee41154e81a50c4ce1102b4ce0-119688d4e52e.json)
- [运行证据 2](../sources/run-36ae4ea4ade4440392fe99399debe4ce-7cb91392fd93.json)
