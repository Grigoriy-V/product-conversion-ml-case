"""Build deterministic conceptual figures for the classical-ML tutorial.

The figures draw fixed schematic shapes and toy points only.  This script does
not read project data, fit a model, or access the frozen test boundary.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "assets" / "tutorial"
STEMS = (
    "data_workflow",
    "cross_validation_folds",
    "preprocessing_pipeline",
    "logistic_vs_tree",
    "random_forest_aggregation",
)
COLORS = {
    "blue": "#0072B2",
    "orange": "#E69F00",
    "green": "#009E73",
    "red": "#D55E00",
    "gray": "#6C757D",
    "light_blue": "#E8F2F8",
    "light_orange": "#FFF3D6",
    "light_green": "#E7F5EF",
    "dark": "#24313B",
}


def save(fig: plt.Figure, stem: str) -> None:
    """Save one diagram in documentation-friendly raster and vector forms."""
    ASSETS.mkdir(parents=True, exist_ok=True)
    fig.savefig(ASSETS / f"{stem}.png", dpi=170, bbox_inches="tight", facecolor="white")
    fig.savefig(ASSETS / f"{stem}.svg", bbox_inches="tight", facecolor="white", metadata={"Date": None})
    plt.close(fig)


def box(ax: plt.Axes, x: float, y: float, width: float, height: float, label: str, color: str, *, fontsize: float = 10) -> None:
    patch = FancyBboxPatch(
        (x, y), width, height,
        boxstyle="round,pad=0.02,rounding_size=0.035",
        facecolor=color,
        edgecolor=COLORS["dark"],
        linewidth=1.2,
    )
    ax.add_patch(patch)
    ax.text(x + width / 2, y + height / 2, label, ha="center", va="center", fontsize=fontsize, color=COLORS["dark"], wrap=True)


def arrow(ax: plt.Axes, start: tuple[float, float], end: tuple[float, float], *, color: str = "#4A4A4A") -> None:
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=14, linewidth=1.5, color=color))


def workflow() -> None:
    fig, ax = plt.subplots(figsize=(12, 3.7))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_title("Путь одной ML-задачи: от сессии к решению", loc="left", weight="bold", pad=13)
    items = [
        (0.02, "Строка-сессия\n(raw data)", COLORS["light_blue"]),
        (0.20, "X: признаки\ny: Revenue", COLORS["light_orange"]),
        (0.38, "Train / CV /\nuntouched test", COLORS["light_green"]),
        (0.58, "Pipeline +\nмодель", COLORS["light_blue"]),
        (0.74, "Score\n0.00...1.00", COLORS["light_orange"]),
        (0.90, "Решение\nпо порогу", COLORS["light_green"]),
    ]
    for index, (x, label, color) in enumerate(items):
        width = 0.13 if index < 5 else 0.075
        box(ax, x, 0.42, width, 0.25, label, color, fontsize=9.5)
        if index:
            previous_x = items[index - 1][0]
            previous_width = 0.13 if index - 1 < 5 else 0.075
            arrow(ax, (previous_x + previous_width + 0.005, 0.545), (x - 0.008, 0.545))
    ax.text(0.02, 0.12, "Сначала проверяем данные и границы. Затем модель ранжирует сессии score; threshold превращает score в действие.", fontsize=10, color=COLORS["dark"])
    save(fig, "data_workflow")


def cross_validation() -> None:
    fig, ax = plt.subplots(figsize=(11.5, 5.4))
    ax.set_xlim(0, 13)
    ax.set_ylim(-0.8, 7)
    ax.axis("off")
    ax.set_title("5-fold CV использует только train; test остаётся закрытым", loc="left", weight="bold", pad=13)
    x0, cell_w = 1.4, 1.12
    colors = [COLORS["blue"], COLORS["blue"], COLORS["blue"], COLORS["blue"], COLORS["orange"]]
    for row in range(5):
        ax.text(0.15, 5.8 - row, f"Fold {row + 1}", va="center", fontsize=10, weight="bold")
        for col in range(5):
            is_validation = col == row
            face = COLORS["light_orange"] if is_validation else COLORS["light_blue"]
            rect = Rectangle((x0 + col * cell_w, 5.43 - row), cell_w - 0.06, 0.62, facecolor=face, edgecolor=COLORS["dark"], linewidth=0.8)
            ax.add_patch(rect)
            ax.text(x0 + col * cell_w + (cell_w - 0.06) / 2, 5.74 - row, "validation" if is_validation else "fit", ha="center", va="center", fontsize=8.3)
    ax.text(x0, -0.05, "Пять частей train (9 864 строк)", fontsize=10, weight="bold")
    box(ax, 8.1, 2.5, 3.7, 1.35, "Frozen test\n2 466 строк\nне участвует в CV", "#F7E4E4", fontsize=11)
    ax.text(8.1, 1.65, "Открывается один раз после\nвыбора модели.", fontsize=9.5, color=COLORS["red"])
    arrow(ax, (6.9, 2.7), (7.9, 2.7), color=COLORS["gray"])
    ax.text(x0, -0.55, "В каждом проходе Pipeline fit-ится только на синих блоках; оранжевый блок получает прогноз и метрику.", fontsize=9.2, color=COLORS["dark"])
    save(fig, "cross_validation_folds")


def preprocessing() -> None:
    fig, ax = plt.subplots(figsize=(12, 5.2))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_title("Fold-safe preprocessing внутри Pipeline", loc="left", weight="bold", pad=13)
    box(ax, 0.03, 0.42, 0.16, 0.18, "Train fold\nraw features", COLORS["light_blue"])
    box(ax, 0.29, 0.63, 0.2, 0.18, "Numeric\nmedian + scaler", COLORS["light_green"])
    box(ax, 0.29, 0.20, 0.2, 0.18, "Categorical\nmost-frequent + one-hot", COLORS["light_orange"], fontsize=9)
    box(ax, 0.59, 0.42, 0.16, 0.18, "Общий\nfeature matrix", COLORS["light_blue"])
    box(ax, 0.83, 0.42, 0.13, 0.18, "Estimator\nLR / RF", COLORS["light_green"])
    arrow(ax, (0.19, 0.52), (0.28, 0.72))
    arrow(ax, (0.19, 0.48), (0.28, 0.29))
    arrow(ax, (0.49, 0.72), (0.58, 0.52))
    arrow(ax, (0.49, 0.29), (0.58, 0.48))
    arrow(ax, (0.75, 0.51), (0.82, 0.51))
    ax.add_patch(FancyBboxPatch((0.24, 0.1), 0.74, 0.78, boxstyle="round,pad=0.02,rounding_size=0.03", fill=False, edgecolor=COLORS["blue"], linewidth=2, linestyle="--"))
    ax.text(0.61, 0.91, "Один sklearn Pipeline", ha="center", fontsize=11, color=COLORS["blue"], weight="bold")
    ax.text(0.03, 0.06, "На каждом CV-проходе imputer, encoder, scaler и модель fit-ятся только на training folds, а затем применяются к validation fold.", fontsize=9.2)
    save(fig, "preprocessing_pipeline")


def logistic_vs_tree() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.9), sharex=True, sharey=True, constrained_layout=True)
    points_positive = [(0.72, 0.70), (0.80, 0.52), (0.64, 0.84), (0.87, 0.78), (0.58, 0.59)]
    points_negative = [(0.16, 0.23), (0.31, 0.60), (0.43, 0.24), (0.48, 0.45), (0.25, 0.83), (0.55, 0.36)]
    for ax, title in zip(axes, ("Logistic Regression: гладкая граница", "Decision tree: ступенчатые области"), strict=True):
        ax.set_title(title, loc="left", weight="bold")
        ax.scatter(*zip(*points_negative), c=COLORS["blue"], s=55, label="Нет покупки")
        ax.scatter(*zip(*points_positive), c=COLORS["orange"], marker="^", s=65, label="Покупка")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xlabel("Признак A (условный)")
        ax.grid(color="#E2E2E2", linewidth=0.7)
    axes[0].set_ylabel("Признак B (условный)")
    axes[0].plot([0.08, 0.94], [0.20, 0.91], color=COLORS["red"], linewidth=2, label="Линейная граница")
    axes[1].axvline(0.60, color=COLORS["red"], linewidth=2)
    axes[1].hlines(0.48, 0.60, 1.0, color=COLORS["red"], linewidth=2)
    axes[1].add_patch(Rectangle((0.60, 0.48), 0.40, 0.52, facecolor="#FDE9D9", alpha=0.55, zorder=0))
    axes[1].text(0.77, 0.25, "несколько\nпороговых\nправил", ha="center", color=COLORS["red"], fontsize=10)
    axes[0].legend(frameon=False, loc="upper left", fontsize=9)
    fig.text(0.5, -0.035, "Концептуальная synthetic-иллюстрация: точки не из датасета проекта и модели здесь не обучаются.", ha="center", fontsize=9, color=COLORS["gray"])
    save(fig, "logistic_vs_tree")


def random_forest() -> None:
    fig, ax = plt.subplots(figsize=(12, 4.8))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_title("Random Forest: несколько деревьев усредняют свой score", loc="left", weight="bold", pad=13)
    box(ax, 0.03, 0.41, 0.15, 0.2, "Одна\nсессия X", COLORS["light_blue"])
    tree_positions = [0.30, 0.46, 0.62]
    for index, x in enumerate(tree_positions, start=1):
        box(ax, x, 0.56, 0.10, 0.15, f"Tree {index}\nscore", COLORS["light_green"], fontsize=9)
        ax.plot([x + 0.05, x + 0.05], [0.34, 0.56], color=COLORS["dark"], linewidth=1.2)
        ax.plot([x + 0.05, x - 0.005], [0.44, 0.34], color=COLORS["dark"], linewidth=1.2)
        ax.plot([x + 0.05, x + 0.105], [0.44, 0.34], color=COLORS["dark"], linewidth=1.2)
        arrow(ax, (0.18, 0.51), (x - 0.01, 0.63))
    ax.text(0.72, 0.64, "...", fontsize=22, color=COLORS["gray"], ha="center")
    box(ax, 0.75, 0.41, 0.11, 0.2, "Среднее\nscores", COLORS["light_orange"])
    box(ax, 0.90, 0.41, 0.075, 0.2, "Final\nscore", COLORS["light_blue"], fontsize=8.5)
    for x in tree_positions:
        arrow(ax, (x + 0.10, 0.635), (0.74, 0.53), color=COLORS["gray"])
    arrow(ax, (0.86, 0.51), (0.89, 0.51))
    ax.text(0.03, 0.12, "В проекте использован фиксированный Random Forest из 200 деревьев. Схема показывает принцип, а не все 200 деревьев.", fontsize=10, color=COLORS["dark"])
    save(fig, "random_forest_aggregation")


def main() -> None:
    workflow()
    cross_validation()
    preprocessing()
    logistic_vs_tree()
    random_forest()
    print("Built five conceptual tutorial figures in docs/assets/tutorial as PNG and SVG.")


if __name__ == "__main__":
    main()
