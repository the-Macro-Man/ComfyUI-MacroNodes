"""
Prompt Prefix (Macro)
=====================
Keeps your system prompts in .txt files and offers them as a dropdown, so a
different prefix per model is one click instead of a paste.

Written for feeding an LLM node's `system` input - ComfyUI-Ollama's
`Ollama Generate`, the Krea2 enhancer, any node taking a STRING - but it is just
a file reader, so it works anywhere a long piece of text is wanted.

Where it looks, in order:

  1. $MACRONODES_PREFIX_DIR              an absolute path you set yourself
  2. <models>/prefixes                   registered with folder_paths, so
                                         extra_model_paths.yaml and shared model
                                         directories are picked up automatically
  3. <ComfyUI>/user/prefixes             fallback if neither of the above exists

Files from every location are merged. A name appearing in more than one place
resolves to the first hit in that order.

Pure stdlib.
"""

import os

try:
    import folder_paths
except Exception:            # importable outside ComfyUI, e.g. for tests
    folder_paths = None

ENV_VAR = "MACRONODES_PREFIX_DIR"
FOLDER_KEY = "prefixes"
EXTS = (".txt", ".md")


def _register() -> None:
    """Tell ComfyUI about a `prefixes` folder so its path machinery covers us."""
    if folder_paths is None:
        return
    try:
        folder_paths.add_model_folder_path(
            FOLDER_KEY, os.path.join(folder_paths.models_dir, FOLDER_KEY))
    except Exception:
        pass


_register()


def prefix_dirs() -> list:
    """Every directory that might hold prefixes, de-duplicated, existing only."""
    dirs = []
    env = (os.environ.get(ENV_VAR) or "").strip().strip('"')
    if env:
        dirs.append(env)
    if folder_paths is not None:
        try:
            dirs += list(folder_paths.get_folder_paths(FOLDER_KEY))
        except Exception:
            pass
        try:
            dirs.append(os.path.join(folder_paths.get_user_directory(), FOLDER_KEY))
        except Exception:
            pass
    seen, out = set(), []
    for d in dirs:
        try:
            key = os.path.normcase(os.path.abspath(d))
        except Exception:
            continue
        if key in seen:
            continue
        seen.add(key)
        if os.path.isdir(d):
            out.append(d)
    return out


def scan() -> dict:
    """{display name: absolute path}. First directory wins on a name clash."""
    found = {}
    for d in prefix_dirs():
        try:
            names = sorted(os.listdir(d))
        except Exception:
            continue
        for n in names:
            p = os.path.join(d, n)
            if not os.path.isfile(p) or not n.lower().endswith(EXTS):
                continue
            stem = os.path.splitext(n)[0]
            found.setdefault(stem, p)
    return found


class PromptPrefixNode:
    """
    Loads one of your saved prefixes and hands it on as a STRING.

    The dropdown is built when ComfyUI scans nodes, so a newly added file needs
    a refresh of the browser tab (or a restart) before it appears. Editing the
    CONTENTS of a file needs neither - it is read on every run.
    """

    @classmethod
    def INPUT_TYPES(cls):
        names = sorted(scan().keys())
        if not names:
            # An empty combo makes the node unusable and the reason invisible,
            # so put the diagnosis in the dropdown itself.
            names = [f"(no .txt files found - set {ENV_VAR})"]
        return {
            "required": {
                "prefix": (names, {
                    "tooltip": "Pick a saved prefix. Files come from "
                               f"${ENV_VAR}, <models>/prefixes, or "
                               "<ComfyUI>/user/prefixes."}),
            },
            "optional": {
                "custom_file": ("STRING", {
                    "default": "", "multiline": False,
                    "tooltip": "Absolute path to a .txt file. Overrides the dropdown - "
                               "useful for a one-off that does not live in the folder."}),
                "append": ("STRING", {
                    "default": "", "multiline": True,
                    "tooltip": "Extra text added after the prefix. For a per-run note "
                               "you do not want saved into the file."}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("prefix_text", "source_path")
    FUNCTION = "load"
    CATEGORY = "MacroNodes/utils"
    OUTPUT_NODE = False
    DESCRIPTION = ("Loads a saved system prompt from a .txt file, chosen from a dropdown. "
                   "Feed it into an LLM node's system input so each model can have its "
                   "own prefix without pasting.")

    @classmethod
    def IS_CHANGED(cls, prefix, custom_file="", append="", **kwargs):
        # Re-read when the file changes on disk, so editing a prefix takes effect
        # without touching the graph. Falls back to NaN (always re-run) if the
        # file cannot be stat'ed.
        path = custom_file.strip() or scan().get(prefix, "")
        try:
            return f"{os.path.getmtime(path)}:{os.path.getsize(path)}:{append}"
        except Exception:
            return float("nan")

    def load(self, prefix, custom_file="", append=""):
        path = custom_file.strip().strip('"')
        if path:
            if not os.path.isfile(path):
                raise RuntimeError(f"[MacroNodes] custom_file not found: {path}")
        else:
            path = scan().get(prefix, "")
            if not path:
                looked = prefix_dirs() or ["(no existing directories)"]
                raise RuntimeError(
                    f"[MacroNodes] No prefix named '{prefix}'. Looked in:\n  "
                    + "\n  ".join(looked)
                    + f"\nSet {ENV_VAR} to a folder of .txt files, or put them in "
                      f"<models>/prefixes.")

        try:
            text = open(path, encoding="utf-8").read()
        except UnicodeDecodeError:
            text = open(path, encoding="utf-8-sig", errors="replace").read()

        text = text.strip()
        if append.strip():
            text = f"{text}\n\n{append.strip()}"

        print(f"[MacroNodes] Prefix '{prefix}' loaded from {path} ({len(text)} chars)")
        return (text, path)


NODE_CLASS_MAPPINGS = {
    "PromptPrefixMacro": PromptPrefixNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptPrefixMacro": "Prompt Prefix (Macro)",
}


def _report() -> None:
    """
    Say at startup where we looked and what we found.

    An empty dropdown has three possible causes that look identical in the UI:
    the variable was never set, it was set but the app cached an older
    environment, or the folder is real but holds no .txt files. Printing the
    resolved value and the per-directory counts separates them immediately.
    """
    env = (os.environ.get(ENV_VAR) or "").strip().strip('"')
    dirs = prefix_dirs()
    files = scan()

    if env:
        exists = os.path.isdir(env)
        print(f"[MacroNodes] {ENV_VAR} = {env!r}"
              + ("" if exists else "   <-- NOT A DIRECTORY"))
    else:
        print(f"[MacroNodes] {ENV_VAR} is not set in this process. If you ran setx, "
              f"fully quit and reopen ComfyUI - the desktop app caches its "
              f"environment and an in-app Restart keeps the old one.")

    if dirs:
        for d in dirs:
            try:
                n = len([f for f in os.listdir(d) if f.lower().endswith(EXTS)])
            except Exception:
                n = 0
            print(f"[MacroNodes]   scanning {d}  ({n} prefix file(s))")
    else:
        print("[MacroNodes]   no existing prefix directories found")

    print(f"[MacroNodes] Prompt Prefix: {len(files)} prefix(es) available"
          + (f": {', '.join(sorted(files))}" if files else ""))


_report()
