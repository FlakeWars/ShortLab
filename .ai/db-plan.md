0. Migracja kanoniczna
- Jedyna migracja schematu: `migrations/versions/9f3a2c7d8b1e_create_core_domain_schema.py`
- Legacy migracje usunięte; dane testowe można odtwarzać przez `make db-migrate`

1. Lista tabel z ich kolumnami, typami danych i ograniczeniami

**user_account**
- id UUID PK DEFAULT gen_random_uuid()
- email CITEXT UNIQUE NOT NULL
- password_hash TEXT NOT NULL
- is_active BOOLEAN NOT NULL DEFAULT true
- last_login_at TIMESTAMPTZ
- created_at TIMESTAMPTZ NOT NULL
- updated_at TIMESTAMPTZ NOT NULL

**dsl_version**
- id UUID PK DEFAULT gen_random_uuid()
- version TEXT UNIQUE NOT NULL
- schema_json JSONB NOT NULL
- created_at TIMESTAMPTZ NOT NULL

**design_system_version**
- id UUID PK DEFAULT gen_random_uuid()
- version TEXT UNIQUE NOT NULL
- meta JSONB
- created_at TIMESTAMPTZ NOT NULL

**idea_batch**
- id UUID PK DEFAULT gen_random_uuid()
- run_date DATE NOT NULL
- window_id TEXT NOT NULL
- source TEXT NOT NULL CHECK (source IN ('schedule','manual'))
- created_at TIMESTAMPTZ NOT NULL
- UNIQUE (run_date, window_id)

**idea_candidate**
- id UUID PK DEFAULT gen_random_uuid()
- idea_batch_id UUID NOT NULL REFERENCES idea_batch(id) ON DELETE CASCADE
- title TEXT NOT NULL
- summary TEXT
- what_to_expect TEXT
- preview TEXT
- generator_source TEXT NOT NULL CHECK (generator_source IN ('ai','fallback','manual'))
- similarity_status TEXT NOT NULL CHECK (similarity_status IN ('ok','too_similar','unknown'))
- status TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new','later','picked'))
- selected BOOLEAN NOT NULL DEFAULT false
- selected_by UUID REFERENCES user_account(id)
- selected_at TIMESTAMPTZ
- decision_by UUID REFERENCES user_account(id)
- decision_at TIMESTAMPTZ
- created_at TIMESTAMPTZ NOT NULL

**idea**
- id UUID PK DEFAULT gen_random_uuid()
- idea_candidate_id UUID REFERENCES idea_candidate(id) ON DELETE SET NULL
- title TEXT NOT NULL
- summary TEXT
- what_to_expect TEXT
- preview TEXT
- idea_hash TEXT
- created_at TIMESTAMPTZ NOT NULL

**idea_similarity**
- id UUID PK DEFAULT gen_random_uuid()
- idea_candidate_id UUID NOT NULL REFERENCES idea_candidate(id) ON DELETE CASCADE
- compared_idea_id UUID NOT NULL REFERENCES idea(id) ON DELETE CASCADE
- score NUMERIC(5,4) NOT NULL
- embedding_version TEXT
- created_at TIMESTAMPTZ NOT NULL
- UNIQUE (idea_candidate_id, compared_idea_id)

**idea_embedding**
- id UUID PK DEFAULT gen_random_uuid()
- idea_candidate_id UUID NOT NULL REFERENCES idea_candidate(id) ON DELETE CASCADE
- idea_id UUID REFERENCES idea(id) ON DELETE SET NULL
- provider TEXT NOT NULL
- model TEXT NOT NULL
- version TEXT NOT NULL
- vector JSONB NOT NULL
- created_at TIMESTAMPTZ NOT NULL
- UNIQUE (idea_candidate_id, version)

**animation**
- id UUID PK DEFAULT gen_random_uuid()
- animation_code TEXT UNIQUE NOT NULL
- idea_id UUID REFERENCES idea(id) ON DELETE SET NULL
- parent_animation_id UUID REFERENCES animation(id) ON DELETE SET NULL
- status TEXT NOT NULL CHECK (status IN ('draft','queued','running','review','accepted','rejected','published','archived'))
- pipeline_stage TEXT NOT NULL CHECK (pipeline_stage IN ('idea','render','qc','publish','metrics','done'))
- expires_at TIMESTAMPTZ
- soft_deleted_at TIMESTAMPTZ
- created_at TIMESTAMPTZ NOT NULL
- updated_at TIMESTAMPTZ NOT NULL

