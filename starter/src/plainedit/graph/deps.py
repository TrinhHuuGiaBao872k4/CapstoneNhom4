"""What the graph nodes need from the outside, in one frozen object."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

from    dataclasses                     import  dataclass
from    pathlib                         import  Path

from    plainedit.config                  import  Config
from    plainedit.knowledge.vector_store  import  VectorStore
from    plainedit.llm.chat_source         import  ChatSource


#==========================================================================
# Dependencies
#==========================================================================
@dataclass(frozen=True)
class Deps:
    """
    Purpose: the config, the lazy chat model, the guideline store, the word
    swaps and the file that publish appends to. Nodes receive it with
    functools.partial, so they stay plain functions that tests can call.
    """

    config: Config
    chat: ChatSource
    store: VectorStore
    swaps: list[dict[str, str]]
    published_path: Path
