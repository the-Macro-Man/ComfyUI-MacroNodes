"""
Concat Text (Macro)
===================
Joins up to ten inputs into one string.

What it does that the other concat nodes do not:

- **Takes any type, not just STRING.** ComfyUI refuses to link `OLLAMA_META` or
  `OLLAMA_HISTORY` into a STRING socket, which is why people end up inserting a
  `Preview as Text` purely to launder the type. These inputs are wildcards and
  non-strings are serialised here instead, so those outputs connect directly.
- **A delimiter that can contain newlines.** Other nodes use a single-line
  widget and special-case the exact value `\\n`, so `\\n----\\n` comes through
  literally. Escapes here are expanded wherever they appear.
- **Optional labels.** Prints `=== text2 ===` above each block, which is what
  you want when a chain of prefix + generated prompt + triggers produces
  something unexpected and you need to see which part did it.

Pure stdlib.
"""

import json

try:
    # ComfyUI's own wildcard marker, used by core's PreviewAny.
    from comfy.comfy_types.node_typing import IO
    ANY = IO.ANY
except Exception:
    class _Any(str):
        """Compares equal to every type name, which is how ComfyUI spells 'any'."""
        def __ne__(self, other):
            return False

    ANY = _Any("*")

SLOTS = 10
ESCAPES = [("\\\\", "\x00"), ("\\n", "\n"), ("\\t", "\t"), ("\\r", "\r")]


def expand_escapes(s: str) -> str:
    """
    Turn the two-character sequence \\n into a real newline, anywhere in the
    string. The backslash is parked on a sentinel first so that a literal \\\\n
    stays a backslash followed by an n rather than becoming a newline.
    """
    for src, dst in ESCAPES:
        s = s.replace(src, dst)
    return s.replace("\x00", "\\")


def stringify(v) -> str:
    """
    Any value to text, matching core PreviewAny so output is consistent with
    what people already see in a Preview node.
    """
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, (int, float, bool)):
        return str(v)
    try:
        return json.dumps(v, indent=4, ensure_ascii=False)
    except Exception:
        try:
            return str(v)
        except Exception:
            return "(value exists but could not be serialised)"


class ConcatTextNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "delimiter": ("STRING", {
                    "default": "\\n\\n", "multiline": False,
                    "tooltip": r"Text placed between blocks. \n, \t and \r are expanded "
                               r"anywhere in the value, so \n----\n works. Use \\ for a "
                               r"literal backslash."}),
                "labels": ("BOOLEAN", {
                    "default": False,
                    "label_on": "=== labels ===", "label_off": "no labels",
                    "tooltip": "Print the socket name above each block. Renaming an input "
                               "changes its label, so they stay meaningful."}),
                "trim": ("BOOLEAN", {
                    "default": True,
                    "label_on": "trim", "label_off": "keep whitespace",
                    "tooltip": "Strip leading and trailing whitespace from each block "
                               "before joining."}),
                "skip_empty": ("BOOLEAN", {
                    "default": True,
                    "label_on": "skip empty", "label_off": "keep empty",
                    "tooltip": "Leave unconnected or blank slots out entirely. Off means "
                               "they contribute an empty block and a delimiter."}),
            },
            "optional": {
                f"text{i}": (ANY, {
                    "tooltip": "Any type. Strings pass through; anything else is "
                               "serialised, so OLLAMA_META and OLLAMA_HISTORY can "
                               "connect straight in."})
                for i in range(1, SLOTS + 1)
            },
            "hidden": {"unique_id": "UNIQUE_ID"},
        }

    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("concat", "block_count")
    FUNCTION = "concat"
    CATEGORY = "MacroNodes/utils"
    OUTPUT_NODE = False
    DESCRIPTION = ("Joins up to ten inputs of any type into one string. Handles newlines "
                   "in the delimiter, can label each block, and accepts non-STRING inputs "
                   "directly instead of needing a Preview node to convert them.")

    def concat(self, delimiter="\\n\\n", labels=False, trim=True, skip_empty=True,
               unique_id=None, **slots):
        sep = expand_escapes(delimiter)

        blocks = []
        for i in range(1, SLOTS + 1):
            name = f"text{i}"
            if name not in slots:
                continue
            text = stringify(slots[name])
            if trim:
                text = text.strip()
            if skip_empty and not text:
                continue
            blocks.append(f"=== {name} ===\n{text}" if labels else text)

        out = sep.join(blocks)
        print(f"[MacroNodes] Concat: {len(blocks)} block(s), {len(out)} chars")
        return (out, len(blocks))


NODE_CLASS_MAPPINGS = {
    "ConcatTextMacro": ConcatTextNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ConcatTextMacro": "Concat Text (Macro)",
}
