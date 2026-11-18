"""Turn tool calls into text for a local model, and its <tool_call> text back.

Hosted APIs force a tool call while decoding. A local Qwen model only sees the
tools in its chat template and writes <tool_call>{json}</tool_call> blocks;
when a call is required it is asked to in the system text.
"""

#==========================================================================
# Imports
#==========================================================================
from    __future__                      import  annotations

import  json
import  re
import  uuid
from    typing                          import  Any

from    plainedit.ai_logger             import  aiLogger


#==========================================================================
# Ask for a tool call when the caller requires one
#==========================================================================
def with_tool_instruction(
    dicts: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
    tool_choice: Any,
) -> list[dict[str, Any]]:
    """
    Add one sentence to the system message when tool_choice forces a call
    (with_structured_output binds "any"; OpenAI clients send "required" or
    {"type": "function", "function": {"name": ...}}).

    Input:
        . dicts         : chat-template messages (role, content)
        . tools         : OpenAI tool schemas, or None
        . tool_choice   : None, "auto", "none", "any", "required", a name or a dict
    Output:
        . dicts         : the same messages, the system text extended if forced
    """
    if not tools or not tool_choice or tool_choice in ("auto", "none"):
        return dicts
    name = None
    if isinstance(tool_choice, dict):
        name = tool_choice.get("function", {}).get("name")
    elif tool_choice not in ("any", "required"):
        name = tool_choice
    if name:
        must = f"You must answer by calling the function {name} inside <tool_call></tool_call> tags."
    else:
        must = "You must answer by calling one of the functions inside <tool_call></tool_call> tags."
    if dicts and dicts[0]["role"] == "system":
        return [dict(dicts[0], content=f"{dicts[0]['content']}\n{must}"), *dicts[1:]]
    return [{"role": "system", "content": must}, *dicts]


#==========================================================================
# Read <tool_call> blocks out of generated text
#==========================================================================
def parse_tool_calls(text: str) -> tuple[str, list[dict[str, Any]]]:
    """
    Split generated text into its answer text and LangChain tool calls. A
    small model often forgets the closing </tool_call> tag, keeps writing
    after the JSON, or drops the last closing brace: the first complete JSON
    value after <tool_call> is used, and up to two missing closing braces are
    added when a closing tag follows (a warning says so). Anything else
    unreadable stays in the text, where a person or a test sees it.

    Input:
        . text          : decoded model output
    Output:
        . content       : the text without the readable tool-call blocks
        . calls         : [{"name", "args", "id", "type": "tool_call"}, ...]
    """

    #----------------------------------------------------------------------
    # Parse each block; keep the unreadable ones as text
    #----------------------------------------------------------------------
    calls   = []
    content = text
    for match in re.finditer(r"<tool_call>\s*", text):
        data, end = _read_json(text, match.end())
        if data is None or "name" not in data:
            aiLogger.warning("Unreadable tool call kept as text: %s", text[match.end():][:80])
            continue
        calls.append({
            "name": data["name"],
            "args": data.get("arguments", {}),
            "id": f"call_{uuid.uuid4().hex[:8]}",
            "type": "tool_call",
        })
        closing = re.match(r"\s*</tool_call>", text[end:])
        content = content.replace(text[match.start() : end + (closing.end() if closing else 0)], "", 1)
    return content.strip(), calls


#==========================================================================
# Read one JSON object after <tool_call>
#==========================================================================
def _read_json(text: str, start: int) -> tuple[dict[str, Any] | None, int]:
    """
    Decode the first JSON object that starts at `start`. When it is cut
    short but </tool_call> follows, add up to two closing braces.

    Input:
        . text          : the whole generated text
        . start         : index just after <tool_call>
    Output:
        . data          : the decoded object, or None
        . end           : index just after the object in `text` (start when None)
    """
    decoder = json.JSONDecoder()

    #----------------------------------------------------------------------
    # The first complete JSON value, whatever follows it
    #----------------------------------------------------------------------
    try:
        data, size = decoder.raw_decode(text[start:])
        return (data, start + size) if isinstance(data, dict) else (None, start)
    except json.JSONDecodeError:
        pass

    #----------------------------------------------------------------------
    # Cut short: add closing braces, but only when the closing tag follows
    #----------------------------------------------------------------------
    close = text.find("</tool_call>", start)
    if close < 0:
        return None, start
    for extra in ("}", "}}"):
        try:
            data, _ = decoder.raw_decode(text[start:close].rstrip() + extra)
        except json.JSONDecodeError:
            continue
        aiLogger.warning("Tool call repaired: %d missing closing brace(s) added", len(extra))
        return (data, close) if isinstance(data, dict) else (None, start)
    return None, start
