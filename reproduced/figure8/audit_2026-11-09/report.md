# Аудит Figure 8 и численные дополнения к §3.7.1

Дата: 2026-11-09. Все результаты получены из сохранённых CSV и проверены по исходным QC/дескрипторным таблицам. Обучение, генерация и изменение публикационных рисунков не выполнялись.

## Основной вывод

Все места моделей, названные в предоставленных автором трёх абзацах S1–S3, подтверждаются `figure08_scenario_rankings_v2.csv`. Однако выбранный публикационный `paper/figures/fig08_multiobjective.pdf` показывает другую, исходную постановку: QC retention + unique-formula yield + 3d-containing yield. Поэтому ссылка на этот PDF как на иллюстрацию трёх сценариев методически некорректна. Это несогласованность версий анализа и рисунка, а не ошибка извлечённых чисел.

## Файлы и происхождение

- Скрипт: [build_paper_figure08.py](../../../scripts/analysis/build_paper_figure08.py). Режим по умолчанию использует `METRICS` с `3d_containing_yield_pct`; `--compare-scenarios` задаёт S1–S3; `--build-figure8-v2` только визуализирует сохранённые сценарные результаты. В рамках аудита эти режимы не запускались, поскольку они записывают результаты/рисунки.
- Выбранный PDF: [fig08_multiobjective.pdf](../../../paper/figures/legacy/fig08_multiobjective_presence_original.pdf); подпись: [fig08_caption.md](../../../docs/figures/legacy/fig08_presence_caption.md).
- Исходная многокритериальная матрица: [fig08_metric_matrix.csv](../../../tables/figure_sources/fig08_metric_matrix.csv); распределения мест: [fig08_rank_distribution.csv](../../../tables/figure_sources/fig08_rank_distribution.csv); частоты: [fig08_ranking_summary.csv](../../../tables/figure_sources/fig08_ranking_summary.csv); доминирование: [fig08_dominance_matrix.csv](../../../tables/figure_sources/fig08_dominance_matrix.csv).
- Сценарные величины: [figure08_scenario_metrics_v2.csv](../../../tables/figure_sources/figure8/figure08_scenario_metrics_v2.csv), оценки/места: [figure08_scenario_rankings_v2.csv](../../../tables/figure_sources/figure8/figure08_scenario_rankings_v2.csv), Pareto: [figure08_scenario_pareto_v2.csv](../../../tables/figure_sources/figure8/figure08_scenario_pareto_v2.csv).
- Отдельная, уже существующая сценарная визуализация: [figure08_scenarios_v2.pdf](../legacy/scenarios_v2/figure08_scenarios_v2.pdf). Это другой файл, не выбранный публикационный Figure 8. Никакая замена не выполнялась.
- Структурные и формульные числа: [fig06_diversity_summary.csv](../../../tables/figure_sources/fig06_diversity_summary.csv).
- Популяция Figure 8: [fig05_energy_magnetism.csv](../../../tables/figure_sources/fig05_energy_magnetism.csv); составы: [analysis_v2_magnetic.csv](../../../tables/10_analysis_v2_magnetic/analysis_v2_magnetic.csv) и два дополнения [CrystalFormer FT](../../../tables/figure_sources/crystalformer_finetuned_descriptors.csv), [CrystaLLM FT](../../../tables/figure_sources/crystallm_finetuned_descriptors.csv).
- QC-источники по каждому набору перечислены в [qc_budget_verification.csv](qc_budget_verification.csv). Для четырёх Base использована таблица `tables/02_validation/master_structures_with_validation_status.csv`, для остальных — полные QC-аннотации `tables/03_features/*_with_classes.csv`, включая rejected.

Численные источники Figure 8 найдены в CSV; Parquet/JSON для этого расчёта не используются. `verification.json` — новый журнал этого аудита, не исходный научный результат.

## Десять наборов и бюджет

Подтверждены MatterGen, Con-CDVAE, CrystalFormer и CrystaLLM в состояниях Base и Fine-tuned, плюс Crys-JEPA Base и Refined. Во всех десяти QC-популяциях по 2000 записей. QC-retained: соответственно 1657, 1376, 1864, 1299, 1083, 1380, 98, 217, 1764, 1543 в порядке сравнительной таблицы. Сумма — 12281.

