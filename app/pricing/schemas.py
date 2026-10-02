from pydantic import BaseModel, Field, field_validator


class PricingModel(BaseModel):
    """Represents a controlled pricing model for a SecureOps Africa service."""

    model_id: str = Field(
        min_length=1,
        description="Unique identifier for the pricing model.",
    )

    name: str = Field(
        min_length=1,
        description="Name of the pricing model.",
    )

    service_category: str = Field(
        min_length=1,
        description="Service category covered by the pricing model.",
    )

    base_implementation_cost: float = Field(
        ge=0,
        description="Base implementation cost.",
    )

    annual_maintenance_cost: float = Field(
        ge=0,
        description="Annual maintenance cost.",
    )

    training_cost: float = Field(
        ge=0,
        description="Training cost.",
    )

    minimum_project_value: float = Field(
        ge=0,
        description="Minimum commercially viable project value.",
    )

    maximum_project_value: float = Field(
        ge=0,
        description="Maximum project value supported by this pricing model.",
    )

    @field_validator(
        "base_implementation_cost",
        "annual_maintenance_cost",
        "training_cost",
        "minimum_project_value",
        "maximum_project_value",
    )
    @classmethod
    def validate_non_negative(cls, value: float) -> float:
        """Ensure all pricing values are non-negative."""
        if value < 0:
            raise ValueError("Pricing values cannot be negative.")
        return value

    @field_validator("maximum_project_value")
    @classmethod
    def validate_project_value_range(
        cls,
        value: float,
        info,
    ) -> float:
        """Ensure the maximum project value is not below the minimum."""
        minimum_value = info.data.get("minimum_project_value")

        if minimum_value is not None and value < minimum_value:
            raise ValueError(
                "maximum_project_value cannot be less than "
                "minimum_project_value."
            )

        return value

    @property
    def estimated_first_year_cost(self) -> float:
        """
        Calculate the estimated first-year delivery cost.

        This includes:
        - implementation
        - annual maintenance
        - training
        """
        return (
            self.base_implementation_cost
            + self.annual_maintenance_cost
            + self.training_cost
        )

    def supports_project_value(self, project_value: float) -> bool:
        """Return True when the project value falls within this pricing model."""
        if project_value < 0:
            raise ValueError("project_value cannot be negative.")

        return (
            self.minimum_project_value
            <= project_value
            <= self.maximum_project_value
        )


class PricingDataset(BaseModel):
    """Validated collection of pricing models for the company."""

    dataset_name: str = Field(
        min_length=1,
        description="Name of the pricing dataset.",
    )

    dataset_type: str = Field(
        min_length=1,
        description="Dataset classification.",
    )

    description: str = Field(
        min_length=1,
        description="Description of the pricing dataset.",
    )

    company_name: str = Field(
        min_length=1,
        description="Company associated with the pricing models.",
    )

    currency: str = Field(
        min_length=1,
        description="Currency used by the pricing dataset.",
    )

    pricing_models: list[PricingModel] = Field(
        min_length=1,
        description="Available pricing models.",
    )


class PricingAnalysisResult(BaseModel):
    """Result produced by the pricing analysis stage."""

    matched_model_id: str | None = Field(
        default=None,
        description="Best matching pricing model identifier.",
    )

    matched_model_name: str | None = Field(
        default=None,
        description="Best matching pricing model name.",
    )

    service_category: str | None = Field(
        default=None,
        description="Service category of the matched pricing model.",
    )

    project_value: float | None = Field(
        default=None,
        ge=0,
        description="Project value evaluated against the pricing model.",
    )

    estimated_first_year_cost: float | None = Field(
        default=None,
        ge=0,
        description="Estimated first-year cost from the matched pricing model.",
    )

    commercial_fit_score: float = Field(
        ge=0,
        le=100,
        description="Commercial fit score from 0 to 100.",
    )

    within_project_value_range: bool = Field(
        default=False,
        description="Whether the project value falls within the pricing range.",
    )

    pricing_models_considered: int = Field(
        default=0,
        ge=0,
        description="Number of pricing models considered.",
    )

    rationale: str = Field(
        min_length=1,
        description="Explanation of the pricing analysis result.",
    )
