from pydantic import BaseModel


class CreditScoreFactor(BaseModel):
    name: str
    impact: int
    value: str
    explanation: str


class CreditScoreResponse(BaseModel):
    score: int
    raw_score: int
    baseline: int
    range_min: int
    range_max: int
    label: str
    disclaimer: str
    factors: list[CreditScoreFactor]
