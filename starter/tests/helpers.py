"""Shared test helpers: a fake config in a temporary folder, a hashing store, graph dependencies."""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

import  json
import  shutil
from    dataclasses                     import  replace
from    functools                       import  partial
from    pathlib                         import  Path

from    plainedit.config                      import  Config, KnowledgeConfig, PathConfig, ServerConfig
from    plainedit.config                      import  with_backend
from    plainedit.integrations.chroma_server  import  open_chroma_client
from    plainedit.knowledge.hash_embeddings   import  HashEmbeddings
from    plainedit.graph.deps                  import  Deps
from    plainedit.knowledge.chunking          import  chunk_documents, load_documents
from    plainedit.knowledge.vector_store      import  VectorStore
from    plainedit.llm.chat_source             import  ChatSource
from    plainedit.llm.fake_chat_model         import  FakeRules


ROOT     = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


#==========================================================================
# Fake config in a temporary folder
#==========================================================================
def fake_config(tmp_path: Path) -> Config:
    """
    Build the fake-backend config with every path inside tmp_path.

    Input:
        . tmp_path      : pytest's temporary folder
    Output:
        . config        : backend fake, embedded store, temporary paths
    """
    paths = PathConfig(
        root        = tmp_path,
        data_dir    = tmp_path / "data",
        docs_dir    = tmp_path / "docs",
        runtime_dir = tmp_path / "runtime",
        results_dir = tmp_path / "results",
        kb_dir      = tmp_path / "kb_store",
    )
    return with_backend(replace(Config(), paths=paths), "fake")


#==========================================================================
# Embedded store with hashing vectors
#==========================================================================
def hash_store(
    tmp_path: Path,
    *,
    collection: str = "test-kb",
    threshold: float = 0.1,
    embedding_name: str = "hash-64",
) -> VectorStore:
    """
    Open a VectorStore in tmp_path with HashEmbeddings: no model download.

    Input:
        . tmp_path      : pytest's temporary folder
        . collection    : collection name (3+ characters, Chroma's rule)
        . threshold     : retriever score threshold
        . embedding_name: the name recorded on the collection
    Output:
        . store         : an unopened VectorStore
    """
    knowledge = KnowledgeConfig(collection=collection, threshold=threshold)
    client    = partial(open_chroma_client, knowledge, ServerConfig(), kb_dir=tmp_path / "kb_store")
    return VectorStore(
        knowledge,
        open_client     = client,
        open_embeddings = HashEmbeddings,
        embedding_name  = embedding_name,
    )


#==========================================================================
# Config of a project copy in a temporary folder
#==========================================================================
def project_copy(tmp_path: Path) -> Path:
    """
    Copy configs/app.toml and data/ (without raw/) into tmp_path and write a
    config whose paths point there, so a command can run end to end without
    touching the repository.

    Input:
        . tmp_path      : pytest's temporary folder
    Output:
        . config_path   : the TOML file to pass with --config
    """
    shutil.copytree(ROOT / "data", tmp_path / "data", ignore=shutil.ignore_patterns("raw"))
    for name in ("holdout", "flows"):
        if (ROOT / name).exists():
            shutil.copytree(ROOT / name, tmp_path / name)

    #----------------------------------------------------------------------
    # Point every path into tmp_path
    #----------------------------------------------------------------------
    text  = (ROOT / "configs" / "app.toml").read_text(encoding="utf-8")
    start = text.index("[paths]")
    end   = text.index("[servers]")
    paths = "[paths]\n" + "".join(
        f'{name} = "{tmp_path / folder}"\n'
        for name, folder in (
            ("root", "."), ("data_dir", "data"), ("docs_dir", "data/docs"), ("runtime_dir", "runtime"),
            ("results_dir", "results"), ("kb_dir", "kb_store"), ("holdout_dir", "holdout"),
            ("flows_dir", "flows"), ("my_work_dir", "my_work"),
        )
    )
    path = tmp_path / "app.toml"
    path.write_text(text[:start] + paths + "\n" + text[end:], encoding="utf-8")
    return path


#==========================================================================
# Graph dependencies on the fake backend
#==========================================================================
def plain_deps(tmp_path: Path, *, rules: FakeRules | None = None) -> Deps:
    """
    Build Deps with the fake chat model (project rules, or the given ones),
    a hashing guideline store holding the real guideline chunks, and the real
    word swaps. No download, deterministic.

    Input:
        . tmp_path      : pytest's temporary folder
        . rules         : FakeRules for this test, or None for project_fake_rules()
    Output:
        . deps          : ready for build_graph and the nodes
    """
    config = fake_config(tmp_path)
    store  = hash_store(tmp_path, collection="plain-test", threshold=-1.0)
    docs   = load_documents(ROOT / "data" / "docs")
    store.index(chunk_documents(docs, size=config.knowledge.chunk_size, overlap=config.knowledge.chunk_overlap))
    return Deps(
        config          = config,
        chat            = ChatSource(config.model, config.servers, rules=rules),
        store           = store,
        swaps           = json.loads((ROOT / "data" / "word_swaps.json").read_text(encoding="utf-8")),
        published_path  = tmp_path / "runtime" / "published.jsonl",
    )


#==========================================================================
# One dev case
#==========================================================================
def dev_case(draft_id: str) -> dict:
    """
    Read one case of data/dev_cases.json by id.

    Input:
        . draft_id      : e.g. "D07"
    Output:
        . case          : the case dict (id, inputs, outputs, kind, note)
    """
    cases = json.loads((ROOT / "data" / "dev_cases.json").read_text(encoding="utf-8"))
    return next(case for case in cases if case["id"] == draft_id)
