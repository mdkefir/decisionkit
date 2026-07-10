# Concepts

DecisionKit ranks alternatives using weighted criteria and optional rules.

## Building blocks

| Concept | Role |
| --- | --- |
| `Criterion` | Named scored field with weight and `max`/`min` direction |
| `Alternative` | Candidate option with an `id` and field values |
| `Constraint` | Hard filter; failing alternatives are excluded |
| `Penalty` | Soft rule that subtracts from the score |
| `Bonus` | Soft rule that adds to the score |
| `DecisionModel` | Configures method + criteria + rules |
| `DecisionResult` | Ranking, explanations, and audit output |

## Methods

- `weighted_sum`: min-max normalize criteria (min criteria inverted), then weighted sum
- `topsis`: vector normalize, compare distance to ideal best/worst

Weights are renormalized internally and do not need to sum to 1.0.

## Explanations

When `explain=True`, each ranked alternative gets deterministic plain-text
explanation plus structured contribution data.
