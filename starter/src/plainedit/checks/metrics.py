"""Measure a text with plain code: sentence length, shall, complex words, passive voice, ...

The model never measures anything. Every number the graph shows an editor
comes from here, so a run can be repeated and an evaluator can recompute it.

passive_hits is a HEURISTIC: a form of "to be" followed by a word ending in
-ed (not -eed) or an irregular participle. It misses passives with other
shapes ("got paid") and flags adjectives ("is interested"); the report must
say so.
"""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

import  re
from    functools                       import  lru_cache
from    typing                          import  Any

from    plainedit.config                import  EditorConfig


#==========================================================================
# Sentences
#==========================================================================
def split_sentences(text: str, *, editor: EditorConfig) -> list[str]:
    """
    Split a text into sentences at . ! ? followed by a space, and at line
    breaks; dots of the configured abbreviations do not end a sentence.

    Input:
        . text          : a notice
        . editor        : abbreviations
    Output:
        . sentences     : non-empty sentences in order
    """
    for abbreviation in editor.abbreviations:
        text = text.replace(abbreviation, abbreviation.replace(".", "\x00"))
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [part.replace("\x00", ".").strip() for part in parts if part.strip()]


#==========================================================================
# Words
#==========================================================================
def count_words(text: str) -> int:
    """
    Count whitespace-separated tokens that contain a letter or a digit.

    Input:
        . text          : any text
    Output:
        . words         : number of words
    """
    return sum(1 for token in text.split() if re.search(r"\w", token))


#==========================================================================
# Words of a text, normalised
#==========================================================================
def normalize_words(text: str) -> str:
    """
    Lower-case the text and turn every punctuation run into one space, so a
    quote can be compared with its notice by plain substring.

    Input:
        . text          : a quote or a notice
    Output:
        . words         : lower-case words separated by single spaces
    """
    return " ".join(re.sub(r"[^\w]+", " ", text.lower()).split())


#==========================================================================
# Find every issue in a text
#==========================================================================
def find_issues(text: str, *, editor: EditorConfig, swaps: list[dict[str, str]]) -> dict[str, list[str]]:
    """
    Find the text of every issue, by type. The lists are what the editor and
    the rewrite feedback quote; counts are derived from them.

    Input:
        . text          : a notice or a rewrite
        . editor        : limit and patterns
        . swaps         : word_swaps.json rows
    Output:
        . found         : issue type -> list of quoted sentences or phrases
    """
    sentences = split_sentences(text, editor=editor)
    return {
        "long_sentence": [item for item in sentences if count_words(item) > editor.sentence_limit],
        "passive": _matches([_passive_pattern(editor)], text),
        "shall": _matches([r"\bshall\b(?:\s+\w+){0,3}"], text),
        "complex_words": _complex(text, swaps),
        "hidden_verb": _matches(list(editor.hidden_verb_patterns), text),
        "double_negative": _matches(list(editor.double_negative_patterns), text),
    }


#==========================================================================
# Measure a text
#==========================================================================
def measure(text: str, *, editor: EditorConfig, swaps: list[dict[str, str]]) -> dict[str, Any]:
    """
    Compute the metrics of a text: sizes, one count per issue type and the
    weighted issue_score.

    Input:
        . text          : a notice or a rewrite
        . editor        : limit, weights, patterns
        . swaps         : word_swaps.json rows
    Output:
        . metrics       : words, sentences, max_sentence_words, avg_sentence_words,
                          long_sentences, shall_count, complex_words, passive_hits,
                          hidden_verbs, double_negatives, issue_score
    """

    #----------------------------------------------------------------------
    # Find the issues and the sentence lengths
    #----------------------------------------------------------------------
    found   = find_issues(text, editor=editor, swaps=swaps)
    lengths = [count_words(item) for item in split_sentences(text, editor=editor)] or [0]
    counts  = {
        "long_sentences": len(found["long_sentence"]),
        "passive_hits": len(found["passive"]),
        "shall_count": len(found["shall"]),
        "complex_words": len(found["complex_words"]),
        "hidden_verbs": len(found["hidden_verb"]),
        "double_negatives": len(found["double_negative"]),
    }

    #----------------------------------------------------------------------
    # Assemble the metrics
    #----------------------------------------------------------------------
    return {
        "words": count_words(text),
        "sentences": len(lengths),
        "max_sentence_words": max(lengths),
        "avg_sentence_words": round(sum(lengths) / len(lengths), 1),
        **counts,
        "issue_score": issue_score(counts, editor=editor),
    }


