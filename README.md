# LogSense --- AI-Powered Log Analytics & Incident Intelligence

LogSense is a production-oriented AI/ML log analytics platform for
detecting anomalous operational behavior, correlating related log
signals into incidents, investigating evidence, and generating
evidence-grounded incident summaries.

The platform combines classical unsupervised anomaly detection,
deep-learning reconstruction error, density-based analysis, incident
correlation, interactive visualization, and an optional Gemini-powered
AI assistant.

------------------------------------------------------------------------

## 1. Key Capabilities

### Multi-model anomaly detection

LogSense currently compares three complementary anomaly detectors:

1.  **Autoencoder --- Primary Model**
    -   Learns normal patterns from numerical log features.
    -   Uses reconstruction error as the anomaly score.
    -   The primary dashboard field `is_anomaly` is based on the
        Autoencoder.
    -   The Overview anomaly count therefore represents Autoencoder
        anomalies.
2.  **Isolation Forest**
    -   Provides a scalable classical unsupervised baseline.
    -   Trained on a bounded representative sample.
    -   Scores the complete dataset.
3.  **HDBSCAN**
    -   Performs density-based behavioral clustering.
    -   Uses PCA and a representative sample to keep the dashboard
        responsive.
    -   Full-dataset scoring is based on distance to discovered cluster
        centroids.
    -   The dashboard therefore describes this as an **HDBSCAN-based
        density anomaly score**, not an exact full-dataset HDBSCAN
        score.

### 2-of-3 anomaly consensus

The Anomalies page also provides a consensus detector:

``` text
Isolation Forest
       +
Autoencoder
       +
HDBSCAN
       |
       v
2-of-3 consensus
```

A record is considered a high-confidence consensus anomaly when at least
two of the three models flag it.

### Incident intelligence

Operational signals are correlated into incident candidates using:

-   Autoencoder anomaly signals
-   Severity/error/failure signals
-   Timestamp proximity
-   Component continuity

Incident correlation is intended to identify related operational
activity. It does not claim definitive root cause.

### AI Incident Assistant

The optional Gemini-powered assistant generates an evidence-grounded
incident summary from:

-   Incident metadata
-   Selected incident-window log evidence
-   Component information
-   Message types
-   Severity
-   Primary anomaly signal

The AI assistant is decision support. Engineers should review the
underlying evidence before taking operational action.

------------------------------------------------------------------------

# 2. Architecture

``` text
                         processed_logs.jsonl
                                  |
                                  v
                           Log Loader
                                  |
                                  v
                         Feature Extraction
                                  |
                    +-------------+-------------+
                    |                           |
                    v                           v
             Severity Signals           Numeric Features
                                                |
                                                v
                                      Standardized Features
                                                |
                         +----------------------+----------------------+
                         |                      |                      |
                         v                      v                      v
                    Autoencoder         Isolation Forest          HDBSCAN
                    PRIMARY MODEL             |                      |
                         |                    |                      |
                         +--------------------+----------------------+
                                              |
                                              v
                                      Model Comparison
                                              |
                                              v
                                       2-of-3 Consensus
                                              |
                                              v
                                      Incident Correlation
                                              |
                         +--------------------+--------------------+
                         |                                         |
                         v                                         v
                  Streamlit Dashboard                         Flask REST API
                         |
                         v
                  AI Incident Assistant
                         |
                         v
                  Gemini / LiteLLM
```

------------------------------------------------------------------------

# 3. Project Structure

``` text
AI-powered-Log-Analytics-Platform/
│
├── app/
│   └── main.py
│
├── api/
│   └── server.py
│
├── src/
│   ├── loader.py
│   ├── features.py
│   ├── anomaly.py
│   ├── incidents.py
│   ├── insights.py
│   └── charts.py
│
├── scripts/
│   ├── validate_dataset.py
│   └── check_environment.py
│
├── tests/
│   ├── test_features.py
│   └── test_incidents.py
│
├── data/
│   └── processed_logs.jsonl
│
├── .streamlit/
│   └── config.toml
│
├── .env
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

------------------------------------------------------------------------

# 4. System Requirements

Recommended:

-   Python **3.11 or 3.12**
-   Git
-   8 GB+ RAM recommended for the supplied large dataset
-   Internet connection for installing Python packages
-   Gemini API key only if AI summaries are required

For the full 253k+ log dataset, more RAM can improve performance.

------------------------------------------------------------------------

# 5. Installation --- Windows

Open PowerShell in the project directory.

## Step 1 --- Create the virtual environment

``` powershell
python -m venv .venv
```

Activate it:

``` powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, you can run the environment's Python
directly without activating it:

