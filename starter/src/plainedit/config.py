"""Load the project configuration from TOML into frozen config classes.

main.py creates one Config at startup and passes it down; nothing else reads
the TOML file. A project adds its own section with one more frozen class and
one more field in Config: load_config finds it by the field's type.
"""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

import  tomllib
from    dataclasses                     import  dataclass, fields, replace
from    pathlib                         import  Path
from    typing                          import  Any, get_type_hints


#==========================================================================
# Model settings
#==========================================================================
@dataclass(frozen=True)
class ModelConfig:
    """
    Purpose: choose the chat backend and the models. "local" runs Qwen in this
    process, "server" calls the OpenAI-compatible model server, "fake" answers
    by rules with no download.
    """

    #----------------------------------------------------------------------
    # Backend and models
    #----------------------------------------------------------------------
    backend: str                        = "local"
    chat_model: str                     = "Qwen/Qwen2.5-1.5B-Instruct"
    small_chat_model: str               = "Qwen/Qwen2.5-0.5B-Instruct"
    embedding_model: str                = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    max_new_tokens: int                 = 300

    #----------------------------------------------------------------------
    # Reject an unknown backend at startup
    #----------------------------------------------------------------------
    def __post_init__(self) -> None:
        """
        Stop when no chat source can create the requested backend.
        """
        if self.backend not in ("local", "fake", "server"):
            raise ValueError(
                f"model.backend must be 'local', 'fake' or 'server', got {self.backend!r}"
            )


#==========================================================================
# Knowledge base settings
#==========================================================================
@dataclass(frozen=True)
class KnowledgeConfig:
    """
    Purpose: the Chroma collection and how documents are cut and searched.
    "embedded" opens the folder in this process; "server" calls `chroma run`,
    the collection Langflow reads too.
    """

    #----------------------------------------------------------------------
    # Collection
    #----------------------------------------------------------------------
    collection: str                     = "plain-guidelines"
    store: str                          = "embedded"

    #----------------------------------------------------------------------
    # Chunking (words) and search
    #----------------------------------------------------------------------
    chunk_size: int                     = 60
    chunk_overlap: int                  = 15
    top_k: int                          = 3
    threshold: float                    = 0.35      # cosine similarity, 1 - distance

    #----------------------------------------------------------------------
    # Validate the store kind and the chunk window
    #----------------------------------------------------------------------
    def __post_init__(self) -> None:
        """
        Stop on a store kind nobody opens or a window that cannot advance.
        """
        if self.store not in ("embedded", "server"):
            raise ValueError(f"knowledge.store must be 'embedded' or 'server', got {self.store!r}")
        if not 0 <= self.chunk_overlap < self.chunk_size:
            raise ValueError(
                f"knowledge.chunk_overlap must be in [0, chunk_size): "
                f"{self.chunk_overlap} vs {self.chunk_size}"
            )


#==========================================================================
# File locations
#==========================================================================
@dataclass(frozen=True)
class PathConfig:
    """
    Purpose: every folder the project reads or writes. load_config resolves
    them from the project root, so commands work from any directory.
    """

    root: Path                          = Path(".")
    data_dir: Path                      = Path("data")
    docs_dir: Path                      = Path("data/docs")
    runtime_dir: Path                   = Path("runtime")     # traces, checkpoints; safe to delete
    results_dir: Path                   = Path("results")     # experiments, submitted
    kb_dir: Path                        = Path("kb_store")    # Chroma folder, embedded or `chroma run --path`
    holdout_dir: Path                   = Path("holdout")     # instructor only; absent in the starter
    flows_dir: Path                     = Path("flows")       # exported Langflow flow(s)
    my_work_dir: Path                   = Path("my_work")     # the learner's notes


#==========================================================================
# Local server addresses
#==========================================================================
@dataclass(frozen=True)
class ServerConfig:
    """
    Purpose: where the model server, the Chroma server and Langflow listen,
    and which flow the code calls.
    """

    #----------------------------------------------------------------------
    # Model server and Chroma server
    #----------------------------------------------------------------------
    model_host: str                     = "127.0.0.1"
    model_port: int                     = 8000
    chroma_host: str                    = "127.0.0.1"
    chroma_port: int                    = 8001
    request_timeout: float              = 300.0     # seconds; a CPU answer can take a minute

    #----------------------------------------------------------------------
    # Langflow
    #----------------------------------------------------------------------
    langflow_url: str                   = "http://127.0.0.1:7860"
    flow_name: str                      = "plainedit-rag"

    #----------------------------------------------------------------------
    # Base URL of the OpenAI-compatible API
    #----------------------------------------------------------------------
    @property
    def model_url(self) -> str:
        """
        Build the base URL that ServerChat, ServerEmbeddings and Langflow use.

        Output:
            . url           : e.g. http://127.0.0.1:8000/v1
        """
        return f"http://{self.model_host}:{self.model_port}/v1"


#==========================================================================
# Tracing and LangSmith
#==========================================================================
@dataclass(frozen=True)
class TracingConfig:
    """
    Purpose: how runs are labelled, locally and on LangSmith, and the name of
    the LangSmith dataset the cloud experiment creates once.
    """

    project: str                        = "plainedit"
    tags: tuple[str, ...]               = ("plainedit",)
    dataset: str                        = "plainedit-dataset"


