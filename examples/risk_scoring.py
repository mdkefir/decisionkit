"""Application / risk scoring example."""

from __future__ import annotations

from decisionkit import DecisionModel


def main() -> None:
    model = DecisionModel.from_dict(
        {
            "method": "weighted_sum",
            "criteria": [
                {"name": "fraud_signal", "weight": 0.4, "direction": "min"},
                {"name": "credit_score", "weight": 0.35, "direction": "max"},
                {"name": "doc_completeness", "weight": 0.25, "direction": "max"},
            ],
            "constraints": [
                {
                    "name": "kyc_passed",
                    "field": "kyc_status",
                    "operator": "eq",
                    "value": "passed",
                    "reason": "KYC must pass before scoring",
                },
                {
                    "name": "age_gate",
                    "all": [
                        {"field": "age", "operator": "gte", "value": 18},
                        {
                            "field": "country",
                            "operator": "in",
                            "value": ["US", "CA", "GB"],
                        },
                    ],
                    "reason": "Applicant must be adult in supported country",
                },
            ],
            "penalties": [
                {
                    "name": "high_fraud",
                    "field": "fraud_signal",
                    "operator": "gte",
                    "value": 0.7,
                    "amount": 0.15,
                }
            ],
            "bonuses": [
                {
                    "name": "strong_docs",
                    "field": "doc_completeness",
                    "operator": "gte",
                    "value": 0.95,
                    "amount": 0.05,
                }
            ],
        }
    )

    applications = [
        {
            "id": "app_1",
            "fraud_signal": 0.2,
            "credit_score": 720,
            "doc_completeness": 0.98,
            "kyc_status": "passed",
            "age": 34,
            "country": "US",
        },
        {
            "id": "app_2",
            "fraud_signal": 0.75,
            "credit_score": 690,
            "doc_completeness": 0.80,
            "kyc_status": "passed",
            "age": 29,
            "country": "CA",
        },
        {
            "id": "app_3",
            "fraud_signal": 0.1,
            "credit_score": 760,
            "doc_completeness": 1.0,
            "kyc_status": "pending",
            "age": 41,
            "country": "US",
        },
    ]

    result = model.rank(applications)
    print(f"Lowest-risk ranked first: {result.best.id}")
    print(result.explain())
    audit = result.to_audit_dict(decision_id="risk-batch-1", include_hash=True)
    print(audit["audit_hash"])


if __name__ == "__main__":
    main()
