"""Vendor / supplier ranking example."""

from __future__ import annotations

from decisionkit import DecisionModel


def main() -> None:
    model = DecisionModel.from_dict(
        {
            "method": "topsis",
            "explain": True,
            "criteria": [
                {"name": "quality", "weight": 0.4, "direction": "max"},
                {"name": "price", "weight": 0.35, "direction": "min"},
                {"name": "lead_time_days", "weight": 0.25, "direction": "min"},
            ],
            "constraints": [
                {
                    "name": "certified",
                    "field": "iso_certified",
                    "operator": "eq",
                    "value": True,
                    "reason": "Supplier must be ISO certified",
                }
            ],
            "penalties": [
                {
                    "name": "single_source_risk",
                    "field": "single_source",
                    "operator": "eq",
                    "value": True,
                    "amount": 0.05,
                    "reason": "Prefer diversified supply",
                }
            ],
            "bonuses": [
                {
                    "name": "local_bonus",
                    "field": "region",
                    "operator": "eq",
                    "value": "EU",
                    "amount": 0.03,
                }
            ],
        }
    )

    vendors = [
        {
            "id": "vendor_a",
            "quality": 9.0,
            "price": 120,
            "lead_time_days": 14,
            "iso_certified": True,
            "single_source": False,
            "region": "EU",
        },
        {
            "id": "vendor_b",
            "quality": 8.0,
            "price": 95,
            "lead_time_days": 21,
            "iso_certified": True,
            "single_source": True,
            "region": "US",
        },
        {
            "id": "vendor_c",
            "quality": 9.5,
            "price": 150,
            "lead_time_days": 10,
            "iso_certified": False,
            "single_source": False,
            "region": "EU",
        },
    ]

    result = model.rank(vendors)
    print(f"Selected vendor: {result.best.id}")
    print(result.explain())
    print(result.audit_hash())


if __name__ == "__main__":
    main()