#==========================================================================
# The editor: limits, weights and the text patterns of the checks
#==========================================================================
@dataclass(frozen=True)
class EditorConfig:
    """
    Purpose: every number and pattern the code checks use: sentence limit,
    issue weights, loop limits, and the regular expressions that find passive
    voice, hidden verbs, double negatives, instruction-like sentences and
    facts. Code decides pass or fail from these; the model never does.
    """

    #----------------------------------------------------------------------
    # Pass rule and loop
    #----------------------------------------------------------------------
    sentence_limit: int                 = 25        # words in the longest allowed sentence
    target_score: int                   = 3         # issue_score of a rewrite must be <= this
    min_length_ratio: float             = 0.35      # rewrite words / original words (plain rewrites shrink a lot)
    max_length_ratio: float             = 1.3
    max_rounds: int                     = 3         # rewrite attempts before pick_best
    max_findings: int                   = 4         # critique findings kept

    #----------------------------------------------------------------------
    # The issue types the code can detect, in the order they are reported
    #----------------------------------------------------------------------
    issue_types: tuple[str, ...]        = (
        "long_sentence", "passive", "shall", "complex_words", "hidden_verb", "double_negative",
    )

    #----------------------------------------------------------------------
    # Weights of the issue_score
    #----------------------------------------------------------------------
    w_long_sentence: int                = 2         # per sentence over the limit
    w_passive: int                      = 2
    w_shall: int                        = 2
    w_complex: int                      = 1
    w_hidden_verb: int                  = 2
    w_double_negative: int              = 2

    #----------------------------------------------------------------------
    # Sentence splitting: abbreviations whose dot does not end a sentence
    #----------------------------------------------------------------------
    abbreviations: tuple[str, ...]      = ("a.m.", "p.m.", "Mr.", "Ms.", "Mrs.", "Dr.", "St.", "No.", "e.g.", "i.e.")

    #----------------------------------------------------------------------
    # Passive voice heuristic: a form of "to be" + a past participle
    #----------------------------------------------------------------------
    be_forms: tuple[str, ...]           = ("am", "is", "are", "was", "were", "be", "been", "being")
    irregular_participles: tuple[str, ...] = (
        "given", "made", "taken", "done", "sent", "paid", "held", "kept", "known", "shown", "seen",
        "written", "begun", "built", "chosen", "found", "bought", "set", "put", "withdrawn", "left",
        "lost", "told", "met", "read", "sold", "understood", "worn", "drawn", "forgotten",
    )

    #----------------------------------------------------------------------
    # Other patterns (case-insensitive regular expressions)
    #----------------------------------------------------------------------
    hidden_verb_patterns: tuple[str, ...] = (
        r"\b(?:make|makes|made|making|give|gives|gave|giving|conduct|conducts|conducted|conducting"
        r"|perform|performs|performed|undertake|carry|carries|carried|provide|provides|provided|providing)"
        r"\s+(?:out\s+)?(?:a|an|the|any)?\s*(?:\w+\s+)?"
        r"(?:decision|determination|investigation|inspection|review|assessment|payment|adjustment"
        r"|consideration|assistance|notification|evaluation|examination|selection|modification)\b",
    )
    double_negative_patterns: tuple[str, ...] = (
        r"\b(?:not|no|never|cannot|none)\b[^.;]{0,40}?\b(?:unless|without)\b",
        r"\bnot\s+(?:uncommon|unusual|unreasonabl[ey]|unable|unlikely|unavailable|unpaid|invalid|incomplete"
        r"|impossible|ineligible|insufficient|inadequate|improper|irrelevant|unnecessary|undue|unauthorized)\b",
        r"\bnot\s+fail(?:s|ed)?\s+to\b",
    )
    injection_patterns: tuple[str, ...] = (
        r"\b(?:ignore|disregard|forget)\b.{0,60}\b(?:style guide|guidelines?|instructions?|rules?|above|previous)\b",
        r"^\s*(?:editors?|note to (?:the )?editors?|assistant|ai)\s*:",
    )
    fact_units: tuple[str, ...]         = (
        "days", "day", "weeks", "week", "months", "month", "years", "year", "hours", "hour",
        "minutes", "minute", "business days", "copies", "pages",
    )


#==========================================================================
# What to search for each issue type
#==========================================================================
@dataclass(frozen=True)
class RetrievalConfig:
    """
    Purpose: for every issue type, the guideline section to search in and the
    query text; plus how many rules to keep per issue type.
    """

    per_issue_k: int                    = 3
    section_long_sentence: str          = "concise"
    query_long_sentence: str            = "write short sentences, one idea per sentence"
    section_passive: str                = "conversational"
    query_passive: str                  = "use active voice, say who does what"
    section_shall: str                  = "conversational"
    query_shall: str                    = "use must instead of shall to indicate requirements"
    section_complex_words: str          = "words"
    query_complex_words: str            = "use simple words and phrases instead of complex ones"
    section_hidden_verb: str            = "words"
    query_hidden_verb: str              = "avoid hidden verbs, use the verb instead of a noun"
    section_double_negative: str        = "concise"
    query_double_negative: str          = "use positive language, avoid negatives and double negatives"

    #----------------------------------------------------------------------
    # Section and query of one issue type
    #----------------------------------------------------------------------
    def for_issue(self, issue: str) -> tuple[str, str]:
        """
        Look up the guideline section and the query text of an issue type.

        Input:
            . issue         : long_sentence, passive, shall, complex_words, hidden_verb or double_negative
        Output:
            . pair          : (section, query)
        """
        return getattr(self, f"section_{issue}"), getattr(self, f"query_{issue}")


