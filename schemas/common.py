from typing import Annotated

from pydantic import Field


MAX_RESOURCE_ID = 9_223_372_036_854_775_807

ResourceId = Annotated[
    int,
    Field(
        gt=0,
        le=MAX_RESOURCE_ID,
    ),
]