**render**
- id UUID PK DEFAULT gen_random_uuid()
- animation_id UUID NOT NULL REFERENCES animation(id) ON DELETE CASCADE
- source_render_id UUID REFERENCES render(id) ON DELETE SET NULL
- status TEXT NOT NULL CHECK (status IN ('queued','running','succeeded','failed'))
- seed BIGINT NOT NULL
- dsl_version_id UUID NOT NULL REFERENCES dsl_version(id)
- design_system_version_id UUID NOT NULL REFERENCES design_system_version(id)
- renderer_version TEXT NOT NULL
- duration_ms INTEGER NOT NULL CHECK (duration_ms >= 0)
- width INTEGER NOT NULL
- height INTEGER NOT NULL
- fps NUMERIC(6,3) NOT NULL
- params_json JSONB NOT NULL
- metadata_json JSONB
- created_at TIMESTAMPTZ NOT NULL
- started_at TIMESTAMPTZ
- finished_at TIMESTAMPTZ

**artifact**
- id UUID PK DEFAULT gen_random_uuid()
- render_id UUID NOT NULL REFERENCES render(id) ON DELETE CASCADE
- artifact_type TEXT NOT NULL CHECK (artifact_type IN ('video','preview','thumbnail','dsl','metadata','other'))
- storage_path TEXT NOT NULL
- checksum TEXT
- size_bytes BIGINT
- created_at TIMESTAMPTZ NOT NULL

**qc_checklist_version**
- id UUID PK DEFAULT gen_random_uuid()
- name TEXT NOT NULL
- version TEXT NOT NULL
- is_active BOOLEAN NOT NULL DEFAULT false
- created_at TIMESTAMPTZ NOT NULL
- UNIQUE (name, version)

**qc_checklist_item**
- id UUID PK DEFAULT gen_random_uuid()
- checklist_version_id UUID NOT NULL REFERENCES qc_checklist_version(id) ON DELETE CASCADE
- item_key TEXT NOT NULL
- description TEXT NOT NULL
- severity TEXT NOT NULL CHECK (severity IN ('hard','soft'))
- position INTEGER NOT NULL
- is_active BOOLEAN NOT NULL DEFAULT true
- UNIQUE (checklist_version_id, item_key)

**qc_decision**
- id UUID PK DEFAULT gen_random_uuid()
- animation_id UUID NOT NULL REFERENCES animation(id) ON DELETE CASCADE
- checklist_version_id UUID NOT NULL REFERENCES qc_checklist_version(id)
- result TEXT NOT NULL CHECK (result IN ('accepted','rejected','regenerate'))
- decision_payload JSONB
- notes TEXT
- decided_by UUID REFERENCES user_account(id)
- decided_at TIMESTAMPTZ NOT NULL
- created_at TIMESTAMPTZ NOT NULL

**publish_record**
- id UUID PK DEFAULT gen_random_uuid()
- render_id UUID NOT NULL REFERENCES render(id) ON DELETE CASCADE
- platform_type TEXT NOT NULL CHECK (platform_type IN ('youtube','tiktok'))
- status TEXT NOT NULL CHECK (status IN ('queued','uploading','published','failed','manual_confirmed'))
- content_id TEXT
- url TEXT
- scheduled_for TIMESTAMPTZ
- published_at TIMESTAMPTZ
- error_payload JSONB
- created_at TIMESTAMPTZ NOT NULL
- updated_at TIMESTAMPTZ NOT NULL
- UNIQUE (platform_type, content_id)

**metrics_pull_run**
- id UUID PK DEFAULT gen_random_uuid()
- platform_type TEXT NOT NULL CHECK (platform_type IN ('youtube','tiktok'))
- status TEXT NOT NULL CHECK (status IN ('queued','running','succeeded','failed'))
- source TEXT NOT NULL CHECK (source IN ('api','manual'))
- started_at TIMESTAMPTZ
- finished_at TIMESTAMPTZ
- error_payload JSONB
- created_at TIMESTAMPTZ NOT NULL

