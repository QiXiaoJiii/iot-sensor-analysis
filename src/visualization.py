"""
可视化模块 — 传感器数据可视化

功能:
  1. 时间序列折线图（单/多通道）
  2. 散点图与相关性图
  3. 热力图（相关性矩阵）
  4. 分布直方图 + 核密度估计
  5. 箱线图
  6. 多子图组合仪表盘
  7. 图表保存
"""

import os
from typing import Optional, Union, Literal
from datetime import datetime

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.dates import DateFormatter
from scipy import stats as scipy_stats


# ── Nature 期刊级图表基础配置 ──
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Microsoft YaHei", "SimHei",
                        "Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
    "axes.unicode_minus": False,
    "axes.spines.right": False,
    "axes.spines.top": False,
    "axes.linewidth": 0.8,
    "legend.frameon": False,
    "legend.fontsize": 9,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "axes.labelsize": 9,
    "axes.titlesize": 11,
    "figure.titlesize": 13,
    "lines.linewidth": 1.5,
    "grid.alpha": 0.25,
    "grid.linestyle": "--",
})


class SensorVisualizer:
    """传感器数据可视化器（Nature 期刊风格）"""

    # Nature 级配色：蓝主色 / 绿正向 / 红对比 / 青辅 / 紫辅 / 灰中性 / 金强调
    COLOR_PALETTE = [
        "#0F4D92",  # deep blue (hero)
        "#8BCF8B",  # green (positive)
        "#B64342",  # red (contrast)
        "#42949E",  # teal
        "#9A4D8E",  # violet
        "#767676",  # neutral mid gray
        "#FFD700",  # gold accent
        "#EA84DD",  # magenta
    ]

    def __init__(self, df: Optional[pd.DataFrame] = None,
                 timestamp_col: Optional[str] = None,
                 dpi: int = 150,
                 figsize: tuple = (8, 4.5)):
        self.df = df
        self.timestamp_col = timestamp_col
        self.dpi = dpi
        self.figsize = figsize

    def set_data(self, df: pd.DataFrame, timestamp_col: Optional[str] = None):
        """设置可视化数据"""
        self.df = df
        if timestamp_col:
            self.timestamp_col = timestamp_col
        elif timestamp_col is None:
            # 自动检测时间戳列
            for col in df.columns:
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    self.timestamp_col = col
                    break

    # ──────────────────────────────────────────
    # 单一图表类
    # ──────────────────────────────────────────

    def plot_time_series(self, columns: Union[str, list],
                         title: Optional[str] = None,
                         show_grid: bool = True,
                         legend: bool = True,
                         save_path: Optional[str] = None) -> Figure:
        """
        时间序列折线图（核心图表）

        参数:
            columns: 要绘制的传感器列（单个列名或列表）
            title: 图表标题
            show_grid: 是否显示网格
            legend: 是否显示图例
            save_path: 保存路径（可选）

        返回:
            matplotlib Figure 对象
        """
        if isinstance(columns, str):
            columns = [columns]

        fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)
        fig.patch.set_facecolor("white")
        n_colors = len(self.COLOR_PALETTE)

        for i, col in enumerate(columns):
            if col not in self.df.columns:
                continue
            color = self.COLOR_PALETTE[i % n_colors]
            if self.timestamp_col and self.timestamp_col in self.df.columns:
                ax.plot(self.df[self.timestamp_col], self.df[col],
                        label=col, color=color, linewidth=1.6)
            else:
                ax.plot(self.df[col], label=col,
                        color=color, linewidth=1.6)

        if self.timestamp_col and self.timestamp_col in self.df.columns:
            ax.xaxis.set_major_formatter(DateFormatter("%m-%d %H:%M"))
            fig.autofmt_xdate(rotation=30, ha="right")

        ax.set_xlabel("时间" if self.timestamp_col else "采样点")
        ax.set_ylabel("数值")
        ax.set_title(title or "时序图", pad=10)
        if show_grid:
            ax.grid(True, alpha=0.2, linestyle="--", linewidth=0.5)
        if legend and len(columns) <= 8:
            ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1),
                      borderaxespad=0, fontsize=8)

        fig.tight_layout(pad=1.2)
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches="tight",
                       facecolor="white", edgecolor="none")
        return fig

    def plot_scatter(self, col_x: str, col_y: str,
                     title: Optional[str] = None,
                     color: str = "#5470C6",
                     alpha: float = 0.6,
                     add_trend_line: bool = True,
                     save_path: Optional[str] = None) -> Figure:
        """
        散点图（两传感器相关性可视化）

        参数:
            col_x: X 轴传感器
            col_y: Y 轴传感器
            add_trend_line: 是否添加线性趋势线

        返回:
            Figure 对象
        """
        fig, ax = plt.subplots(figsize=(6, 5.5), dpi=self.dpi)
        fig.patch.set_facecolor("white")

        x = self.df[col_x].dropna().values
        y = self.df[col_y].dropna().values
        min_len = min(len(x), len(y))
        x, y = x[:min_len], y[:min_len]

        ax.scatter(x, y, c=self.COLOR_PALETTE[0], alpha=0.55,
                   edgecolors="none", s=22)

        if add_trend_line and len(x) > 2:
            slope, intercept, r_val, p_val, std_err = scipy_stats.linregress(x, y)
            x_line = np.linspace(x.min(), x.max(), 100)
            y_line = slope * x_line + intercept
            ax.plot(x_line, y_line, color=self.COLOR_PALETTE[2],
                    linewidth=1.8, linestyle="--",
                    label=f"r = {r_val:.3f}")
            ax.legend(loc="upper right", fontsize=9)

        ax.set_xlabel(col_x)
        ax.set_ylabel(col_y)
        ax.set_title(title or f"{col_x} vs {col_y}", pad=10)
        ax.grid(True, alpha=0.2, linestyle="--", linewidth=0.5)

        fig.tight_layout(pad=1.2)
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches="tight",
                       facecolor="white", edgecolor="none")
        return fig

    def plot_heatmap(self, columns: Optional[list] = None,
                     method: Literal["pearson", "spearman",
                                     "kendall"] = "pearson",
                     title: Optional[str] = None,
                     annot: bool = True,
                     cmap: str = "RdBu_r",
                     save_path: Optional[str] = None) -> Figure:
        """
        相关性热力图

        参数:
            columns: 要分析的传感器列
            method: 相关系数方法
            annot: 是否在格子中显示数值

        返回:
            Figure 对象
        """
        if columns is None:
            columns = self.df.select_dtypes(include=[np.number]).columns.tolist()
        elif isinstance(columns, str):
            columns = [columns]

        corr = self.df[columns].corr(method=method)

        fig, ax = plt.subplots(figsize=(max(8, len(columns) * 1.2),
                                         max(7, len(columns) * 1.0)),
                                dpi=self.dpi)
        im = ax.imshow(corr.values, cmap=cmap, vmin=-1, vmax=1,
                       aspect="auto")

        if annot:
            for i in range(len(columns)):
                for j in range(len(columns)):
                    text = f"{corr.values[i, j]:.2f}"
                    color = "white" if abs(corr.values[i, j]) > 0.5 else "black"
                    ax.text(j, i, text, ha="center", va="center",
                            fontsize=9, color=color)

        n = len(columns)
        hfont = 9 if n <= 6 else (8 if n <= 10 else 7)
        ax.set_xticks(range(n))
        ax.set_yticks(range(n))
        ax.set_xticklabels(columns, rotation=45, ha="right", fontsize=hfont)
        ax.set_yticklabels(columns, fontsize=hfont)
        ax.set_title(title or f"相关系数矩阵 ({method})")

        fig.colorbar(im, ax=ax, shrink=0.8, label="相关系数")
        fig.tight_layout(pad=1.2)
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches="tight",
                       facecolor="white", edgecolor="none")
        return fig

    def plot_histogram(self, columns: Union[str, list],
                       bins: int = 30,
                       kde: bool = True,
                       title: Optional[str] = None,
                       alpha: float = 0.6,
                       save_path: Optional[str] = None) -> Figure:
        """
        分布直方图（带核密度估计）

        参数:
            columns: 传感器列名或列表
            bins: 分箱数
            kde: 是否叠加核密度曲线

        返回:
            Figure 对象
        """
        if isinstance(columns, str):
            columns = [columns]

        n_cols = len(columns)
        fig, axes = plt.subplots(1, n_cols, figsize=(5 * n_cols, 5),
                                  dpi=self.dpi, squeeze=False)
        ax_list = axes.flatten()
        n_colors = len(self.COLOR_PALETTE)

        for idx, col in enumerate(columns):
            if col not in self.df.columns:
                continue
            ax = ax_list[idx]
            data = self.df[col].dropna().values
            color = self.COLOR_PALETTE[idx % n_colors]

            ax.hist(data, bins=bins, density=True, alpha=alpha,
                    color=color, edgecolor="white", linewidth=0.5)

            if kde:
                x_grid = np.linspace(data.min(), data.max(), 200)
                kernel = scipy_stats.gaussian_kde(data)
                ax.plot(x_grid, kernel(x_grid), color="red",
                        linewidth=1.5, label="KDE")
                ax.legend(fontsize=8)

            ax.set_xlabel(col)
            ax.set_ylabel("密度")
            ax.set_title(col)
            ax.grid(True, alpha=0.3, linestyle="--")

        fig.suptitle(title or "分布直方图", fontsize=13, y=1.02)
        fig.tight_layout(pad=1.2)
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches="tight",
                       facecolor="white", edgecolor="none")
        return fig

    def plot_boxplot(self, columns: Optional[list] = None,
                     title: Optional[str] = None,
                     show_outliers: bool = True,
                     save_path: Optional[str] = None) -> Figure:
        """
        箱线图（多传感器分布对比）

        参数:
            columns: 传感器列名列表
            show_outliers: 是否显示异常值点

        返回:
            Figure 对象
        """
        if columns is None:
            columns = self.df.select_dtypes(include=[np.number]).columns.tolist()
        elif isinstance(columns, str):
            columns = [columns]

        fig, ax = plt.subplots(figsize=(max(10, len(columns) * 0.8), 6),
                                dpi=self.dpi)

        data_list = [self.df[col].dropna().values for col in columns
                     if col in self.df.columns]

        bp = ax.boxplot(data_list, labels=columns, patch_artist=True,
                        showfliers=show_outliers)

        for patch, color in zip(bp["boxes"], self.COLOR_PALETTE):
            patch.set_facecolor(color)
            patch.set_alpha(0.6)

        ax.set_ylabel("数值")
        ax.set_title(title or "箱线图")
        ax.grid(True, alpha=0.3, linestyle="--")
        # 列多时自动缩小字号并加大旋转，防止标签重叠
        n = len(columns)
        xfont = 9 if n <= 6 else (8 if n <= 10 else 7)
        xrot = 30 if n <= 6 else 60
        ax.tick_params(axis="x", rotation=xrot, labelsize=xfont)

        fig.tight_layout(pad=1.2)
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches="tight",
                       facecolor="white", edgecolor="none")
        return fig

    # ──────────────────────────────────────────
    # 组合仪表盘
    # ──────────────────────────────────────────

    def plot_dashboard(self, columns: Optional[list] = None,
                       save_path: Optional[str] = None) -> Figure:
        """
        综合仪表盘：折线图 + 直方图 + 箱线图 + 散点图矩阵（选前4个传感器）

        用于快速概览数据全貌
        """
        if columns is None:
            columns = self.df.select_dtypes(include=[np.number]).columns.tolist()
        elif isinstance(columns, str):
            columns = [columns]

        columns = columns[:4]  # 最多 4 个传感器

        fig, axes = plt.subplots(2, 2, figsize=(10, 7), dpi=self.dpi)
        n_colors = len(self.COLOR_PALETTE)

        # (1) 时间序列（左上）
        ax1 = axes[0, 0]
        for i, col in enumerate(columns):
            if col not in self.df.columns:
                continue
            color = self.COLOR_PALETTE[i % n_colors]
            ax1.plot(self.df[col], label=col, color=color,
                     linewidth=1.2, alpha=0.85)
        ax1.set_title("时间序列")
        ax1.grid(True, alpha=0.3, linestyle="--")
        ax1.legend(fontsize=8)

        # (2) 直方图（右上）
        ax2 = axes[0, 1]
        for i, col in enumerate(columns):
            if col not in self.df.columns:
                continue
            data = self.df[col].dropna().values
            color = self.COLOR_PALETTE[i % n_colors]
            ax2.hist(data, bins=25, density=True, alpha=0.5,
                     label=col, color=color, edgecolor="white")
        ax2.set_title("分布直方图")
        ax2.grid(True, alpha=0.3, linestyle="--")
        ax2.legend(fontsize=8)

        # (3) 箱线图（左下）
        ax3 = axes[1, 0]
        data_list = [self.df[col].dropna().values for col in columns
                     if col in self.df.columns]
        bp = ax3.boxplot(data_list, labels=columns, patch_artist=True)
        for patch, color in zip(bp["boxes"], self.COLOR_PALETTE):
            patch.set_facecolor(color)
            patch.set_alpha(0.6)
        ax3.set_title("箱线图")
        ax3.grid(True, alpha=0.3, linestyle="--")
        ax3.tick_params(axis="x", rotation=45, labelsize=7)

        # (4) 相关性热力图（右下）
        ax4 = axes[1, 1]
        if len(columns) >= 2:
            valid_cols = [c for c in columns if c in self.df.columns]
            corr = self.df[valid_cols].corr()
            im = ax4.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1,
                            aspect="auto")
            for i in range(len(valid_cols)):
                for j in range(len(valid_cols)):
                    ax4.text(j, i, f"{corr.values[i, j]:.2f}",
                             ha="center", va="center", fontsize=9)
            ax4.set_xticks(range(len(valid_cols)))
            ax4.set_yticks(range(len(valid_cols)))
            ax4.set_xticklabels(valid_cols, rotation=45, fontsize=8)
            ax4.set_yticklabels(valid_cols, fontsize=8)
            ax4.set_title("相关性热力图")
            fig.colorbar(im, ax=ax4, shrink=0.7)

        fig.suptitle("仪表盘", fontsize=13, y=0.97)
        fig.tight_layout(pad=2.0, h_pad=3.0, w_pad=2.5)
        if save_path:
            fig.savefig(save_path, dpi=self.dpi, bbox_inches="tight")
        return fig

    # ──────────────────────────────────────────
    # 批量导出
    # ──────────────────────────────────────────

    def export_all_charts(self, output_dir: str,
                          columns: Optional[list] = None,
                          prefix: str = "") -> list:
        """
        一键导出所有图表

        参数:
            output_dir: 输出目录
            columns: 要分析的传感器列
            prefix: 文件名前缀

        返回:
            已生成的文件路径列表
        """
        os.makedirs(output_dir, exist_ok=True)
        generated_files = []

        if columns is None:
            columns = self.df.select_dtypes(
                include=[np.number]
            ).columns.tolist()
        elif isinstance(columns, str):
            columns = [columns]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 时间序列图
        ts_path = os.path.join(
            output_dir, f"{prefix}timeseries_{timestamp}.png"
        )
        self.plot_time_series(
            columns, title="传感器时间序列",
            save_path=ts_path
        )
        generated_files.append(ts_path)

        # 相关性热力图
        if len(columns) >= 2:
            hm_path = os.path.join(
                output_dir, f"{prefix}heatmap_{timestamp}.png"
            )
            self.plot_heatmap(columns, save_path=hm_path)
            generated_files.append(hm_path)

        # 箱线图
        bx_path = os.path.join(
            output_dir, f"{prefix}boxplot_{timestamp}.png"
        )
        self.plot_boxplot(columns, save_path=bx_path)
        generated_files.append(bx_path)

        # 直方图（最多 4 列一图）
        for i in range(0, len(columns), 4):
            batch = columns[i:i + 4]
            hist_path = os.path.join(
                output_dir, f"{prefix}histogram_{i}_{timestamp}.png"
            )
            self.plot_histogram(batch, save_path=hist_path)
            generated_files.append(hist_path)

        # 仪表盘
        dash_path = os.path.join(
            output_dir, f"{prefix}dashboard_{timestamp}.png"
        )
        self.plot_dashboard(columns, save_path=dash_path)
        generated_files.append(dash_path)

        return generated_files