``` powershell
.\.venv\Scripts\python.exe --version
```

------------------------------------------------------------------------

## Step 2 --- Verify Python

``` powershell
python --version
python -c "import sys; print(sys.executable)"
```

You should see the Python executable inside:

``` text
...\AI-powered-Log-Analytics-Platform\.venv\Scripts\python.exe
```

------------------------------------------------------------------------

## Step 3 --- Repair pip if necessary

If you see:

``` text
No module named pip
```

run:

``` powershell
python -m ensurepip --upgrade
python -m pip install --upgrade pip
```

Verify:

``` powershell
python -m pip --version
```

------------------------------------------------------------------------

## Step 4 --- Install project dependencies

``` powershell
python -m pip install -r requirements.txt
```

The project requires PyTorch for the Autoencoder.

If PyTorch was not installed successfully:

``` powershell
python -m pip install --upgrade torch
```

Verify:

``` powershell
python -c "import torch; print('PyTorch:', torch.__version__); print('CUDA available:', torch.cuda.is_available())"
```

CPU execution is supported. CUDA is optional.

------------------------------------------------------------------------

## Step 5 --- Verify HDBSCAN support

The project uses the scikit-learn HDBSCAN implementation.

Run:

``` powershell
python -c "import sklearn; from sklearn.cluster import HDBSCAN; print('scikit-learn:', sklearn.__version__); print('HDBSCAN: OK')"
```

If the import fails, upgrade scikit-learn:

``` powershell
python -m pip install --upgrade scikit-learn
```

Then verify again.

------------------------------------------------------------------------

# 6. Installation --- macOS / Linux

Create the virtual environment:

``` bash
python3 -m venv .venv
```

Activate:

``` bash
source .venv/bin/activate
```

Upgrade pip:

``` bash
python -m ensurepip --upgrade
python -m pip install --upgrade pip
```

Install dependencies:

``` bash
python -m pip install -r requirements.txt
```

Install/repair PyTorch if required:

``` bash
python -m pip install --upgrade torch
```

Verify:

``` bash
python -c "import torch; print('PyTorch:', torch.__version__); print('CUDA available:', torch.cuda.is_available())"
```

Verify HDBSCAN:

``` bash
python -c "import sklearn; from sklearn.cluster import HDBSCAN; print('scikit-learn:', sklearn.__version__); print('HDBSCAN: OK')"
```

------------------------------------------------------------------------

# 7. Dataset Setup

The expected default dataset path is:

``` text
data/processed_logs.jsonl
```

Copy the processed dataset into:

``` text
AI-powered-Log-Analytics-Platform/
└── data/
    └── processed_logs.jsonl
```

Alternatively, configure another path with the `LOG_FILE` environment
variable.

### Windows PowerShell

``` powershell
$env:LOG_FILE="C:\path\to\processed_logs.jsonl"
```

### macOS / Linux

``` bash
export LOG_FILE="/path/to/processed_logs.jsonl"
```

------------------------------------------------------------------------

# 8. Dataset Validation

Validate the processed JSONL dataset:

``` powershell
python scripts/validate_dataset.py data/processed_logs.jsonl
```

The dataset is expected to contain fields such as:

``` text
event_id
timestamp
normalized_timestamp
ingestion_timestamp
component
process_id
message
parsed_message_type
extracted_metrics
source
line_number
raw_message
quality_flags
metadata
```

The supplied dataset used during development contains approximately
**253k JSONL records**.

Do not commit the full operational dataset to GitHub if it contains
sensitive, proprietary, or personally identifiable information.

------------------------------------------------------------------------

# 9. Environment Verification

Before starting the application, run:

``` powershell
python scripts/check_environment.py
```

This verifies:

-   Python environment
-   PyTorch
-   CUDA availability
-   scikit-learn
-   HDBSCAN availability

A healthy environment should report something similar to:

``` text
Python: 3.12.x
PyTorch: ...
CUDA available: False
scikit-learn: ...
HDBSCAN: available via sklearn.cluster.HDBSCAN
```

CUDA being `False` is acceptable. The Autoencoder can run on CPU.

------------------------------------------------------------------------

# 10. Gemini AI Assistant Setup

Gemini is optional.

The core dashboard and anomaly detection pipeline can operate without a
Gemini API key.

Create a `.env` file in the project root.

Example:

``` env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini/gemini-3.6-flash
LOG_FILE=data/processed_logs.jsonl
```

Do not commit `.env` to Git.

The recommended `.gitignore` should include:

``` text
.env
.venv/
__pycache__/
*.pyc
```

