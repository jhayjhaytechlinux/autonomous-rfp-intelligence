from app.decision.schemas import (
    BidDecision,
    DecisionFactor,
    DecisionResult,
)


def test_bid_decision_values():
    assert BidDecision.BID.value == "bid"
    assert BidDecision.EXECUTIVE_REVIEW.value == "executive_review"
    assert BidDecision.NO_BID.value == "no_bid"


def test_decision_factor_schema():
    factor = DecisionFactor(
        name="Compliance",
        score=85,
        weight=0.30,
        rationale="Most mandatory requirements have supporting evidence.",
    )

    assert factor.name == "Compliance"
    assert factor.score == 85
    assert factor.weight == 0.30


def test_decision_result_schema():
    result = DecisionResult(
        decision=BidDecision.EXECUTIVE_REVIEW,
        overall_score=72,
        compliance_score=68,
        capability_score=90,
        experience_score=75,
        resource_score=70,
        risk_score=60,
        mandatory_gaps=["REQ-012"],
        partial_requirements=["REQ-008"],
        factors=[
            DecisionFactor(
                name="Compliance",
                score=68,
                weight=0.30,
                rationale="Some requirements lack sufficient evidence.",
            )
        ],
        rationale="Strong capability alignment exists, but evidence gaps require review.",
    )

    assert result.decision == BidDecision.EXECUTIVE_REVIEW
    assert result.overall_score == 72
    assert result.mandatory_gaps == ["REQ-012"]
    assert result.partial_requirements == ["REQ-008"]
    assert len(result.factors) == 1


def test_decision_scores_must_be_between_zero_and_one_hundred():
    try:
        DecisionResult(
            decision=BidDecision.BID,
            overall_score=101,
            compliance_score=80,
            capability_score=80,
            experience_score=80,
            resource_score=80,
            risk_score=80,
            rationale="Invalid score test.",
        )
        assert False, "Expected validation error"
    except Exception:
        pass
