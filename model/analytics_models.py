from typing import List

from pydantic import BaseModel, Field


class AnalyticsModelItemPercentage(BaseModel):
    success: float
    failure: float


class AnalyticsModelItem(BaseModel):
    success: List[str]= Field(default_factory=list)
    failure: List[str] = Field(default_factory=list)
    percentages: AnalyticsModelItemPercentage = Field(default_factory=AnalyticsModelItemPercentage)


class AnalyticsModel(BaseModel):
    scraped: AnalyticsModelItem
    content_retrieved: AnalyticsModelItem
    uploaded: AnalyticsModelItem