The application reads the Gemini model from:

``` python
os.getenv(
    "GEMINI_MODEL",
    "gemini/gemini-3.6-flash",
)
```

If `GEMINI_MODEL` is not defined, the default Gemini 3.6 Flash model is
used.

------------------------------------------------------------------------

# 11. Start the Streamlit Dashboard

From the project root:

``` powershell
python -m streamlit run app/main.py
```

Streamlit will provide a local address, normally similar to:

``` text
http://localhost:8501
```

Open that address in your browser.

------------------------------------------------------------------------

# 12. Dashboard Sections

## Overview

Displays:

-   Processed logs
-   Primary anomaly count
-   Error/failure signals
-   Correlated incidents
-   Top affected components
-   Overview charts

### Important

The Overview `Anomalies` metric uses:

``` text
is_anomaly
```

and `is_anomaly` is now the **Autoencoder anomaly signal**.

Therefore:

``` text
Overview Anomalies = Autoencoder anomalies
```

------------------------------------------------------------------------

## Log Explorer

Provides:

-   Message search
-   Component filtering
-   Message-type filtering
-   Severity filtering
-   Anomaly score inspection
-   Anomaly flag inspection
-   Paginated/limited log display

------------------------------------------------------------------------

## Anomalies

The Anomalies page compares:

### Isolation Forest

Classical unsupervised anomaly detection using isolation-based scoring.

### Autoencoder

Primary deep-learning detector using reconstruction error.

Higher reconstruction error means the record differs more strongly from
the patterns learned by the Autoencoder.

### HDBSCAN

Density-based behavioral analysis.

The implementation:

1.  Standardizes features.
2.  Applies PCA.
3.  Fits HDBSCAN on a representative sample.
4.  Discovers behavioral clusters.
5.  Calculates full-dataset distances to discovered cluster centroids.
6.  Flags high-distance records as HDBSCAN-based density anomalies.

### 2-of-3 Consensus

A record is a consensus anomaly when at least two of:

``` text
Isolation Forest
Autoencoder
HDBSCAN
```

flag it.

------------------------------------------------------------------------

# 13. Anomaly Features

The anomaly pipeline uses available numeric features such as:

``` text
message_length
word_count
severity_score
hour
minute
second
```

It also includes available numeric extracted metric columns beginning
with:

``` text
metric_
```

Up to the first eight suitable numeric metric columns are included.

Features are cleaned and standardized before model execution.

------------------------------------------------------------------------

# 14. Model Sampling

The full dataset does not need to be used to train every model.

Current configuration:

``` python
MODEL_SAMPLE_SIZE = 30_000
HDBSCAN_SAMPLE_SIZE = 15_000
BATCH_SIZE = 1024
AUTOENCODER_EPOCHS = 8
RANDOM_STATE = 42
```

### Autoencoder

The Autoencoder trains on up to:

``` text
30,000 records
```

and then calculates reconstruction error across the full dataset.

### Isolation Forest

Isolation Forest trains on up to:

``` text
30,000 records
```

and scores the full dataset.

### HDBSCAN

HDBSCAN fits on up to:

``` text
15,000 records
```

with PCA dimensionality reduction.

This design keeps the application practical for the supplied large
dataset.

------------------------------------------------------------------------

# 15. Anomaly Evaluation

Because the dataset does not contain ground-truth anomaly labels,
traditional supervised metrics such as:

``` text
Accuracy
Precision
Recall
F1
```

are not scientifically valid as direct anomaly-detector performance
measures.

Instead, the dashboard reports:

-   Anomaly count
-   Anomaly rate
-   Alignment with severity/error/failure rules
-   Pairwise model agreement
-   2-of-3 consensus
-   HDBSCAN cluster count
-   HDBSCAN sample noise rate
-   HDBSCAN silhouette score
-   Model score distributions

If labeled incident/anomaly data becomes available, supervised
evaluation can be added later.

------------------------------------------------------------------------

# 16. Incident Correlation

Incident candidates are built from operational signals.

The primary anomaly signal is:

``` text
Autoencoder anomaly
```

and operational severity signals are also retained.

Conceptually:

``` python
is_signal = is_anomaly | (severity_score >= 2)
```

Because:

``` text
is_anomaly = Autoencoder anomaly
```

incident correlation now incorporates Autoencoder anomalies.

The incident engine groups related operational signals using timestamp
proximity and component continuity.

Incidents should be treated as **correlated operational candidates**,
not definitive root-cause determinations.

------------------------------------------------------------------------

# 17. AI Incident Assistant

The AI Assistant is available when:

``` env
GEMINI_API_KEY=...
```

