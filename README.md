# 🚀 FireworksAI

> **An AI-powered, production-grade YouTube content automation pipeline built with Clean Architecture and Python.**

FireworksAI transforms a structured Markdown script into a complete, YouTube-ready content package. The system follows a modular, pipeline-based architecture where every component has a single responsibility, making it scalable, testable, and easy to maintain.

---

# 🎯 Project Goal

The objective of FireworksAI is to automate the complete YouTube content creation workflow.

Instead of manually creating narration, subtitles, videos, thumbnails, and metadata, users simply write a Markdown lesson.

FireworksAI automatically converts it into:

- 🎙 AI-generated narration
- 🎬 Video with synchronized subtitles
- 🖼 Thumbnail plan and assets
- 📝 SEO-optimized YouTube metadata
- 📦 Complete publish-ready package

---

# 🏗 Architecture

```
Markdown Script
       │
       ▼
Milestone 2
Content Ingestion
       │
       ▼
Structured Script
       │
       ▼
Milestone 3
Audio Narration
       │
       ▼
Narrated Audio
       │
       ▼
Milestone 4
Video Assembly
       │
       ▼
Final MP4
       │
       ▼
Milestone 5
YouTube Publishing
       │
       ▼
Publish Package
```

The project follows **Clean Architecture** principles:

- Models
- Services
- Pipelines
- Dependency Injection
- Protocol-based abstractions
- Extensive Unit Testing

---

# 📂 Project Structure

```
FireworksAI/

app/
│
├── core/
│
├── models/
│
├── services/
│
├── pipeline/
│
├── utils/
│
└── exceptions.py

content/

tests/

docs/

requirements.txt
README.md
```

---

# 🚀 Completed Milestones

## ✅ Milestone 1 — Project Foundation

- Project structure
- Configuration management
- Logging
- Exception hierarchy
- Testing framework

---

## ✅ Milestone 2 — Content Ingestion

Reads Markdown lessons and converts them into structured `Script` objects.

### Components

- Script data models
- Markdown parser
- File loader
- Content pipeline

---

## ✅ Milestone 3 — Audio Narration Pipeline

Generates narrated audio from structured lessons.

### Components

- Audio models
- TTS abstraction
- Audio generation
- Audio pipeline
- Validation

---

## ✅ Milestone 4 — Video Assembly Pipeline

Creates synchronized educational videos.

### Components

- Image loader
- Subtitle builder
- FFmpeg wrapper
- Video validator
- Video assembly pipeline

---

## 🚧 Milestone 5 — YouTube Publishing (In Progress)

Will generate:

- SEO title
- Description
- Tags
- Chapters
- Thumbnail planning
- Thumbnail generation
- Publish package

---

# 🔄 Complete Workflow

```
Markdown Lesson
        │
        ▼
Content Pipeline
        │
        ▼
Audio Pipeline
        │
        ▼
Video Pipeline
        │
        ▼
Publishing Pipeline
        │
        ▼
YouTube Ready Package
```

---

# 🛠 Tech Stack

## Language

- Python 3.12

## AI

- Google Gemini API

## Media

- FFmpeg
- FFprobe

## Parsing

- Markdown
- YAML

## Testing

- Pytest

## Architecture

- Clean Architecture
- SOLID Principles
- Dependency Injection
- Protocols
- Dataclasses

---

# ⚙ Installation

Clone the repository:

```bash
git clone https://github.com/SUNDARKARTHICK/FireworksAI.git

cd FireworksAI
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it:

### Windows

```bash
.venv\Scripts\activate
```

### Linux/macOS

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# ▶ Running the Project

Current pipeline:

```python
from pathlib import Path

from app.pipeline.content_pipeline import run_content_pipeline

script = run_content_pipeline(
    Path("content/phase01.md")
)

print(script.metadata.title)
```

Future releases will provide a single command:

```bash
python main.py
```

which will automatically generate the complete YouTube publishing package.

---

# ✅ Running Tests

Execute the full test suite:

```bash
python -m pytest
```

Current Status:

```
254 tests passed
```

---

# 📌 Design Principles

- Single Responsibility Principle
- Dependency Injection
- Immutable Models
- Protocol-based Interfaces
- Pure Services
- Thin Pipelines
- High Test Coverage
- Modular Components

---

# 📈 Roadmap

- ✅ Foundation
- ✅ Content Ingestion
- ✅ Audio Narration
- ✅ Video Assembly
- 🚧 YouTube Publishing
- ⏳ AI Thumbnail Generation
- ⏳ Automated YouTube Upload
- ⏳ Analytics & Reporting

---

# 👨‍💻 Author

**Sundar Karthick M**

AI Engineer • Python Developer • LLM Engineer • Agentic AI Developer

GitHub:
https://github.com/SUNDARKARTHICK

---

# ⭐ Project Status

**Current Version:** `v0.4.0`

**Milestones Completed:** 4 / 5

**Test Status:** ✅ 254 / 254 Passing

**Architecture:** Production-ready

**License:** MIT
