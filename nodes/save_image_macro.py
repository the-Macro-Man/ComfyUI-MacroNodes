"""
Save Image (Macro)
==================
SaveImage, named after the model that made the picture, with control over what
goes with it.

Why this exists rather than Model Name Extractor plus core SaveImage:

- **The workflow JSON pairs exactly.** This node does the saving, so it knows the
  counter. `art_krea2_00007_.png` gets `art_krea2_00007_.json`. A node that only
  hands SaveImage a string cannot know which number SaveImage will land on.
- **Metadata can be turned off per node.** ComfyUI's only switch is the global
  `--disable-metadata`, which also kills the JSON. Here `embed_workflow` is off
  for this node alone, so `embed_workflow=false` with `save_workflow_json=true`
  gives clean images to post publicly and the recipe kept beside them on disk.
- **Path shortening can be measured.** Only this node knows the real output
  directory and final filename, so it can shorten only when the path would
  actually break, instead of truncating names that were fine.

Uses PIL and numpy, both of which ComfyUI already requires. No network, no
subprocess, no dynamic execution.
"""

import json
import os

import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo

import folder_paths

from ._shared import (base_name, model_name_from_graph, sanitize, shorten_to_fit)


class SaveImageMacroNode:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.compress_level = 4

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE", {"tooltip": "The images to save."}),
            },
            "optional": {
                "folder_prefix": ("STRING", {
                    "default": "", "multiline": False,
                    "tooltip": "Text prepended to the FOLDER name, e.g. 'art_' gives "
                               "art_krea2_turbo/. Only used when create_folder is on."}),
                "file_prefix": ("STRING", {
                    "default": "", "multiline": False,
                    "tooltip": "Text prepended to the FILE name, e.g. 'draft_'."}),
                "create_folder": ("BOOLEAN", {
                    "default": True,
                    "label_on": "folder per model", "label_off": "flat (no folder)",
                    "tooltip": "ON: save into a subfolder named after the model."}),
                "embed_workflow": ("BOOLEAN", {
                    "default": True,
                    "label_on": "workflow in PNG", "label_off": "strip metadata",
                    "tooltip": "OFF writes a clean PNG with no prompt or workflow inside - "
                               "safe to post publicly. Combine with save_workflow_json to "
                               "keep the workflow beside the file instead."}),
                "save_workflow_json": ("BOOLEAN", {
                    "default": False,
                    "label_on": "write .json", "label_off": "no .json",
                    "tooltip": "Writes the workflow next to each image, with a matching "
                               "number. Drag the .json into ComfyUI to reload the graph."}),
                "save_summary_txt": ("BOOLEAN", {
                    "default": False,
                    "label_on": "write .txt", "label_off": "no .txt",
                    "tooltip": "A short readable summary - model, LoRAs, sampler, steps, "
                               "CFG, seed, prompt. Greppable without opening ComfyUI."}),
                "shorten_if_needed": ("BOOLEAN", {
                    "default": True,
                    "label_on": "shorten long paths", "label_off": "never shorten",
                    "tooltip": "Only acts when the finished path would exceed the Windows "
                               "260-character limit. Drops _fp8_scaled and similar first, "
                               "then truncates. Short names are never touched."}),
                "model_name": ("STRING", {
                    "default": "", "multiline": False,
                    "tooltip": "Leave blank to detect from the graph. Type a name to force one."}),
                "text": ("STRING", {
                    "forceInput": True,
                    "tooltip": "Text to save beside each image, numbered to match. Connect "
                               "the prompt you actually used - the auto summary is a guess "
                               "assembled from the graph, this is the real thing. Writes "
                               "the .txt even when save_summary_txt is off."}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "save"
    OUTPUT_NODE = True
    CATEGORY = "MacroNodes/image"
    DESCRIPTION = ("Saves PNGs named after the model that made them. Can strip the workflow "
                   "from the image and write it alongside instead, so you can share the "
                   "picture without sharing the prompt.")

    # ── naming ───────────────────────────────────────────────────────────────

    def _resolve_model_name(self, model_name, prompt, unique_id):
        if model_name and model_name.strip():
            return base_name(model_name.strip())
        if prompt and unique_id is not None:
            try:
                raw = model_name_from_graph(prompt, unique_id)
                if raw:
                    return base_name(raw)
            except Exception as e:
                print(f"[MacroNodes] SaveImage: graph walk failed: {e}")
        print("[MacroNodes] SaveImage: could not determine model name.")
        return "unknown_model"

    # ── summary sidecar ──────────────────────────────────────────────────────

    @staticmethod
    def _summarise(prompt, model):
        """
        Readable one-screen summary pulled from the API prompt.

        Best-effort by design: it looks for the widget names the common samplers
        and loaders use and simply omits anything it cannot find, rather than
        guessing or raising in the middle of a save.
        """
        lines = [f"model: {model}"]
        if not isinstance(prompt, dict):
            return "\n".join(lines) + "\n"

        loras, sampler, texts = [], {}, []
        for node in prompt.values():
            if not isinstance(node, dict):
                continue
            ins = node.get("inputs", {})
            ctype = str(node.get("class_type", ""))

            if "lora" in ctype.lower():
                for k in ("lora_name", "lora"):
                    if isinstance(ins.get(k), str) and ins[k].strip():
                        sm = ins.get("strength_model", ins.get("strength"))
                        loras.append(f"{ins[k]}" + (f" @ {sm}" if sm is not None else ""))
                        break

            if "steps" in ins and "cfg" in ins:
                for k in ("steps", "cfg", "sampler_name", "scheduler", "seed", "denoise"):
                    if k in ins and not isinstance(ins[k], list):
                        sampler.setdefault(k, ins[k])

            if "text" in ins and isinstance(ins["text"], str) and ins["text"].strip():
                texts.append(ins["text"].strip())

        # Heuristic: of the CLIPTextEncode nodes, the longest is almost always
        # the positive prompt and the next longest the negative. Collect first
        # and rank afterwards - comparing pairwise while iterating drops the
        # negative whenever the positive happens to be seen first.
        texts.sort(key=len, reverse=True)
        positive = texts[0] if texts else None
        negative = texts[1] if len(texts) > 1 else None

        if loras:
            lines.append("loras: " + ", ".join(dict.fromkeys(loras)))
        for k in ("sampler_name", "scheduler", "steps", "cfg", "denoise", "seed"):
            if k in sampler:
                lines.append(f"{k}: {sampler[k]}")
        if positive:
            lines.append("\npositive:\n" + positive)
        if negative:
            lines.append("\nnegative:\n" + negative)
        return "\n".join(lines) + "\n"

    # ── main ─────────────────────────────────────────────────────────────────

    def save(self, images, folder_prefix="", file_prefix="", create_folder=True,
             embed_workflow=True, save_workflow_json=False, save_summary_txt=False,
             shorten_if_needed=True, model_name="", text=None, prompt=None,
             extra_pnginfo=None, unique_id=None):

        name = self._resolve_model_name(model_name, prompt, unique_id)

        clean_file_prefix = sanitize(file_prefix, fallback="") if file_prefix else ""
        clean_folder_prefix = sanitize(folder_prefix, fallback="") if folder_prefix else ""

        if shorten_if_needed:
            # Everything in the path that is not the model name: output dir,
            # separators, the prefixes, "_00001_.png" and a little headroom for
            # the .json/.txt sidecars sharing the stem.
            overhead = (len(self.output_dir) + 2
                        + len(clean_folder_prefix) + len(clean_file_prefix)
                        + len("_00001_.png") + 8)
            name, note = shorten_to_fit(name, overhead, doubled=create_folder)
            if note:
                print(f"[MacroNodes] SaveImage: {note}")

        filename = f"{clean_file_prefix}{name}" if clean_file_prefix else name
        if create_folder:
            folder = f"{clean_folder_prefix}{name}" if clean_folder_prefix else name
            filename_prefix = f"{folder}/{filename}"
        else:
            filename_prefix = filename

        full_output_folder, filename, counter, subfolder, _ = \
            folder_paths.get_save_image_path(
                filename_prefix, self.output_dir, images[0].shape[1], images[0].shape[0])

        # Respect ComfyUI's global switch as well as this node's own toggle.
        try:
            from comfy.cli_args import args
            globally_disabled = bool(args.disable_metadata)
        except Exception:
            globally_disabled = False
        write_metadata = embed_workflow and not globally_disabled

        workflow = (extra_pnginfo or {}).get("workflow")
        results = []

        for image in images:
            arr = 255.0 * image.cpu().numpy()
            img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

            metadata = None
            if write_metadata:
                metadata = PngInfo()
                if prompt is not None:
                    metadata.add_text("prompt", json.dumps(prompt))
                for k, v in (extra_pnginfo or {}).items():
                    metadata.add_text(k, json.dumps(v))

            stem = f"{filename}_{counter:05}_"
            img.save(os.path.join(full_output_folder, stem + ".png"),
                     pnginfo=metadata, compress_level=self.compress_level)

            if save_workflow_json:
                if workflow is None:
                    print("[MacroNodes] SaveImage: no workflow available to write "
                          "(ComfyUI sends it only from the UI, not from the API).")
                else:
                    try:
                        with open(os.path.join(full_output_folder, stem + ".json"),
                                  "w", encoding="utf-8") as fh:
                            json.dump(workflow, fh, indent=2)
                    except Exception as e:
                        print(f"[MacroNodes] SaveImage: could not write .json: {e}")

            # Connected text wins the top of the file; the generated summary is
            # appended under it when both are wanted. Connecting text is taken as
            # intent to write the sidecar, so the toggle is not also required.
            supplied = (text or "").strip()
            if supplied or save_summary_txt:
                parts = []
                if supplied:
                    parts.append(supplied)
                if save_summary_txt:
                    summary = self._summarise(prompt, name)
                    parts.append(("--- workflow summary ---\n" + summary)
                                 if supplied else summary)
                try:
                    with open(os.path.join(full_output_folder, stem + ".txt"),
                              "w", encoding="utf-8") as fh:
                        fh.write("\n\n".join(parts).rstrip() + "\n")
                except Exception as e:
                    print(f"[MacroNodes] SaveImage: could not write .txt: {e}")

            results.append({"filename": stem + ".png",
                            "subfolder": subfolder,
                            "type": self.type})
            counter += 1

        extras = []
        if save_workflow_json:
            extras.append(".json")
        if (text or "").strip() or save_summary_txt:
            extras.append(".txt")
        print(f"[MacroNodes] Saved {len(results)} image(s) to "
              f"{subfolder or 'output root'}/ as {filename}_*"
              + (f" (+{', '.join(extras)})" if extras else "")
              + ("" if write_metadata else "  [metadata stripped]"))

        return {"ui": {"images": results}}


NODE_CLASS_MAPPINGS = {
    "SaveImageMacro": SaveImageMacroNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SaveImageMacro": "Save Image (Macro)",
}
