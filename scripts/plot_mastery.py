"""Draw the learner's supplied mastery values with Python/Matplotlib.

Run: apps/api/.venv/Scripts/python.exe scripts/plot_mastery.py
Exports PNG, SVG and PDF charts plus the input data under outputs/mastery-charts.
"""

import json
import os
import sys
from pathlib import Path
from textwrap import fill

ROOT = Path(__file__).resolve().parents[1]
LOCAL_LIBS = ROOT / ".local" / "chart-libs"
if LOCAL_LIBS.exists():
    sys.path.insert(0, str(LOCAL_LIBS))
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".local" / "matplotlib-cache"))

import matplotlib

matplotlib.use("Agg")
from matplotlib import font_manager
from matplotlib import pyplot as plt

DATA = [
    ("Phân biệt huấn luyện và suy luận", 76),
    ("Bài toán hồi quy với dữ liệu tổng hợp", 77),
    ("Quy trình nghiên cứu nhỏ khi huấn luyện", 45),
]
OUTPUT = ROOT / "outputs" / "mastery-charts"
PAPER, INK, MUTED, TRACK = "#FBF8F0", "#36312C", "#756D65", "#E8E1D6"
COLORS = ["#7860A3", "#7860A3", "#BB873E"]


def export(figure, stem: str) -> None:
    for extension in ("png", "svg", "pdf"):
        figure.savefig(
            OUTPUT / f"{stem}.{extension}",
            dpi=200,
            facecolor=PAPER,
            bbox_inches="tight",
            pad_inches=0.25,
        )
    plt.close(figure)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    # Windows Arial includes Vietnamese; DejaVu Sans is the portable fallback.
    arial = Path("C:/Windows/Fonts/arial.ttf")
    if arial.exists():
        font_manager.fontManager.addfont(str(arial))
        bold = arial.with_name("arialbd.ttf")
        if bold.exists():
            font_manager.fontManager.addfont(str(bold))
        family = "Arial"
    else:
        family = "DejaVu Sans"
    plt.rcParams.update(
        {
            "font.family": family,
            "font.size": 12,
            "text.color": INK,
            "axes.labelcolor": MUTED,
            "xtick.color": MUTED,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
        }
    )

    figure = plt.figure(figsize=(13.5, 5.8), facecolor=PAPER)
    figure.text(
        0.04, 0.94, "MỨC ĐỘ THÀNH THẠO CỦA NGƯỜI HỌC", fontsize=22, weight="bold"
    )
    figure.text(
        0.04,
        0.875,
        "Ba phần kiến thức · Giá trị được cung cấp · Thang 0–100%",
        color=MUTED,
    )
    axis = figure.add_axes([0.43, 0.23, 0.52, 0.52], facecolor=PAPER)
    axis.barh(range(3), [100] * 3, height=0.43, color=TRACK, zorder=2)
    axis.barh(
        range(3), [value for _, value in DATA], height=0.43, color=COLORS, zorder=3
    )
    for index, (label, value) in enumerate(DATA):
        axis.text(
            -0.04,
            index,
            fill(label, width=34),
            transform=axis.get_yaxis_transform(),
            ha="right",
            va="center",
            fontsize=13,
        )
        axis.text(
            value + 1.5,
            index,
            f"{value}%",
            va="center",
            fontsize=16,
            weight="bold",
            color=COLORS[index],
        )
    axis.set_xlim(0, 100)
    axis.set_ylim(2.6, -0.6)
    axis.set_yticks([])
    axis.set_xticks([0, 20, 40, 60, 80, 100])
    axis.set_xticklabels([f"{value}%" for value in (0, 20, 40, 60, 80, 100)])
    axis.tick_params(axis="x", length=0, pad=12)
    axis.set_xlabel("Mức độ thành thạo (%)", labelpad=14)
    axis.grid(axis="x", color=TRACK, linewidth=0.8, zorder=0)
    for spine in axis.spines.values():
        spine.set_visible(False)
    figure.text(
        0.04,
        0.055,
        "Phần màu nhạt biểu thị phần còn lại đến 100%. Mỗi kiến thức được đo độc lập.",
        color=MUTED,
        fontsize=10,
    )
    export(figure, "muc-do-thanh-thao")

    figure, axes = plt.subplots(1, 3, figsize=(13.5, 5.7), facecolor=PAPER)
    figure.subplots_adjust(left=0.04, right=0.96, top=0.66, bottom=0.10, wspace=0.40)
    figure.text(
        0.04, 0.94, "THÀNH THẠO THEO TỪNG KIẾN THỨC", fontsize=22, weight="bold"
    )
    figure.text(
        0.04,
        0.875,
        "Mỗi vòng tròn biểu diễn mức độ thành thạo của một phần kiến thức",
        color=MUTED,
    )
    for axis, (label, value), color in zip(axes, DATA, COLORS, strict=True):
        axis.pie(
            [value, 100 - value],
            startangle=90,
            counterclock=False,
            colors=[color, TRACK],
            wedgeprops={"width": 0.14, "edgecolor": "none"},
        )
        axis.text(
            0,
            0.07,
            f"{value}%",
            ha="center",
            va="center",
            fontsize=34,
            weight="bold",
            color=color,
        )
        axis.text(
            0, -0.24, "thành thạo", ha="center", va="center", fontsize=11, color=MUTED
        )
        axis.set_title(fill(label, width=28), fontsize=12, color=INK, pad=17)
        axis.set_aspect("equal")
    figure.text(
        0.04,
        0.045,
        "Các tỷ lệ thuộc ba kiến thức riêng biệt và không cộng lại với nhau.",
        fontsize=10,
        color=MUTED,
    )
    export(figure, "thanh-thao-tung-kien-thuc")

    (OUTPUT / "du-lieu.json").write_text(
        json.dumps(
            [
                {"kien_thuc": label, "thanh_thao_phan_tram": value}
                for label, value in DATA
            ],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print("Created two mastery charts (PNG, SVG, PDF) in outputs/mastery-charts")


if __name__ == "__main__":
    main()
