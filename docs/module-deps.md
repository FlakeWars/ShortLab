# Mapa zaleznosci modulow

```mermaid
flowchart LR
  %% Moduly logiki i decyzji
  GEN[Generator pomyslow]
  GATE[Idea Gate]
  EMB[Embedding Service]

  %% Pipeline i render
  PIPE[Pipeline jobs-queue]
  RENDER[Renderer]
  QC[QC / Review]
  PUB[Publikacja]
  MET[Metryki / Analiza]

  %% UI operacyjne
  UI[Panel operacyjny UI]

  %% Infra / storage
  DB[(Postgres)]
  OBJ[(MinIO / storage)]

  %% Zaleznosci miedzy modulami
  GEN --> GATE
  GATE <---> EMB
  GATE --> PIPE

  PIPE --> RENDER
  RENDER --> OBJ
  RENDER --> DB

  PIPE --> QC
  QC --> DB
  QC --> PUB
  PUB --> MET
  MET --> DB

  UI --- PIPE
  UI --- DB
  UI --- OBJ
  UI --- GATE
  UI --- QC
  UI --- MET

  EMB --> DB
  GEN --> DB
  GATE --> DB
```

## Uwagi
- Idea Gate jest opcjonalny w pipeline (tryb auto lub wybor operatora).
- Embedding Service jest zaleznoscia Idea Gate i Generatora (deduplikacja, podobienstwo).
- UI to modul przekrojowy: podglad statusow, metadanych i artefaktow z DB/MinIO.