is configured.

The assistant receives:

-   Incident ID
-   Severity
-   Primary component
-   Incident start/end
-   Event count
-   Selected evidence records

The model is instructed to:

-   Use only supplied evidence
-   Avoid inventing events
-   Avoid inventing metrics
-   Avoid inventing root causes
-   Clearly label hypotheses
-   Provide investigation steps
-   Explain confidence and limitations

The AI output is evidence-grounded decision support.

------------------------------------------------------------------------

# 18. Running the Flask API

Start the API with:

``` powershell
python api/server.py
```

The API exposes endpoints such as:

``` text
GET /api/health
GET /api/summary
GET /api/incidents
GET /api/logs?limit=100
```

Use the API for programmatic access to LogSense analytics.

------------------------------------------------------------------------

# 19. Running Tests

Run:

``` powershell
pytest -q
```

The test suite currently covers core feature and incident functionality.

For syntax validation of individual modules:

``` powershell
python -m py_compile src/anomaly.py
python -m py_compile src/insights.py
python -m py_compile app/main.py
```

------------------------------------------------------------------------

# 20. Common Problems

## PyTorch import error

If you see:

``` text
AttributeError: 'NoneType' object has no attribute 'Module'
```

the PyTorch import failed.

Run:

``` powershell
python -m pip install --upgrade pip
python -m pip install --upgrade torch
```

Then verify:

``` powershell
python -c "import torch; print(torch.__version__)"
```

Restart Streamlit afterward.

------------------------------------------------------------------------

## Virtual environment has no pip

If you see:

``` text
No module named pip
```

run:

``` powershell
python -m ensurepip --upgrade
python -m pip install --upgrade pip
```

Then:

``` powershell
python -m pip install -r requirements.txt
```

------------------------------------------------------------------------

## HDBSCAN import error

If:

``` python
from sklearn.cluster import HDBSCAN
```

fails, upgrade scikit-learn:

``` powershell
python -m pip install --upgrade scikit-learn
```

Then verify:

``` powershell
python -c "from sklearn.cluster import HDBSCAN; print('HDBSCAN OK')"
```

------------------------------------------------------------------------

## Gemini API error

If Gemini reports that a model is unavailable, check `.env`:

``` env
GEMINI_MODEL=gemini/gemini-3.6-flash
```

Also verify:

``` env
GEMINI_API_KEY=your_key
```

Restart Streamlit after changing `.env`.

------------------------------------------------------------------------

## Gemini sampling parameter warnings

Do not pass deprecated Gemini 3.x sampling parameters such as:

``` python
temperature=0.2
top_p=0.9
top_k=...
```

Use:

``` python
response = completion(
    model=GEMINI_MODEL,
    messages=messages,
    api_key=api_key,
)
```

------------------------------------------------------------------------

## Streamlit DataFrame hashing warning

You may see:

``` text
Streamlit's default hashing method failed for a pandas DataFrame,
so it is falling back to pickling the object.
Original error: unhashable type: 'dict'
```

This is caused by object/dictionary values in the processed log
DataFrame, such as metadata or extracted metrics.

It is a **warning, not an anomaly-model failure**.

Streamlit falls back to pickling the object.

For a large dataset, caching strategy can be optimized later to avoid
repeated serialization overhead.

------------------------------------------------------------------------

## Streamlit `use_container_width` warning

Newer Streamlit versions prefer:

``` python
width="stretch"
```

instead of:

``` python
use_container_width=True
```

For example:

``` python
st.dataframe(
    df,
    width="stretch",
)
```

and:

``` python
st.button(
    "Generate",
    width="stretch",
)
```

------------------------------------------------------------------------

# 21. Performance Considerations

The platform is designed to work with large processed-log datasets
without fitting every expensive model over the entire dataset.

Performance is improved through:

-   Representative model training samples
-   Autoencoder batch processing
-   PCA before HDBSCAN
-   HDBSCAN sample-based clustering
-   Chunked nearest-centroid distance calculations
-   Streamlit caching
-   Limited dashboard evidence display

For production-scale data beyond the current dataset size, move
ingestion and storage into dedicated infrastructure rather than loading
the entire JSONL file into memory.

------------------------------------------------------------------------

# 22. Security and Data Handling

Never commit:

``` text
.env
processed_logs.jsonl
```

if they contain secrets, customer information, proprietary logs, tokens,
credentials, or other sensitive information.

Use:

``` text
.env.example
```

for documenting required environment variables without exposing real
credentials.

The Gemini assistant should receive only the minimum incident metadata
and evidence necessary for the requested analysis.

