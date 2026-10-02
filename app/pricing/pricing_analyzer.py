from app.pricing.schemas import (
    PricingAnalysisResult,
    PricingDataset,
    PricingModel,
)


class PricingAnalyzer:
    """
    Analyze an RFP opportunity against available company pricing models.

    The analyzer provides a commercial-fit score based on:
    - Whether the opportunity falls within the model's supported value range.
    - How well the project value fits inside that range.
    - Whether the estimated first-year delivery cost is commercially
      reasonable relative to the project value.
    """

    def analyze(
        self,
        pricing_dataset: PricingDataset,
        project_value: float | None = None,
        service_category: str | None = None,
    ) -> PricingAnalysisResult:
        """
        Evaluate an opportunity against the company's pricing models.

        Args:
            pricing_dataset: Validated company pricing dataset.
            project_value: Estimated RFP/project value.
            service_category: Optional service category to prioritize.

        Returns:
            PricingAnalysisResult containing the matched pricing model
            and commercial fit assessment.
        """
        if project_value is not None and project_value < 0:
            raise ValueError("project_value cannot be negative.")

        models = self._filter_models(
            pricing_dataset.pricing_models,
            service_category,
        )

        if not models:
            return PricingAnalysisResult(
                commercial_fit_score=0,
                pricing_models_considered=0,
                project_value=project_value,
                rationale=(
                    "No pricing models were available for the requested "
                    "service category."
                ),
            )

        if project_value is None:
            return self._analyze_without_project_value(
                models=models,
                pricing_dataset=pricing_dataset,
            )

        matched_model = self._select_best_model(
            models=models,
            project_value=project_value,
        )

        within_range = matched_model.supports_project_value(project_value)

        commercial_fit_score = self._calculate_commercial_fit_score(
            pricing_model=matched_model,
            project_value=project_value,
        )

        rationale = self._build_rationale(
            pricing_model=matched_model,
            project_value=project_value,
            within_range=within_range,
            commercial_fit_score=commercial_fit_score,
        )

        return PricingAnalysisResult(
            matched_model_id=matched_model.model_id,
            matched_model_name=matched_model.name,
            service_category=matched_model.service_category,
            project_value=project_value,
            estimated_first_year_cost=(
                matched_model.estimated_first_year_cost
            ),
            commercial_fit_score=commercial_fit_score,
            within_project_value_range=within_range,
            pricing_models_considered=len(models),
            rationale=rationale,
        )

    @staticmethod
    def _filter_models(
        models: list[PricingModel],
        service_category: str | None,
    ) -> list[PricingModel]:
        """Filter pricing models by service category when supplied."""
        if not service_category:
            return models

        normalized_category = service_category.strip().lower()

        matching_models = [
            model
            for model in models
            if model.service_category.strip().lower()
            == normalized_category
        ]

        return matching_models or models

    @staticmethod
    def _select_best_model(
        models: list[PricingModel],
        project_value: float,
    ) -> PricingModel:
        """
        Select the most commercially appropriate pricing model.

        Models containing the project value are preferred. When multiple
        models contain the value, the model with the smallest supported
        range is selected because it provides the most specific fit.

        If no model contains the project value, the model whose supported
        range is closest to the project value is selected.
        """
        in_range = [
            model
            for model in models
            if model.supports_project_value(project_value)
        ]

        if in_range:
            return min(
                in_range,
                key=lambda model: (
                    model.maximum_project_value
                    - model.minimum_project_value,
                    model.minimum_project_value,
                ),
            )

        return min(
            models,
            key=lambda model: PricingAnalyzer._distance_from_range(
                model,
                project_value,
            ),
        )

    @staticmethod
    def _distance_from_range(
        pricing_model: PricingModel,
        project_value: float,
    ) -> float:
        """Calculate the distance between a value and a pricing range."""
        if project_value < pricing_model.minimum_project_value:
            return (
                pricing_model.minimum_project_value
                - project_value
            )

        if project_value > pricing_model.maximum_project_value:
            return (
                project_value
                - pricing_model.maximum_project_value
            )

        return 0.0

    @staticmethod
    def _calculate_commercial_fit_score(
        pricing_model: PricingModel,
        project_value: float,
    ) -> float:
        """
        Calculate a 0-100 commercial fit score.

        Scoring:
        - 70% based on project-value fit.
        - 30% based on first-year cost coverage.

        A project inside the supported pricing range receives the strongest
        project-value component. Projects outside the range receive a
        reduced score based on their distance from the supported range.
        """
        value_fit_score = PricingAnalyzer._calculate_value_fit_score(
            pricing_model,
            project_value,
        )

        cost_ratio = (
            pricing_model.estimated_first_year_cost / project_value
            if project_value > 0
            else 1.0
        )

        cost_coverage_score = PricingAnalyzer._calculate_cost_coverage_score(
            cost_ratio
        )

        score = (
            value_fit_score * 0.70
            + cost_coverage_score * 0.30
        )

        return round(max(0.0, min(100.0, score)), 2)

    @staticmethod
    def _calculate_value_fit_score(
        pricing_model: PricingModel,
        project_value: float,
    ) -> float:
        """Calculate how well a project value fits the pricing range."""
        minimum = pricing_model.minimum_project_value
        maximum = pricing_model.maximum_project_value

        if minimum <= project_value <= maximum:
            midpoint = (minimum + maximum) / 2

            if midpoint == minimum:
                return 100.0

            distance_from_midpoint = abs(project_value - midpoint)
            half_range = (maximum - minimum) / 2

            if half_range == 0:
                return 100.0

            score = 100 - (
                distance_from_midpoint / half_range * 20
            )

            return round(max(80.0, min(100.0, score)), 2)

        distance = PricingAnalyzer._distance_from_range(
            pricing_model,
            project_value,
        )

        range_size = max(
            pricing_model.maximum_project_value
            - pricing_model.minimum_project_value,
            1,
        )

        penalty = min(
            70.0,
            (distance / range_size) * 70,
        )

        return round(max(0.0, 70.0 - penalty), 2)

    @staticmethod
    def _calculate_cost_coverage_score(
        cost_ratio: float,
    ) -> float:
        """
        Score how well the project value covers first-year delivery costs.

        Lower cost ratios receive higher scores because more of the project
        value remains available for margin and commercial overhead.
        """
        if cost_ratio <= 0.30:
            return 100.0

        if cost_ratio <= 0.40:
            return 90.0

        if cost_ratio <= 0.50:
            return 80.0

        if cost_ratio <= 0.60:
            return 70.0

        if cost_ratio <= 0.70:
            return 60.0

        if cost_ratio <= 0.80:
            return 45.0

        if cost_ratio <= 1.00:
            return 30.0

        return 10.0

    def _analyze_without_project_value(
        self,
        models: list[PricingModel],
        pricing_dataset: PricingDataset,
    ) -> PricingAnalysisResult:
        """Return pricing coverage information when no project value exists."""
        return PricingAnalysisResult(
            matched_model_id=None,
            matched_model_name=None,
            service_category=None,
            project_value=None,
            estimated_first_year_cost=None,
            commercial_fit_score=0,
            within_project_value_range=False,
            pricing_models_considered=len(models),
            rationale=(
                f"{len(models)} pricing model(s) are available in the "
                f"{pricing_dataset.company_name} {pricing_dataset.currency} "
                "pricing dataset, but the RFP does not provide a project "
                "value for commercial-fit evaluation."
            ),
        )

    @staticmethod
    def _build_rationale(
        pricing_model: PricingModel,
        project_value: float,
        within_range: bool,
        commercial_fit_score: float,
    ) -> str:
        """Build a concise explanation of the pricing assessment."""
        if within_range:
            range_statement = (
                f"The project value of {project_value:,.2f} falls within "
                f"the supported range of "
                f"{pricing_model.minimum_project_value:,.2f} to "
                f"{pricing_model.maximum_project_value:,.2f}."
            )
        else:
            range_statement = (
                f"The project value of {project_value:,.2f} falls outside "
                f"the supported range of "
                f"{pricing_model.minimum_project_value:,.2f} to "
                f"{pricing_model.maximum_project_value:,.2f}."
            )

        return (
            f"Matched pricing model: {pricing_model.name}. "
            f"{range_statement} "
            f"Estimated first-year delivery cost is "
            f"{pricing_model.estimated_first_year_cost:,.2f}. "
            f"Commercial fit score: {commercial_fit_score:.2f}/100."
        )
