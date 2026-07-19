# Classical ML Project Roadmap

**Статус:** предметная ML-работа ещё не начата.

Это единственный канонический roadmap проекта. Техническая история предыдущих
проверок сохранена в Git и `reports/`; она не определяет порядок
ML-экспериментов.

Ни один dataset не выбран. Dataset preparation, model training, evaluation,
download или другая ML/data operation ещё не выполнялись.

## Правила

1. Выбор dataset, задачи и target требует явного human approval.
2. Использовать только публичный dataset с проверенной лицензией и допустимым
   portfolio-использованием.
3. До обучения проверить смысл target, leakage risks, качество данных и
   пригодность split.
4. Начать с простой интерпретируемой baseline-модели.
5. Все preprocessing steps обучать только внутри sklearn `Pipeline`.
6. Сравнения выполнять при frozen split, метриках и cross-validation protocol.
7. Calibration и threshold tuning добавлять только когда это требуется
   постановкой задачи и стоимостью ошибок.
8. Материальные ML-операции фиксировать в experiment ledger только после их
   фактического выполнения.

## Следующая ML-последовательность

### 1. Human-approved dataset и постановка задачи

- Рассмотреть публичные кандидаты без предварительного выбора победителя.
- Для выбранного кандидата зафиксировать источник, лицензию и допустимое
  использование.
- Определить задачу, единицу наблюдения, target и практический смысл прогноза.
- Получить human approval до download или подготовки данных.

### 2. Dataset / target / leakage audit

- Проверить schema, типы, missing values, duplicates и подозрительные поля.
- Исследовать class balance или распределение target.
- Выявить прямой, временной, групповой и post-outcome leakage.
- Зафиксировать ограничения данных и решение continue/change/stop.

### 3. Train / validation / test split

- Выбрать random, stratified, grouped или temporal split по природе данных.
- Заморозить test split до model selection.
- Зафиксировать seed, split fingerprints и правила cross-validation.

### 4. Простая baseline

- Начать с dummy baseline и одной простой интерпретируемой модели.
- Использовать минимальный preprocessing, достаточный для корректного запуска.
- Зафиксировать метрики, runtime и основные ошибки.

### 5. sklearn Pipeline и cross-validation

- Поместить imputation, encoding, scaling и estimator в единый `Pipeline`.
- Fit preprocessing выполнять только на training folds.
- Сравнить ограниченный набор обоснованных моделей при одинаковом CV protocol.
- Не расширять search space без evidence, что это полезно.

### 6. Метрики и error analysis

- Выбрать primary и secondary metrics по задаче и стоимости ошибок.
- Проверить стабильность по folds и релевантным slices.
- Разобрать false positives/false negatives или крупные regression errors.
- Сравнить результат с baseline и описать ограничения.

### 7. Calibration и threshold — только при необходимости

- Для вероятностной классификации проверить calibration.
- Настраивать threshold только на validation evidence и под явную cost
  function.
- Не использовать threshold tuning для задач, где он не имеет смысла.

### 8. Portfolio summary

- Описать задачу, данные, leakage controls, split и pipeline.
- Показать baseline, итоговые метрики, error analysis и ограничения.
- Добавить воспроизводимые команды и ссылки на experiment evidence.
- Не делать production claims без соответствующих проверок.

## Ближайшее точное действие

Подготовить короткий список публичных dataset-кандидатов с лицензией,
возможной задачей и target для human review. До выбора пользователя не
скачивать данные и не запускать model operation.