**metrics_daily**
- id UUID PK DEFAULT gen_random_uuid()
- platform_type TEXT NOT NULL CHECK (platform_type IN ('youtube','tiktok'))
- content_id TEXT NOT NULL
- publish_record_id UUID REFERENCES publish_record(id) ON DELETE SET NULL
- render_id UUID REFERENCES render(id) ON DELETE SET NULL
- date DATE NOT NULL
- views INTEGER NOT NULL DEFAULT 0
- likes INTEGER NOT NULL DEFAULT 0
- comments INTEGER NOT NULL DEFAULT 0
- shares INTEGER NOT NULL DEFAULT 0
- watch_time_seconds BIGINT NOT NULL DEFAULT 0
- avg_view_percentage NUMERIC(5,2)
- avg_view_duration_seconds INTEGER
- extra_metrics JSONB
- created_at TIMESTAMPTZ NOT NULL
- UNIQUE (platform_type, content_id, date)

**tag**
- id UUID PK DEFAULT gen_random_uuid()
- name TEXT UNIQUE NOT NULL
- tag_type TEXT NOT NULL CHECK (tag_type IN ('canonical','experimental'))
- created_at TIMESTAMPTZ NOT NULL

**animation_tag**
- animation_id UUID NOT NULL REFERENCES animation(id) ON DELETE CASCADE
- tag_id UUID NOT NULL REFERENCES tag(id) ON DELETE CASCADE
- added_by UUID REFERENCES user_account(id)
- added_at TIMESTAMPTZ NOT NULL
- PRIMARY KEY (animation_id, tag_id)

**tag_event**
- id UUID PK DEFAULT gen_random_uuid()
- animation_id UUID NOT NULL REFERENCES animation(id) ON DELETE CASCADE
- tag_id UUID NOT NULL REFERENCES tag(id) ON DELETE CASCADE
- action TEXT NOT NULL CHECK (action IN ('added','removed','edited'))
- source TEXT NOT NULL CHECK (source IN ('ui','system'))
- changed_by UUID REFERENCES user_account(id)
- changed_at TIMESTAMPTZ NOT NULL
- payload JSONB

**pipeline_run**
- id UUID PK DEFAULT gen_random_uuid()
- idea_batch_id UUID REFERENCES idea_batch(id) ON DELETE SET NULL
- run_date DATE NOT NULL
- window_id TEXT NOT NULL
- status TEXT NOT NULL CHECK (status IN ('scheduled','running','succeeded','failed','canceled'))
- started_at TIMESTAMPTZ
- finished_at TIMESTAMPTZ
- created_at TIMESTAMPTZ NOT NULL
- updated_at TIMESTAMPTZ NOT NULL
- UNIQUE (run_date, window_id)

**job**
- id UUID PK DEFAULT gen_random_uuid()
- job_type TEXT NOT NULL
- status TEXT NOT NULL CHECK (status IN ('queued','running','succeeded','failed'))
- attempt INTEGER NOT NULL DEFAULT 1
- max_attempts INTEGER NOT NULL DEFAULT 1
- parent_job_id UUID REFERENCES job(id) ON DELETE SET NULL
- payload JSONB
- error_payload JSONB
- queued_at TIMESTAMPTZ
- started_at TIMESTAMPTZ
- finished_at TIMESTAMPTZ
- created_at TIMESTAMPTZ NOT NULL
- updated_at TIMESTAMPTZ NOT NULL

**job_stage_run**
- id UUID PK DEFAULT gen_random_uuid()
- pipeline_run_id UUID NOT NULL REFERENCES pipeline_run(id) ON DELETE CASCADE
- stage TEXT NOT NULL CHECK (stage IN ('generate','idea_gate','render','qc','publish','metrics'))
- status TEXT NOT NULL CHECK (status IN ('queued','running','succeeded','failed'))
- job_id UUID REFERENCES job(id) ON DELETE SET NULL
- started_at TIMESTAMPTZ
- finished_at TIMESTAMPTZ
- error_payload JSONB
- updated_at TIMESTAMPTZ NOT NULL

