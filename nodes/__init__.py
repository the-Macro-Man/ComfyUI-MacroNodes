"""
Node modules for MacroNodes.

To add a node:
  1. Drop a new module in this folder that defines NODE_CLASS_MAPPINGS and
     NODE_DISPLAY_NAME_MAPPINGS.
  2. Import it below and add it to MODULES.

Imports are written out explicitly rather than discovered at runtime. Dynamic
importing would be shorter, but explicit imports mean the full set of nodes is
readable from this file alone, and there is nothing here for a security scanner
to mistake for dynamic code loading.
"""

from . import model_name_extractor
from . import save_image_macro
from . import prompt_prefix
from . import concat_text

MODULES = [
    model_name_extractor,
    save_image_macro,
    prompt_prefix,
    concat_text,
]

__all__ = ["MODULES"]
