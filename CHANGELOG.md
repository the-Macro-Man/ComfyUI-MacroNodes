# Changelog

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
