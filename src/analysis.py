"""
统计分析模块 — 传感器数据的统计分析与相关性分析

功能:
  1. 基本统计描述
  2. 多传感器相关性分析（Pearson / Spearman）
  3. 趋势分析（线性回归斜率、季节性分解）
  4. 数据分布检验（正态性检验）
"""

from typing import Optional, Literal

import pandas as pd
import numpy as np
from scipy import stats as scipy_stats


class SensorAnalyzer:
    """传感器数据分析器"""

    def __init__(self, df: Optional[pd.DataFrame] = None):
        self.df = df

    def set_data(self, df: pd.DataFrame):
        self.df = df.copy()

    # ──────────────────────────────────────────
    # 相关性分析
    # ──────────────────────────────────────────

    def correlation_analysis(self, columns: Optional[list] = None,
                             method: Literal["pearson", "spearman",
                                             "kendall"] = "pearson") -> dict:
        """
        多传感器相关性分析

        参数:
            columns: 要分析的传感器列
            method: 相关系数方法
                - "pearson": 皮尔逊（线性相关）
                - "spearman": 斯皮尔曼（单调相关）
                - "kendall": 肯德尔（有序分类）

        返回:
            {
                "correlation_matrix": DataFrame,
                "highly_correlated": [(列1, 列2, 系数), ...],
                "method": method
            }
        """
        if self.df is None or self.df.empty:
            raise ValueError("无数据可分析")

        if columns is None:
            columns = self.df.select_dtypes(include=[np.number]).columns.tolist()
        elif isinstance(columns, str):
            columns = [columns]

        # 确保列都存在
        valid_cols = [c for c in columns if c in self.df.columns]
        if len(valid_cols) < 2:
            raise ValueError("需要至少两个有效数值列")

        corr_matrix = self.df[valid_cols].corr(method=method)

        # 提取高相关对（|r| > 0.7，且排除自相关）
        high_corr = []
        threshold = 0.7
        cols_list = corr_matrix.columns
        for i in range(len(cols_list)):
            for j in range(i + 1, len(cols_list)):
                val = corr_matrix.iloc[i, j]
                if abs(val) >= threshold:
                    high_corr.append((cols_list[i], cols_list[j],
                                      round(val, 4)))

        high_corr.sort(key=lambda x: abs(x[2]), reverse=True)

        return {
            "correlation_matrix": corr_matrix,
            "highly_correlated": high_corr,
            "method": method,
        }

    def find_lagged_correlation(self, col_a: str, col_b: str,
                                max_lag: int = 20) -> dict:
        """
        查找两个传感器序列的滞后的相关性（互相关分析）

        用于发现"传感器A变化后多久，传感器B跟着变化"

        参数:
            col_a: 参考传感器列
            col_b: 目标传感器列
            max_lag: 最大滞后步数

        返回:
            {"lags": [...], "correlations": [...], "best_lag": int, "best_corr": float}
        """
        if self.df is None or self.df.empty:
            raise ValueError("无数据可分析")

        a = self.df[col_a].dropna().values
        b = self.df[col_b].dropna().values

        min_len = min(len(a), len(b))
        a, b = a[:min_len], b[:min_len]

        correlations = []
        for lag in range(-max_lag, max_lag + 1):
            if lag < 0:
                corr = np.corrcoef(a[:-lag], b[-lag:])[0, 1]
            elif lag == 0:
                corr = np.corrcoef(a, b)[0, 1]
            else:
                corr = np.corrcoef(a[lag:], b[:-lag])[0, 1]
            correlations.append(corr if not np.isnan(corr) else 0)

        lags = list(range(-max_lag, max_lag + 1))
        best_idx = np.argmax(np.abs(correlations))
        best_lag = lags[best_idx]
        best_corr = correlations[best_idx]

        return {
            "lags": lags,
            "correlations": correlations,
            "best_lag": best_lag,
            "best_corr": round(best_corr, 4),
        }

    # ──────────────────────────────────────────
    # 趋势分析
    # ──────────────────────────────────────────

    def trend_analysis(self, column: str) -> dict:
        """
        传感器趋势分析（线性回归）

        参数:
            column: 分析的传感器列

        返回:
            {"slope": 斜率, "intercept": 截距, "r_value": 相关系数,
             "p_value": P值, "trend": "上升"/"下降"/"平稳"}
        """
        if self.df is None or self.df.empty:
            raise ValueError("无数据可分析")

        series = self.df[column].dropna().values
        x = np.arange(len(series))

        slope, intercept, r_value, p_value, std_err = scipy_stats.linregress(x, series)

        # 判断趋势
        if p_value < 0.05:
            if slope > 0:
                trend = "上升"
            elif slope < 0:
                trend = "下降"
            else:
                trend = "平稳"
        else:
            trend = "无明显趋势（p > 0.05）"

        return {
            "slope": round(slope, 6),
            "intercept": round(intercept, 4),
            "r_value": round(r_value, 4),
            "r_squared": round(r_value ** 2, 4),
            "p_value": round(p_value, 6),
            "std_err": round(std_err, 6),
            "trend": trend,
        }

    def sensor_comparison(self, columns: Optional[list] = None) -> pd.DataFrame:
        """
        多传感器横向对比统计

        返回含均值、波动性、稳定性等指标的对比表
        """
        if columns is None:
            columns = self.df.select_dtypes(include=[np.number]).columns.tolist()
        elif isinstance(columns, str):
            columns = [columns]

        stats_data = []
        for col in columns:
            if col not in self.df.columns:
                continue
            series = self.df[col].dropna().values
            if len(series) == 0:
                continue

            cv = np.std(series) / np.mean(series) if np.mean(series) != 0 else 0
            stats_data.append({
                "传感器": col,
                "均值": round(np.mean(series), 4),
                "标准差": round(np.std(series), 4),
                "变异系数": round(cv, 4),
                "最小值": round(np.min(series), 4),
                "最大值": round(np.max(series), 4),
                "极差": round(np.max(series) - np.min(series), 4),
                "稳定度": "高" if cv < 0.1 else ("中" if cv < 0.3 else "低"),
            })

        return pd.DataFrame(stats_data)

    # ──────────────────────────────────────────
    # 分布分析
    # ──────────────────────────────────────────

    def distribution_analysis(self, column: str) -> dict:
        """
        传感器数据分布分析

        参数:
            column: 传感器列名

        返回:
            {"normality": 正态性检验结果, "skewness": 偏度,
             "kurtosis": 峰度, "quantiles": 分位数}
        """
        if self.df is None or self.df.empty:
            raise ValueError("无数据可分析")

        series = self.df[column].dropna().values
        if len(series) < 3:
            raise ValueError(f"数据点太少 ({len(series)})，无法分析")

        # Shapiro-Wilk 正态性检验（适用于 < 5000 样本）
        if len(series) < 5000:
            stat, p_value = scipy_stats.shapiro(series)
            normality_test = "shapiro"
        else:
            stat, p_value = scipy_stats.normaltest(series)
            normality_test = "dagostino"

        is_normal = p_value > 0.05

        # 偏度与峰度
        skewness = scipy_stats.skew(series)
        kurtosis = scipy_stats.kurtosis(series)  # 超额峰度

        # 分位数
        quantiles = {
            "1%": round(np.percentile(series, 1), 4),
            "5%": round(np.percentile(series, 5), 4),
            "25%": round(np.percentile(series, 25), 4),
            "50%": round(np.percentile(series, 50), 4),
            "75%": round(np.percentile(series, 75), 4),
            "95%": round(np.percentile(series, 95), 4),
            "99%": round(np.percentile(series, 99), 4),
        }

        # 判断分布形状
        if abs(skewness) < 0.5:
            skew_desc = "近似对称"
        elif skewness > 0:
            skew_desc = "右偏（正偏）"
        else:
            skew_desc = "左偏（负偏）"

        if kurtosis > 0:
            kurt_desc = "尖峰（厚尾）"
        elif kurtosis < 0:
            kurt_desc = "平峰（薄尾）"
        else:
            kurt_desc = "适中"

        return {
            "test_method": normality_test,
            "statistic": round(stat, 4),
            "p_value": round(p_value, 6),
            "is_normal": bool(is_normal),
            "skewness": round(skewness, 4),
            "skewness_description": skew_desc,
            "kurtosis": round(kurtosis, 4),
            "kurtosis_description": kurt_desc,
            "quantiles": quantiles,
        }


class DataExporter:
    """数据导出工具，将分析结果导出为结构化数据"""

    @staticmethod
    def to_excel(df: pd.DataFrame, file_path: str,
                 sheet_name: str = "Sheet1",
                 include_stats: bool = True) -> str:
        """
        导出 DataFrame 到 Excel 文件

        参数:
            df: 要导出的数据
            file_path: 输出路径（需含 .xlsx 后缀）
            sheet_name: 工作表名称
            include_stats: 是否在第二个 sheet 加入统计摘要

        返回:
            输出文件路径
        """
        if not file_path.endswith(".xlsx"):
            file_path += ".xlsx"

        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)

            if include_stats:
                stats_df = SensorAnalyzer(df).sensor_comparison()
                if not stats_df.empty:
                    stats_df.to_excel(writer, sheet_name="统计摘要", index=False)

        return file_path

    @staticmethod
    def correlation_to_csv(corr_result: dict, file_path: str) -> str:
        """导出相关性矩阵到 CSV"""
        corr_matrix = corr_result["correlation_matrix"]
        corr_matrix.to_csv(file_path)
        return file_path
