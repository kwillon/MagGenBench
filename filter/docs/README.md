# Integration notes

The `filter/` directory is self-contained and can be placed at the root of a larger project repository. Install it with `python -m pip install -e ./filter` or add `filter/src` to the parent project's Python environment.

The runtime model is packaged under `src/cifmagfilter/data/model/`; publication and audit tables under `paper/` do not contain a second runtime model copy.