**platform_config**
- id UUID PK DEFAULT gen_random_uuid()
- platform_type TEXT NOT NULL CHECK (platform_type IN ('youtube','tiktok'))
- encrypted_payload BYTEA NOT NULL
- updated_by UUID REFERENCES user_account(id)
- updated_at TIMESTAMPTZ NOT NULL
- created_at TIMESTAMPTZ NOT NULL
- UNIQUE (platform_type)

**audit_event**
- id UUID PK DEFAULT gen_random_uuid()
- event_type TEXT NOT NULL
- source TEXT NOT NULL CHECK (source IN ('ui','system','worker'))
- actor_user_id UUID REFERENCES user_account(id)
- occurred_at TIMESTAMPTZ NOT NULL
- ip_address INET
- user_agent TEXT
- payload JSONB

2. Relacje między tabelami
- idea_batch 1‑N idea_candidate
- idea_candidate 1‑0..1 idea (wybór operatora)
- idea_candidate 1‑N idea_similarity, idea_similarity N‑1 idea (historyczne porównanie)
- idea_candidate 1‑N idea_embedding (wektory embeddingów)
- idea 1‑N animation
- animation 1‑N render
- render 1‑N artifact
- render 1‑N publish_record
- publish_record 1‑N metrics_daily
- render 1‑N metrics_daily (opcjonalne powiązanie)
- animation 1‑N qc_decision
- qc_checklist_version 1‑N qc_checklist_item
- animation N‑M tag (tabela łącząca animation_tag)
- animation 1‑N tag_event
- pipeline_run 1‑N job_stage_run
- job 1‑N job_stage_run (opcjonalne powiązanie)
- pipeline_run 0..1‑1 idea_batch (referencja przez pipeline_run.idea_batch_id)
- user_account 1‑N qc_decision / tag_event / platform_config / audit_event / animation_tag

3. Indeksy
- animation(status, created_at)
- animation(pipeline_stage, updated_at)
- render(animation_id, created_at)
- publish_record(platform_type, published_at)
- idea_batch(run_date, window_id)
- pipeline_run(run_date, window_id)
- metrics_daily(platform_type, date)
- metrics_daily(render_id, date)
- job(status, updated_at)
- job_stage_run(pipeline_run_id, stage)
- GIN: render(params_json), render(metadata_json)
- GIN: qc_decision(decision_payload)
- GIN: job(error_payload)
- GIN: audit_event(payload)
- GIN: tag(name) (opcjonalnie trigram/citext przy wyszukiwaniu)

4. Zasady PostgreSQL (RLS)
- platform_config: RLS włączone; polityka owner‑only: dostęp tylko gdy `current_setting('app.user_id')::uuid = updated_by`.
- audit_event: RLS włączone; polityka owner‑only: dostęp tylko gdy `current_setting('app.user_id')::uuid = actor_user_id` albo rola systemowa (np. `app.is_system`).

5. Dodatkowe uwagi / decyzje projektowe
- Normalizacja do 3NF; denormalizacja ograniczona do metryk dziennych i payloadów JSONB.
- Metadane renderu: kluczowe pola w kolumnach (seed, wersje, duration), reszta w JSONB.
- Metryki i audit log: partycjonowanie miesięczne po przekroczeniu ~1–5M rekordów.
- KPI: start od widoków SQL (rolling 14 dni, 72h, 7d), później materialized views.
- Wymagane rozszerzenia: `pgcrypto` (UUID), `citext` (email); opcjonalnie `pg_trgm` do wyszukiwania tagów.
- Decyzja (2026-02-02): `pgcrypto` i `citext` włączone w migracji kanonicznej; `pg_trgm` opcjonalne (index tworzony tylko jeśli extension istnieje).

6. RLS / roles
- RLS włączone dla wszystkich tabel w migracji kanonicznej.
- `platform_config` i `audit_event` mają **FORCE RLS**.
- Role: `anon` (brak dostępu), `authenticated` (pełny dostęp dla większości tabel), wyjątki:
  - `user_account`: owner-only (`app.user_id`).
  - `platform_config`: owner-only (`app.user_id`).
  - `audit_event`: tylko owner lub kontekst systemowy (`app.is_system`), brak update/delete.
