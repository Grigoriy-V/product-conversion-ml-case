# Classical ML Project Roadmap

> **Current status (2026-07-19):** Steps 1–7 and the intermediate step-8
> portfolio package are accepted. The selected
> dataset is UCI Online Shoppers Purchasing Intention Dataset (UCI id 468),
> unit=session, binary target=`Revenue`, positive class=`TRUE`, source license
> CC BY 4.0. The accepted audit excludes `Revenue` and `PageValues` from
> features, records duplicate and feature-availability risks, and limits claims
> to an offline session-level benchmark; it does not establish a deployable
> real-time or early-session predictor. The frozen holdout is a deterministic
> group-safe stratified 80/20 split with seed `20260719`; model selection must
> use the accepted five-fold group-safe protocol on training rows only.
>
> **Step 6 result:** the selected fixed Random Forest was fitted once on all
> 9,864 frozen training rows and evaluated once on the 2,466-row frozen test.
> Final AP=`0.368148`, ROC-AUC=`0.778014`; at the unchanged default threshold
> 0.5, balanced accuracy=`0.521619`, precision=`0.512821`,
> recall=`0.052356`, and F1=`0.095012`. No test-driven model, preprocessing,
> calibration, or threshold change was made.
>
> **Step 7 result:** train-only five-fold OOF analysis selected threshold
> `0.127325` under the illustrative F2 objective: precision=`0.253803`,
> recall=`0.863696`, F2=`0.583341`, predicted-positive rate=`0.526460`.
> Calibration was not performed and the frozen test was not accessed.
>
> **Intermediate portfolio package:** README, case study, and reproducible
> Matplotlib AP/threshold figures are available. This is not final closeout.
>
> **Current nearest action:** stop for human direction. A future bounded
> model-improvement phase is planned but has not started. Candidate selection
> must stay on the accepted train-CV protocol; the used test must not be
> reopened, and a new unbiased final claim requires a separate independent
> external dataset or newly frozen evaluation boundary.

**Статус:** шаги 1–7 приняты. Окружение: Python 3.12.4,
`numpy==2.2.6`, `pandas==2.3.1`, `scikit-learn==1.7.0`. Train-only baseline
показал average precision `0.154704` для dummy и `0.330526` для фиксированной
`LogisticRegression`. Фиксированный `RandomForestClassifier` улучшил
train-only CV average precision до `0.379083` и прошёл единственную финальную
holdout-оценку: AP `0.368148`, ROC-AUC `0.778014`. Held-out test закрыт для
дальнейшего выбора модели и порога.

Это единственный канонический roadmap проекта. Техническая история предыдущих
проверок сохранена в Git и `reports/`; она не определяет порядок
ML-экспериментов.

Dataset audit, frozen split, baseline, model comparison и единственная
финальная holdout evaluation выполнены и приняты.

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

**Статус:** принято.

- Рассмотреть публичные кандидаты без предварительного выбора победителя.
- Для выбранного кандидата зафиксировать источник, лицензию и допустимое
  использование.
- Определить задачу, единицу наблюдения, target и практический смысл прогноза.
- Получить human approval до download или подготовки данных.

### 2. Dataset / target / leakage audit

**Статус:** принято с ограничением на offline session-level benchmark.

- Проверить schema, типы, missing values, duplicates и подозрительные поля.
- Исследовать class balance или распределение target.
- Выявить прямой, временной, групповой и post-outcome leakage.
- Зафиксировать ограничения данных и решение continue/change/stop.

### 3. Train / validation / test split

**Статус:** принято.

- Выбрать random, stratified, grouped или temporal split по природе данных.
- Заморозить test split до model selection.
- Зафиксировать seed, split fingerprints и правила cross-validation.

### 4. Простая baseline

**Статус:** принято.

- Начать с dummy baseline и одной простой интерпретируемой модели.
- Использовать минимальный preprocessing, достаточный для корректного запуска.
- Зафиксировать метрики, runtime и основные ошибки.

### 5. sklearn Pipeline и cross-validation

**Статус:** принято; выбран фиксированный Random Forest.

- Поместить imputation, encoding, scaling и estimator в единый `Pipeline`.
- Fit preprocessing выполнять только на training folds.
- Сравнить ограниченный набор обоснованных моделей при одинаковом CV protocol.
- Не расширять search space без evidence, что это полезно.

### 6. Метрики и error analysis

**Статус:** принято.

- Выбрать primary и secondary metrics по задаче и стоимости ошибок.
- Проверить стабильность по folds и релевантным slices.
- Разобрать false positives/false negatives или крупные regression errors.
- Сравнить результат с baseline и описать ограничения.

### 7. Calibration и threshold — только при необходимости

**Статус:** принято; выполнен train-only OOF threshold analysis без calibration.

- Для вероятностной классификации проверить calibration.
- Настраивать threshold только на validation evidence и под явную cost
  function.
- Не использовать threshold tuning для задач, где он не имеет смысла.

### 8. Portfolio summary

**Статус:** промежуточный portfolio package принят; финальный closeout отложен
до решения о будущей фазе улучшения модели.

- Описать задачу, данные, leakage controls, split и pipeline.
- Показать baseline, итоговые метрики, error analysis и ограничения.
- Добавить воспроизводимые команды и ссылки на experiment evidence.
- Не делать production claims без соответствующих проверок.

### 9. Planned model-improvement return

**Статус:** запланировано, не начато.

- До запуска заранее ограничить набор новых кандидатов и критерий улучшения.
- Сравнивать новые модели только на принятом frozen train-CV protocol.
- Не использовать уже открытый held-out test для повторного выбора или
  подтверждения улучшения.
- Для нового unbiased final claim заранее определить отдельный внешний dataset
  или новую независимую frozen evaluation boundary.
- После этой фазы обновить portfolio summary только по принятому evidence.

## Ближайшее точное действие

Остановиться для human direction. Промежуточный portfolio package принят.
Будущая фаза улучшения модели записана, но не начата; held-out test больше не
использовать для выбора модели, preprocessing, calibration или threshold.
