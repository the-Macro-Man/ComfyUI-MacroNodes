# Changelog

## 1.2.0 - 2026-10-17

> Written on 11 September and in daily use here since, across Krea 2, Z-Image
> and image-enhancement workflows. Held back from release only because the
> machine's test sandbox was broken by a Windows update on 8 September.

### Added

- **Prompt Prefix (Macro)** - keeps system prompts as `.txt` files and offers them
  as a dropdown, so a different prefix per model is one click instead of a paste.
  Looks in `$MACRONODES_PREFIX_DIR`, `<models>/prefixes` and `<ComfyUI>/user/prefixes`.
  Editing a file takes effect on the next run; adding one needs a browser refresh.
  Reports at startup where it looked and what it found, because an empty dropdown
  otherwise looks identical whether the variable is unset, the path is wrong, or
  the folder is empty.
- **Concat Text (Macro)** - joins up to ten inputs. Two things the existing concat
  nodes do not do:
  - **Wildcard inputs.** ComfyUI will not link `OLLAMA_META` or `OLLAMA_HISTORY`
    into a STRING socket, so people insert a `Preview as Text` purely to convert
    the type. These slots take any type and serialise non-strings the same way
    core's `PreviewAny` does, so those outputs connect directly.
  - **A delimiter that can hold newlines.** tinyterra's special-cases the exact
    value `\n`; `\n----\n` comes through literally. Escapes here are expanded
    wherever they appear.
  - Plus `labels` (`=== text2 ===` headers, for finding which block caused a
    surprise), `trim` and an explicit `skip_empty`.
- **`text` input on Save Image (Macro)** - connect the prompt you actually used and
  it is written to the numbered `.txt` beside the image. Connecting it is taken as
  intent, so `save_summary_txt` is not also required; with both on, the generated
  summary is appended below under a `--- workflow summary ---` rule.

### Changed

- **An `Icon` is now set in `pyproject.toml`**, pointing at `icon.png` in this repo.
  1.0.0 deliberately shipped without one so the package contained zero URLs the
  Registry's YARA scanner could object to, and it came back Active. That isolates
  the variable: `raw.githubusercontent.com` is now the only blacklisted-pattern
  candidate in a package that still has no network code. If this release verifies,
  that URL was never what got 11 versions of `comfyui-amdmonitor` banned. See
  Comfy-Org/registry-backend#215.

### Notes

- Still no `eval`, `exec`, `subprocess`, `pickle` or network access anywhere in the
  package. Concat Text is pure string handling.

## 1.1.0 - 2026-09-07

### Added

- **Save Image (Macro)** - a second node. Saves PNGs named after the model, and does
  three things a node that only hands SaveImage a string cannot:
  - `save_workflow_json` writes the workflow beside each image with a **matching
    number** - `art_krea2_00007_.png` gets `art_krea2_00007_.json`. Only the node
    doing the saving knows which counter it landed on.
  - `embed_workflow` off strips prompt and workflow from the PNG **for this node
    only**. ComfyUI's `--disable-metadata` is global and would kill the .json too.
    Turning this off while `save_workflow_json` is on gives clean images to share
    and the recipe kept locally.
  - `shorten_if_needed` measures the real finished path and only acts when it would
    exceed the Windows 260-character limit, dropping `_fp8_scaled`-style suffixes
    first and truncating only if that is not enough. Short names are never touched,
    and if it still cannot fit it says so rather than failing silently mid-run.
  - `save_summary_txt` writes a readable sidecar: model, LoRAs, sampler, steps, CFG,
    seed and both prompts.
- **`folder_prefix` on Model Name Extractor** - prefixes the folder independently of
  the filename. `art_` gives `art_krea2_turbo/krea2_turbo_00001_.png`.

### Changed

- Naming, sanitising and the graph walk moved to `nodes/_shared.py`, so both nodes
  resolve a model to the same name rather than drifting apart.

### Notes

- **Model Name Extractor is unchanged in behaviour and is not deprecated.** It works
  with any saver - SaveAnimatedWEBP, video nodes, third-party save nodes. Save Image
  (Macro) only handles images.
- Still no `eval`, `exec`, `subprocess`, `os.system`, `pickle` or `__import__`. The
  new node adds `PIL` and `numpy`, both already required by ComfyUI.

## 1.0.0 - 2026-09-06

First release.

### Added

- **Model Name Extractor** - outputs the loaded model's filename as a STRING for
  `SaveImage.filename_prefix`. Walks the workflow graph backwards to find the loader,
  so it works with Load Checkpoint, Load Diffusion Model, UNETLoader, GGUF loaders and
  most custom loaders without knowing about any of them specifically.
  - `prefix` - text prepended to the filename
  - `create_folder` - save into a per-model subfolder
  - `model_name` - manual override
  - Filenames sanitised for Windows and Linux, including reserved device names
  - `IS_CHANGED` returns NaN so a checkpoint swap updates the name immediately

### Notes

- Standard library only. The single import in the package is `os`.
- No `Icon` is set in `pyproject.toml` for this release. See the comment in that file.
