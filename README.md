# Macro Nodes

Quality-of-life nodes for ComfyUI. Small, no extra dependencies, and each one solves
a thing that was annoying enough to fix properly.

- **[Save Image (Macro)](#save-image-macro)** - save named after the model, with a
  numbered workflow `.json` and a per-node metadata switch
- **[Model Name Extractor](#model-name-extractor)** - the model's name as a STRING,
  for any save node
- **[Prompt Prefix (Macro)](#prompt-prefix-macro)** - system prompts as `.txt` files,
  picked from a dropdown
- **[Concat Text (Macro)](#concat-text-macro)** - join up to ten inputs of any type,
  with a delimiter that can hold newlines

**Registry:** `macronodes` · **Publisher:** `the-macroman` · MIT

## Install

**ComfyUI Manager** - search for *Macro Nodes*.

**CLI**

```bash
comfy node install macronodes
```

**Manually**

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/the-Macro-Man/ComfyUI-MacroNodes
```

Restart ComfyUI. There is nothing to `pip install` - the pack uses the standard
library plus numpy and PIL, which ComfyUI already requires.

---

## Nodes

### Save Image (Macro)

SaveImage, named after the model that made the picture, with control over what goes
with it.

Found under **MacroNodes/image**. Connect an IMAGE and that is it - the model name is
read from the graph, so there is nothing to wire up and nothing to type.

| Input | Default | What it does |
|---|---|---|
| `images` | - | The images to save |
| `folder_prefix` | `""` | Prefixes the FOLDER, e.g. `art_` → `art_krea2_turbo/` |
| `file_prefix` | `""` | Prefixes the FILE, e.g. `draft_` |
| `create_folder` | on | Save into a subfolder named after the model |
| `embed_workflow` | on | Off writes a clean PNG with no prompt or workflow inside |
| `save_workflow_json` | off | Writes the workflow beside each image, numbered to match |
| `save_summary_txt` | off | Readable summary: model, LoRAs, sampler, steps, CFG, seed, prompts |
| `shorten_if_needed` | on | Only acts if the path would break the Windows limit |
| `model_name` | `""` | Force a name instead of detecting one |

#### Share the picture, keep the recipe

Set **`embed_workflow` off** and **`save_workflow_json` on**:

```
art_krea2_turbo/
├─ draft_krea2_turbo_00007_.png    <- clean, no metadata, safe to post anywhere
└─ draft_krea2_turbo_00007_.json   <- the workflow, kept on your disk
```

ComfyUI's own switch for this is `--disable-metadata`, which is global, applies to
every save node, and would remove the workflow entirely rather than moving it beside
the file. This toggle is per-node.

Drag the `.json` into ComfyUI to reload the graph, exactly as you would the PNG.

#### Why the numbers match

The `.json` and `.txt` carry the same counter as the image because this node does the
saving and therefore knows which number it landed on. A node that only hands
`SaveImage` a filename prefix has no way to know that, which is why Model Name
Extractor cannot offer this.

#### Path shortening

`shorten_if_needed` measures the finished path against Windows' 260-character limit
and does nothing unless it would be exceeded. When it must act it first drops
suffixes that describe the file rather than the model - `_fp8_scaled`, `_fp16`,
`_pruned_emaonly` and similar - and only truncates if that is still not enough. If
even truncation cannot make it fit, it says so in the log instead of letting the save
fail silently part-way through a batch.

This matters more than it sounds: `create_folder` puts the model name in the path
twice, so every character saved counts double.

---

### Model Name Extractor

Names your saved files after the model that made them. Switch checkpoints and the
filename follows, with nothing to retype.

```
Load Checkpoint ──MODEL──> Model Name Extractor ──STRING──> SaveImage.filename_prefix
```

> `filename_prefix` is a widget by default. Right-click the SaveImage node and choose
> **Convert widget to input** before you can connect to it. This is the one step
> everybody gets stuck on.

Found under **MacroNodes/utils**.

#### Inputs

| Input | Default | What it does |
|---|---|---|
| `model` | - | Connect any MODEL output |
| `prefix` | `""` | Prefixes the FILE name, e.g. `Draft_` |
| `folder_prefix` | `""` | Prefixes the FOLDER name, e.g. `art_`. Needs `create_folder` |
| `create_folder` | off | On: saves into a subfolder named after the model |
| `model_name` | `""` | Type a name here to override auto-detection |

Use this rather than Save Image (Macro) when you are saving something that is not a
plain image - `SaveAnimatedWEBP`, the VideoHelperSuite nodes, or any third-party save
node. It just produces a string, so it works with all of them.

#### Results

With `sd_xl_base_1.0.safetensors` loaded:

| Settings | Output file |
|---|---|
| defaults | `sd_xl_base_1.0_00001.png` |
| `prefix = Draft_` | `Draft_sd_xl_base_1.0_00001.png` |
| `create_folder = on` | `sd_xl_base_1.0/sd_xl_base_1.0_00001.png` |
| both | `sd_xl_base_1.0/Draft_sd_xl_base_1.0_00001.png` |

Folders are created if absent and reused if present.

#### How it finds the name

It walks the workflow graph backwards from its own MODEL input until it hits a node
carrying a filename widget - `ckpt_name`, `unet_name`, `model_name`, `model_path`,
`gguf_name` or `name`. That covers Load Checkpoint, Load Diffusion Model, UNETLoader,
the GGUF loaders and most custom loaders, without needing to know about any of them
individually.

If the walk finds nothing it inspects the model object itself, and failing that
returns `unknown_model` rather than raising.

Names are sanitised for both Windows and Linux: `< > : " / \ | ? *` and control
characters become underscores, trailing dots and spaces are stripped, and Windows
reserved device names (`CON`, `PRN`, `COM1`…) get an underscore prefix. The Windows
rules are applied on every platform so filenames stay portable.

`IS_CHANGED` returns NaN, so the node re-evaluates every run and a checkpoint swap
shows up immediately.

---

### Prompt Prefix (Macro)

Keeps system prompts as `.txt` files on disk and offers them as a dropdown, so using
a different prefix per model is one click instead of a paste.

Feed `prefix_text` into an LLM node's `system` input - comfyui-ollama's Ollama Chat,
a captioner, anything that takes a system prompt as a string.

| Input | Does |
|---|---|
| `prefix` | Dropdown of the `.txt` files found. |
| `custom_file` | An explicit path, overriding the dropdown. |
| `append` | Extra text added after the file's contents, for a one-off tweak. |

Outputs `prefix_text` and `source_path`, the latter so you can record which file was
actually used.

#### Where it looks

In order: `$MACRONODES_PREFIX_DIR`, then `<models>/prefixes`, then
`<ComfyUI>/user/prefixes`. One `.txt` per prefix; the filename becomes the dropdown
entry.

**Editing a file takes effect on the next run. Adding or removing one needs a browser
refresh**, because ComfyUI builds a node's dropdown contents when it scans nodes, not
when it runs them.

At startup the node prints where it looked and what it found. An empty dropdown
otherwise looks identical whether the environment variable is unset, the path is
wrong, or the folder is simply empty.

`IS_CHANGED` is the file's mtime and size, so editing a prefix invalidates the cache
but an unchanged file does not force everything downstream to re-run.

---

### Concat Text (Macro)

Joins up to ten inputs into one string. Two things set it apart from the concat nodes
already out there.

**The inputs take any type.** ComfyUI will not let you drag an `OLLAMA_META` or
`OLLAMA_HISTORY` output into a `STRING` socket, so the usual workaround is to insert a
`Preview as Text` node purely to launder the type. These slots accept anything and
serialise non-strings the same way core's `PreviewAny` does, so those outputs connect
directly.

**The delimiter can hold newlines.** Escape sequences are expanded wherever they
appear, so `\n\n` gives a blank line between blocks and `\n----\n` gives a rule. Some
existing nodes special-case the exact string `\n` and pass anything else through
literally.

| Input | Does |
|---|---|
| `text1`–`text10` | All optional. Gaps are fine. |
| `delimiter` | Inserted between blocks. Escapes expanded. |
| `labels` | Prefixes each block with `=== text2 ===`. |
| `trim` | Strips leading and trailing whitespace per block. |
| `skip_empty` | Drops empty blocks instead of leaving stray delimiters. |

Outputs `concat` and `block_count`. `labels` is worth turning on while building a
chain - when the result is wrong, it tells you which input caused it.

---

## Adding to this pack

Nodes live one per module in `nodes/`. To add one:

1. Create `nodes/your_node.py` defining `NODE_CLASS_MAPPINGS` and
   `NODE_DISPLAY_NAME_MAPPINGS`.
2. Import it in `nodes/__init__.py` and append it to `MODULES`.

The root `__init__.py` merges everything and warns on duplicate node ids rather than
letting one quietly overwrite another. Imports are explicit rather than discovered at
runtime, so the full node list is readable from one file.

## What this package does not do

No network calls. No `eval`, `exec`, `subprocess`, `os.system`, `pickle` or
`__import__`. No dynamic imports - `nodes/__init__.py` lists every module by name, so
the full node list is readable from one file.

**Nothing to `pip install`.** The imports are `os`, `json`, `numpy`, `PIL`, and
ComfyUI's own `folder_paths`, `comfy.cli_args` and `comfy.comfy_types`. numpy and PIL
are already hard requirements of ComfyUI itself, so the pack adds no dependency you do
not already have.

## Licence

MIT - see [LICENSE](LICENSE).
