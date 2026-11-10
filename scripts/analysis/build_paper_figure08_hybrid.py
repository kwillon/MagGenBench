"""Compatibility entry point for the historical Figure 8 generator.

The selected publication figure is now Figure 7. Frozen calculation inputs
retain their original Figure 8 identifiers; publication outputs use 07.
"""
if __package__:
    from .build_paper_multiobjective_figure import main
else:
    from build_paper_multiobjective_figure import main


if __name__ == "__main__":
    main()