------------------------------------------------------------------------

# 23. Production Architecture --- Future Direction

The current project is designed as a production-oriented prototype.

A production deployment could evolve toward:

``` text
Log Sources
    |
    v
Message Queue / Streaming
    |
    v
Log Ingestion Workers
    |
    +--------------------+
    |                    |
    v                    v
OpenSearch/Elastic    PostgreSQL/TimescaleDB
    |                    |
    +---------+----------+
              |
              v
       Feature Pipeline
              |
       +------+------+
       |             |
       v             v
  ML Detection    Incident Engine
       |             |
       +------+------+
              |
              v
        API / Services
              |
       +------+------+
       |             |
       v             v
  Streamlit UI    AI Assistant
                     |
                     v
                  Gemini
```

Potential production upgrades include:

-   OpenSearch / Elasticsearch for high-volume log search
-   PostgreSQL / TimescaleDB for incident persistence
-   Redis for caching
-   Background ingestion workers
-   Prometheus / Grafana observability
-   Distributed tracing
-   Request/trace-ID based incident correlation
-   Persistent model artifacts
-   Scheduled model retraining
-   Ground-truth anomaly labels
-   Automated anomaly evaluation datasets
-   Automated RCA evaluation
-   Authentication and authorization
-   Docker/Kubernetes deployment
-   CI/CD
-   Structured application logging
-   Model and prompt versioning

------------------------------------------------------------------------

# 24. Recommended Development Workflow

After cloning the repository:

``` powershell
git clone <repository-url>
cd AI-powered-Log-Analytics-Platform
```

Create environment:

``` powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install:

``` powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Verify:

``` powershell
python scripts/check_environment.py
```

Validate data:

``` powershell
python scripts/validate_dataset.py data/processed_logs.jsonl
```

Run tests:

``` powershell
pytest -q
```

Start dashboard:

``` powershell
python -m streamlit run app/main.py
```

------------------------------------------------------------------------

# 25. Technology Stack

### Application

-   Python
-   Streamlit
-   Flask

### Data Processing

-   Pandas
-   NumPy

### Machine Learning

-   scikit-learn
-   Isolation Forest
-   PCA
-   HDBSCAN
-   StandardScaler

### Deep Learning

-   PyTorch
-   Feed-forward Autoencoder

### AI / GenAI

-   LiteLLM
-   Google Gemini
-   Gemini 3.6 Flash

### Visualization

-   Plotly
-   Streamlit charts

### Testing

-   pytest

### Deployment

-   Docker
-   Docker Compose

------------------------------------------------------------------------

# 26. Design Principles

LogSense follows several principles:

### Evidence first

Operational conclusions should be grounded in actual log evidence.

### Multiple detection methods

No single anomaly detector is treated as universally correct.

### Primary + supporting models

The Autoencoder is the primary anomaly signal while Isolation Forest and
HDBSCAN provide complementary views.

### Consensus over blind confidence

The 2-of-3 ensemble provides a stronger signal when multiple independent
detectors agree.

### No fake accuracy

Without ground-truth labels, the system does not claim traditional
supervised accuracy metrics.

### Human-in-the-loop AI

AI-generated incident analysis is decision support and should be
reviewed by engineers.

### Scalable by sampling

Expensive ML operations use representative samples and batch processing
where appropriate.

------------------------------------------------------------------------

# 27. Current Project Status

LogSense currently provides:

-   Processed JSONL log ingestion
-   Feature engineering
-   Severity inference
-   Autoencoder anomaly detection
-   Isolation Forest anomaly detection
-   HDBSCAN-based density anomaly detection
-   2-of-3 anomaly consensus
-   Model comparison and evaluation views
-   Incident correlation
-   Incident evidence exploration
-   Streamlit dashboard
-   Flask REST API
-   Optional Gemini-powered incident summaries
-   Dataset validation
-   Environment validation
-   Automated tests

The separate **Grounded Operational Insights report** component has been
removed from the current version. The AI Assistant currently focuses on
evidence-grounded incident summaries.

------------------------------------------------------------------------


## Quick Start

For a new Windows environment:

``` powershell
git clone <repository-url>
cd AI-powered-Log-Analytics-Platform

python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m ensurepip --upgrade
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python scripts/check_environment.py
python scripts/validate_dataset.py data/processed_logs.jsonl

pytest -q

python -m streamlit run app/main.py
```

For Gemini:

``` env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini/gemini-3.6-flash
```

Then restart Streamlit.

**LogSense --- detect abnormal behavior, correlate incidents,
investigate evidence, and turn operational logs into actionable
intelligence.**
