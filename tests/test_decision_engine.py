from app.compliance.schemas import ComplianceMatrix, ComplianceStatus
from app.decision.decision_engine import BidDecision, DecisionEngine
from app.extraction.schemas import Requirement, RequirementCategory


def make_requirement(
    requirement_id: str,
    category: RequirementCategory = RequirementCategory.TECHNICAL,
    mandatory: bool = True,
) -> Requirement:
    return Requirement(
        requirement_id=requirement_id,
        category=category,
        description=f"Requirement {requirement_id}",
        mandatory=mandatory,
        source_section="Technical Requirements",
        evidence=f"Evidence for {requirement_id}",
    )


def make_matrix(statuses: list[ComplianceStatus]) -> ComplianceMatrix:
    results = []

    for index, status in enumerate(statuses, start=1):
        matched_capability_ids = []

        if status in {
            ComplianceStatus.COMPLIANT,
            ComplianceStatus.PARTIAL,
        }:
            matched_capability_ids = [f"CAP-{index:03d}"]

        results.append(
            {
                "requirement_id": f"REQ-{index:03d}",
                "status": status,
                "matched_capability_ids": matched_capability_ids,
                "evidence": (
                    [f"Evidence for REQ-{index:03d}"]
                    if matched_capability_ids
                    else []
                ),
                "rationale": f"Assessment for REQ-{index:03d}",
            }
        )

    compliant_count = sum(
        1 for status in statuses if status == ComplianceStatus.COMPLIANT
    )
    partial_count = sum(
        1 for status in statuses if status == ComplianceStatus.PARTIAL
    )
    gap_count = sum(
        1 for status in statuses if status == ComplianceStatus.GAP
    )
    unknown_count = sum(
        1 for status in statuses if status == ComplianceStatus.UNKNOWN
    )

    return ComplianceMatrix(
        company_name="SecureOps Africa",
        total_requirements=len(statuses),
        compliant_count=compliant_count,
        partial_count=partial_count,
        gap_count=gap_count,
        unknown_count=unknown_count,
        results=results,
    )


def test_all_compliant_requirements_produce_high_score():
    matrix = make_matrix(
        [
            ComplianceStatus.COMPLIANT,
            ComplianceStatus.COMPLIANT,
            ComplianceStatus.COMPLIANT,
        ]
    )

    requirements = [
        make_requirement("REQ-001"),
        make_requirement("REQ-002"),
        make_requirement("REQ-003"),
    ]

    engine = DecisionEngine()

    result = engine.evaluate(
        matrix,
        requirements,
        resource_score=100,
        historical_relevance_score=100,
        matched_historical_proposals=[
            "PROP-001",
            "PROP-002",
        ],
    )

    assert result.overall_score == 100
    assert result.compliance_score == 100
    assert result.capability_score == 100
    assert result.experience_score == 100
    assert result.historical_relevance_score == 100
    assert result.resource_score == 100
    assert result.risk_score == 100
    assert result.decision == BidDecision.BID
    assert result.mandatory_gaps == []
    assert result.partial_requirements == []
    assert result.matched_historical_proposals == [
        "PROP-001",
        "PROP-002",
    ]


def test_partial_and_gap_requirements_reduce_score():
    matrix = make_matrix(
        [
            ComplianceStatus.COMPLIANT,
            ComplianceStatus.PARTIAL,
            ComplianceStatus.GAP,
            ComplianceStatus.UNKNOWN,
        ]
    )

    requirements = [
        make_requirement("REQ-001"),
        make_requirement("REQ-002"),
        make_requirement("REQ-003"),
        make_requirement("REQ-004"),
    ]

    engine = DecisionEngine()

    result = engine.evaluate(
        matrix,
        requirements,
        resource_score=50,
        historical_relevance_score=0,
    )

    assert result.compliance_score == 43.75
    assert result.capability_score == 50
    assert result.experience_score == 100
    assert result.historical_relevance_score == 0
    assert result.resource_score == 50
    assert result.risk_score == 72.5

    # Weighted score:
    # (43.75 * 0.25)
    # + (50 * 0.20)
    # + (100 * 0.15)
    # + (0 * 0.15)
    # + (50 * 0.10)
    # + (72.5 * 0.15)
    # = 51.8125 -> rounded to 51.81
    assert result.overall_score == 51.81

    assert result.decision == BidDecision.NO_BID
    assert "REQ-003" in result.mandatory_gaps
    assert "REQ-002" in result.partial_requirements


def test_historical_relevance_contributes_to_overall_score():
    matrix = make_matrix(
        [
            ComplianceStatus.COMPLIANT,
            ComplianceStatus.COMPLIANT,
        ]
    )

    requirements = [
        make_requirement("REQ-001"),
        make_requirement("REQ-002"),
    ]

    engine = DecisionEngine()

    result_without_history = engine.evaluate(
        matrix,
        requirements,
        resource_score=50,
        historical_relevance_score=0,
    )

    result_with_history = engine.evaluate(
        matrix,
        requirements,
        resource_score=50,
        historical_relevance_score=100,
        matched_historical_proposals=["PROP-001"],
    )

    assert result_without_history.historical_relevance_score == 0
    assert result_with_history.historical_relevance_score == 100

    assert (
        result_with_history.overall_score
        > result_without_history.overall_score
    )

    assert result_with_history.matched_historical_proposals == [
        "PROP-001"
    ]


