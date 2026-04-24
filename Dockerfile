FROM mambaorg/micromamba:1.5.8

# Рабочая директория внутри контейнера
WORKDIR /app

# 1) Сначала кладём env-файл отдельно — это даёт кеш слоёв
COPY --chown=$MAMBA_USER:$MAMBA_USER environment.yml /app/environment.yml

# 2) Создаём окружение (имя берём из environment.yml -> name:)
RUN micromamba create -y -f /app/environment.yml && \
    micromamba clean -a -y

# Важно: активируем окружение для всех последующих RUN/CMD
ENV MAMBA_DOCKERFILE_ACTIVATE=1

# 3) Копируем код проекта
COPY --chown=$MAMBA_USER:$MAMBA_USER . /app

# 4) Ставим пакет в editable (чтобы консольная команда mvp появилась)
# Если у вас pyproject.toml настроен корректно, mvp появится автоматически.
RUN micromamba run -n mvpipeline pip install -e .

# По умолчанию показываем help
ENTRYPOINT ["micromamba", "run", "-n", "mvpipeline"]
CMD ["mvp", "--help"]
