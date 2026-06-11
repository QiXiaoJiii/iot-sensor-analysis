"""
数据接入模块 — 支持三种传感器数据源接入

功能:
  1. CSV 文件导入（最常用）
  2. 串口实时读取（连接 Arduino/ESP32 等硬件）
  3. MQTT 订阅（连接物联网云平台）
  4. 数据预览与格式校验

典型传感器数据格式：
  时间戳, 传感器1, 传感器2, 传感器3, ...
  2026-06-01 08:00:00, 23.5, 60.2, 101.3
"""

import csv
import io
import json
import time
import threading
from datetime import datetime
from typing import Optional, Callable

import pandas as pd
import numpy as np


class DataSourceConfig:
    """数据源配置项，统一管理三种来源的参数"""

    def __init__(self, source_type: str = "csv"):
        """
        参数:
            source_type: 数据源类型，可选 "csv" / "serial" / "mqtt"
        """
        self.source_type = source_type.lower()
        # CSV 配置
        self.file_path: Optional[str] = None
        self.encoding: str = "utf-8"
        self.delimiter: str = ","
        self.skip_rows: int = 0
        # 串口配置
        self.port: Optional[str] = None
        self.baudrate: int = 115200
        self.bytesize: int = 8
        self.parity: str = "N"
        self.stopbits: float = 1.0
        self.timeout: float = 1.0
        # MQTT 配置
        self.broker: Optional[str] = None
        self.port_mqtt: int = 1883
        self.topic: Optional[str] = None
        self.client_id: str = f"sensor_analyzer_{int(time.time())}"
        self.username: Optional[str] = None
        self.password: Optional[str] = None
        # 公共配置（列名映射）
        self.column_names: Optional[list] = None
        self.timestamp_column: str = "timestamp"
        self.value_columns: list = []