Для всех 12281 записей совпадают пары `(analysis_cohort, sample_uid)` между дескрипторами и популяцией Figure 8; проверены отсутствие повторных sample_uid, числа принятых структур и уникальных reduced formula. Подтверждены нормированный benchmark-бюджет и QC-статусы, а не физическое число попыток в произвольных исходных generation logs. Старые README/подпись называют бюджет неподтверждённым; этот аудит подтверждает его по полным локальным benchmark QC-таблицам. Он не восстанавливает более раннюю гармонизацию raw generation logs.

## Единицы, знаменатели и нормировка

Пусть Q — принятые QC структуры набора, U — число различных `formula_reduced` в Q, N = 2000, f3(i) и fLn(i) — атомные доли соответствующих настроенных групп внутри структуры i.

| Величина | Определение | Единица |
|---|---|---|
| QC retention | 100 × len(Q) / N | % от номинального числа генераций |
| Unique-formula yield | 100 × U / N | % от номинального числа генераций |
| S1: 3d atomic-content yield | 100 × sum(f3(i), i in Q) / N | %; атомная доля, усреднённая на номинальный бюджет |
| S2: lanthanide atomic-content yield | 100 × sum(fLn(i), i in Q) / N | %; атомная доля, усреднённая на номинальный бюджет |
| S3: combined coverage yield | 100 × count(i in Q: f3(i)>0 OR fLn(i)>0) / N | % от номинального числа генераций |
| Исходный 3d-containing yield | 100 × count(i in Q: f3(i)>0) / N | % от номинального числа генераций |

Atomic-content yield равен QC retention (%) × средней атомной доле группы среди QC-retained. Это не доля содержащих группу структур и не отношение суммарного числа атомов группы к суммарному числу атомов всех ячеек: каждая структура в сумме имеет одинаковый вес, независимо от размера ячейки. Rejected-записи не дают вклада в числитель, но входят в N. Unique-formula yield не равен within-QC uniqueness (100 × U / len(Q)); например, MatterGen Fine-tuned имеет 20.60% yield и 29.941860465116…% within-QC uniqueness.

S3 использует логическое OR, а не AND; структура с обеими группами учитывается один раз. Охватываются только настроенные 3d и lanthanide группы, не все потенциально магнитные элементы; показатели не подтверждают магнитную функциональность.

Точные группы из `config/magnetism.yaml`: 3d = Sc, Ti, V, Cr, Mn, Fe, Co, Ni, Cu; lanthanides = Ce, Pr, Nd, Sm, Eu, Gd, Tb, Dy, Ho, Er, Tm, Yb. Поэтому «lanthanide» здесь означает именно настроенную группу, без La, Pm и Lu; Zn также не входит в настроенную 3d-группу. Числа не следует обобщать на иной список элементов без отдельного расчёта.

Для каждого сценария три критерия — QC, unique formula и соответствующий химический показатель — независимо нормируются min-max среди всех десяти наборов: z = (x − min(x)) / (max(x) − min(x)). Equal-weight score = (zQC + zUnique + zChem) / 3; это безразмерная оценка на шкале 0–1, не процент и не среднее исходных процентов. Rank — место по убыванию этой оценки, 1 = лучшее. Код использует стабильный порядок наборов при равенстве; для рассматриваемых оценок равенства нет. Частоты по 20000 Dirichlet(1,1,1) весам (seed 1984) — отдельная характеристика чувствительности, не equal-weight rank.

## Численные результаты

Полная компактная таблица: [comparison_table.md](comparison_table.md). Машиночитаемые файлы: [исходная точность](scenario_results_source_precision.csv), [публикационное округление](scenario_results_publication.csv). Исходная точность сохранена текстом непосредственно из CSV, без дополнительного округления. В публикационной версии проценты даны до двух знаков, оценки до четырёх; ненулевые проценты меньше 0.01% — до четырёх знаков, чтобы избежать ложного нуля.

Готовые три английских абзаца с сохранением сценарной структуры: [section_3_7_1_insert.md](section_3_7_1_insert.md).

## Согласованность Methods, текста и Figure 8

