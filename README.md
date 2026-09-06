# Macro Nodes

Quality-of-life nodes for ComfyUI. Small, dependency-free, and each one solves a
thing that was annoying enough to fix properly.

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

Restart ComfyUI. There is nothing to `pip install` - the pack uses only the
Python standard library.

---

## Nodes

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
| `prefix` | `""` | Text put in front of the name, e.g. `Draft_` |
| `create_folder` | off | On: saves into a subfolder named after the model |
| `model_name` | `""` | Type a name here to override auto-detection |

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
`__import__`. No dependencies beyond the standard library. The only import in the
whole package is `os`.

## Licence

MIT - see [LICENSE](LICENSE).
