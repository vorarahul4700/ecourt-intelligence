# eCourt India Case Details Scraper

A high-performance, automated Python application and web dashboard for scraping real-time case details by **CNR Number** from the official Indian Judiciary portal ([eCourts Services](https://services.ecourts.gov.in/ecourtindia_v6/?p=home/index)).

Features an automated **neural network captcha solver**, dynamic session token synchronization, persistent connection pooling, and structured case analytics. Ready for 1-click deployment on **Render**.

---

## Performance Optimizations

- **Pre-Warmed Singleton Neural OCR**: The `ddddocr` model is pre-warmed on server boot and maintained as an in-memory singleton. Captcha decoding executes in **~30ms** without model reloading overhead.
- **Dynamic Header Caching**: In-memory caching for security delimiter headers extracted from `components.js`, eliminating a redundant 65KB network round-trip.
- **HTTP Connection Pooling & Keep-Alive**: Uses `requests.adapters.HTTPAdapter` with connection pooling to reuse TLS handshakes.
- **High-Speed Regex Token Extraction**: Extracts CSRF tokens and captcha URLs from the initial DOM in **<0.1ms** (compared to 50ms full-DOM parsers).
- **Self-Healing Low-Latency Retry Loop**: Automatically refreshes expired tokens and retries with new captcha challenges in milliseconds if verification fails.

---

## Features

- **User-Defined CNR**: Accepts any 16-character alphanumeric CNR number via Web UI or CLI.
- **Structured Data Extraction**:
  - **Case Details**: Case Type, Filing Number, Filing Date, Registration Number, Registration Date, CNR Number, e-Filing Number, e-Filing Date.
  - **Case Status**: First Hearing Date, Next Hearing Date, Case Stage, Court Number and Judge.
  - **Litigants & Counsel**: Petitioners and Advocates, Respondents and Advocates.
  - **Acts & Sections**: Under Act(s), Under Section(s).
  - **Processes**: Process ID, Title, and Date.
  - **IA Status**: Interlocutory Applications (IA Number, Parties, Filing Date, Next Date, Purpose, Status).
  - **Hearing History**: Chronological records (Judge, Business Date, Next Hearing Date, Purpose of Hearing).
- **Multiple Output Formats**: Interactive Web Dashboard, Rich Terminal Tables, Structured JSON, or Raw HTML.

---

## Project Structure

```
ecourt-scrapper/
├── ecourt/
│   ├── __init__.py           # Package exports
│   ├── config.py             # URLs, headers, retry limits, timeouts
│   ├── models.py             # Pydantic data schemas
│   ├── captcha.py            # Pre-warmed singleton neural captcha solver
│   ├── parser.py             # Robust HTML parser for eCourts response tables
│   └── scraper.py            # Ultra-fast scraper engine & session manager
├── web/
│   ├── app.py                # FastAPI web server with SSE live progress
│   ├── static/
│   │   ├── css/style.css     # Premium dark glassmorphic styling
│   │   └── js/app.js         # Reactive dashboard JavaScript
│   └── templates/
│       └── index.html        # Semantic HTML5 dashboard
├── tests/
│   └── test_parser.py        # Pytest parser validation suite
├── main.py                   # Command-line interface
├── Procfile                  # Render deployment process definition
├── render.yaml               # Render Infrastructure-as-Code blueprint
├── requirements.txt          # Production dependencies (with headless opencv)
└── README.md                 # Documentation
```

---

## Running the Web App

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the Web Server

Run any of the following commands from the project root:

#### Standard Python Command:
```bash
python -m web.app
```

#### Via Uvicorn (Production mode):
```bash
python -m uvicorn web.app:app --host 0.0.0.0 --port 8080
```

#### With Auto-Reload (Development mode):
```bash
python -m uvicorn web.app:app --host 0.0.0.0 --port 8080 --reload
```

#### Custom Port (e.g., Port 8000):
```bash
python -m uvicorn web.app:app --host 0.0.0.0 --port 8000
```

### 3. Open the Dashboard
Navigate to:
- [**http://localhost:8080**](http://localhost:8080) or [**http://127.0.0.1:8080**](http://127.0.0.1:8080)

---

## Deploying to Render

This repository is pre-configured for deployment on [Render](https://render.com) using the included `Procfile` and `render.yaml`.

### Option A: Deploy via GitHub (Recommended)
1. Push this repository to your GitHub account:
   ```bash
   git init
   git add .
   git commit -m "Initial commit of eCourts Scraper"
   git remote add origin https://github.com/your-username/ecourt-scrapper.git
   git push -u origin main
   ```
2. Log into [Render Dashboard](https://dashboard.render.com).
3. Click **New +** > **Web Service**.
4. Connect your GitHub repository.
5. Render will automatically detect the configuration from `render.yaml` or use:
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn web.app:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/healthz`
6. Click **Deploy Web Service**.

### Option B: Deploy via Render Blueprint
1. In the Render Dashboard, click **New +** > **Blueprint**.
2. Connect your repository. Render will automatically read `render.yaml` and provision the service.

*(Note: `opencv-python-headless` is included in `requirements.txt` to ensure smooth container builds on Render's Debian/Linux images without missing GUI libraries).*

### Important: Indian Gateway Cloud Geo-Blocking
The Indian National Informatics Centre (NIC) firewalls running on `services.ecourts.gov.in` strictly block or drop traffic coming from foreign cloud datacenters (including Render's US and Frankfurt regions).

If you deploy to Render, you **must route outbound eCourts requests through an Indian proxy** or deploy in an Indian cloud region (AWS Mumbai `ap-south-1`, GCP Mumbai, etc.):
1. In the **Render Dashboard**, navigate to your Web Service > **Environment**.
2. Add an environment variable:
   - **Key**: `ECOURT_PROXY`
   - **Value**: `http://username:password@indian-proxy-ip:port` *(or `socks5://...`)*
3. Click **Save Changes**. The service will automatically route all eCourts requests through your Indian proxy.

---

## CLI Usage

### Interactive Mode
```bash
python main.py
```
```text
Enter 16-digit CNR Number: <YOUR_16_DIGIT_CNR>
```

### Direct CNR Search with Terminal Tables
```bash
python main.py --cnr <YOUR_16_DIGIT_CNR> --format table
```

### Export as JSON
```bash
python main.py --cnr <YOUR_16_DIGIT_CNR> --format json --output result.json
```

---

## Programmatic Python API

```python
from ecourt import ECourtScraper

scraper = ECourtScraper()
result = scraper.search_case("<YOUR_16_DIGIT_CNR>")

print("Court:", result.court_name)
print("Filing Number:", result.case_details.filing_number)
print("Case Stage:", result.case_status.case_stage)
print("Next Hearing Date:", result.case_status.next_hearing_date)

for hearing in result.case_history:
    print(f"Date: {hearing.business_on_date} -> Next: {hearing.hearing_date} ({hearing.purpose_of_hearing})")

# Export as dictionary or JSON
json_output = result.model_dump_json(indent=2)
```

---

## Running Tests

```bash
python tests/test_parser.py
```
