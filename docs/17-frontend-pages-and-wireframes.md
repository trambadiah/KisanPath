# Frontend Pages and Wireframes

## Route map

```text
/                         landing
/assistant                voice/text farmer assistant
/schemes                  optional browse/search page
/schemes/[id]             scheme detail/evidence
/demo/evaluation          judge/developer metric explorer
/demo/trajectories        sanitized trajectory viewer
/privacy                   concise privacy/safety explanation
```

Admin ingestion/review screens can live under a separately protected `/admin` area if implemented.

## Landing wireframe

```text
+--------------------------------------------------------------+
| KisanPath                         Language       Try KisanPath |
+--------------------------------------------------------------+
|                                                              |
|  Find the schemes meant for your farm.                       |
|  Speak naturally. We check the published conditions          |
|  and show you why a scheme may match.                        |
|                                                              |
|          [ premium voice orb / Speak now ]                   |
|                 [ Type instead ]                             |
|                                                              |
|  Speak  ->  Verify  ->  Understand                           |
|                                                              |
|        [ sample premium recommendation preview ]             |
|                                                              |
|  Evidence-backed. Multilingual. Not an official approval.    |
+--------------------------------------------------------------+
```

## Assistant wireframe

```text
+--------------------------------------------------------------+
| KisanPath     Gujarati v                         session ...  |
+--------------------------------------------------------------+
|                                                              |
|   Assistant: Tell me what support you are looking for.       |
|                                                              |
|             [        VOICE ORB        ]                      |
|              Tap and hold / tap to speak                     |
|                                                              |
|   You: "..."                                                |
|                                                              |
|   Confirmed profile                                          |
|   [Gujarat ✓] [Junagadh ✓] [3 acres ?] [Groundnut ✓]       |
|                                                              |
|   [confirmation / clarification card]                        |
|                                                              |
|                         [type a message................]      |
+--------------------------------------------------------------+
```

## Results wireframe

```text
+--------------------------------------------------------------+
|  3 schemes may match your situation                          |
|  Based on the published information we reviewed.             |
|                                                              |
|  +--------------------------------------------------------+  |
|  | Scheme name                          Likely eligible    |  |
|  | Brief benefit                                            | |
|  | 5 conditions passed · 1 needs information               | |
|  | [Why this?] [Documents] [Listen]                         | |
|  +--------------------------------------------------------+  |
|                                                              |
|  +--------------------------------------------------------+  |
|  | Scheme name                    Need more information     | |
|  | Missing: ownership status                               | |
|  | [Answer question] [Why this?]                           | |
|  +--------------------------------------------------------+  |
+--------------------------------------------------------------+
```

## Evidence detail

On desktop use a refined side drawer; on mobile use a full-height bottom sheet or dedicated page.

```text
Why this scheme
Published conditions
  ✓ State condition
  ✓ Crop/activity condition
  ? Registration condition - information missing
Documents
Application guidance
Official source evidence
```

## Evaluation demo wireframe

```text
Primary metric
Baseline   XX
KisanPath  YY

Safety metric: false eligibility rate
...

[case explorer] [iteration changelog] [trajectory links]
```

Keep this visually distinct from the farmer experience so technical judging features do not clutter the product UI.
