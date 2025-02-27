from typing import List

from model.base_mapped_models import BaseMappedIterativeWithConstraintJournal, BaseMappedIterativeWithConstraintConfig


class CopernicusConfig(BaseMappedIterativeWithConstraintConfig):
    journals: List[BaseMappedIterativeWithConstraintJournal]
