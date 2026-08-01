"""IO helpers.

Heavy CIF parsing helpers are loaded lazily so dependency-light stage-table
utilities can be imported without pymatgen.
"""

_LAZY_EXPORTS = {
    "discover_cifs": ("mvpipeline.io.discover", "discover_cifs"),
    "read_structure": ("mvpipeline.io.cif_reader", "read_structure"),
    "write_validated": ("mvpipeline.io.writers", "write_validated"),
    "write_rejected": ("mvpipeline.io.writers", "write_rejected"),
}


def __getattr__(name):
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = _LAZY_EXPORTS[name]
    from importlib import import_module

    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


__all__ = [
    "discover_cifs",
    "read_structure",
    "write_validated",
    "write_rejected",
]
