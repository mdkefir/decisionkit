# Examples

Runnable scripts live in `examples/`.

| File | Scenario |
| --- | --- |
| `reviewer_selection.py` | Editorial reviewer ranking with availability + capacity rules |
| `vendor_ranking.py` | Supplier selection by quality, price, and lead time |
| `task_prioritization.py` | Backlog ranking by impact, urgency, and effort |
| `risk_scoring.py` | Application risk scoring with hard gates and penalties |
| `fastapi_example.py` | Config-driven `/rank` endpoint returning audit output |
| `django_service_example.py` | Service-layer ranking from settings-like config |

Run:

```bash
python examples/vendor_ranking.py
python examples/task_prioritization.py
python examples/risk_scoring.py
```
