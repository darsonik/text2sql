# text2sql

A minimal scaffold for a Text-to-SQL project using LangGraph for orchestration
and LlamaIndex for retrieval. This repository contains initial placeholders
for modules, example scripts, and docs; implementation will be added later.

## Quick start

1. Create a Python virtual environment and install dependencies:

```cmd
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

2. Configure `src/text2sql/config/config.yaml` with API keys and model names.
3. See `examples/text2sql_demo.py` for how the pieces will connect.

## Project structure

- `src/text2sql/` — package source
- `src/text2sql/agents` — LangGraph flow definitions
- `src/text2sql/retrieval` — LlamaIndex connectors
- `examples/` — small example scripts and sample data
- `notebooks/` — demo notebook
- `tests/` — basic unit tests

## Next steps

- Implement retrieval connector (LlamaIndex)
- Create LangGraph flows to orchestrate the retrieval + LLM prompt steps
- Add integration tests and example workflows