class SensorDataIngestion:
    """传感器数据采集器，封装三种数据源的读取逻辑"""

    # 常见传感器列名映射表
    COLUMN_ALIASES = {
        "温度": ["temperature", "temp", "t", "温度", "温"],
        "湿度": ["humidity", "hum", "h", "湿度", "湿"],
        "气压": ["pressure", "pres", "p", "气压", "大气压"],
        "光照": ["light", "lux", "illuminance", "光照", "光强"],
        "风速": ["wind_speed", "wind", "风速"],
        "PM2.5": ["pm2_5", "pm25", "pm2.5"],
        "CO2": ["co2", "二氧化碳"],
        "噪声": ["noise", "sound", "db", "噪声", "噪音"],
        "电压": ["voltage", "v", "电压"],
        "电流": ["current", "i", "电流"],
        "加速度": ["acceleration", "accel", "acc_x", "acc_y", "acc_z"],
        "角度": ["angle", "gyro", "陀螺仪"],
    }

    def __init__(self):
        self.data: Optional[pd.DataFrame] = None
        self.metadata: dict = {
            "source": None,
            "rows": 0,
            "columns": 0,
            "time_range": None,
            "import_time": None,
        }
        self._serial_thread: Optional[threading.Thread] = None
        self._mqtt_thread: Optional[threading.Thread] = None
        self._running = False
        self._buffer: list = []

    # ──────────────────────────────────────────
    # CSV 导入
    # ──────────────────────────────────────────

    def from_csv(self, config: DataSourceConfig) -> pd.DataFrame:
        """
        从 CSV 文件导入传感器数据

        参数:
            config: 数据源配置（含文件路径、编码、分隔符等）

        返回:
            pandas DataFrame，自动解析时间戳列
        """
        try:
            df = pd.read_csv(
                config.file_path,
                encoding=config.encoding,
                delimiter=config.delimiter,
                skiprows=config.skip_rows,
                low_memory=False,
            )
        except FileNotFoundError:
            raise FileNotFoundError(f"文件不存在: {config.file_path}")
        except UnicodeDecodeError:
            # 编码探测：尝试常见中文编码
            for enc in ["gbk", "gb2312", "utf-16", "latin1"]:
                try:
                    df = pd.read_csv(
                        config.file_path,
                        encoding=enc,
                        delimiter=config.delimiter,
                        skiprows=config.skip_rows,
                    )
                    break
                except (UnicodeDecodeError, FileNotFoundError):
                    continue
            else:
                raise ValueError("无法识别文件编码，请手动指定")

        # 自动识别时间戳列
        self._auto_parse_timestamp(df, config)

        # 自动识别传感器值列
        self._auto_label_columns(df, config)

        # 记录元数据
        self.data = df
        self.metadata.update({
            "source": f"CSV: {config.file_path}",
            "rows": len(df),
            "columns": len(df.columns),
            "import_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        if config.timestamp_column in df.columns:
            self.metadata["time_range"] = (
                str(df[config.timestamp_column].min()),
                str(df[config.timestamp_column].max()),
            )

        return df

    def preview_csv(self, file_path: str, n_rows: int = 10) -> dict:
        """
        预览 CSV 文件的前 N 行，用于导入前确认

        参数:
            file_path: CSV 文件路径
            n_rows: 预览行数

        返回:
            包含列名、类型、样例数据的字典
        """
        preview = {}
        # 尝试常见编码
        for enc in ["utf-8", "gbk", "gb2312"]:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    reader = csv.reader(f)
                    preview["encoding"] = enc
                    preview["delimiter"] = self._detect_delimiter(f.name)
                    break
            except (UnicodeDecodeError, FileNotFoundError):
                continue

        df_sample = pd.read_csv(
            file_path, encoding=preview.get("encoding", "utf-8"),
            nrows=n_rows
        )
        preview["columns"] = list(df_sample.columns)
        preview["dtypes"] = {c: str(df_sample[c].dtype) for c in df_sample.columns}
        preview["sample"] = df_sample.head(5).to_dict(orient="records")
        preview["null_counts"] = df_sample.isnull().sum().to_dict()
        preview["total_rows_estimate"] = self._estimate_csv_rows(file_path)
        return preview

    # ──────────────────────────────────────────
    # 串口读取
    # ──────────────────────────────────────────

    def from_serial(self, config: DataSourceConfig,
                    callback: Optional[Callable] = None) -> threading.Thread:
        """
        从串口实时读取传感器数据（异步线程）

        参数:
            config: 串口配置（端口、波特率等）
            callback: 每收到一条数据时的回调函数

        返回:
            后台读取线程
        """
        try:
            import serial
        except ImportError:
            raise ImportError("请先安装 pyserial: pip install pyserial")

        self._running = True
        self._buffer = []

        def _read_loop():
            try:
                ser = serial.Serial(
                    port=config.port,
                    baudrate=config.baudrate,
                    bytesize=config.bytesize,
                    parity=config.parity,
                    stopbits=config.stopbits,
                    timeout=config.timeout,
                )
                print(f"[串口] 已连接 {config.port} @ {config.baudrate} baud")
            except serial.SerialException as e:
                raise ConnectionError(f"串口连接失败: {e}")

            line_buffer = ""
            while self._running:
                try:
                    byte = ser.read(1)
                    if byte:
                        char = byte.decode("utf-8", errors="ignore")
                        if char == "\n":
                            self._parse_serial_line(line_buffer, config, callback)
                            line_buffer = ""
                        else:
                            line_buffer += char
                except serial.SerialException:
                    print("[串口] 连接断开")
                    break
                except Exception as e:
                    print(f"[串口] 读取错误: {e}")
            ser.close()
            print("[串口] 已关闭")

        self._serial_thread = threading.Thread(target=_read_loop, daemon=True)
        self._serial_thread.start()
        return self._serial_thread

    def stop_serial(self):
        """停止串口读取"""
        self._running = False
        if self._serial_thread:
            self._serial_thread.join(timeout=2.0)

    # ──────────────────────────────────────────
    # MQTT 订阅
    # ──────────────────────────────────────────

    def from_mqtt(self, config: DataSourceConfig,
                  callback: Optional[Callable] = None) -> threading.Thread:
        """
        从 MQTT 代理订阅传感器数据（异步线程）

        参数:
            config: MQTT 配置（代理地址、端口、主题等）
            callback: 每条消息的回调函数

        返回:
            后台订阅线程
        """
        try:
            import paho.mqtt.client as mqtt
        except ImportError:
            raise ImportError("请先安装 paho-mqtt: pip install paho-mqtt")

        self._running = True

        def _on_connect(client, userdata, flags, rc):
            if rc == 0:
                print(f"[MQTT] 已连接 {config.broker}:{config.port_mqtt}")
                client.subscribe(config.topic)
                print(f"[MQTT] 已订阅主题: {config.topic}")
            else:
                print(f"[MQTT] 连接失败，返回码: {rc}")

        def _on_message(client, userdata, msg):
            try:
                payload = msg.payload.decode("utf-8")
                # 尝试解析 JSON 格式传感器数据
                self._parse_mqtt_payload(payload, config, callback)
            except Exception as e:
                print(f"[MQTT] 解析错误: {e}")

        client = mqtt.Client(client_id=config.client_id)
        if config.username and config.password:
            client.username_pw_set(config.username, config.password)
        client.on_connect = _on_connect
        client.on_message = _on_message

        def _loop():
            try:
                client.connect(config.broker, config.port_mqtt, 60)
                client.loop_forever()
            except Exception as e:
                print(f"[MQTT] 连接异常: {e}")

        self._mqtt_thread = threading.Thread(target=_loop, daemon=True)
        self._mqtt_thread.start()
        return self._mqtt_thread

    def stop_mqtt(self):
        """停止 MQTT 订阅"""
        self._running = False
        if self._mqtt_thread:
            self._mqtt_thread.join(timeout=2.0)

    # ──────────────────────────────────────────
    # 数据工具方法
    # ──────────────────────────────────────────

    def get_data_summary(self) -> dict:
        """获取当前数据的汇总统计"""
        if self.data is None or self.data.empty:
            return {"error": "暂无数据"}

        numeric_cols = self.data.select_dtypes(include=[np.number]).columns
        summary = {
            "行数": len(self.data),
            "列数": len(self.data.columns),
            "数值列数": len(numeric_cols),
            "缺失值总数": int(self.data.isnull().sum().sum()),
            "列信息": {}
        }

        for col in self.data.columns:
            col_info = {"类型": str(self.data[col].dtype)}
            if col in numeric_cols:
                col_info.update({
                    "最小值": round(float(self.data[col].min()), 4),
                    "最大值": round(float(self.data[col].max()), 4),
                    "均值": round(float(self.data[col].mean()), 4),
                    "标准差": round(float(self.data[col].std()), 4),
                    "缺失数": int(self.data[col].isnull().sum()),
                })
            summary["列信息"][col] = col_info

        return summary

    # ──────────────────────────────────────────
    # 内部方法
    # ──────────────────────────────────────────

    def _auto_parse_timestamp(self, df: pd.DataFrame, config: DataSourceConfig):
        """自动识别并解析时间戳列"""
        for col in df.columns:
            col_lower = col.lower().strip()
            if col_lower in ["timestamp", "time", "datetime", "date",
                               "时间", "时间戳", "采集时间", "记录时间"]:
                config.timestamp_column = col
                try:
                    df[col] = pd.to_datetime(df[col], errors="coerce")
                except Exception:
                    pass
                break

    def _auto_label_columns(self, df: pd.DataFrame, config: DataSourceConfig):
        """自动标记传感器值列（数值列中非时间戳的列）"""
        timestamp_col = config.timestamp_column
        for col in df.columns:
            if col == timestamp_col:
                continue
            if pd.api.types.is_numeric_dtype(df[col]):
                config.value_columns.append(col)

    @staticmethod
    def _detect_delimiter(file_path: str) -> str:
        """自动探测 CSV 分隔符"""
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            sample = f.read(4096)
        common_delimiters = [",", "\t", ";", "|"]
        counts = {d: sample.count(d) for d in common_delimiters}
        return max(counts, key=counts.get) if max(counts.values()) > 0 else ","

    @staticmethod
    def _estimate_csv_rows(file_path: str) -> int:
        """估算 CSV 总行数（不全部加载）"""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                first_kb = f.read(8192)
                lines_in_sample = first_kb.count("\n")
                if lines_in_sample == 0:
                    return 0
                import os
                file_size = os.path.getsize(file_path)
                return int(file_size / max(len(first_kb), 1) * lines_in_sample)
        except Exception:
            return -1

    def _parse_serial_line(self, line: str, config: DataSourceConfig,
                           callback: Optional[Callable]):
        """解析串口一行数据"""
        line = line.strip()
        if not line:
            return
        parts = line.split(",")
        record = {"timestamp": datetime.now().isoformat()}
        if config.column_names and len(parts) == len(config.column_names):
            for i, col in enumerate(config.column_names):
                try:
                    record[col] = float(parts[i])
                except ValueError:
                    record[col] = parts[i]
        else:
            for i, val in enumerate(parts):
                try:
                    record[f"sensor_{i + 1}"] = float(val)
                except ValueError:
                    record[f"sensor_{i + 1}"] = val
        self._buffer.append(record)
        if callback:
            callback(record)

    def _parse_mqtt_payload(self, payload: str, config: DataSourceConfig,
                            callback: Optional[Callable]):
        """解析 MQTT JSON 消息"""
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            # 非 JSON 格式，当作纯文本记录
            data = {"raw": payload, "timestamp": datetime.now().isoformat()}

        if "timestamp" not in data:
            data["timestamp"] = datetime.now().isoformat()

        self._buffer.append(data)
        if callback:
            callback(data)
