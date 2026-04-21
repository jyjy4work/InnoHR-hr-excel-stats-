# HR Excel Statistics Dashboard

A multilingual HR analytics dashboard built with Python & Streamlit.  
Upload your employee Excel or CSV file and get instant interactive charts, KPIs, and exportable reports — no database or server required.

---

## Features

| Tab | What it shows |
|-----|--------------|
| Dashboard | KPI cards — headcount, new hires, resignations, turnover rate, avg tenure |
| Headcount | Dept distribution, gender ratio, age groups, tenure, pyramid chart |
| Attrition | Monthly hire/resign trend, turnover by dept, avg tenure by dept |
| Gender & DI | Diversity index, gender balance by dept, age-gender pyramid |
| Time-to-Hire | Avg/median/min/max TTH, trend, distribution histogram, by dept |
| YoY | Year-over-year headcount & turnover comparison |
| Dept Analysis | Dept-level deep dive with stacked gender bar |
| Forecast | 6-month headcount forecast (linear trend) |
| Cohort | Retention heatmap + survival curves by hire year |
| Risk | Attrition risk scoring per employee (low/medium/high) |
| Search | Employee-level search & filter |
| Report | Custom report builder — choose sections, export HTML/PDF |
| Additional | Org structure stats, tenure & age distributions |

### Export formats
- Excel (`.xlsx`) — multi-sheet with formatted tables
- CSV — UTF-8 BOM encoded (Excel-compatible)
- HTML report — self-contained, interactive Plotly charts
- PDF report — multi-page with charts and KPI tables
- PNG summary — matplotlib-rendered overview image

### Languages
Korean · English · French  
All chart labels, axis titles, KPIs, and exported reports follow the selected language.

---

## Quick Start

### Requirements
- Python 3.10+
- pip

### Install & Run

**Windows**
```bat
run.bat
```

**Mac / Linux**
```bash
chmod +x run.sh
./run.sh
```

**Manual**
```bash
pip install -r requirements.txt
streamlit run hr_excel_stats/app.py
```

Then open your browser at `http://localhost:8501`

---

## Supported File Formats

| Format | Extensions |
|--------|-----------|
| Excel | `.xlsx`, `.xls` |
| CSV | `.csv` (auto-detects encoding) |

**Max file size:** 50 MB

---

## Column Mapping

The app auto-detects columns by common aliases. Required columns:

| Standard name | Recognized aliases |
|---------------|--------------------|
| `employee_id` | 사번, 직원번호, emp_id, id |
| `department` | 부서, 팀, dept, team |
| `hire_date` | 입사일, join_date, start_date |
| `is_active` | 재직여부, status, active |

Optional columns (features are skipped if missing):

| Standard name | Recognized aliases |
|---------------|--------------------|
| `name` | 이름, 성명, full_name |
| `gender` | 성별, sex |
| `birth_date` | 생년월일, dob, date_of_birth |
| `position` | 직급, 직위, grade, rank |
| `employment_type` | 고용형태, contract_type |
| `resign_date` | 퇴사일, end_date, termination_date |
| `resign_reason` | 퇴사사유, termination_reason |
| `application_date` | 지원일, apply_date (for Time-to-Hire) |
| `offer_date` | 오퍼일, offer_sent_date (for Time-to-Hire) |

Gender values are auto-normalized:  
`남 / 남성 / m / male / homme` → Male  
`여 / 여성 / f / female / femme` → Female

---

## Project Structure

```
hr_excel_stats/
├── app.py          # Streamlit UI, 13 tabs, CSS, download buttons
├── analytics.py    # All data analysis functions
├── charts.py       # Plotly chart builders (26 chart types)
├── exporter.py     # Excel / CSV / HTML / PDF / PNG export
├── parser.py       # File loading & column normalization
├── config.py       # Column mapping, app settings, bins
├── i18n.py         # Translations (KO / EN / FR, 260+ keys)
├── requirements.txt
├── run.bat         # Windows launcher
└── run.sh          # Mac/Linux launcher

tests/              # pytest test suite
docs/               # PDCA design & analysis documents
```

---

## Dependencies

```
streamlit >= 1.32.0
pandas >= 2.0.0
openpyxl >= 3.1.0
plotly >= 5.18.0
xlsxwriter >= 3.1.0
matplotlib >= 3.7.0
xlrd >= 2.0.1
fpdf2 (optional — required for PDF export)
```

---

## Privacy & Security

- All data is processed **locally in your browser session** — nothing is uploaded to any server.
- Never commit real employee data files (`.xlsx`, `.csv`) to this repository — they are blocked by `.gitignore`.
- The app runs fully offline after initial `pip install`.

---

## License

MIT License — free to use, modify, and distribute.
