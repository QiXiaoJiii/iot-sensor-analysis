"""
图形界面模块 — Tkinter 主窗口（增强版）

功能:
  1. 主窗口布局（菜单栏、工具栏、标签页切换）
  2. 数据导入与预览（CSV 文件选择）
  3. 数据处理参数配置
  4. 图表内嵌展示（matplotlib FigureCanvasTkAgg）
  5. 交互式图表设置（选类型 → 选列 → 生成 → 显示）
  6. 分析结果展示
  7. 报告导出入口
  8. 进度条与状态反馈
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from typing import Optional
from datetime import datetime

import ttkbootstrap as tb
from tkinter import ttk  # ttkbootstrap 会自动增强 ttk

import pandas as pd

from .data_ingestion import SensorDataIngestion, DataSourceConfig
from .data_processing import DataProcessor, OutlierDetectionReport
from .analysis import SensorAnalyzer
from .visualization import SensorVisualizer
from .report_export import ReportGenerator

# Matplotlib 内嵌支持
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure


class SensorAnalysisGUI:
    """传感器数据分析系统主窗口"""

    APP_TITLE = "物联网多源传感器数据分析系统 V1.1"
    WINDOW_SIZE = "1600x950"
    OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Documents", "IoT_Sensor_Output")

    # 图表类型选项
    CHART_TYPES = [
        "时间序列图", "散点图", "相关性热力图",
        "分布直方图", "箱线图", "综合仪表盘",
    ]

    def __init__(self):
        self.root = tb.Window(themename="cosmo")
        self.root.title(self.APP_TITLE)
        self.root.geometry(self.WINDOW_SIZE)
        self.root.minsize(1200, 800)

        self._setup_style()
        self._setup_states()
        self._setup_components()
        self._build_menu_bar()
        self._build_toolbar()
        self._build_main_area()
        self._build_status_bar()

    def _setup_states(self):
        """数据状态"""
        self.current_df: pd.DataFrame = None
        self.timestamp_col: str = None
        self.data_source: str = None
        self.current_figure: Optional[Figure] = None
        self._canvas_widget: Optional[FigureCanvasTkAgg] = None

    def _setup_components(self):
        """核心组件"""
        self.ingestion = SensorDataIngestion()
        self.processor = DataProcessor()
        self.analyzer = SensorAnalyzer()
        self.visualizer = SensorVisualizer()
        self.reporter = ReportGenerator()

    # ──────────────────────────────────────────
    # 样式设置
    # ──────────────────────────────────────────

    def _setup_style(self):
        """全局样式"""
        style = tb.Style()
        style.configure(".", font=("微软雅黑", 9))
        style.configure("TButton", font=("微软雅黑", 9), padding=(12, 6))
        style.configure("TNotebook.Tab", font=("微软雅黑", 10),
                        padding=(18, 8))
        style.configure("TLabelframe.Label", font=("微软雅黑", 10, "bold"))
        style.configure("Status.TLabel", font=("微软雅黑", 9))

    # ──────────────────────────────────────────
    # 界面构建
    # ──────────────────────────────────────────

    def _build_menu_bar(self):
        """构建菜单栏（精简版：每个功能只保留一个入口）"""
        menubar = tk.Menu(self.root)

        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="导入 CSV 文件...", command=self._on_import_csv,
                              accelerator="Ctrl+O")
        file_menu.add_command(label="导入示例数据", command=self._on_load_sample)
        file_menu.add_separator()
        file_menu.add_command(label="导出数据到 Excel...", command=self._on_export_excel)
        file_menu.add_command(label="导出分析报告...", command=self._on_export_report)
        file_menu.add_command(label="批量导出图表...", command=self._on_export_charts)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit, accelerator="Ctrl+Q")
        menubar.add_cascade(label="文件", menu=file_menu)

        # 处理菜单
        process_menu = tk.Menu(menubar, tearoff=0)
        process_menu.add_command(label="缺失值填充...", command=self._on_fill_missing)
        process_menu.add_command(label="异常值检测...", command=self._on_detect_outliers)
        process_menu.add_command(label="数据平滑...", command=self._on_smooth_data)
        process_menu.add_command(label="标准化/归一化...", command=self._on_normalize)
        process_menu.add_separator()
        process_menu.add_command(label="运行默认处理管线", command=self._on_run_pipeline)
        menubar.add_cascade(label="处理", menu=process_menu)

        # 分析菜单（唯一入口）
        analyze_menu = tk.Menu(menubar, tearoff=0)
        analyze_menu.add_command(label="统计摘要", command=self._on_show_stats)
        analyze_menu.add_command(label="相关性分析", command=self._on_correlation)
        analyze_menu.add_command(label="趋势分析", command=self._on_trend_analysis)
        analyze_menu.add_command(label="分布检验", command=self._on_distribution_test)
        menubar.add_cascade(label="分析", menu=analyze_menu)

        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="关于", command=self._on_about)
        menubar.add_cascade(label="帮助", menu=help_menu)

        self.root.config(menu=menubar)

        # 快捷键
        self.root.bind("<Control-o>", lambda e: self._on_import_csv())
        self.root.bind("<Control-q>", lambda e: self.root.quit())

    def _build_toolbar(self):
        """工具栏 — B骨架(灰蓝主色) + C点缀(暖色高亮)"""
        toolbar = ttk.Frame(self.root, padding=(12, 8))
        btn_data = [
            ("📂  导入CSV",  self._on_import_csv,     "primary"),   # cosmo深蓝
            ("📋  仪表盘",   lambda: self._on_quick_plot("综合仪表盘"), "warning"),  # 琥珀暖色
            ("💾  导出报告", self._on_export_report,   "success"),   # 绿色
        ]
        for i, (text, cmd, bstyle) in enumerate(btn_data):
            if i > 0:
                ttk.Separator(toolbar, orient=tk.VERTICAL).pack(
                    side=tk.LEFT, fill=tk.Y, padx=8, pady=3)
            ttk.Button(toolbar, text=text, command=cmd,
                       bootstyle=bstyle).pack(side=tk.LEFT, padx=2)
        toolbar.pack(side=tk.TOP, fill=tk.X)

    def _build_main_area(self):
        """构建主工作区（标签页布局）"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(6, 4))
        self._build_data_preview_tab()
        self._build_analysis_tab()
        self._build_visualization_tab()
        self._build_log_tab()

    def _build_data_preview_tab(self):
        """数据预览标签页"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="  📋 数据预览 ")

        info_frame = ttk.LabelFrame(frame, text="数据信息", padding=(10, 8))
        info_frame.pack(fill=tk.X, padx=12, pady=(12, 6))

        self.info_text = tk.Text(info_frame, height=4,
                                 font=("Consolas", 10),
                                 bg="#FAFAFA", relief="flat", borderwidth=1,
                                 padx=8, pady=6)
        self.info_text.pack(fill=tk.X)
        self.info_text.insert(tk.END,
            "欢迎使用物联网多源传感器数据分析系统 V1.1\n\n"
            "→ 点击工具栏「导入CSV」或菜单「文件 → 导入示例数据」开始")
        self.info_text.config(state=tk.DISABLED)

        table_frame = ttk.LabelFrame(frame, text="数据表格（前 100 行）",
                                     padding=(10, 8))
        table_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 12))

        columns = ("#1", "#2", "#3")
        self.tree = ttk.Treeview(table_frame, columns=columns,
                                  show="headings", height=15,
                                  selectmode="browse")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150)

        v_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL,
                                 command=self.tree.yview)
        h_scroll = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL,
                                 command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set,
                            xscrollcommand=h_scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

    def _build_analysis_tab(self):
        """统计分析标签页（分析功能统一走菜单栏「分析」入口）"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="  📊 统计分析 ")

        hint = ttk.Label(
            frame, text="点击菜单栏「分析」→ 选择分析项，结果将在此显示",
            font=("微软雅黑", 10), foreground="#888",
            padding=(12, 10),
        )
        hint.pack(fill=tk.X, padx=12, pady=(10, 0))

        self.analysis_text = scrolledtext.ScrolledText(
            frame, wrap=tk.WORD, font=("Consolas", 10),
            bg="#FAFAFA", relief="flat", borderwidth=1,
        )
        self.analysis_text.pack(fill=tk.BOTH, expand=True,
                                padx=12, pady=(2, 12))
        self.analysis_text.insert(tk.END, "运行分析后结果将在此处显示\n")
        self.analysis_text.config(state=tk.DISABLED)

    def _build_visualization_tab(self):
        """可视化标签页"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="  📈 可视化 ")

        control_frame = ttk.LabelFrame(frame, text="图表设置", padding=(12, 10))
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(12, 8), pady=12)
        control_frame.configure(width=230)
        control_frame.pack_propagate(False)

        ttk.Label(control_frame, text="图表类型：",
                  font=("微软雅黑", 9)).pack(anchor=tk.W, pady=(0, 3))
        self.chart_type_var = tk.StringVar(value="时间序列图")
        chart_combo = ttk.Combobox(
            control_frame, textvariable=self.chart_type_var,
            values=self.CHART_TYPES, state="readonly", width=22,
            font=("微软雅黑", 10),
        )
        chart_combo.pack(fill=tk.X, pady=(0, 12))
        chart_combo.bind("<<ComboboxSelected>>", self._on_chart_type_changed)

        ttk.Label(control_frame, text="传感器列（多选）：",
                  font=("微软雅黑", 9)).pack(anchor=tk.W, pady=(0, 3))
        col_frame = ttk.Frame(control_frame)
        col_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 4))

        self.column_listbox = tk.Listbox(
            col_frame, selectmode=tk.MULTIPLE,
            font=("Consolas", 10), height=10,
            bg="#FAFAFA", relief="flat", borderwidth=1,
        )
        col_scroll = ttk.Scrollbar(col_frame, orient=tk.VERTICAL,
                                   command=self.column_listbox.yview)
        self.column_listbox.configure(yscrollcommand=col_scroll.set)
        self.column_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        col_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 全选/取消 快捷按钮
        sel_bar = ttk.Frame(control_frame)
        sel_bar.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(sel_bar, text="全选", command=self._on_select_all,
                   bootstyle="link", width=5).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(sel_bar, text="取消", command=self._on_select_none,
                   bootstyle="link", width=5).pack(side=tk.LEFT)

        btn_style = {"fill": tk.X, "pady": (0, 5)}
        ttk.Button(control_frame, text="🔄  生成图表",
                   command=self._on_generate_chart,
                   bootstyle="primary").pack(**btn_style)
        ttk.Button(control_frame, text="💾  保存图表",
                   command=self._on_save_chart,
                   bootstyle="warning-outline").pack(**btn_style)
        ttk.Button(control_frame, text="📦  批量导出",
                   command=self._on_export_charts,
                   bootstyle="success-outline").pack(fill=tk.X)

        display_frame = ttk.LabelFrame(frame, text="图表显示", padding=(5, 5))
        display_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True,
                           padx=(4, 12), pady=12)

        self.chart_container = ttk.Frame(display_frame)
        self.chart_container.pack(fill=tk.BOTH, expand=True)

        self.chart_placeholder = ttk.Label(
            self.chart_container,
            text="← 请先在左侧选择图表类型和传感器列，\n    然后点击「生成图表」",
            font=("微软雅黑", 12), foreground="#AAA",
            anchor=tk.CENTER, justify=tk.CENTER,
        )
        self.chart_placeholder.pack(fill=tk.BOTH, expand=True)

        self.chart_info_var = tk.StringVar(value="")
        chart_info = ttk.Label(display_frame,
                               textvariable=self.chart_info_var,
                               font=("微软雅黑", 9), foreground="#888")
        chart_info.pack(anchor=tk.W, pady=(3, 0))

    def _build_log_tab(self):
        """处理日志标签页"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="  📝 处理日志 ")

        self.log_text = scrolledtext.ScrolledText(
            frame, wrap=tk.WORD, font=("Consolas", 10),
            bg="#FAFAFA", relief="flat", borderwidth=1,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        self.log_text.insert(tk.END, "系统就绪。操作日志将在此处显示\n")
        self.log_text.config(state=tk.DISABLED)

    def _build_status_bar(self):
        """构建状态栏（含进度条）"""
        bar_frame = ttk.Frame(self.root)
        bar_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_var = tk.StringVar(value="就绪 ✅")
        status_label = ttk.Label(bar_frame, textvariable=self.status_var,
                                 font=("微软雅黑", 9), padding=(12, 4))
        status_label.pack(side=tk.LEFT)

        self.progress_bar = ttk.Progressbar(
            bar_frame, mode="indeterminate", length=140,
            bootstyle="info-striped",
        )

        self.row_count_var = tk.StringVar(value="")
        row_label = ttk.Label(bar_frame, textvariable=self.row_count_var,
                              font=("微软雅黑", 9), padding=(12, 4))
        row_label.pack(side=tk.RIGHT)

    # ──────────────────────────────────────────
    # 可视化页方法
    # ──────────────────────────────────────────

    def _refresh_column_list(self):
        """刷新传感器列选择列表（从当前数据中提取数值列）"""
        self.column_listbox.delete(0, tk.END)
        if self.current_df is None:
            return
        numeric_cols = self.current_df.select_dtypes(include=["number"]).columns
        for col in numeric_cols:
            self.column_listbox.insert(tk.END, col)
        # 默认全选
        if self.column_listbox.size() > 0:
            self.column_listbox.selection_set(0, tk.END)

    def _on_select_all(self):
        """全选传感器列"""
        if self.column_listbox.size() > 0:
            self.column_listbox.selection_set(0, tk.END)

    def _on_select_none(self):
        """取消全选"""
        self.column_listbox.selection_clear(0, tk.END)

    def _on_chart_type_changed(self, event=None):
        """图表类型切换时的辅助提示"""
        chart_type = self.chart_type_var.get()
        if chart_type == "散点图" and self.column_listbox.size() >= 2:
            # 散点图推荐选 2 列
            self.column_listbox.selection_clear(0, tk.END)
            self.column_listbox.selection_set(0)
            self.column_listbox.selection_set(1)

    def _on_quick_plot(self, chart_type: str):
        """工具栏快捷生成图表"""
        if not self._check_data():
            return
        self.chart_type_var.set(chart_type)
        self._on_generate_chart()

    def _on_generate_chart(self):
        """根据当前设置生成图表并内嵌显示"""
        if not self._check_data():
            return

        chart_type = self.chart_type_var.get()
        indices = self.column_listbox.curselection()
        if not indices:
            messagebox.showwarning("选择列", "请至少选择一个传感器列")
            return

        selected_cols = [self.column_listbox.get(i) for i in indices]

        if chart_type == "散点图" and len(selected_cols) < 2:
            messagebox.showwarning("散点图", "散点图需要至少选择两个传感器列")
            return

        self._set_status(f"正在生成 {chart_type}...")
        self._show_progress(True)
        self.root.update_idletasks()

        try:
            fig = self._plot_inline(chart_type, selected_cols)
            if fig:
                self._display_figure(fig)
                self._append_log(
                    f"[{datetime.now().strftime('%H:%M:%S')}] "
                    f"生成图表: {chart_type} "
                    f"({', '.join(selected_cols[:4])})"
                )
                self._set_status(f"✅ {chart_type} 已生成")
            else:
                self._set_status("❌ 图表生成失败")
        except Exception as e:
            messagebox.showerror("生成失败", str(e))
            self._set_status("❌ 图表生成失败")
        finally:
            self._show_progress(False)

    def _plot_inline(self, chart_type: str,
                     columns: Optional[list] = None) -> Optional[Figure]:
        """
        根据图表类型和列生成图表，返回 Figure 对象

        参数:
            chart_type: 图表类型名称（中文）
            columns: 要绘制的传感器列

        返回:
            matplotlib Figure 对象，失败时返回 None
        """
        if not self._check_data():
            return None

        if columns is None:
            selected = self.column_listbox.curselection()
            if selected:
                columns = [self.column_listbox.get(i) for i in selected]
            else:
                columns = (self.current_df
                           .select_dtypes(include=["number"])
                           .columns[:4].tolist())

        try:
            chart_map = {
                "时间序列图": lambda: self.visualizer.plot_time_series(
                    columns, title="传感器时间序列",
                ),
                "散点图": lambda: self.visualizer.plot_scatter(
                    columns[0], columns[1],
                    title=f"{columns[0]} vs {columns[1]} 散点图",
                ) if len(columns) >= 2 else None,
                "相关性热力图": lambda: self.visualizer.plot_heatmap(
                    columns, title="传感器相关系数热力图",
                ),
                "分布直方图": lambda: self.visualizer.plot_histogram(
                    columns[:4], title="传感器数据分布",
                ),
                "箱线图": lambda: self.visualizer.plot_boxplot(
                    columns, title="传感器数据箱线图",
                ),
                "综合仪表盘": lambda: self.visualizer.plot_dashboard(
                    columns[:4],
                ),
            }

            plot_func = chart_map.get(chart_type)
            if plot_func is None:
                raise ValueError(f"不支持的图表类型: {chart_type}")

            return plot_func()

        except Exception as e:
            messagebox.showerror("图表生成失败", str(e))
            return None

    def _display_figure(self, fig: Figure):
        """
        在图表容器中显示 matplotlib Figure，自动适配容器大小

        参数:
            fig: matplotlib Figure 对象
        """
        # 清除占位符
        self.chart_placeholder.pack_forget()

        # 清除旧的 canvas 和 toolbar
        for widget in self.chart_container.winfo_children():
            widget.destroy()

        # 创建新 canvas
        self.current_figure = fig
        canvas = FigureCanvasTkAgg(fig, master=self.chart_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # matplotlib 导航工具栏
        toolbar = NavigationToolbar2Tk(canvas, self.chart_container)
        toolbar.update()

        # 切换到可视化标签页
        self.notebook.select(2)

        # 强制完整更新（非 idle），确保 widget 销毁/重建后的几何信息准确
        self.root.update()

        # 根据容器实际尺寸重新缩放 Figure，留出工具栏高度
        cw = self.chart_container.winfo_width()
        ch = self.chart_container.winfo_height()
        if cw > 100 and ch > 100:
            dpi = fig.get_dpi()
            toolbar_h = 36 if hasattr(self, '_canvas_widget') and self._canvas_widget else 36
            fig.set_size_inches((cw - 6) / dpi, (ch - toolbar_h - 4) / dpi)
            fig.tight_layout(pad=1.5)
            canvas.draw()

        # 更新图表信息（含简要说明）
        chart_type = self.chart_type_var.get()
        tips = {
            "时间序列图": "展示各传感器数值随时间的变化趋势",
            "散点图": "两两传感器之间的相关关系",
            "相关性热力图": "多传感器相关系数矩阵，颜色越深越相关",
            "分布直方图": "各传感器数值的分布形态与密度曲线",
            "箱线图": "各传感器的中位数、四分位数与异常值",
            "综合仪表盘": "四合一总览：时序 + 分布 + 箱线 + 相关性",
        }
        n_lines = len(fig.axes[0].get_lines()) if fig.axes else 0
        self.chart_info_var.set(
            f"{chart_type} — {tips.get(chart_type, '')}"
        )

        self._canvas_widget = canvas

    def _on_save_chart(self):
        """保存当前显示的图表到文件"""
        if self.current_figure is None:
            messagebox.showwarning("无图表", "请先生成图表")
            return

        file_path = filedialog.asksaveasfilename(
            title="保存图表",
            defaultextension=".png",
            filetypes=[
                ("PNG 图片", "*.png"),
                ("JPEG 图片", "*.jpg"),
                ("PDF 文档", "*.pdf"),
                ("SVG 矢量图", "*.svg"),
            ],
        )
        if not file_path:
            return

        try:
            self.current_figure.savefig(file_path, dpi=150, bbox_inches="tight")
            self._set_status(f"✅ 图表已保存: {os.path.basename(file_path)}")
            self._append_log(
                f"[{datetime.now().strftime('%H:%M:%S')}] "
                f"保存图表: {file_path}"
            )
        except Exception as e:
            messagebox.showerror("保存失败", str(e))

    # ──────────────────────────────────────────
    # 进度条辅助
    # ──────────────────────────────────────────

    def _show_progress(self, show: bool):
        """显示或隐藏进度条动画"""
        if show:
            self.progress_bar.pack(side=tk.RIGHT, padx=(8, 0))
            self.progress_bar.start(8)
        else:
            self.progress_bar.stop()
            self.progress_bar.pack_forget()

    # ──────────────────────────────────────────
    # 事件处理方法
    # ──────────────────────────────────────────

    def _on_import_csv(self):
        """导入 CSV 文件"""
        file_path = filedialog.askopenfilename(
            title="选择传感器数据 CSV 文件",
            filetypes=[("CSV 文件", "*.csv"), ("所有文件", "*.*")],
        )
        if not file_path:
            return

        self._set_status("正在导入数据...")
        self._show_progress(True)
        self.root.update_idletasks()

        try:
            config = DataSourceConfig("csv")
            config.file_path = file_path
            df = self.ingestion.from_csv(config)

            self.current_df = df
            self.timestamp_col = config.timestamp_column
            self.data_source = file_path
            self.processor.set_data(df)
            self.visualizer.set_data(df, config.timestamp_column)
            self.analyzer.set_data(df)

            self._update_data_preview(df)
            self._refresh_column_list()
            self._set_status(f"✅ 已导入 {len(df)} 行 × {len(df.columns)} 列")
            self._append_log(
                f"[{datetime.now().strftime('%H:%M:%S')}] "
                f"导入文件: {os.path.basename(file_path)}"
            )

        except Exception as e:
            messagebox.showerror("导入失败", str(e))
            self._set_status("❌ 导入失败")
        finally:
            self._show_progress(False)

    def _on_load_sample(self):
        """加载内置示例数据（4 传感器 × 1000 条，含人工异常值）"""
        self._set_status("正在生成示例数据...")
        self._show_progress(True)
        self.root.update_idletasks()

        try:
            import numpy as np
            np.random.seed(42)
            n = 1000
            t = pd.date_range("2026-06-01", periods=n, freq="5min")

            df = pd.DataFrame({"timestamp": t})
            # 温度: 25 + 5*sin + 噪声 + 异常区间
            df["temperature"] = (
                25 + 5 * np.sin(np.linspace(0, 6 * np.pi, n))
                + np.random.normal(0, 0.5, n)
            )
            df.loc[150:155, "temperature"] += 15   # 注入异常突增
            # 湿度: 60 + 10*cos + 噪声 + 异常区间
            df["humidity"] = (
                60 + 10 * np.cos(np.linspace(0, 4 * np.pi, n))
                + np.random.normal(0, 1, n)
            )
            df.loc[500:505, "humidity"] -= 30       # 注入异常突降
            # 气压: 微幅波动
            df["pressure"] = (
                1013 + 2 * np.sin(np.linspace(0, 8 * np.pi, n))
                + np.random.normal(0, 0.3, n)
            )
            # 光照: 正弦 + 截断
            base_light = np.clip(
                500 * np.sin(np.linspace(0, 12 * np.pi, n)), 0, None,
            )
            df["light"] = base_light + np.random.normal(0, 20, n)

            self.current_df = df
            self.timestamp_col = "timestamp"
            self.ingestion.data = df   # 同步给 ingestion，供统计摘要使用
            self.processor.set_data(df)
            self.visualizer.set_data(df, "timestamp")
            self.analyzer.set_data(df)

            self._update_data_preview(df)
            self._refresh_column_list()
            self._set_status(f"✅ 已加载示例数据: {len(df)} 行 × "
                             f"{len(df.columns)} 列")
            self._append_log(
                f"[{datetime.now().strftime('%H:%M:%S')}] "
                f"加载示例数据 (4 传感器, {n} 条)"
            )

        except Exception as e:
            messagebox.showerror("加载失败", str(e))
            self._set_status("❌ 加载失败")
        finally:
            self._show_progress(False)

    def _on_fill_missing(self):
        """缺失值填充"""
        if not self._check_data():
            return
        result = messagebox.askyesno(
            "缺失值填充",
            "是否使用线性插值填充所有缺失值？\n选择「否」将使用前向填充。",
        )
        method = "linear" if result else "ffill"
        try:
            self.processor.fill_missing(method=method)
            self.current_df = self.processor.df
            self._update_data_preview(self.current_df)
            self._set_status(f"✅ 缺失值填充完成 (方法: {method})")
            self._append_log(
                f"[{datetime.now().strftime('%H:%M:%S')}] "
                f"填充缺失值: {method}"
            )
        except Exception as e:
            messagebox.showerror("处理失败", str(e))

    def _on_detect_outliers(self):
        """异常值检测（3σ 准则）"""
        if not self._check_data():
            return
        try:
            results = self.processor.detect_outliers_3sigma()
            report = OutlierDetectionReport.generate_report(results)

            self._show_in_analysis(report)
            self.notebook.select(1)
            self._set_status("✅ 异常检测完成")
            self._append_log(
                f"[{datetime.now().strftime('%H:%M:%S')}] "
                f"异常检测 (3σ)"
            )
        except Exception as e:
            messagebox.showerror("分析失败", str(e))

    def _on_smooth_data(self):
        """数据平滑（移动平均）"""
        if not self._check_data():
            return
        try:
            self.processor.smooth_moving_average(window=5)
            self.current_df = self.processor.df
            self._update_data_preview(self.current_df)
            self._set_status("✅ 数据平滑完成 (移动平均, 窗口=5)")
            self._append_log(
                f"[{datetime.now().strftime('%H:%M:%S')}] "
                f"数据平滑: 移动平均 window=5"
            )
        except Exception as e:
            messagebox.showerror("处理失败", str(e))

    def _on_normalize(self):
        """标准化 / 归一化"""
        if not self._check_data():
            return
        choice = messagebox.askyesno(
            "标准化/归一化",
            "选择「是」使用 Z-Score 标准化\n选择「否」使用 Min-Max 归一化",
        )
        try:
            if choice:
                self.processor.standardize()
                self._set_status("✅ Z-Score 标准化完成")
            else:
                self.processor.normalize()
                self._set_status("✅ Min-Max 归一化完成")
            self.current_df = self.processor.df
            self._update_data_preview(self.current_df)
            self._append_log(
                f"[{datetime.now().strftime('%H:%M:%S')}] "
                f"{'标准化' if choice else '归一化'}完成"
            )
        except Exception as e:
            messagebox.showerror("处理失败", str(e))

    def _on_run_pipeline(self):
        """运行默认处理管线：填充 → 异常删除 → 平滑"""
        if not self._check_data():
            return
        if not messagebox.askyesno(
            "确认",
            "运行默认处理管线？\n\n步骤: 填充缺失值 → 异常值删除 → 移动平均平滑",
        ):
            return
        try:
            self._set_status("🔄 运行处理管线...")
            self._show_progress(True)
            self.root.update_idletasks()

            self.processor.run_pipeline([
                ("fill_missing", {"method": "linear"}),
                ("remove_outliers", {"method": "3sigma"}),
                ("smooth_moving_average", {"window": 5}),
            ])
            self.current_df = self.processor.df
            self._update_data_preview(self.current_df)
            self._set_status("✅ 处理管线完成")
            self._append_log(
                f"[{datetime.now().strftime('%H:%M:%S')}] "
                f"管线完成: 填充→异常删除→平滑"
            )
        except Exception as e:
            messagebox.showerror("管线失败", str(e))
        finally:
            self._show_progress(False)

    def _on_show_stats(self):
        """显示数据统计摘要"""
        if not self._check_data():
            return
        try:
            stats = self.ingestion.get_data_summary()
            if "error" in stats:
                self._show_in_analysis(f"⚠  {stats['error']}。请先通过「文件」菜单导入数据或加载示例数据。")
                self.notebook.select(1)
                return
            lines = [f"行数: {stats['行数']}",
                     f"列数: {stats['列数']}",
                     f"数值列数: {stats['数值列数']}",
                     f"缺失值总数: {stats['缺失值总数']}",
                     ""]

            for col, info in stats.get("列信息", {}).items():
                lines.append(f"【{col}】(类型: {info['类型']})")
                if "均值" in info:
                    lines.append(f"  均值={info['均值']}  "
                                 f"标准差={info['标准差']}")
                    lines.append(f"  范围=[{info['最小值']}, {info['最大值']}]"
                                 f"  缺失={info['缺失数']}")
                lines.append("")

            self._show_in_analysis("\n".join(lines))
            self.notebook.select(1)
            self._set_status("✅ 统计摘要已生成")
        except Exception as e:
            messagebox.showerror("分析失败", str(e))

    def _on_correlation(self):
        """相关性分析（Pearson）"""
        if not self._check_data():
            return
        try:
            result = self.analyzer.correlation_analysis()
            corr_df = result["correlation_matrix"]

            lines = [str(corr_df.round(4)), ""]

            pairs = result["highly_correlated"]
            if pairs:
                lines.append("高相关对 (|r| >= 0.7):")
                for col_a, col_b, r in pairs:
                    direction = "正相关" if r > 0 else "负相关"
                    lines.append(f"  {col_a} ↔ {col_b}: r={r} ({direction})")
            else:
                lines.append("未发现高相关对")

            self._show_in_analysis("\n".join(lines))
            self.notebook.select(1)
            self._set_status("✅ 相关性分析完成")
            self._append_log(
                f"[{datetime.now().strftime('%H:%M:%S')}] "
                f"相关性分析完成"
            )
        except Exception as e:
            messagebox.showerror("分析失败", str(e))

    def _on_trend_analysis(self):
        """趋势分析（线性回归）"""
        if not self._check_data():
            return
        try:
            numeric_cols = (self.current_df
                            .select_dtypes(include=["number"])
                            .columns)
            lines = []
            for col in numeric_cols[:6]:
                trend = self.analyzer.trend_analysis(col)
                lines.append(f"【{col}】")
                lines.append(f"  趋势: {trend['trend']}")
                lines.append(f"  斜率: {trend['slope']}")
                lines.append(f"  R²: {trend['r_squared']}")
                lines.append(f"  显著性(p): {trend['p_value']}")
                lines.append("")

            self._show_in_analysis("\n".join(lines))
            self.notebook.select(1)
            self._set_status("✅ 趋势分析完成")
        except Exception as e:
            messagebox.showerror("分析失败", str(e))

    def _on_distribution_test(self):
        """分布检验（正态性检验）"""
        if not self._check_data():
            return
        try:
            numeric_cols = (self.current_df
                            .select_dtypes(include=["number"])
                            .columns[:6])
            lines = []
            for col in numeric_cols:
                try:
                    result = self.analyzer.distribution_analysis(col)
                    lines.append(f"【{col}】")
                    lines.append(f"  检验方法: {result['test_method']}")
                    lines.append(f"  P值: {result['p_value']}")
                    is_norm = result['is_normal']
                    lines.append(f"  正态性: {'✅ 服从正态' if is_norm
                                              else '❌ 不服从正态'}")
                    lines.append(f"  偏度: {result['skewness']} "
                                 f"({result['skewness_description']})")
                    lines.append(f"  峰度: {result['kurtosis']} "
                                 f"({result['kurtosis_description']})")
                    lines.append("")
                except Exception as e:
                    lines.append(f"【{col}】检验失败: {e}\n")

            self._show_in_analysis("\n".join(lines))
            self.notebook.select(1)
            self._set_status("✅ 分布检验完成")
        except Exception as e:
            messagebox.showerror("分析失败", str(e))

    def _on_export_charts(self):
        """批量导出所有图表到 output 目录"""
        if not self._check_data():
            return

        self._set_status("🔄 正在批量导出图表...")
        self._show_progress(True)
        self.root.update_idletasks()

        try:
            os.makedirs(self.OUTPUT_DIR, exist_ok=True)
            cols = (self.current_df
                    .select_dtypes(include=["number"])
                    .columns)
            files = self.visualizer.export_all_charts(
                self.OUTPUT_DIR, cols.tolist(), prefix="batch_",
            )

            self._set_status(f"✅ 已生成 {len(files)} 张图表到 output/ 目录")
            self._append_log(
                f"[{datetime.now().strftime('%H:%M:%S')}] "
                f"批量导出 {len(files)} 张图表"
            )

            if messagebox.askyesno(
                "导出完成",
                f"已生成 {len(files)} 张图表到:\n"
                f"{os.path.abspath(self.OUTPUT_DIR)}\n\n是否打开文件夹？",
            ):
                os.startfile(os.path.abspath(self.OUTPUT_DIR))
        except Exception as e:
            import traceback
            detail = traceback.format_exc()
            self._append_log(f"[ERROR] 批量导出失败:\n{detail}")
            self._set_status("❌ 导出失败，详见日志")
            messagebox.showerror("导出失败",
                f"{str(e)}\n\n详细信息已写入「处理日志」标签页")
        finally:
            self._show_progress(False)

    def _on_export_excel(self):
        """导出原始数据到 Excel"""
        if not self._check_data():
            return
        file_path = filedialog.asksaveasfilename(
            title="导出 Excel",
            defaultextension=".xlsx",
            filetypes=[("Excel 文件", "*.xlsx")],
        )
        if not file_path:
            return
        try:
            self.reporter.to_excel_simple(self.current_df, file_path)
            self._set_status(f"✅ 已导出: {os.path.basename(file_path)}")
            self._append_log(
                f"[{datetime.now().strftime('%H:%M:%S')}] "
                f"导出 Excel: {file_path}"
            )
        except Exception as e:
            messagebox.showerror("导出失败", str(e))

    def _on_export_report(self):
        """导出完整分析报告（文本或 Excel）"""
        if not self._check_data():
            return
        file_path = filedialog.asksaveasfilename(
            title="导出分析报告",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("Excel 文件", "*.xlsx")],
        )
        if not file_path:
            return

        try:
            analysis_results = {}
            try:
                analysis_results["correlation"] = self.analyzer.correlation_analysis()
            except Exception:
                pass
            try:
                analysis_results["outliers"] = self.processor.detect_outliers_3sigma()
            except Exception:
                pass
            try:
                cols = (self.current_df
                        .select_dtypes(include=["number"])
                        .columns)
                trends = {}
                for col in cols:
                    trends[col] = self.analyzer.trend_analysis(col)
                analysis_results["trends"] = trends
            except Exception:
                pass

            if file_path.endswith(".xlsx"):
                self.reporter.to_excel_with_charts(
                    self.current_df, analysis_results, file_path=file_path,
                )
            else:
                self.reporter.to_text_report(
                    self.current_df, analysis_results, file_path=file_path,
                )

            self._set_status(f"✅ 报告已导出: {os.path.basename(file_path)}")
            self._append_log(
                f"[{datetime.now().strftime('%H:%M:%S')}] "
                f"导出报告: {file_path}"
            )
        except Exception as e:
            messagebox.showerror("导出失败", str(e))

    def _on_about(self):
        """关于对话框"""
        messagebox.showinfo(
            "关于",
            f"{self.APP_TITLE}\n\n"
            "作者: Anonymous\n"
            "技术栈: Python + Tkinter + Pandas + Matplotlib\n"
            "功能: 多源传感器数据接入、处理、分析与可视化\n\n"
            "本软件仅供学习和研究使用",
        )

    # ──────────────────────────────────────────
    # 辅助方法
    # ──────────────────────────────────────────

    def _check_data(self) -> bool:
        """检查是否已加载数据"""
        if self.current_df is None or self.current_df.empty:
            messagebox.showwarning("无数据", "请先导入数据文件或加载示例数据")
            return False
        return True

    def _update_data_preview(self, df: pd.DataFrame):
        """更新数据预览表格和信息区域"""
        # 更新信息区域
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete("1.0", tk.END)
        info_lines = [
            f"行数: {len(df)}",
            f"列数: {len(df.columns)}",
            f"列名: {', '.join(df.columns.tolist())}",
            f"数值列: {len(df.select_dtypes(include=['number']).columns)}",
            f"缺失值: {int(df.isnull().sum().sum())}",
            f"来源: {self.data_source or '示例数据'}",
        ]
        self.info_text.insert(tk.END, "\n".join(info_lines))
        self.info_text.config(state=tk.DISABLED)

        # 更新表格
        self.tree.delete(*self.tree.get_children())
        columns = list(df.columns)
        self.tree["columns"] = columns
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, minwidth=80)

        # 只显示前 100 行
        display_df = df.head(100)
        for _, row in display_df.iterrows():
            values = []
            for col in columns:
                val = row[col]
                if isinstance(val, float):
                    values.append(f"{val:.4f}")
                else:
                    values.append(str(val))
            self.tree.insert("", tk.END, values=values)

        # 更新底部行数信息
        self.row_count_var.set(f"📊 {len(df)} 行 × {len(df.columns)} 列")

    def _show_in_analysis(self, text: str):
        """在分析标签页显示内容"""
        self.analysis_text.config(state=tk.NORMAL)
        self.analysis_text.delete("1.0", tk.END)
        self.analysis_text.insert(tk.END, text)
        self.analysis_text.config(state=tk.DISABLED)

    def _append_log(self, message: str):
        """追加日志"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _set_status(self, message: str):
        """设置状态栏文本"""
        self.status_var.set(message)

    # ──────────────────────────────────────────
    # 运行
    # ──────────────────────────────────────────

    def run(self):
        """启动主窗口"""
        self.root.mainloop()
