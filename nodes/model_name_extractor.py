"""
Model Name Extractor
====================
Outputs the loaded model's filename (no path, no extension) as a STRING, for use
as SaveImage's filename_prefix - optionally as a per-model subfolder.

Works with any saver: SaveImage, SaveAnimatedWEBP, video nodes, third-party save
nodes. Save Image (Macro) in this pack does more, but only for images; this node
stays the general-purpose option.

Pure stdlib. No network, no subprocess, no dynamic execution.
"""

from ._shared import base_name, model_name_from_graph, model_name_from_object, sanitize


class ModelNameNode:
    """
    Works automatically with ANY loader - Load Checkpoint, Load Diffusion Model,
    UNETLoader, GGUF loaders, etc. It walks the workflow graph backwards from the
    MODEL input to find the loader node, then reads its filename widget.
    Switching checkpoints updates the output automatically; no typing required.

    Options:
      prefix         - text prepended to the filename, e.g. "Draft_"
      folder_prefix  - text prepended to the folder name, e.g. "art_"
      create_folder  - when enabled, output becomes "folder/prefixModelName" so
                       SaveImage puts images in a per-model subfolder (created if
                       absent, reused if it already exists)
      model_name     - force a literal name, overriding auto-detection

    All names are sanitised of characters that are illegal in Windows/Linux paths.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
            },
            "optional": {
                "prefix": ("STRING", {
                    "default": "", "multiline": False,
                    "tooltip": "Text prepended to the FILE name, e.g. 'Draft_'"}),
                "folder_prefix": ("STRING", {
                    "default": "", "multiline": False,
                    "tooltip": "Text prepended to the FOLDER name, e.g. 'art_' gives "
                               "art_krea2_turbo/. Only used when create_folder is on."}),
                "create_folder": ("BOOLEAN", {
                    "default": False,
                    "label_on": "folder per model", "label_off": "flat (no folder)",
                    "tooltip": "ON: save into a subfolder named after the model (created if it "
                               "doesn't exist). OFF: save directly in the output folder."}),
                "model_name": ("STRING", {
                    "default": "", "multiline": False,
                    "tooltip": "Leave blank for automatic detection. Type a name here only to "
                               "force a specific value."}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("model_name",)
    FUNCTION = "get_name"
    CATEGORY = "MacroNodes/utils"
    OUTPUT_NODE = False
    DESCRIPTION = ("Names your saved files after the model that made them. Connect to "
                   "SaveImage's filename_prefix; switch checkpoints and the name follows.")

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # Always re-evaluate so switching checkpoints updates the filename immediately
        return float("nan")

    def get_name(self, model, prefix="", folder_prefix="", create_folder=False,
                 model_name="", prompt=None, unique_id=None):
        raw = None

        # 1. Explicit override wins
        if model_name and model_name.strip():
            raw = model_name.strip()

        # 2. Trace the workflow graph back to the loader node
        if raw is None and prompt and unique_id is not None:
            try:
                raw = model_name_from_graph(prompt, unique_id)
            except Exception as e:
                print(f"[MacroNodes] ModelNameExtractor: graph walk failed: {e}")

        # 3. Fall back to inspecting the model object itself
        if raw is None:
            raw = model_name_from_object(model)

        if not raw:
            print("[MacroNodes] ModelNameExtractor: could not determine model name.")
            raw = "unknown_model"

        name = base_name(raw)

        clean_prefix = sanitize(prefix, fallback="") if prefix else ""
        filename = f"{clean_prefix}{name}" if clean_prefix else name

        if create_folder:
            clean_folder_prefix = sanitize(folder_prefix, fallback="") if folder_prefix else ""
            folder = f"{clean_folder_prefix}{name}" if clean_folder_prefix else name
            # A forward slash in filename_prefix makes SaveImage write into that
            # subfolder of the output directory, creating it if it doesn't exist.
            result = f"{folder}/{filename}"
            print(f"[MacroNodes] Model: {name}  ->  folder '{folder}/', file '{filename}_'")
        else:
            result = filename
            print(f"[MacroNodes] Model: {name}  ->  file '{filename}_'")

        return (result,)


NODE_CLASS_MAPPINGS = {
    "ModelNameExtractor": ModelNameNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ModelNameExtractor": "Model Name Extractor",
}
