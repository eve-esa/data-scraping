from typing import List
from pydantic import BaseModel

from model.base_iterative_publisher_models import BaseIterativePublisherConfig


class AMSJournal(BaseModel):
    name: str
    code: str


class AMSConfig(BaseIterativePublisherConfig):
    journals: List[AMSJournal]