#==========================================================================
# The Langflow slice: the same values in code and in the flow
#==========================================================================
@dataclass(frozen=True)
class FlowConfig:
    """
    Purpose: the "ask the guidelines" slice. rag_slice.py reads these values
    and flows/FLOW_SPEC.json is written from them, so the flow and the code
    cannot drift apart.
    """

    file_name: str                      = "plainedit_rag.json"
    k: int                              = 3
    max_tokens: int                     = 300
    parser_pattern: str                 = "[{chunk_id}] {text}"
    system: str                         = (
        "You answer questions about the U.S. Federal Plain Language Guidelines. "
        "Use only the numbered context. Cite the chunk id in square brackets. "
        "If the context does not answer the question, say you cannot find it in the guidelines."
    )
    template: str                       = "Context:\n{context}\n\nQuestion: {question}\nAnswer in at most three sentences."
    description: str                    = "Ask the guidelines: Chat Input -> embeddings -> Chroma -> parser -> prompt -> model -> Chat Output"
    questions_file: str                 = "data/guideline_questions.json"


#==========================================================================
# All sections
#==========================================================================
@dataclass(frozen=True)
class Config:
    """
    Purpose: group every section; created once in main.py and passed down.
    A project adds its own section class as one more field here.
    """

    model: ModelConfig                  = ModelConfig()
    knowledge: KnowledgeConfig          = KnowledgeConfig()
    paths: PathConfig                   = PathConfig()
    servers: ServerConfig               = ServerConfig()
    tracing: TracingConfig              = TracingConfig()
    editor: EditorConfig                = EditorConfig()
    retrieval: RetrievalConfig          = RetrievalConfig()
    flow: FlowConfig                    = FlowConfig()


#==========================================================================
# Load one TOML file
#==========================================================================
def load_config(path: Path, *, root: Path) -> Config:
    """
    Read a TOML file into Config; a typo in a section or key stops the run.

    Input:
        . path          : the TOML file, e.g. configs/app.toml
        . root          : project root that relative paths start from
    Output:
        . config        : every section, each validated by its own class
    """

    #----------------------------------------------------------------------
    # Read the file and refuse unknown sections
    #----------------------------------------------------------------------
    with path.open("rb") as file:
        raw = tomllib.load(file)
    hints   = get_type_hints(Config)
    known   = [item.name for item in fields(Config)]
    unknown = sorted(set(raw) - set(known))
    if unknown:
        raise ValueError(f"{path.name}: unknown section(s) {unknown}; known: {known}")

    #----------------------------------------------------------------------
    # Build each section from its class
    #----------------------------------------------------------------------
    sections: dict[str, Any] = {}
    for name in known:
        sections[name] = _section(hints[name], raw.get(name, {}), name=name)
    paths = sections["paths"]
    sections["paths"] = replace(
        paths, **{item.name: root / getattr(paths, item.name) for item in fields(paths)}
    )
    return Config(**sections)


#==========================================================================
# Build one section
#==========================================================================
def _section(section_class: type, values: dict[str, Any], *, name: str) -> Any:
    """
    Create one config class from its TOML table, refusing unknown keys.
    TOML arrays become tuples, so a frozen config really is immutable.

    Input:
        . section_class : the frozen dataclass of this section
        . values        : the TOML table of this section
        . name          : the section name, for the error message
    Output:
        . section       : an instance of section_class
    """
    allowed = {item.name for item in fields(section_class)}
    extra   = sorted(set(values) - allowed)
    if extra:
        raise ValueError(f"[{name}]: unknown key(s) {extra}; allowed: {sorted(allowed)}")
    return section_class(**{key: tuple(value) if isinstance(value, list) else value for key, value in values.items()})


#==========================================================================
# Switch the backend (the --fake flag)
#==========================================================================
def with_backend(config: Config, backend: str) -> Config:
    """
    Return the same config with another model backend. "fake" also uses an
    embedded collection of its own, so fake vectors never mix with real ones
    and no server is needed.

    Input:
        . config        : the loaded configuration
        . backend       : "local", "fake" or "server"
    Output:
        . config        : a new Config; the old one is unchanged
    """
    model = replace(config.model, backend=backend)
    if backend != "fake":
        return replace(config, model=model)
    knowledge = replace(
        config.knowledge,
        collection  = f"{config.knowledge.collection}-fake",
        store       = "embedded",
    )
    return replace(config, model=model, knowledge=knowledge)
