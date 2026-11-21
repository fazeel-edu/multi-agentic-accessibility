"""ElementKey: tagged union produced by tools.element (AD-15). Models only, no parsing."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class _Key(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class NodeKey(_Key):
    kind: Literal["node"] = "node"
    path: str = Field(min_length=1)


class NodesKey(_Key):
    kind: Literal["nodes"] = "nodes"
    paths: tuple[str, ...] = Field(min_length=1)


class PageKey(_Key):
    kind: Literal["page"] = "page"


class UnresolvedKey(_Key):
    kind: Literal["unresolved"] = "unresolved"
    raw: str


ElementKey = Annotated[NodeKey | NodesKey | PageKey | UnresolvedKey, Field(discriminator="kind")]