1. **3d-containing и atomic-content — разные показатели.** Например, MatterGen Base: 62.40% containing против 38.98092152128916% atomic-content; MatterGen Fine-tuned: 68.70% против 57.17966033171336%. Поэтому переименование подписи без замены данных не исправит несогласованность.
2. **S1 ranking в сохранённом сценарном расчёте использует atomic-content.** MatterGen Base 0.7678980714986876 / rank 1, Con-CDVAE Base 0.6995159005526701 / rank 2, Crys-JEPA Base 0.680009268950399 / rank 3, MatterGen Fine-tuned 0.6442467018778166 / rank 4. Это соответствует указанному автором определению Methods. Полный текст Methods не предоставлен, поэтому вывод относится к этому определению, а не к построчному аудиту всей Methods.
3. **Подпись Figure 8A соответствует фактически изображённому containing-показателю.** В исходном PDF нет atomic-content-колонок S1/S2 или combined-coverage-колонки S3. Несогласованность возникает при интерпретации Figure 8A как численной матрицы сценарного анализа.
4. **Figure 8C и D не представляют S1–S3.** Это распределения мест и top-5 частоты одной исходной трёхкритериальной постановки с containing-показателем (вариант A в сравнении критериев). Это также не строго S1, поскольку S1 использует atomic-content. Панель B и её Pareto-обводки относятся к той же исходной постановке.
5. **Места в предоставленном тексте подтверждены для сохранённых S1–S3.** S1: MatterGen Base > Con-CDVAE Base > Crys-JEPA Base; S2: Crys-JEPA Base > Con-CDVAE Base > MatterGen Base > Crys-JEPA Refined, MatterGen Fine-tuned — восьмой; S3: Con-CDVAE Base > MatterGen Base > Crys-JEPA Base. Однако одинаковый top-3 исходного анализа и S1 скрывает различие: MatterGen Fine-tuned имеет место 5 в исходном анализе против 4 в S1, CrystalFormer Fine-tuned — 4 против 5. Полное сравнение: [original_vs_scenario_ranks.csv](original_vs_scenario_ranks.csv).
6. **Частоты исходного рисунка нельзя переносить на S1.** Например, исходная first-place frequency MatterGen Fine-tuned — 6.04%, а сохранённая S1 — 25.66%; top-5 — 52.315% против 65.02%. В Figure 8D показана именно исходная top-5 частота.
7. **Интерпретация S2 требует различать presence и abundance.** У Crys-JEPA Refined максимальный lanthanide atomic-content yield (10.352646118501381%), но лишь четвёртое агрегированное место. У Con-CDVAE Base химический показатель ниже (5.359443245308182%), но QC/формульные выходы выше. Для MatterGen Fine-tuned показатель 0.004545454545454545% ненулевой. Снижение lanthanide-containing yield при fine-tuning также подтверждается сохранённой химической сводкой: MatterGen 25.00→0.05%, Con-CDVAE 27.05→0.35%, CrystalFormer 10.70→0.40%, CrystaLLM 0.40→0.20% (везде знаменатель 2000). Это поддерживает локально утверждение о reduced occurrence; содержание §3.3 целиком не проверялось.
8. **Компромисс S3:** Con-CDVAE Base выигрывает по aggregate score (0.8874429223744292) при coverage 53.25%, хотя MatterGen Base имеет максимальное coverage 77.90% и score 0.8779640505517192. Причина — более высокие QC/unique-formula yields Con-CDVAE Base, 93.20/92.10% против 82.85/69.60%. Называть победителя S3 лидером именно по coverage было бы неверно.

Исправления рисунка или его подписи автоматически не выполнялись. Для согласования рукописи потребуется отдельно выбрать, какую версию анализа иллюстрировать; готовые абзацы ниже относятся именно к сохранённым S1–S3.

## Проверка и воспроизводимость аудита

[audit_saved_results.py](audit_saved_results.py) использует только стандартную библиотеку Python, читает сохранённые источники и независимо проверяет расчёт показателей, min-max нормировку и equal-weight ranks. Допуск проверки — 1e-10 процентного пункта для yields, 1e-14 для normalized/equal-weight scores. Повторный запуск преднамеренно не перезаписывает уже существующие выходные файлы.

[verification.json](verification.json) содержит результат PASS и SHA256 исходных файлов; [qc_budget_verification.csv](qc_budget_verification.csv) — QC-бюджеты. Исходный PDF визуально проверен по отдельному рендеру `../audit_2026-11-09_original_render.png`: значения A и top-5 значения D соответствуют сохранённым источникам. Случайные веса заново не сэмплировались. Окружение `.venv` не импортирует бинарные NumPy/PyMuPDF DLL, поэтому для численного аудита использована независимая проверка Decimal/csv, для просмотра PDF — доступный pdftoppm.
