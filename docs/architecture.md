# Architecture

This project will use the following high-level design:

- Retrieval: `LlamaIndex` will build an index over schema and metadata
  for fast retrieval of relevant schema snippets.
- Orchestration: `LangGraph` will be used to define flows that combine
  retrieval, prompt engineering, and LLM calls to produce SQL.
- CLI / Notebook: Examples will demonstrate how to ingest schema data,
  run retrieval, and call agent flows to get SQL from natural language.

Components are currently placeholders and will be implemented later.
