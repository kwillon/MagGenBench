import pandas as pd
import os
from pymatgen.core import Composition


def process_train_csv(input_path, output_path):
    print(f"Обработка {input_path}...")

    # Читаем CSV
    df = pd.read_csv(input_path)

    # 1. Маппинг ID
    # В ваших примерах везде 'material_id'
    new_df = pd.DataFrame()
    new_df["id"] = df["material_id"]

    # 2. Обработка формулы (приводим к reduced_formula через pymatgen)
    def clean_formula(f):
        try:
            # Composition сам сделает формулу "красивой" и сокращенной
            return Composition(str(f)).reduced_formula
        except:
            return str(f)

    new_df["reduced_formula"] = df["pretty_formula"].apply(clean_formula)

    # 3. Поиск колонки со Space Group (она отличается в разных файлах)
    # Ищем подходящее имя колонки
    sg_col = None
    possible_sg_cols = ["spacegroup_number", "spacegroup.number"]

    for col in possible_sg_cols:
        if col in df.columns:
            sg_col = col
            break

    if sg_col:
        # Приводим к инту (в csv 1 они могут быть как 8.0)
        new_df["spacegroup"] = df[sg_col].fillna(0).astype(int)
    else:
        print(f"Предупреждение: Колонка spacegroup не найдена в {input_path}!")
        new_df["spacegroup"] = 0

    # Сохраняем результат
    new_df.to_csv(output_path, index=False)
    print(f"Сохранено: {output_path} (строк: {len(new_df)})")


# Список ваших файлов (замените на реальные пути)
files_to_process = ["crystalformer_test.csv", "mattergen_train.csv", "concdvae.csv","crystalllm_train.csv",]

for file in files_to_process:
    if os.path.exists(file):
        # Extract model name from filename by removing extension and common prefixes/suffixes
        model_name = (
            os.path.splitext(file)[0].replace("_test", "").replace("_train", "")
        )
        output_name = f"train_reference_{model_name}.csv"
        process_train_csv(file, output_name)
    else:
        print(f"Файл {file} не найден.")
