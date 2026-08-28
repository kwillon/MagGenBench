from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer


app = typer.Typer(add_completion=False)
reproduce_app = typer.Typer(add_completion=False)
figures_app = typer.Typer(add_completion=False)
app.add_typer(reproduce_app, name="reproduce")
app.add_typer(figures_app, name="figures")


@reproduce_app.command("analysis-v1")
def reproduce_analysis_v1_command(
    repo_root: Path = typer.Option(
        Path("."),
        "--repo-root",
        help="Repository root containing the frozen Analysis v1 manifest.",
    ),
    artifact_root: Optional[Path] = typer.Option(
        None,
        "--artifact-root",
        help="Optional root for repository-relative frozen artifacts.",
    ),
    baseline_joined: Path = typer.Option(
        ...,
        "--baseline-joined",
        help="Baseline joined CSV replacing the historical absolute artifact.",
    ),
    output_dir: Path = typer.Option(
        Path("reproduced/analysis_v1"),
        "--output-dir",
        help="Directory for the reproduced unified Analysis v1 CSV.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Replace an existing reproduced unified Analysis v1 CSV.",
    ),
) -> None:
    from mvpipeline.reproduction.analysis_v1 import (
        ReproductionError,
        reproduce_analysis_v1,
    )

    try:
        result = reproduce_analysis_v1(
            repo_root=repo_root,
            artifact_root=artifact_root,
            baseline_joined=baseline_joined,
            output_dir=output_dir,
            force=force,
        )
    except ReproductionError as exc:
        raise typer.BadParameter(str(exc)) from exc

    typer.echo("Analysis v1 reproduction: PASSED")
    typer.echo(f"CSV: {result.output_path}")
    typer.echo(f"Rows: {result.row_count}")
    typer.echo(f"Columns: {result.column_count}")
    typer.echo(f"SHA256: {result.sha256}")
    typer.echo("Checksum verification: PASSED")
    typer.echo(f"Figures: {result.figure_output_dir}")
    for path in result.figure_files:
        typer.echo(f"Figure output: {path}")


@figures_app.command("analysis-v1")
def figures_analysis_v1_command(
    input_csv: Path = typer.Option(
        Path("runs/analysis_v1/unified_analysis_v1.csv"),
        "--input-csv",
        help="Unified Analysis v1 CSV to plot.",
    ),
    output_dir: Path = typer.Option(
        Path("reproduced/analysis_v1/figures"),
        "--output-dir",
        help="Directory for Analysis v1 figure outputs.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Replace existing owned Analysis v1 figure outputs.",
    ),
) -> None:
    from mvpipeline.analysis.figures_v1 import generate_analysis_v1_figures

    if not input_csv.is_file():
        typer.echo(f"Input CSV does not exist: {input_csv}")
        raise typer.Exit(1)

    try:
        report = generate_analysis_v1_figures(
            input_csv=input_csv,
            output_dir=output_dir,
            force=force,
        )
    except (FileNotFoundError, RuntimeError) as exc:
        raise typer.BadParameter(str(exc)) from exc

    typer.echo("Analysis v1 figures: PASSED")
    typer.echo(f"Input CSV: {report.input_csv}")
    typer.echo(f"Output directory: {report.output_dir}")
    for path in report.output_files:
        typer.echo(f"Output: {path}")