#==========================================================================
# Weighted issue score
#==========================================================================
def issue_score(counts: dict[str, int], *, editor: EditorConfig) -> int:
    """
    Add the issue counts, each times its weight from the config.

    Input:
        . counts        : long_sentences, passive_hits, shall_count, complex_words,
                          hidden_verbs, double_negatives
        . editor        : the w_* weights
    Output:
        . score         : 0 means no detected issue
    """
    return (
        editor.w_long_sentence * counts["long_sentences"]
        + editor.w_passive * counts["passive_hits"]
        + editor.w_shall * counts["shall_count"]
        + editor.w_complex * counts["complex_words"]
        + editor.w_hidden_verb * counts["hidden_verbs"]
        + editor.w_double_negative * counts["double_negatives"]
    )


#==========================================================================
# Which issue types a text has
#==========================================================================
def detected_issues(found: dict[str, list[str]], *, editor: EditorConfig) -> list[str]:
    """
    List the issue types with at least one hit, in the configured order.

    Input:
        . found         : from find_issues
        . editor        : issue_types order
    Output:
        . issues        : e.g. ["long_sentence", "passive"]
    """
    return [issue for issue in editor.issue_types if found[issue]]


#==========================================================================
# Count of one issue type in a metrics dict
#==========================================================================
def issue_count(metrics: dict[str, Any], issue: str) -> int:
    """
    Read the count of one issue type from measure() output.

    Input:
        . metrics       : from measure
        . issue         : long_sentence, passive, shall, complex_words, hidden_verb, double_negative
    Output:
        . count         : how many hits the metrics recorded
    """
    keys = {
        "long_sentence": "long_sentences",
        "passive": "passive_hits",
        "shall": "shall_count",
        "complex_words": "complex_words",
        "hidden_verb": "hidden_verbs",
        "double_negative": "double_negatives",
    }
    return metrics[keys[issue]]


#==========================================================================
# Length ratio
#==========================================================================
def length_ratio(original: str, rewrite: str) -> float:
    """
    Compare the size of a rewrite with its original; a very short rewrite
    probably dropped content, a very long one probably added some.

    Input:
        . original      : the notice
        . rewrite       : the rewrite
    Output:
        . ratio         : words(rewrite) / words(original)
    """
    return round(count_words(rewrite) / max(1, count_words(original)), 2)


#==========================================================================
# Passive voice pattern
#==========================================================================
def _passive_pattern(editor: EditorConfig) -> str:
    """
    Build the passive-voice regular expression from the config: a form of
    "to be", an optional adverb or "not", then a participle.

    Input:
        . editor        : be_forms, irregular_participles
    Output:
        . pattern       : a regular expression (use with re.IGNORECASE)
    """
    be         = "|".join(editor.be_forms)
    irregular  = "|".join(editor.irregular_participles)
    return rf"\b(?:{be})\b(?:\s+\w+ly)?(?:\s+not)?\s+(?:\w{{2,}}(?<!e)ed|{irregular})\b"


#==========================================================================
# Regex matches
#==========================================================================
def _matches(patterns: list[str], text: str) -> list[str]:
    """
    Return the matched text of every pattern, case-insensitive, in text order.

    Input:
        . patterns      : regular expressions
        . text          : the text to search
    Output:
        . hits          : matched strings
    """
    found = [match for pattern in patterns for match in re.finditer(pattern, text, re.IGNORECASE)]
    return [" ".join(match.group(0).split()) for match in sorted(found, key=lambda match: match.start())]


#==========================================================================
# Complex words from the swap table
#==========================================================================
def _complex(text: str, swaps: list[dict[str, str]]) -> list[str]:
    """
    Find every word or phrase of word_swaps.json in the text, longest
    entries first so "in the event that" wins over "in the event".

    Input:
        . text          : the text to search
        . swaps         : word_swaps.json rows
    Output:
        . hits          : the found terms, lower-case, in text order
    """
    terms = tuple(sorted({row["complex"] for row in swaps}, key=lambda term: (-len(term), term)))
    return [hit.lower() for hit in _matches([_swap_pattern(terms)], text)]


#==========================================================================
# Compiled swap pattern
#==========================================================================
@lru_cache(maxsize=4)
def _swap_pattern(terms: tuple[str, ...]) -> str:
    """
    Join the complex terms into one alternation with word boundaries.

    Input:
        . terms         : complex words and phrases, longest first
    Output:
        . pattern       : a regular expression string
    """
    return r"\b(?:" + "|".join(re.escape(term) for term in terms) + r")\b"
