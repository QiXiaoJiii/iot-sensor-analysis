"""
数据处理模块 — 传感器数据清洗、异常检测、平滑滤波

功能:
  1. 缺失值处理（前向填充、线性插值、均值填充）
  2. 异常值检测（3σ 准则、IQR 四分位距法）
  3. 数据平滑（移动平均、Savitzky-Golay 滤波）
  4. 数据重采样（降采样/升采样）
  5. 数据标准化与归一化
"""

from typing import Union, Optional, Literal

import pandas as pd
import numpy as np
from scipy import signal, stats


class DataProcessor:
    """传感器数据处理器，提供完整的清洗与分析管线"""

    def __init__(self, df: Optional[pd.DataFrame] = None):
        """
        参数:
            df: 待处理的 DataFrame
        """
        self.df = df
        self.processing_log: list = []

    def set_data(self, df: pd.DataFrame):
        """设置/更新待处理的数据"""
        self.df = df.copy()
        self.processing_log = []

    # ──────────────────────────────────────────
    # 缺失值处理
    # ──────────────────────────────────────────

    def fill_missing(self, columns: Optional[list] = None,
                     method: Literal["ffill", "bfill", "linear",
                                     "mean", "median", "zero"] = "linear",
                     **kwargs) -> pd.DataFrame:
        """
        填充缺失值

        参数:
            columns: 要处理的列名列表，为 None 则处理所有数值列
            method: 填充方法
                - "ffill":   前向填充（用上一个有效值填充）
                - "bfill":   后向填充（用下一个有效值填充）
                - "linear":  线性插值（默认）
                - "mean":    列均值填充
                - "median":  列中位数填充
                - "zero":    填充为 0
            kwargs: 传递给插值函数的额外参数

        返回:
            填充后的 DataFrame
        """
        if self.df is None or self.df.empty:
            raise ValueError("无数据可处理")

        df = self.df.copy()

        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()
        elif isinstance(columns, str):
            columns = [columns]

        missing_before = df[columns].isnull().sum().sum()

        for col in columns:
            if col not in df.columns:
                continue
            if method == "ffill":
                df[col] = df[col].ffill()
            elif method == "bfill":
                df[col] = df[col].bfill()
            elif method == "linear":
                df[col] = df[col].interpolate(method="linear", **kwargs)
            elif method == "mean":
                df[col] = df[col].fillna(df[col].mean())
            elif method == "median":
                df[col] = df[col].fillna(df[col].median())
            elif method == "zero":
                df[col] = df[col].fillna(0)
            else:
                raise ValueError(f"不支持的填充方法: {method}")

        # 仍有剩余缺失值用前向填充兜底
        df[columns] = df[columns].ffill().bfill()

        missing_after = df[columns].isnull().sum().sum()
        filled = missing_before - missing_after

        self.processing_log.append({
            "操作": "缺失值填充",
            "方法": method,
            "列": columns,
            "填充前缺失数": int(missing_before),
            "填充后缺失数": int(missing_after),
            "已填充数": int(filled),
        })

        self.df = df
        return df

    # ──────────────────────────────────────────
    # 异常值检测
    # ──────────────────────────────────────────

    def detect_outliers_iqr(self, columns: Optional[list] = None,
                            multiplier: float = 1.5) -> dict:
        """
        基于 IQR 四分位距法检测异常值

        公式: 异常值 < Q1 - k*IQR 或 > Q3 + k*IQR
        其中 k 默认为 1.5（中度异常），3.0 为极端异常

        参数:
            columns: 要检测的列
            multiplier: IQR 倍数（默认 1.5）

        返回:
            {列名: {"异常索引": [...], "异常值": [...], "上下界": (lo, hi)}}
        """
        if self.df is None or self.df.empty:
            raise ValueError("无数据可检测")

        if columns is None:
            columns = self.df.select_dtypes(include=[np.number]).columns.tolist()
        elif isinstance(columns, str):
            columns = [columns]

        results = {}
        for col in columns:
            if col not in self.df.columns:
                continue
            series = self.df[col].dropna()
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - multiplier * iqr
            upper_bound = q3 + multiplier * iqr

            outlier_mask = (self.df[col] < lower_bound) | (self.df[col] > upper_bound)
            outlier_indices = self.df.index[outlier_mask].tolist()
            outlier_values = self.df.loc[outlier_mask, col].tolist()

            results[col] = {
                "异常索引": outlier_indices,
                "异常值": outlier_values,
                "异常个数": len(outlier_indices),
                "异常占比": round(len(outlier_indices) / max(len(series), 1) * 100, 2),
                "下界": round(lower_bound, 4),
                "上界": round(upper_bound, 4),
                "Q1": round(q1, 4),
                "Q3": round(q3, 4),
                "IQR": round(iqr, 4),
            }

        return results

    def detect_outliers_3sigma(self, columns: Optional[list] = None) -> dict:
        """
        基于 3σ 准则（拉依达准则）检测异常值

        公式: |x - μ| > 3σ 视为异常
        适用于近似正态分布的数据

        参数:
            columns: 要检测的列

        返回:
            {列名: {"异常索引": [...], "异常值": [...], "统计信息": {...}}}
        """
        if self.df is None or self.df.empty:
            raise ValueError("无数据可检测")

        if columns is None:
            columns = self.df.select_dtypes(include=[np.number]).columns.tolist()
        elif isinstance(columns, str):
            columns = [columns]

        results = {}
        for col in columns:
            if col not in self.df.columns:
                continue
            series = self.df[col].dropna()
            mean = series.mean()
            std = series.std()

            if std == 0:
                results[col] = {"异常个数": 0, "说明": "标准差为0，所有值相同"}
                continue

            lower_bound = mean - 3 * std
            upper_bound = mean + 3 * std

            outlier_mask = (self.df[col] < lower_bound) | (self.df[col] > upper_bound)
            outlier_indices = self.df.index[outlier_mask].tolist()
            outlier_values = self.df.loc[outlier_mask, col].tolist()

            results[col] = {
                "异常索引": outlier_indices,
                "异常值": outlier_values,
                "异常个数": len(outlier_indices),
                "异常占比": round(len(outlier_indices) / max(len(series), 1) * 100, 2),
                "均值": round(mean, 4),
                "标准差": round(std, 4),
                "下界": round(lower_bound, 4),
                "上界": round(upper_bound, 4),
                "方法": "3σ",
            }

        return results

    def remove_outliers(self, columns: Optional[list] = None,
                        method: Literal["iqr", "3sigma"] = "iqr",
                        inplace: bool = False,
                        **kwargs) -> pd.DataFrame:
        """
        删除异常值（替换为 NaN）

        参数:
            columns: 要处理的列
            method: 检测方法 "iqr" 或 "3sigma"
            inplace: 是否就地修改
            kwargs: 传递给检测方法的额外参数

        返回:
            处理后的 DataFrame
        """
        if columns is None:
            columns = self.df.select_dtypes(include=[np.number]).columns.tolist()
        elif isinstance(columns, str):
            columns = [columns]

        if method == "iqr":
            results = self.detect_outliers_iqr(columns, **kwargs)
        elif method == "3sigma":
            results = self.detect_outliers_3sigma(columns)
        else:
            raise ValueError(f"不支持的方法: {method}")

        df_target = self.df if inplace else self.df.copy()

        total_removed = 0
        for col, info in results.items():
            if "异常索引" in info and info["异常索引"]:
                df_target.loc[info["异常索引"], col] = np.nan
                total_removed += len(info["异常索引"])

        self.processing_log.append({
            "操作": "异常值删除",
            "方法": method,
            "列": columns,
            "已删除数": total_removed,
        })

        if not inplace:
            self.df = df_target
        return df_target

    # ──────────────────────────────────────────
    # 数据平滑
    # ──────────────────────────────────────────

    def smooth_moving_average(self, columns: Optional[list] = None,
                              window: int = 5, center: bool = True,
                              min_periods: Optional[int] = None) -> pd.DataFrame:
        """
        移动平均平滑

        参数:
            columns: 要平滑的列
            window: 滑动窗口大小（奇数效果较好）
            center: 是否居中对齐

        返回:
            平滑后的 DataFrame（新列以 _sma 后缀标识）
        """
        if self.df is None or self.df.empty:
            raise ValueError("无数据可处理")

        if columns is None:
            columns = self.df.select_dtypes(include=[np.number]).columns.tolist()
        elif isinstance(columns, str):
            columns = [columns]

        df = self.df.copy()
        for col in columns:
            if col not in df.columns:
                continue
            new_col = f"{col}_sma"
            df[new_col] = df[col].rolling(
                window=window, center=center,
                min_periods=min_periods or max(1, window // 2)
            ).mean()

        self.processing_log.append({
            "操作": "移动平均平滑",
            "窗口": window,
            "列": columns,
        })

        self.df = df
        return df

    def smooth_savitzky_golay(self, columns: Optional[list] = None,
                              window_length: int = 11,
                              polyorder: int = 3) -> pd.DataFrame:
        """
        Savitzky-Golay 滤波器平滑
        在保持数据趋势的同时去除噪声

        参数:
            columns: 要平滑的列
            window_length: 窗口长度（必须是奇数，且 > polyorder）
            polyorder: 多项式阶数

        返回:
            平滑后的 DataFrame（新列以 _sg 后缀标识）
        """
        if self.df is None or self.df.empty:
            raise ValueError("无数据可处理")

        if columns is None:
            columns = self.df.select_dtypes(include=[np.number]).columns.tolist()
        elif isinstance(columns, str):
            columns = [columns]

        if window_length % 2 == 0:
            window_length += 1  # 确保奇数
        if window_length <= polyorder:
            raise ValueError("窗口长度必须大于多项式阶数")

        df = self.df.copy()
        for col in columns:
            if col not in df.columns:
                continue
            series = df[col].dropna().values
            if len(series) < window_length:
                continue
            try:
                smoothed = signal.savgol_filter(
                    series, window_length=window_length, polyorder=polyorder
                )
                new_col = f"{col}_sg"
                # 只替换非 NaN 位置
                df.loc[df[col].notna(), new_col] = smoothed
            except ValueError as e:
                print(f"平滑失败 ({col}): {e}")

        self.processing_log.append({
            "操作": "Savitzky-Golay 平滑",
            "窗口长度": window_length,
            "多项式阶数": polyorder,
            "列": columns,
        })

        self.df = df
        return df

    # ──────────────────────────────────────────
    # 重采样
    # ──────────────────────────────────────────

    def resample(self, rule: str,
                 columns: Optional[list] = None,
                 agg_func: Literal["mean", "median", "min", "max",
                                   "sum", "std"] = "mean") -> pd.DataFrame:
        """
        时间序列重采样

        参数:
            rule: 采样规则，如 "1min"、"1H"、"1D"、"1W"
            columns: 要重采样的列，为 None 则处理所有数值列
            agg_func: 聚合函数

        返回:
            重采样后的 DataFrame
        """
        if self.df is None or self.df.empty:
            raise ValueError("无数据可处理")

        # 确保有时间戳列
        timestamp_cols = [c for c in self.df.columns
                          if pd.api.types.is_datetime64_any_dtype(self.df[c])]
        if not timestamp_cols:
            raise ValueError("缺少时间戳列，无法重采样")

        ts_col = timestamp_cols[0]
        df = self.df.set_index(ts_col)

        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()
        elif isinstance(columns, str):
            columns = [columns]

        agg_map = {
            "mean": "mean", "median": "median", "min": "min",
            "max": "max", "sum": "sum", "std": "std",
        }
        if agg_func not in agg_map:
            raise ValueError(f"不支持的聚合函数: {agg_func}")

        resampled = df[columns].resample(rule).agg(agg_func)
        resampled.reset_index(inplace=True)

        self.processing_log.append({
            "操作": "重采样",
            "规则": rule,
            "聚合函数": agg_func,
            "原行数": len(self.df),
            "新行数": len(resampled),
        })

        self.df = resampled
        return resampled

    # ──────────────────────────────────────────
    # 标准化与归一化
    # ──────────────────────────────────────────

    def standardize(self, columns: Optional[list] = None) -> pd.DataFrame:
        """
        Z-Score 标准化: x' = (x - μ) / σ
        使数据均值为 0，标准差为 1

        参数:
            columns: 要标准化的列

        返回:
            标准化后的 DataFrame（新列以 _z 后缀标识）
        """
        if columns is None:
            columns = self.df.select_dtypes(include=[np.number]).columns.tolist()
        elif isinstance(columns, str):
            columns = [columns]

        df = self.df.copy()
        for col in columns:
            if col not in df.columns:
                continue
            mean = df[col].mean()
            std = df[col].std()
            if std == 0:
                continue
            df[f"{col}_z"] = (df[col] - mean) / std

        self.df = df
        return df

    def normalize(self, columns: Optional[list] = None,
                  feature_range: tuple = (0, 1)) -> pd.DataFrame:
        """
        最大-最小归一化: x' = (x - min) / (max - min) * (range_max - range_min) + range_min

        参数:
            columns: 要归一化的列
            feature_range: 目标范围，默认 (0, 1)

        返回:
            归一化后的 DataFrame（新列以 _norm 后缀标识）
        """
        if columns is None:
            columns = self.df.select_dtypes(include=[np.number]).columns.tolist()
        elif isinstance(columns, str):
            columns = [columns]

        r_min, r_max = feature_range
        df = self.df.copy()
        for col in columns:
            if col not in df.columns:
                continue
            col_min = df[col].min()
            col_max = df[col].max()
            if col_max == col_min:
                continue
            normalized = (df[col] - col_min) / (col_max - col_min)
            normalized = normalized * (r_max - r_min) + r_min
            df[f"{col}_norm"] = normalized

        self.df = df
        return df

    # ──────────────────────────────────────────
    # 流程编排
    # ──────────────────────────────────────────

    def run_pipeline(self, steps: list) -> pd.DataFrame:
        """
        按步骤依次执行数据处理管线

        参数:
            steps: 处理步骤列表，每个元素为 (方法名, 参数字典)
            示例:
                [
                    ("fill_missing", {"method": "linear"}),
                    ("detect_outliers_3sigma", {}),
                    ("remove_outliers", {"method": "3sigma"}),
                    ("smooth_moving_average", {"window": 5}),
                ]

        返回:
            处理后的 DataFrame
        """
        available = {
            "fill_missing": self.fill_missing,
            "remove_outliers": self.remove_outliers,
            "smooth_moving_average": self.smooth_moving_average,
            "smooth_savitzky_golay": self.smooth_savitzky_golay,
            "resample": self.resample,
            "standardize": self.standardize,
            "normalize": self.normalize,
        }

        for step_name, step_kwargs in steps:
            if step_name not in available:
                print(f"跳过未知步骤: {step_name}")
                continue
            print(f"[处理管线] 执行: {step_name} ...")
            available[step_name](**step_kwargs)
            print(f"[处理管线] 完成: {step_name}")

        return self.df

    def get_log(self) -> list:
        """获取处理日志"""
        return self.processing_log

    def get_summary_stats(self, columns: Optional[list] = None) -> pd.DataFrame:
        """获取数值列的完整统计描述"""
        if columns is None:
            columns = self.df.select_dtypes(include=[np.number]).columns.tolist()
        elif isinstance(columns, str):
            columns = [columns]

        stats_list = []
        for col in columns:
            if col not in self.df.columns:
                continue
            series = self.df[col].dropna()
            s = {
                "列名": col,
                "样本数": len(series),
                "缺失数": int(self.df[col].isnull().sum()),
                "均值": round(series.mean(), 4),
                "标准差": round(series.std(), 4),
                "最小值": round(series.min(), 4),
                "25%分位": round(series.quantile(0.25), 4),
                "中位数": round(series.median(), 4),
                "75%分位": round(series.quantile(0.75), 4),
                "最大值": round(series.max(), 4),
                "偏度": round(series.skew(), 4),
                "峰度": round(series.kurtosis(), 4),
            }
            stats_list.append(s)

        return pd.DataFrame(stats_list)


class OutlierDetectionReport:
    """异常检测报告生成器"""

    @staticmethod
    def generate_report(results: dict) -> str:
        """
        将异常检测结果格式化为可读报告

        参数:
            results: detect_outliers_iqr 或 detect_outliers_3sigma 的返回结果

        返回:
            格式化的文本报告
        """
        lines = ["=" * 60, "异常检测报告", "=" * 60, ""]

        total_outliers = 0
        for col, info in results.items():
            if "异常个数" not in info:
                continue
            n = info["异常个数"]
            total_outliers += n
            lines.append(f"【{col}】")
            lines.append(f"  异常值数量: {n}")
            lines.append(f"  异常占比: {info.get('异常占比', 'N/A')}%")
            if "下界" in info and "上界" in info:
                lines.append(f"  正常范围: ({info['下界']}, {info['上界']})")
            if "均值" in info:
                lines.append(f"  均值: {info['均值']}, 标准差: {info['标准差']}")
            if "异常值" in info and info["异常值"]:
                # 只显示前10个异常值
                vals = info["异常值"][:10]
                lines.append(f"  异常值样例: {vals}")
                if len(info["异常值"]) > 10:
                    lines.append(f"  ... 还有 {len(info['异常值']) - 10} 个")
            lines.append("")

        lines.append(f"总计发现 {total_outliers} 个异常值")
        lines.append("=" * 60)
        return "\n".join(lines)
