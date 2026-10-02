from pydantic import BaseModel, Field


class TeamRoleCapacity(BaseModel):
    role: str = Field(min_length=1)
    available_hours: float = Field(ge=0)
    allocated_hours: float = Field(ge=0)

    @property
    def remaining_hours(self) -> float:
        return max(
            0.0,
            self.available_hours - self.allocated_hours,
        )


class TeamBandwidth(BaseModel):
    team_id: str = Field(min_length=1)
    team_name: str = Field(min_length=1)
    roles: list[TeamRoleCapacity] = Field(default_factory=list)

    @property
    def total_available_hours(self) -> float:
        return sum(
            role.available_hours
            for role in self.roles
        )

    @property
    def total_allocated_hours(self) -> float:
        return sum(
            role.allocated_hours
            for role in self.roles
        )

    @property
    def total_remaining_hours(self) -> float:
        return sum(
            role.remaining_hours
            for role in self.roles
        )


class TeamBandwidthDataset(BaseModel):
    dataset_name: str = Field(min_length=1)
    dataset_type: str = Field(min_length=1)
    description: str = Field(min_length=1)
    company_name: str = Field(min_length=1)
    planning_period: str = Field(min_length=1)
    teams: list[TeamBandwidth] = Field(default_factory=list)

    @property
    def total_available_hours(self) -> float:
        return sum(
            team.total_available_hours
            for team in self.teams
        )

    @property
    def total_allocated_hours(self) -> float:
        return sum(
            team.total_allocated_hours
            for team in self.teams
        )

    @property
    def total_remaining_hours(self) -> float:
        return sum(
            team.total_remaining_hours
            for team in self.teams
        )
