# FireworksAI

Automates educational YouTube video creation for the fireworks industry.

## Milestone 1 — Project Foundation

This milestone provides only the project foundation:

- Environment-based configuration loading (`app/core/config.py`)
- Immutable settings model (`app/core/settings.py`)
- Logging configuration (`app/core/logging_config.py`)
- Minimal workflow entry point (`app/pipeline/workflow.py`)
- Custom exceptions (`app/exceptions.py`)

No domain logic (Markdown parsing, TTS, FFmpeg, AI, YouTube, n8n) is
implemented yet — that is reserved for future milestones.

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Run

```bash
python -m app.pipeline.workflow
```

## Test

```bash
python -m pytest
```
