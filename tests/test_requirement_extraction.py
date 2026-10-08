from uuid import UUID

import pytest

from backend.schemas.requirements import RFPTextSegment
from backend.services.requirement_extraction import RequirementExtractionService


@pytest.fixture
def extractor() -> RequirementExtractionService:
    return RequirementExtractionService()


def test_extracts_multiple_independent_requirements(extractor: RequirementExtractionService) -> None:
    result = extractor.extract(
        "The supplier must provide 24/7 support.\n"
        "The platform shall encrypt data at rest.\n"
        "The proposal should include a company overview."
    )

    assert len(result.requirements) == 2
    assert result.message == "requirements found"
    assert result.requirements[0].requirement_text == "The supplier must provide 24/7 support."
    assert result.requirements[0].category == "support"
    assert result.requirements[0].priority is None
    assert isinstance(result.requirements[0].requirement_id, UUID)
    assert result.requirements[1].category == "security"


def test_splits_compound_explicit_requirements(extractor: RequirementExtractionService) -> None:
    result = extractor.extract("The supplier must provide hosting and shall maintain daily backups.")

    assert [item.requirement_text for item in result.requirements] == [
        "The supplier must provide hosting",
        "and shall maintain daily backups.",
    ]


def test_preserves_source_metadata_and_explicit_optional_values(extractor: RequirementExtractionService) -> None:
    result = extractor.extract([
        RFPTextSegment(
            text="The supplier shall comply with ISO 27001 by 30 June 2027. Priority: critical.",
            source_section="Security Requirements",
            source_page=8,
        )
    ])

    requirement = result.requirements[0]
    assert requirement.source_section == "Security Requirements"
    assert requirement.source_page == 8
    assert requirement.deadline == "30 June 2027"
    assert requirement.compliance_type == "ISO 27001"
    assert requirement.priority == "critical"


def test_missing_optional_fields_are_null(extractor: RequirementExtractionService) -> None:
    result = extractor.extract("The vendor must submit a pricing schedule.")

    requirement = result.requirements[0]
    assert requirement.deadline is None
    assert requirement.compliance_type is None
    assert requirement.source_section is None
    assert requirement.source_page is None


def test_does_not_create_unsupported_requirements(extractor: RequirementExtractionService) -> None:
    result = extractor.extract("Our company has offices in three countries and serves many clients.")

    assert result.requirements == []
    assert result.message == "no explicit requirements found"


def test_empty_and_invalid_inputs_are_handled(extractor: RequirementExtractionService) -> None:
    assert extractor.extract("").requirements == []
    assert extractor.extract("   ").message == "no explicit requirements found"
    with pytest.raises(TypeError):
        extractor.extract(None)  # type: ignore[arg-type]
