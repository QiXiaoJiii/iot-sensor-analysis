#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
物联网多源传感器数据分析系统 V1.0

功能:
  1. 多源数据接入（CSV / 串口 / MQTT）
  2. 数据清洗与异常检测（3σ / IQR）
  3. 数据平滑与标准化
  4. 统计分析与相关性分析
  5. 可视化（6 种图表 + 综合仪表盘）
  6. 报告导出（Excel / 文本）

运行方式:
  python main.py              # 启动图形界面
  python main.py --gui        # 启动图形界面
  python main.py --cli data.csv  # 命令行批处理模式

依赖:
  pip install -r requirements.txt
"""

import sys
import os
import argparse

# 确保能找到 src 包
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def print_banner():
    """打印启动横幅"""
    banner = """
  ╔══════════════════════════════════════════════╗
  ║    物联网多源传感器数据分析系统 V1.0         ║
  ║    IoT Multi-Source Sensor Data Analyzer     ║
  ╚══════════════════════════════════════════════╝
    """
    print(banner)


def run_gui():
    """启动图形界面模式"""
    import matplotlib
    matplotlib.use("TkAgg")  # 交互式后端，支持内嵌图表显示
    from src.gui import SensorAnalysisGUI
    app = SensorAnalysisGUI()
    app.run()


def run_cli(csv_path: str):
    """
    命令行批处理模式

    自动执行: 导入 → 清洗 → 分析 → 可视化 → 导出报告
    """
    from src.data_ingestion import SensorDataIngestion, DataSourceConfig
    from src.data_processing import DataProcessor, OutlierDetectionReport
    from src.analysis import SensorAnalyzer
    from src.visualization import SensorVisualizer
    from src.report_export import ReportGenerator

    print_banner()
    print(f"[CLI] 分析文件: {csv_path}")
    print()

    # 1. 导入
    print(">> [1/5] 导入数据...")
    config = DataSourceConfig("csv")
    config.file_path = csv_path
    ingestion = SensorDataIngestion()
    df = ingestion.from_csv(config)
    print(f"    已导入 {len(df)} 行 x {len(df.columns)} 列")

    # 2. 处理
    print(">> [2/5] 数据处理...")
    processor = DataProcessor(df)
    processor.fill_missing(method="linear")
    outliers = processor.detect_outliers_3sigma()
    print(OutlierDetectionReport.generate_report(outliers))

    # 3. 分析
    print(">> [3/5] 统计分析...")
    analyzer = SensorAnalyzer(processor.df)
    summary = ingestion.get_data_summary()
    print(f"    行数: {summary['行数']}")
    print(f"    缺失值: {summary['缺失值总数']}")

    # 4. 可视化
    print(">> [4/5] 生成图表...")
    visualizer = SensorVisualizer(processor.df, config.timestamp_column)
    os.makedirs("output", exist_ok=True)
    chart_files = visualizer.export_all_charts("output")
    print(f"    已生成 {len(chart_files)} 张图表")

    # 5. 报告
    print(">> [5/5] 导出报告...")
    analysis_results = {
        "outliers": outliers,
    }
    try:
        analysis_results["correlation"] = analyzer.correlation_analysis()
    except Exception:
        pass

    reporter = ReportGenerator()
    report_path = reporter.to_text_report(
        processor.df, analysis_results, file_path="output/analysis_report.txt"
    )
    print(f"    报告已保存: {report_path}")
    print()
    print("[CLI] 分析完成!")


def main():
    parser = argparse.ArgumentParser(
        description="物联网多源传感器数据分析系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py                    # 启动图形界面
  python main.py --cli data.csv     # 批处理分析 CSV
  python main.py --about            # 显示版本信息
        """
    )
    parser.add_argument("--cli", metavar="CSV_FILE",
                        help="命令行批处理模式，指定 CSV 文件路径")
    parser.add_argument("--gui", action="store_true",
                        help="启动图形界面模式（默认）")
    parser.add_argument("--about", action="store_true",
                        help="显示版本信息")
    parser.add_argument("--version", action="store_true",
                        help="显示版本号")

    args = parser.parse_args()

    if args.about or args.version:
        print_banner()
        print("版本: 1.1.0")
        print("Python 环境:", sys.version)
        sys.exit(0)

    if args.cli:
        if not os.path.exists(args.cli):
            print(f"错误: 文件不存在: {args.cli}")
            sys.exit(1)
        run_cli(args.cli)
    else:
        run_gui()


if __name__ == "__main__":
    main()
