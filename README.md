# Knowledge Architect

> A Python framework for building durable, interoperable, and semantically rich knowledge systems.

Knowledge Architect is an open-source framework for representing, transforming, and synchronizing knowledge while preserving semantic identity, provenance, and structural consistency.

At its core is the **Knowledge Intermediate Representation (KIR)**, a canonical model designed to remain independent of storage technologies, user interfaces, and external platforms. Integrations such as Notion are treated as **projections** of the KIR rather than the source of truth.

---

## Why Knowledge Architect?

Most knowledge tools are tightly coupled to a specific platform or storage model.

Knowledge Architect separates the **domain model** from its representations, allowing the same knowledge to be:

- stored locally;
- synchronized with external platforms;
- transformed into different representations;
- versioned and evolved without losing semantic identity.

The framework is designed around explicit semantic transformations instead of ad hoc data conversions.

---

## Core Principles

- **Canonical Representation**
  - The KIR is always the source of truth.

- **Immutable Transformations**
  - Structural changes produce new semantic identities while preserving provenance.

- **Explicit Semantics**
  - Every transformation records how knowledge changed.

- **Platform Independence**
  - External systems are projections of the canonical model.

- **Extensible Architecture**
  - New repositories and integrations can be added without changing the core domain.

---

## Architecture

```
                Knowledge Architect
                        │
                        ▼
             Knowledge Intermediate
                Representation (KIR)
                        │
        ┌───────────────┴───────────────┐
        ▼                               ▼
 Local Repository              Notion Repository
                                        │
                                        ▼
                                   Notion API
```

The core domain never depends on external platforms.

Repositories are responsible for persistence and synchronization while preserving the semantics defined by the KIR.

---

## Features

- Canonical Knowledge Intermediate Representation (KIR)
- Semantic knowledge model
- Immutable transformation model
- Provenance tracking
- Repository abstraction
- Synchronization framework
- Notion integration
- Comprehensive unit tests
- Integration tests
- GitHub Actions CI

---

## Project Structure

```
knowledge-architect/
├── docs/
├── scripts/
├── src/
│   └── knowledge_architect/
├── tests/
└── pyproject.toml
```

---

## Installation

```bash
git clone https://github.com/LeonardoRufo/knowledge-architect.git

cd knowledge-architect

python -m venv .venv

source .venv/bin/activate

pip install -e .
```

---

## Running Tests

Unit tests:

```bash
pytest --ignore=tests/integration
```

Integration tests:

```bash
pytest tests/integration/notion -m notion
```

---

## Notion Integration

Knowledge Architect includes an optional integration with Notion.

The integration synchronizes Knowledge Units while keeping the KIR as the canonical representation.

The integration is organized into independent components:

- Client
- Mapper
- Repository
- Synchronizer

See:

```
docs/integrations/notion.md
```

---

## Roadmap

### Completed

- KIR Core
- Semantic model
- Transformation model
- Repository abstraction
- Notion integration
- Unit tests
- Integration tests
- Continuous Integration

### Planned

- Additional repository implementations
- Advanced synchronization policies
- Visualization tools
- Knowledge graph exploration

---

## Contributing

Contributions are welcome.

Please open an issue before proposing large architectural changes so they can be discussed within the project's design principles.

---

## License

MIT License
