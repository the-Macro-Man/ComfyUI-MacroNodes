"""
MacroNodes
==========
A small collection of quality-of-life nodes for ComfyUI.

Nodes are defined one per module under nodes/ and collected here. Each module
exposes NODE_CLASS_MAPPINGS and NODE_DISPLAY_NAME_MAPPINGS; this file merges
them and reports duplicates rather than letting one silently overwrite another.

https://github.com/the-Macro-Man/ComfyUI-MacroNodes
"""

from .nodes import MODULES

__version__ = "1.2.0"

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

for _module in MODULES:
    for _key, _cls in getattr(_module, "NODE_CLASS_MAPPINGS", {}).items():
        if _key in NODE_CLASS_MAPPINGS:
            print(f"[MacroNodes] Duplicate node id '{_key}' in {_module.__name__}; skipping.")
            continue
        NODE_CLASS_MAPPINGS[_key] = _cls
    for _key, _label in getattr(_module, "NODE_DISPLAY_NAME_MAPPINGS", {}).items():
        NODE_DISPLAY_NAME_MAPPINGS.setdefault(_key, _label)

print(f"[MacroNodes] v{__version__} loaded {len(NODE_CLASS_MAPPINGS)} node(s): "
      f"{', '.join(sorted(NODE_CLASS_MAPPINGS))}")

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "__version__"]
