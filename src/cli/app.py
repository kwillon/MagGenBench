from __future__ import annotations

"""
cli.py — интерфейс командной строки для mvpipeline.

CLI только:
    1) принимает аргументы
    2) загружает конфиг
    3) вызывает run_validation(...)
    4) печатает результат
"""

import json
from pathlib import Path
from typing import Optional

import typer
from rich import print
from rich.console import Console

from mvpipeline import load_config, run_validation
from mvpipeline.utils import PipelineConfig

app = typer.Typer(add_completion=False)
console = Console()


@app.command()
def validate(
    input_dir: Path = typer.Option(
        ..., "--input-dir", help="Папка с CIF файлами (рекурсивно ищем *.cif)"
    ),
    out_dir: Optional[Path] = typer.Option(
        None,
        "--out-dir",
        help="Куда сохранять результаты (по умолчанию: outputs/<model_name>)",
    ),
    thresholds: Optional[Path] = typer.Option(
        None,
        "--thresholds",
        help="YAML файл с порогами валидации (опционально)",
    ),
    train_reference: Optional[Path] = typer.Option(
        None,
        "--train-reference",
        help="CSV train dataset для расчёта novelty_ratio (опционально)",
    ),
    model_name: Optional[str] = typer.Option(
        None,
        "--model-name",
        help="Имя модели для отчёта (по умолчанию = имя input_dir)",
    ),
    pretty: bool = typer.Option(
        True,
        "--pretty/--no-pretty",
        help="Красиво печатать итоговый отчёт",
    ),
):
    """
    Запускает validation pipeline для CIF-файлов.
    """

    # ------------------------------------------------------------
    # 1) Проверка input_dir
    # ------------------------------------------------------------

    if not input_dir.exists():
        raise typer.BadParameter(f"input-dir не существует: {input_dir}")

    if not input_dir.is_dir():
        raise typer.BadParameter(f"input-dir должен быть директорией: {input_dir}")

    # ------------------------------------------------------------
    # 2) Определяем model_name и out_dir по умолчанию
    # ------------------------------------------------------------

    if model_name is None:
        # Берем имя папки: samples/mattergen_cifs -> mattergen_cifs
        model_name = input_dir.name

    if out_dir is None:
        # Дефолт: outputs/<model_name>
        out_dir = Path("outputs") / model_name
        print(f"[yellow]⚠ out-dir не указан, используется: {out_dir}[/yellow]")

    # ------------------------------------------------------------
    # 3) thresholds: warning если нет
    # ------------------------------------------------------------

    if thresholds is None:
        print(
            "[yellow]⚠ thresholds не указан, используется config по умолчанию[/yellow]"
        )
        cfg = PipelineConfig()

    elif not thresholds.exists():
        print(
            f"[yellow]⚠ thresholds файл не найден: {thresholds}[/yellow]\n"
            "[yellow]Используется config по умолчанию[/yellow]"
        )
        cfg = PipelineConfig()

    else:
        cfg = load_config(thresholds)

    # ------------------------------------------------------------
    # 4) train_reference: warning если нет
    # ------------------------------------------------------------

    if train_reference is None:
        print(
            "[yellow]⚠ train_reference не указан → novelty_ratio не будет рассчитан[/yellow]"
        )

    elif not train_reference.exists():
        print(
            f"[yellow]⚠ train_reference файл не найден: {train_reference}[/yellow]\n"
            "[yellow]novelty_ratio не будет рассчитан[/yellow]"
        )
        train_reference = None

    # ------------------------------------------------------------
    # 5) запуск pipeline
    # ------------------------------------------------------------

    report = run_validation(
        input_dir=input_dir,
        out_dir=out_dir,
        cfg=cfg,
        train_reference=train_reference,
        model_name=model_name,
    )

    # ------------------------------------------------------------
    # 6) вывод результата
    # ------------------------------------------------------------

    print(
        f"\n[bold green]✔ Валидация завершена[/bold green]\n"
        f"Отчёт: {out_dir / 'validation_report.json'}"
    )

    if pretty:
        console.print("\n[bold]Итоговый отчёт:[/bold]")
        console.print_json(json.dumps(report, ensure_ascii=False, indent=2))


def main():
    app()


if __name__ == "__main__":
    main()
