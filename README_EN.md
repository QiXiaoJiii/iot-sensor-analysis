# IoT Multi-Source Sensor Data Analysis System

> A Python-based desktop application for importing, cleaning, analyzing, and visualizing multi-sensor IoT data — with publication-quality charts and causal discovery capabilities.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-lightgrey)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

**📸 Screenshots** → [See below](#screenshots)

---

## ✨ Highlights

- **3 data sources** — CSV import (auto-encoding detection), Serial port (Arduino/ESP32), MQTT subscription
- **6 chart types** in Nature-journal visual style (Tufte-inspired: de-spined, white-background, colorblind-safe palette)
- **Lagged cross-correlation analysis** — discovers causal relationships between sensors by detecting time-delayed correlations
- **Complete data pipeline** — missing value imputation (6 methods) → outlier detection (3σ + IQR) → smoothing (SMA + Savitzky-Golay) → analysis
- **One-click export** — Excel report with embedded charts + plain-text analysis report
- **Standalone Windows installer** — 69MB .exe, no Python required

---

## 🚀 Quick Start

### Option 1: Pre-built installer (Windows)

Download `IoT_Sensor_Analyzer_V1.1_Setup.exe` from [Releases](https://github.com/YOUR_USERNAME/iot-sensor-analysis/releases) and install.

### Option 2: Run from source

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/iot-sensor-analysis.git
cd iot-sensor-analysis

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch GUI
python main.py

# 4. Or use CLI mode
python main.py --cli samples/sample_sensor_data.csv
```

---

## 🧩 Architecture

```
┌─────────────────────────────────────────────────┐
│                  main.py (GUI / CLI)              │
├─────────────────────────────────────────────────┤
│  src/                                            │
│  ├── data_ingestion.py    CSV / Serial / MQTT    │
│  ├── data_processing.py   Clean → Detect → Smooth│
│  ├── analysis.py          Stats + Lagged Corr ✨  │
│  ├── visualization.py     6 chart types (Nature) │
│  ├── report_export.py     Excel + Text reports   │
│  └── gui.py               Tkinter + cosmo theme  │
└─────────────────────────────────────────────────┘
```

---

## 📊 Charts (Nature Journal Style)

| Chart | Description |
|-------|-------------|
| **Time Series** | Multi-channel line plot with adaptive font sizing |
| **Scatter + Trend** | Two-sensor correlation with linear regression line |
| **Heatmap** | Pearson / Spearman / Kendall correlation matrix |
| **Histogram + KDE** | Distribution with kernel density estimation |
| **Box Plot** | Multi-sensor distribution comparison |
| **Dashboard** | 2×2 composite view (series + histogram + box + heatmap) |

All charts follow **Tufte's data-ink ratio principle**: right/top spines removed, frameless legends, restrained color palette, white background, 300 DPI export.

---

## 🔬 Lagged Cross-Correlation (Causal Discovery)

This project goes beyond static correlation. The `find_lagged_correlation()` method detects **time-delayed dependencies** between sensors:

```
Sensor A (temperature) ──[+5 min lag]──→ Sensor B (humidity)
```

This means: *changes in temperature precede changes in humidity by ~5 minutes* — a causal hint that Pearson correlation alone would miss.

**Method:**
1. For each sensor pair, compute cross-correlation across a lag window [-T, T]
2. Identify the optimal lag and corresponding coefficient
3. Build a directed causal graph from lag directions
4. Detect sensor faults by monitoring graph edge stability

➡️ See [paper/](paper/) directory (coming soon) for the full research paper.

---

## 🖼️ Screenshots

<!-- TODO: replace with actual screenshots -->
| | |
|---|---|
| **Dashboard** | **Time Series** |
| ![Dashboard](screenshots/dashboard.png) | ![Time Series](screenshots/timeseries.png) |
| **Heatmap** | **Box Plot** |
| ![Heatmap](screenshots/heatmap.png) | ![Box Plot](screenshots/boxplot.png) |

---

## 📦 Sample Datasets

The `samples/` folder includes ready-to-use CSV files:

| File | Description | Columns |
|------|-------------|---------|
| `sample_sensor_data.csv` | Multi-sensor simulation | temperature, humidity, pressure, light, wind_speed |
| `室内环境监测.csv` | Indoor environment monitoring | 温度, 湿度, CO2, PM2.5 |
| `温室环境监测.csv` | Greenhouse monitoring | 温度, 湿度, 光照, 土壤湿度 |
| `空气质量监测.csv` | Air quality monitoring | PM2.5, PM10, CO2, VOC |
| `设备振动监测.csv` | Equipment vibration | 加速度X, 加速度Y, 加速度Z |

---

## 🔧 Requirements

```
numpy>=1.24
pandas>=2.0
matplotlib>=3.7
scipy>=1.10
openpyxl>=3.1
ttkbootstrap>=1.10
```

Optional (for hardware data sources):
```
pyserial>=3.5      # Serial port reading
paho-mqtt>=1.6     # MQTT subscription
```

---

## 📄 License

MIT — see [LICENSE](LICENSE) for details.

---

## 👤 Author

IoT Engineering undergraduate. Building things, writing papers, preparing for AI graduate studies.

*If you find this useful, a ⭐ means a lot.*