def test_experience_score_is_based_on_experience_requirements():
    matrix = make_matrix(
        [
            ComplianceStatus.COMPLIANT,
            ComplianceStatus.PARTIAL,
            ComplianceStatus.GAP,
        ]
    )

    requirements = [
        make_requirement(
            "REQ-001",
            category=RequirementCategory.EXPERIENCE,
        ),
        make_requirement(
            "REQ-002",
            category=RequirementCategory.EXPERIENCE,
        ),
        make_requirement(
            "REQ-003",
            category=RequirementCategory.EXPERIENCE,
        ),
    ]

    engine = DecisionEngine()

    result = engine.evaluate(
        matrix,
        requirements,
        resource_score=50,
    )

    assert result.experience_score == 50


def test_no_experience_requirements_default_to_full_experience_score():
    matrix = make_matrix(
        [
            ComplianceStatus.COMPLIANT,
        ]
    )

    requirements = [
        make_requirement(
            "REQ-001",
            category=RequirementCategory.TECHNICAL,
        ),
    ]

    engine = DecisionEngine()

    result = engine.evaluate(
        matrix,
        requirements,
        resource_score=50,
    )

    assert result.experience_score == 100


def test_thresholds_control_final_decision():
    matrix = make_matrix(
        [
            ComplianceStatus.COMPLIANT,
        ]
    )

    requirements = [
        make_requirement("REQ-001"),
    ]

    bid_engine = DecisionEngine(
        bid_threshold=80,
        review_threshold=60,
    )

    result = bid_engine.evaluate(
        matrix,
        requirements,
        resource_score=100,
        historical_relevance_score=100,
    )

    assert result.decision == BidDecision.BID

    review_engine = DecisionEngine(
        bid_threshold=100,
        review_threshold=60,
    )

    result = review_engine.evaluate(
        matrix,
        requirements,
        resource_score=50,
        historical_relevance_score=0,
    )

    assert result.decision == BidDecision.EXECUTIVE_REVIEW

    no_bid_engine = DecisionEngine(
        bid_threshold=100,
        review_threshold=100,
    )

    result = no_bid_engine.evaluate(
        matrix,
        requirements,
        resource_score=0,
        historical_relevance_score=0,
    )

    assert result.decision == BidDecision.NO_BID


def test_invalid_thresholds_are_rejected():
    try:
        DecisionEngine(
            bid_threshold=101,
            review_threshold=60,
        )
        assert False, "Expected ValueError for bid_threshold > 100"
    except ValueError as exc:
        assert "bid_threshold" in str(exc)

    try:
        DecisionEngine(
            bid_threshold=80,
            review_threshold=101,
        )
        assert False, "Expected ValueError for review_threshold > 100"
    except ValueError as exc:
        assert "review_threshold" in str(exc)

    try:
        DecisionEngine(
            bid_threshold=-1,
            review_threshold=60,
        )
        assert False, "Expected ValueError for bid_threshold < 0"
    except ValueError as exc:
        assert "bid_threshold" in str(exc)

    try:
        DecisionEngine(
            bid_threshold=60,
            review_threshold=80,
        )
        assert False, (
            "Expected ValueError when review threshold "
            "exceeds bid threshold"
        )
    except ValueError as exc:
        assert "review_threshold" in str(exc)


def test_resource_score_must_be_between_zero_and_one_hundred():
    matrix = make_matrix(
        [
            ComplianceStatus.COMPLIANT,
        ]
    )

    requirements = [
        make_requirement("REQ-001"),
    ]

    engine = DecisionEngine()

    try:
        engine.evaluate(
            matrix,
            requirements,
            resource_score=101,
        )
        assert False, "Expected ValueError for resource_score > 100"
    except ValueError as exc:
        assert "resource_score" in str(exc)

    try:
        engine.evaluate(
            matrix,
            requirements,
            resource_score=-1,
        )
        assert False, "Expected ValueError for resource_score < 0"
    except ValueError as exc:
        assert "resource_score" in str(exc)


def test_historical_relevance_score_must_be_between_zero_and_one_hundred():
    matrix = make_matrix(
        [
            ComplianceStatus.COMPLIANT,
        ]
    )

    requirements = [
        make_requirement("REQ-001"),
    ]

    engine = DecisionEngine()

    try:
        engine.evaluate(
            matrix,
            requirements,
            historical_relevance_score=101,
        )
        assert False, (
            "Expected ValueError for historical relevance > 100"
        )
    except ValueError as exc:
        assert "historical_relevance_score" in str(exc)

    try:
        engine.evaluate(
            matrix,
            requirements,
            historical_relevance_score=-1,
        )
        assert False, (
            "Expected ValueError for historical relevance < 0"
        )
    except ValueError as exc:
        assert "historical_relevance_score" in str(exc)


def test_empty_requirements_are_handled():
    matrix = make_matrix([])

    engine = DecisionEngine()

    result = engine.evaluate(
        matrix,
        [],
        resource_score=50,
        historical_relevance_score=0,
    )

    assert result.compliance_score == 0
    assert result.capability_score == 0
    assert result.experience_score == 100
    assert result.historical_relevance_score == 0
    assert result.resource_score == 50

    # With no gaps, partial requirements, or unknown requirements,
    # the current risk calculation starts and remains at 100.
    assert result.risk_score == 100

    # Weighted score:
    # (0 * 0.25)
    # + (0 * 0.20)
    # + (100 * 0.15)
    # + (0 * 0.15)
    # + (50 * 0.10)
    # + (100 * 0.15)
    # = 35
    assert result.overall_score == 35
    assert result.decision == BidDecision.NO_BID

    assert result.mandatory_gaps == []
    assert result.partial_requirements == []
