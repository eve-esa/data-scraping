from typing import List

from pydantic import BaseModel, Field


class AnalyticsModelItemRatio(BaseModel):
    success: float
    failure: float


class AnalyticsModelItemTotal(BaseModel):
    success: int
    failure: int


class AnalyticsModelItem(BaseModel):
    success: List[str]= Field(default_factory=list)
    failure: List[str] = Field(default_factory=list)
    totals: AnalyticsModelItemTotal = Field(default_factory=AnalyticsModelItemTotal)
    ratios: AnalyticsModelItemRatio = Field(default_factory=AnalyticsModelItemRatio)


class AnalyticsModel(BaseModel):
    scraped: AnalyticsModelItem
    content_retrieved: AnalyticsModelItem
    uploaded: AnalyticsModelItem
