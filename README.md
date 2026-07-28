# FireworksAI

## Milestone 2 – Content Ingestion System

This milestone builds a system that reads an educational Markdown
lesson and converts it into a structured `Script` object for use by
future AI modules. No audio, FFmpeg, YouTube, AI, or n8n logic is
included at this stage.

### Data Flow

```
content/phase01.md
        ↓
app/utils/file_loader.py      (reads raw text)
        ↓
app/services/markdown_parser.py (parses text into a Script)
        ↓
app/models/script.py            (defines Section, Metadata, Script)
        ↓
app/pipeline/content_pipeline.py (orchestrates the above)
        ↓
Script object returned
```

### Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Usage

```python
from pathlib import Path
from app.pipeline.content_pipeline import run_content_pipeline

script = run_content_pipeline(Path("content/phase01.md"))
print(script.metadata.title)
```

### Running Tests

```bash
pytest tests/ -v
```
## Milestone 2

Implemented:

- Script data model
- Markdown file loader
- Markdown parser
- Content pipeline
- Unit tests

Status: ✅ Completed
