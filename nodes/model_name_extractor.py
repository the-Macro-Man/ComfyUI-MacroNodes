"""
Model Name Extractor
====================
Outputs the loaded model's filename (no path, no extension) as a STRING, for use
as SaveImage's filename_prefix - optionally as a per-model subfolder.

Pure stdlib. No network, no subprocess, no dynamic execution.
"""

import os


class ModelNameNode:
    """
    Works automatically with ANY loader - Load Checkpoint, Load Diffusion Model,
    UNETLoader, GGUF loaders, etc. It walks the workflow graph backwards from the
    MODEL input to find the loader node, then reads its filename widget.
    Switching checkpoints updates the output automatically; no typing required.

    Options:
      prefix         - text prepended to the filename, e.g. "Draft_"
      create_folder  - when enabled, output becomes "ModelName/prefixModelName" so
                       SaveImage puts images in a per-model subfolder (created if
                       absent, reused if it already exists)
      model_name     - force a literal name, overriding auto-detection

    All names are sanitised of characters that are illegal in Windows/Linux paths.
    """

    # Widget names used by loader nodes to hold the model filename, in priority order
    _NAME_WIDGETS = [
        "ckpt_name",        # CheckpointLoaderSimple / CheckpointLoader
        "unet_name",        # UNETLoader / Load Diffusion Model
        "model_name",       # various custom loaders
        "model_path",
        "gguf_name",        # ComfyUI-GGUF
        "name",
    ]

    # Reserved device names on Windows - cannot be used as a file or folder name
    _RESERVED = {
        "CON", "PRN", "AUX", "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }

    @classmethod
    def _sanitize(cls, text, fallback="model"):
        """Strip characters that are illegal in file/folder names on Windows or Linux."""
        if not text:
            return fallback
        # Illegal on Windows: < > : " / \ | ? *  - plus control characters 0-31
        cleaned = "".join(
            "_" if (ch in '<>:"/\\|?*' or ord(ch) < 32) else ch
            for ch in text
        )
        # Windows silently drops trailing dots and spaces
        cleaned = cleaned.rstrip(". ").strip()
        # Collapse runs of underscores introduced by the substitution
        while "__" in cleaned:
            cleaned = cleaned.replace("__", "_")
        if not cleaned:
            return fallback
        # Avoid reserved device names (checked against the stem, case-insensitively)
        if cleaned.split(".")[0].upper() in cls._RESERVED:
            cleaned = f"_{cleaned}"
        return cleaned

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
            },
            "optional": {
                "prefix": ("STRING", {
                    "default": "", "multiline": False,
                    "tooltip": "Optional text prepended to the filename, e.g. 'Draft_'"}),
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

    def _walk_graph(self, prompt, node_id, depth=0, seen=None):
        """Walk backwards from node_id through links to find a loader's filename widget."""
        if seen is None:
            seen = set()
        if depth > 24 or node_id is None or node_id in seen:
            return None
        seen.add(node_id)

        node = prompt.get(str(node_id))
        if not isinstance(node, dict):
            return None
        inputs = node.get("inputs", {})

        # Does this node itself carry a model filename widget?
        for widget in self._NAME_WIDGETS:
            val = inputs.get(widget)
            if isinstance(val, str) and val.strip():
                return val

        # Otherwise follow upstream links. A link looks like [source_node_id, output_index].
        # Prefer an input literally named "model", then try any other link.
        ordered = []
        if "model" in inputs:
            ordered.append(inputs["model"])
        ordered += [v for k, v in inputs.items() if k != "model"]

        for link in ordered:
            if isinstance(link, list) and len(link) >= 1:
                found = self._walk_graph(prompt, link[0], depth + 1, seen)
                if found:
                    return found
        return None

    def get_name(self, model, prefix="", create_folder=False, model_name="",
                 prompt=None, unique_id=None):
        raw = None

        # 1. Explicit override wins
        if model_name and model_name.strip():
            raw = model_name.strip()

        # 2. Trace the workflow graph back to the loader node
        if raw is None and prompt and unique_id is not None:
            try:
                raw = self._walk_graph(prompt, unique_id)
            except Exception as e:
                print(f"[MacroNodes] ModelNameExtractor: graph walk failed: {e}")

        # 3. Fall back to inspecting the model object itself
        if raw is None:
            for obj in [model, getattr(model, "model", None)]:
                if obj is None:
                    continue
                fn = getattr(obj, "filename", None)
                if isinstance(fn, str) and fn:
                    raw = fn
                    break
                try:
                    for val in vars(obj).values():
                        if isinstance(val, str) and val.endswith(
                                (".safetensors", ".ckpt", ".gguf", ".pt", ".pth")):
                            raw = val
                            break
                except Exception:
                    pass
                if raw:
                    break

        if not raw:
            print("[MacroNodes] ModelNameExtractor: could not determine model name.")
            raw = "unknown_model"

        # Strip directory (handles both / and \ separators) and file extension
        base = raw.replace("\\", "/").split("/")[-1]
        name = self._sanitize(os.path.splitext(base)[0], fallback="unknown_model")

        clean_prefix = self._sanitize(prefix, fallback="") if prefix else ""
        filename = f"{clean_prefix}{name}" if clean_prefix else name

        if create_folder:
            # A forward slash in filename_prefix makes SaveImage write into that
            # subfolder of the output directory, creating it if it doesn't exist.
            result = f"{name}/{filename}"
            print(f"[MacroNodes] Model: {name}  ->  folder '{name}/', file '{filename}_'")
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
