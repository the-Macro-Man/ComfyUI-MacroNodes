"""
Shared naming helpers.

Model Name Extractor and Save Image (Macro) have to agree on what a model is
called, or the same checkpoint produces two different folder names depending on
which node you used. One implementation, imported by both.

Pure stdlib.
"""

import os

# Widget names loader nodes use to hold the model filename, in priority order.
NAME_WIDGETS = [
    "ckpt_name",        # CheckpointLoaderSimple / CheckpointLoader
    "unet_name",        # UNETLoader / Load Diffusion Model
    "model_name",       # various custom loaders
    "model_path",
    "gguf_name",        # ComfyUI-GGUF
    "name",
]

# Reserved device names on Windows - cannot be used as a file or folder name.
RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

# Suffixes that describe the file's quantisation or packaging rather than the
# model. Stripped only when a path is too long, longest first so that
# "_fp8_scaled" wins over "_scaled".
NOISE_SUFFIXES = [
    "_fp8_e4m3fn_scaled", "_fp8_e5m2_scaled", "_fp8_e4m3fn", "_fp8_e5m2",
    "_fp8_scaled", "_fp16_scaled", "_bf16_scaled", "_nf4_scaled",
    "_fp8_mixed", "_fp8mixed", "_int8_scaled",
    "_pruned_emaonly", "_pruned", "_emaonly",
    "_scaled", "_fp8", "_fp16", "_bf16", "_fp32", "_int8", "_nf4", "_gguf",
]

# Windows' classic MAX_PATH. Long-path support can lift it, but it is off by
# default and a save that trips it fails silently mid-run, so treat it as real.
MAX_PATH = 260


def sanitize(text, fallback="model"):
    """Strip characters illegal in file or folder names on Windows or Linux."""
    if not text:
        return fallback
    # Illegal on Windows: < > : " / \ | ? *  - plus control characters 0-31
    cleaned = "".join(
        "_" if (ch in '<>:"/\\|?*' or ord(ch) < 32) else ch
        for ch in str(text)
    )
    # Windows silently drops trailing dots and spaces
    cleaned = cleaned.rstrip(". ").strip()
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    if not cleaned:
        return fallback
    if cleaned.split(".")[0].upper() in RESERVED:
        cleaned = f"_{cleaned}"
    return cleaned


def strip_noise_suffixes(name):
    """
    Remove quantisation/packaging suffixes: krea2_turbo_fp8_scaled -> krea2_turbo.

    Applied repeatedly, because names like `qwen_3_8b_fp8mixed_scaled` carry more
    than one. Never returns an empty string.
    """
    changed = True
    while changed:
        changed = False
        low = name.lower()
        for suf in NOISE_SUFFIXES:
            if low.endswith(suf) and len(name) > len(suf):
                name = name[: -len(suf)]
                changed = True
                break
    return name or "model"


def model_name_from_graph(prompt, node_id, depth=0, seen=None):
    """
    Walk backwards from node_id through the workflow's links until a node
    carrying a model filename widget turns up.

    Follows any link, not just MODEL, so this works from a save node whose only
    input is IMAGE: IMAGE -> VAEDecode -> LATENT -> KSampler -> MODEL -> loader.
    `model` is tried first at each hop so a graph with several loaders resolves
    to the one actually driving the sampler.
    """
    if seen is None:
        seen = set()
    if depth > 24 or node_id is None or node_id in seen:
        return None
    seen.add(node_id)

    node = prompt.get(str(node_id)) if isinstance(prompt, dict) else None
    if not isinstance(node, dict):
        return None
    inputs = node.get("inputs", {})

    for widget in NAME_WIDGETS:
        val = inputs.get(widget)
        if isinstance(val, str) and val.strip():
            return val

    ordered = []
    if "model" in inputs:
        ordered.append(inputs["model"])
    ordered += [v for k, v in inputs.items() if k != "model"]

    for link in ordered:
        if isinstance(link, list) and len(link) >= 1:
            found = model_name_from_graph(prompt, link[0], depth + 1, seen)
            if found:
                return found
    return None


def model_name_from_object(model):
    """Last resort: look for a filename on the MODEL object itself."""
    for obj in [model, getattr(model, "model", None)]:
        if obj is None:
            continue
        fn = getattr(obj, "filename", None)
        if isinstance(fn, str) and fn:
            return fn
        try:
            for val in vars(obj).values():
                if isinstance(val, str) and val.endswith(
                        (".safetensors", ".ckpt", ".gguf", ".pt", ".pth")):
                    return val
        except Exception:
            pass
    return None


def base_name(raw, fallback="unknown_model"):
    """Filename of a model path, without directory or extension, sanitised."""
    base = str(raw).replace("\\", "/").split("/")[-1]
    return sanitize(os.path.splitext(base)[0], fallback=fallback)


def shorten_to_fit(name, fixed_overhead, doubled=False, floor=8):
    """
    Shorten `name` only if the finished path would exceed MAX_PATH.

    fixed_overhead - length of everything that is not the model name: output
                     directory, separators, prefixes, counter and extension.
    doubled        - True when the name appears twice in the path, which is what
                     create_folder does (folder and filename both carry it), so
                     every character saved counts twice.

    Returns (name, note). A short name comes back untouched with note None, so
    nothing is mangled that did not need to be.
    """
    def total(n):
        return fixed_overhead + len(n) * (2 if doubled else 1)

    if total(name) <= MAX_PATH:
        return name, None

    stripped = strip_noise_suffixes(name)
    if stripped != name and total(stripped) <= MAX_PATH:
        return stripped, f"shortened '{name}' -> '{stripped}' to fit the path limit"

    name = stripped
    budget = MAX_PATH - fixed_overhead
    if doubled:
        budget //= 2
    budget = max(floor, budget)
    if len(name) <= budget:
        return name, f"shortened to '{name}' to fit the path limit"

    truncated = name[:budget].rstrip("_. ")
    truncated = truncated or name[:floor]

    if total(truncated) > MAX_PATH:
        # Below `floor` the name stops identifying anything, so refuse to keep
        # cutting and say so instead. Silently returning a path that still
        # breaks is the failure mode this whole function exists to prevent.
        return truncated, (
            f"WARNING: even shortened to '{truncated}' the path is "
            f"{total(truncated)} characters, over the {MAX_PATH} limit. The save "
            f"will probably fail. Shorten your output directory, turn off "
            f"create_folder, or enable long paths in Windows.")

    return truncated, (f"truncated to '{truncated}' - the full path would have "
                       f"exceeded {MAX_PATH} characters")
