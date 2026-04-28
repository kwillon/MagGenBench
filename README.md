# MVPipeline — Crystal Structure Validation Pipeline

[![Python 3.x](https://img.shields.io/badge/python-3.x-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## О проекте

**MVPipeline** — универсальный валидатор кристаллических структур в формате CIF, сгенерированных генеративными моделями: MatterGen, Con-CDVAE, CrystalFormer и другими.

Генеративные модели могут выдавать тысячи CIF-файлов, однако среди них часто встречаются:

- **Битые файлы** — CIF не поддаётся парсингу
- **Физически невозможные структуры** — атомы пересекаются или находятся слишком далеко друг от друга
- **Химически некорректные структуры** — заряд не сходится
- **Дубликаты** — модель штампует одно и то же
- **Неновые структуры** — уже присутствовали в train-наборе

MVPipeline автоматически прогоняет весь набор CIF через единый pipeline, отфильтровывает мусор и собирает метрики качества генерации. Один запуск — полный отчёт.

---

## Результат одного запуска

```
outputs/my_model/
├── validation_report.json     # Итоговый отчёт с метриками
├── all_structures.csv         # Полный датасет по всем структурам
├── validated_structures/      # Структуры, прошедшие валидацию
└── rejected_structures/       # Отклонённые структуры + причина
```

---

## Возможности

| Функция | Описание |
|---|---|
| Чтение CIF | Рекурсивный поиск и безопасное чтение всех `.cif` файлов из директории |
| Геометрическая валидация | Проверка минимального/максимального расстояния между атомами и объёма на атом |
| Физические ограничения | Проверка допустимой плотности, максимального числа атомов в ячейке |
| Проверка заряда | Оценка charge neutrality на основе заданных степеней окисления |
| Удаление дубликатов | Структурное сравнение через `StructureMatcher` |
| Проверка новизны | Сравнение с `train_reference.csv` по формуле и пространственной группе |
| Магнитные структуры | Детектирование переходных металлов и редкоземельных элементов |
| Метрики и отчёт | Автоматическое формирование `validation_report.json` и `all_structures.csv` |
| Docker-поддержка | Запуск в изолированной среде через Docker |

---

## Установка

### Через conda

```bash
conda env create -f environment.yml
conda activate mvpipeline
pip install -e .
```

### Через Docker

```bash
bash scripts/run_docker.sh
```

---

## Быстрый старт

### Через CLI

```bash
mvp \
  --input-dir samples/mattergen_cifs \
  --out-dir outputs/mattergen \
  --train-reference train_reference.csv \
  --thresholds config/thresholds.yaml
```

### Аргументы CLI

| Аргумент | Обязательный | Описание |
|---|---|---|
| `--input-dir` | Директория с исходными CIF-файлами (поиск рекурсивный) |
| `--out-dir` | Директория для сохранения результатов (по умолчанию: `outputs/<model_name>`) |
| `--train-reference` | Путь к CSV со структурами train-набора (для расчёта `novelty_ratio`) |
| `--thresholds` | Путь к YAML-файлу с порогами валидации (по умолчанию: встроенные значения) |
| `--model-name` | Имя модели для отчёта (по умолчанию: имя папки `input-dir`) |
| `--pretty / --no-pretty` | Красиво печатать итоговый отчёт в консоль (по умолчанию: `--pretty`) |

> **Примечание:** если `--thresholds` или `--train-reference` не указаны, pipeline продолжит работу с предупреждением — `novelty_ratio` не будет рассчитан, а пороги будут взяты из встроенных дефолтов.

### Через Web UI (Streamlit)

```bash
streamlit run src/ui/app.py
```

После запуска открой в браузере:

```bash
http://localhost:8501
```

---

## Конфигурация

Все пороги валидации задаются в `config/thresholds.yaml`.

### Геометрия

```yaml
geometry:
  d_min_reject: 0.7       # Расстояние < 0.7 Å → отклонение (overlap)
  d_max_suspicious: 1.2   # Расстояние 0.7–1.2 Å → предупреждение (suspicious)
  vol_min: 8.0            # Минимальный объём на атом (Å³)
  vol_max: 40.0           # Максимальный объём на атом (Å³)
```

### Физические свойства

```yaml
physical_properties:
  min_density: 0.5        # Минимальная плотность (г/см³)
  max_density: 30.0       # Максимальная плотность (г/см³)
```

### Системные ограничения

```yaml
system_limits:
  max_n_atoms: 500        # Максимальное число атомов в ячейке
```

### Степени окисления

Используются для проверки charge neutrality. Задаются списком допустимых степеней для каждого элемента:

```yaml
oxidation_states:
  Fe: [2, 3]
  Ni: [2, 3]
  O:  [-2, -1]
  Ti: [2, 3, 4]
  # ... и т.д.
```

### Магнитные элементы

Структура помечается как магнитная (`is_magnetic = True`), если содержит хотя бы один элемент из списка. По умолчанию включены переходные металлы 3d/4d/5d-рядов и все редкоземельные элементы:

```yaml
magnetic_elements:
  # 3d переходные металлы
  - Ti, V, Cr, Mn, Fe, Co, Ni, Cu, Zn
  # 4d/5d переходные металлы
  - Mo, Ru, Rh, Pd, Re, Os, Ir
  # Редкоземельные элементы (лантаноиды)
  - Sc, Y, La, Ce, Pr, Nd, Pm, Sm, Eu, Gd, Tb, Dy, Ho, Er, Tm, Yb, Lu
```

---

## Формат входных данных

### train_reference.csv

CSV-файл со структурами из обучающего набора. Используется для проверки новизны.

| Поле | Тип | Описание |
|---|---|---|
| `id` | str | Уникальный идентификатор структуры |
| `reduced_formula` | str | Приведённая химическая формула (например, `Fe2O3`) |
| `spacegroup` | int/str | Номер или символ пространственной группы (опционально) |

Пример:

```csv
id,reduced_formula,spacegroup
mp-1234,Fe2O3,167
mp-5678,NiO,225
```

---

## Формат выходных данных

### Пример validation_report.json

```json
{
  "model_name": "mattergen",
  "n_total": 1000,
  "n_validated": 820,
  "n_rejected": 180,
  "validity_ratio": 0.82,
  "magnetic_ratio": 0.47,
  "novelty_ratio": 0.63,
  "duplicate_ratio": 0.12,
  "avg_density": 5.34,
  "avg_volume_per_atom": 13.2,
  "rejection_reasons": {
    "cif_parse_error": 10,
    "overlap": 95,
    "charge_imbalance": 50,
    "duplicate": 25
  }
}
```

| Метрика | Описание |
|---|---|
| `n_total` | Сколько CIF найдено в `input-dir` |
| `n_validated` | Сколько структур прошло все проверки |
| `n_rejected` | Сколько структур отклонено |
| `validity_ratio` | `n_validated / n_total` |
| `magnetic_ratio` | Доля валидных структур с магнитными элементами |
| `novelty_ratio` | Доля валидных структур, не совпавших с train_reference |
| `duplicate_ratio` | Доля файлов, отклонённых как дубликаты (от `n_total`) |
| `avg_density` | Средняя плотность валидных структур (г/см³) |
| `avg_volume_per_atom` | Средний объём на атом валидных структур (Å³) |
| `rejection_reasons` | Счётчик по причинам отклонения |

### all_structures.csv

Полный датасет по всем CIF для последующего анализа и сравнения моделей.

| Поле | Тип | Описание |
|---|---|---|
| `structure_id` | str | Относительный путь к CIF внутри `input-dir` |
| `input_path` | str | Полный путь к исходному CIF |
| `status` | str | `validated` или `rejected` |
| `rejection_reason` | str/null | Причина отклонения |
| `is_suspicious` | bool | Флаг soft-аномалии (расстояние в диапазоне 0.7–1.2 Å) |
| `is_duplicate` | bool | Является ли структурным дубликатом |
| `is_novel` | bool | Новая ли структура относительно train_reference |
| `is_magnetic` | bool | Содержит ли магнитные элементы |
| `n_atoms` | int | Число атомов в ячейке |
| `density` | float | Плотность (г/см³) |
| `volume_per_atom` | float | Объём на атом (Å³) |
| `min_distance` | float | Минимальное межатомное расстояние (Å) |
| `reduced_formula` | str | Приведённая химическая формула |
| `spacegroup` | str/int/null | Пространственная группа |
| `charge_solution_json` | str/null | JSON со степенями окисления |
| `details_json` | str | Полный JSON с деталями всех проверок |

### rejected_structures/

Рядом с каждым отклонённым CIF создаётся файл `*.reason.json`:

```json
{
  "structure_id": "subdir/a.cif",
  "reason": "overlap",
  "details": {
    "min_distance": 0.42
  }
}
```

Коды причин отклонения:

| Код | Описание |
|---|---|
| `cif_parse_error` | Файл не поддаётся парсингу |
| `overlap` | Расстояние между атомами < `d_min_reject` (0.7 Å) |
| `charge_imbalance` | Заряд элементарной ячейки не нейтрален |
| `duplicate` | Структурный дубликат уже принятой структуры |
| `density_out_of_range` | Плотность вне диапазона `[min_density, max_density]` |
| `volume_out_of_range` | Объём на атом вне диапазона `[vol_min, vol_max]` |
| `too_many_atoms` | Число атомов превышает `max_n_atoms` |

---

## Как работает пайплайн

```
Входная директория с CIF-файлами
    │
    ▼
1. Поиск CIF-файлов
   Рекурсивный обход input-dir, сбор всех *.cif
    │
    ▼
2. Загрузка train_reference
   Построение индекса (formula, spacegroup) для проверки новизны
    │
    ▼
3. Обработка каждого CIF:
    │
    ├─► Чтение CIF (pymatgen)
    │         └─ ошибка → cif_parse_error → отклонено
    │
    ├─► Sanity-проверка
    │   Структура не пустая, решётка корректна, координаты валидны
    │
    ├─► Геометрическая проверка
    │   Межатомные расстояния, объём на атом
    │         └─ расстояние < 0.7 Å → overlap → отклонено
    │         └─ расстояние 0.7–1.2 Å → suspicious (предупреждение)
    │         └─ объём вне [8.0, 40.0] Å³ → отклонено
    │
    ├─► Проверка физических свойств
    │   Плотность, число атомов
    │         └─ плотность вне [0.5, 30.0] г/см³ → отклонено
    │         └─ число атомов > 500 → отклонено
    │
    ├─► Проверка нейтральности заряда
    │   Оценка степеней окисления по таблице из конфига
    │         └─ заряд не нулевой → charge_imbalance → отклонено
    │
    ├─► Вычисление дескрипторов
    │   Плотность, объём на атом, формула, пространственная группа
    │
    ├─► Определение магнитности
    │   Проверка наличия элементов из magnetic_elements
    │   (метрика, не причина отклонения)
    │
    ├─► Проверка на дубликат
    │   StructureMatcher сравнивает с уже принятыми структурами
    │         └─ совпало → duplicate → отклонено
    │
    └─► Проверка новизны
        Сравнение (formula, spacegroup) с train_reference
        (метрика, не причина отклонения)
    │
    ▼
4. Сохранение результатов
   Валидные     → validated_structures/
   Отклонённые  → rejected_structures/ + *.reason.json
    │
    ▼
5. Формирование итоговых артефактов
   all_structures.csv + validation_report.json
```

### Проверка новизны

Структура считается **не новой**, если в `train_reference.csv` уже есть запись с той же парой `(reduced_formula, spacegroup)`. Это позволяет быстро выявить, штампует ли модель очевидные повторения train-набора. Новизна — **метрика**, а не причина отклонения.

### Удаление дубликатов

Дубликаты определяются структурно через `pymatgen.analysis.structure_matcher.StructureMatcher`, а не текстовым сравнением CIF. Кандидаты предварительно группируются по бакетам (формула / число атомов / spacegroup), чтобы избежать полного попарного сравнения.

---

## Технологии

| Библиотека | Назначение |
|---|---|
| [pymatgen](https://pymatgen.org/) | Чтение CIF, вычисление свойств структур, `StructureMatcher` |
| [spglib](https://spglib.readthedocs.io/) | Определение пространственных групп симметрии |
| [typer](https://typer.tiangolo.com/) | CLI-интерфейс |
| [pandas](https://pandas.pydata.org/) | Чтение `train_reference.csv`, формирование `all_structures.csv` |
| [numpy](https://numpy.org/) | Численные операции, агрегация метрик |
| [tqdm](https://tqdm.github.io/) | Прогресс-бар при обработке тысяч файлов |
| [rich](https://rich.readthedocs.io/) | Читаемые логи и итоговая сводка в консоли |
| Docker | Изолированный запуск пайплайна |

---

## Скрипты

| Скрипт | Описание |
|---|---|
| `scripts/run_validation.sh` | Запуск валидации для нескольких моделей подряд |
| `scripts/run_docker.sh` | Запуск валидации внутри Docker |

---

## Сравнение моделей

После запуска для разных моделей можно сравнивать метрики из `validation_report.json`:

```bash
# MatterGen
mvp --input-dir samples/mattergen --out-dir outputs/mattergen ...

# Con-CDVAE
mvp --input-dir samples/cdvae --out-dir outputs/cdvae ...

# CrystalFormer
mvp --input-dir samples/crystalformer --out-dir outputs/crystalformer ...

# CrystalLLM
mvp --input-dir samples/crystallm --out-dir outputs/crystallm ...
```

Затем сравнивать `validity_ratio`, `novelty_ratio`, `duplicate_ratio`, `avg_density` и другие метрики между моделями для объективной оценки качества генерации.

---

## Лицензия

MIT License. Подробнее — в файле [LICENSE](LICENSE).