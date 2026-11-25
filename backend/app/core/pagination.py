from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query


@dataclass(frozen=True)
class Page:
    limit: int = 100
    offset: int = 0


def get_page(
    limit: Annotated[int, Query(ge=1, le=200, description="Max rows to return")] = 100,
    offset: Annotated[int, Query(ge=0, description="Rows to skip")] = 0,
) -> Page:
    return Page(limit=limit, offset=offset)


PageDep = Annotated[Page, Depends(get_page)]
