BenchPRO-NG — Single PRD for Hephaestus (REVISION: v1.1, incorporates PRD_REVIEW.md)

Authoritative input to Hephaestus. This PRD defines scope, architecture, CLI/API, acceptance criteria, data schemas, and delivery plan for BenchPRO‑NG.
All work MUST trace to numbered sections and IDs in this document.

================================================================================
0) EXECUTIVE SUMMARY

Purpose. BenchPRO‑NG is a deterministic, extensible benchmark orchestrator for HPC sites. It simplifies building, running, and comparing benchmarks across systems, with reproducible configuration, robust scheduler integration, and site‑wide results archival.

Who. HPC engineers, researchers, and platform admins running scaling studies and tracking performance across clusters.

Top goals.
G‑1  Reproducible orchestration with layered configuration, interpolation, and strict validation.
G‑2  Efficient execution on local shells and Slurm, with Tasks decoupled from Jobs and packing policies.
G‑3  Strong provenance and a Results Store locally; a site‑wide Results Archive server (v2) for ingest/query/visualization only.
G‑4  Extensible scheduler and parser plugin surfaces.
G‑5  Scriptable, discoverable CLI with dry‑runs, JSON outputs, and shell completion.

Success metrics.
S‑1  ≥90% of common study shapes (nodes/ranks/threads/gpus lists) expressible without writing shell (Appendix A).
S‑2  Plan generation ≤100 ms per 100 tasks; submission throughput ≥50 tasks/s via arrays.
S‑3  Zero silent config overrides; every resolved value has a source map.
S‑4  Results Archive ingest is idempotent; queries p50 <300 ms, p95 <800 ms for typical filters on a 100k‑run corpus (Appendix A).
S‑5  ≥95% of acceptance tests and golden renders stable across three minor releases.

================================================================================
1) BACKGROUND & PRIOR IMPLEMENTATIONS (CONTEXT + TRACEABILITY)

1.1 BenchPRO 1.0 (production‑used)
Strengths: list expansion for nodes/ranks/threads/gpus; Lmod including module use; Slurm reservations; suites; provenance capture.
Weaknesses: custom cfg/template format; dense functional style; weak error handling; one task = one job.
Lessons → Requirements:
  P‑A  Keep list expansion  → R‑RUN‑020, R‑PLAN‑010
  P‑B  Keep Lmod + reservations  → R‑ENV‑010, R‑SLURM‑020
  P‑C  Replace custom cfg with YAML+Jinja and strict validation  → R‑CFG‑001, R‑TPL‑001
  P‑D  Improve errors and source mapping  → R‑ERR‑001..005, R‑CFG‑010
  P‑E  Decouple tasks and jobs; enable packing  → R‑PACK‑001..004

1.2 BenchPRO 2.0 (architecture direction)
Strengths: layered configs; YAML/Jinja; clearer CLI surface; packaging/test direction.
Weaknesses: incomplete implementation; no real‑world usage.
Lessons → Requirements:
  P‑F  Adopt layered precedence and source‑map  → R‑CFG‑001..009, R‑CFG‑010..012
  P‑G  Adopt CLI shape (verb‑first, plan then run)  → R‑CLI‑001..009

1.3 JobSherpa (agent‑over‑tools pattern)
Strengths: external agent plans/monitors using deterministic tools; RAG KBs; script generation.
Risks: scope creep if agent logic lives inside runner.
Lessons → Requirements:
  P‑H  Expose clean deterministic CLI/REST for agents; keep LLM external  → R‑API‑030, R‑SRV‑001
  P‑I  Do not use server to execute jobs; archive only  → R‑SRV‑002

Traceability table (sample):
  P‑A → R‑RUN‑020, A‑RUN‑020
  P‑B → R‑ENV‑010, R‑SLURM‑020
  P‑C → R‑CFG‑001, R‑TPL‑001, A‑TPL‑001
  P‑E → R‑PACK‑001..004, A‑PACK‑001..002
  P‑H → R‑API‑030, A‑API‑030
  P‑I → R‑SRV‑002, A‑SRV‑002

================================================================================
2) GLOSSARY (NORMATIVE)

Task: atomic benchmark invocation (parameters/resources).
Job: scheduler submission unit (local script or sbatch). One Job MAY run one or many Tasks.
JobPackage: plan mapping Tasks into Jobs (array/steps/sequential/binpack) with Task→(job, index|step).
Build: compiled artifacts for an app/toolchain; includes manifest and activation script.
Suite: labeled collection of Tasks or matrices that expand into Tasks.
Result: metrics and provenance captured per Task execution.
Profile: YAML config set (build/bench/suite) with Jinja2 templates and metadata.
Requirements Resolver: selects a Build using partial constraints (code/version/build_label/system).
Packing Policy: algorithm for grouping Tasks into Jobs (array/steps/sequential/binpack).
System Profile: configuration describing an HPC system’s defaults and scheduler options.
Site Profile: organization‑wide defaults applied to all systems.
Derived Fields: read‑only computed values available during interpolation, namespaced as derived.*. Examples:
  • derived.total_cores = nodes × ranks_per_node × threads
  • derived.total_ranks = nodes × ranks_per_node
  • derived.walltime_seconds = parse(walltime to seconds)
  • derived.timestamp = ISO‑8601 current time at plan
  • derived.run_id = generated UUID for the planned run
Derived fields are computed after config merge and before interpolation; they cannot reference other derived fields (no chaining).
Mode: execution paradigm determining launcher and packing compatibility. Values:
  • serial — single process, no parallelism
  • mpi — pure MPI (ranks)
  • openmp — pure OpenMP (threads, single process)
  • hybrid — MPI + OpenMP (ranks with threads/rank)
  • gpu — GPU‑accelerated (may be combined with mpi/hybrid via flags)
Tasks with different modes MUST NOT be co‑packed unless a scheduler backend explicitly supports mixed‑mode execution.

================================================================================
3) REQUIREMENTS (RFC‑2119, WITH IDs)

Configuration & Templates
R‑CFG‑001  MUST support layered precedence (defaults < site < system < user < task/profile < CLI/env) and produce a per‑key source map.
R‑CFG‑002  MUST deep‑merge dicts; lists use per‑key strategies (replace|append|unique); scalars last‑writer wins.
R‑CFG‑003  MUST define config discovery order and search paths (~/.config/benchpro, repo .benchpro/, /etc/benchpro, env BENCHPRO_CONFIG).
R‑CFG‑004  MUST validate on load and again on plan; run MUST refuse if validation failed.
R‑CFG‑005  CLI `--set key=value` MUST override resolved config (dot‑path syntax).
R‑CFG‑006  MUST schema‑validate configs (JSON Schema or equivalent) and emit structured errors.
R‑CFG‑007  MUST detect circular references in config inheritance and fail with clear diagnostics.
R‑CFG‑008  MUST preserve YAML round‑trip semantics for comments/anchors where feasible; document limitations.
R‑CFG‑009  MUST generate config reference docs from schema (auto‑docs).
R‑CFG‑010  CLI MUST expose `bp config show --resolved --source-map`.
R‑TPL‑001  Templates MUST be Jinja2 with strict‑undefined; undefined variables fail unless `--allow-missing-vars`.

Interpolation
R‑INT‑001  MUST support legacy <<<var>>> and modern ${var}/${var:default} after merge, before validation/render.
R‑INT‑002  Expressions disabled by default; enabling MUST only allow safe math (+ - * / min max).
R‑INT‑003  Interpolation scopes MUST include resolved fields, derived.*, env.*, system.*, site.*.
R‑INT‑004  Derived fields MUST be computed deterministically before interpolation; circular references MUST be rejected.

Build Binding
R‑BND‑001  Bench MAY specify build_ref OR requirements; both MUST be supported.
R‑BND‑002  Requirements Resolver MUST deterministically select a Build (see 6.1) and record chosen build_id in run manifests.
R‑BND‑003  Every Build MUST emit build.manifest.json and activate.sh; run scripts MUST source activate.sh before executing the binary.

Execution & Slurm
R‑RUN‑010  Local execution MUST render POSIX scripts and throttle concurrency (see 6.8).
R‑RUN‑011  Local concurrency MUST default to min(8, CPU_count) and be configurable via `--max-concurrent` and system.max_local_tasks.
R‑SLURM‑020  Slurm execution MUST support reservations, account, qos, constraints, dependencies, arrays, and steps.
R‑RUN‑020  Matrices over nodes, ranks_per_node, threads, gpus, and named params MUST be expanded deterministically (see 6.9).

Planning
R‑PLAN‑010  Matrix planning/expansion algorithm MUST follow Section 6.9 and record plan deterministically (task ordering, IDs).

Packing
R‑PACK‑001  MUST decouple Tasks from Jobs.
R‑PACK‑002  MUST provide packing policies: array, steps, sequential, simple binpack.
R‑PACK‑003  Packing MUST enforce compatibility (partition/account/qos/reservation/constraints/resource shape/walltime class/mode).
R‑PACK‑004  No oversubscription by default; parallel steps MUST respect node CPU/GPU limits.

Environment & Lmod
R‑ENV‑010  Lmod integration MUST support module use and deterministic load order; provenance MUST snapshot module list and LOADEDMODULES.
R‑ENV‑020  Modulefile generation MAY be added later; when present it MUST wrap activate.sh.

CLI (”2.0‑style” definition + exceptions)
R‑CLI‑001  CLI verbs MUST include: plan, run, watch, list, show, export, render.
R‑CLI‑002  Nouns MUST include: build, task, suite, results, config, pack, queue, daemon.
R‑CLI‑003  Every mutating action MUST have a plan twin that performs a dry‑run and can emit JSON (`--json`).
R‑CLI‑004  Resource flags MUST be consistent: --nodes, --ranks-per-node, --threads, --gpus, --partition, --time, --account, --qos, --reservation.
R‑CLI‑005  Shell completion MUST install via `bp completion install` and suggest valid subcommands/options.
R‑CLI‑006  `bp help` and each `<noun> --help` MUST show ≥2 runnable examples.
R‑CLI‑007  Shorthand commands (init, watch, queue) MUST document their canonical forms in help (init=workspace bootstrap; watch=task watch; queue=list). 
R‑CLI‑008  `--json` outputs MUST be single JSON objects with stable keys; tabular output MUST be consistent across commands.
R‑CLI‑009  Long‑running operations MUST show progress (spinner/percent) unless `--quiet` is set.

Results Store (Local)
R‑RES‑001  Local store MUST use SQLite for metadata and content‑addressed JSON (CAS) for provenance/artifacts.
R‑RES‑002  Queries MUST support filters by system, app, suite, shape, time, and tags; exports MUST include CSV and JSON; filter semantics MUST match Section 11 A‑RES‑002.

Results Archive Server (v2; archive‑only)
R‑SRV‑001  Server MUST accept ingest (push‑only) and expose read queries and basic chart aggregations (6.4).
R‑SRV‑002  Server MUST NOT plan/execute/monitor jobs and MUST NOT act as a build catalog.
R‑SRV‑003  APIs MUST provide pagination, schema versioning, and idempotent ingest (6.4).

External Agent Support
R‑API‑030  BenchPRO MUST be controllable by external agents via CLI; agents MAY query the Results Archive; execution MUST remain client‑side.

Security
R‑SEC‑001  Secret detection/redaction MUST apply to logs, provenance, and error messages (see 6.7).
R‑SEC‑002  Environment variable allowlist MUST default to PATH, HOME, USER, LANG, LC_*, TZ, TMPDIR; deny *_TOKEN, *_KEY, *_SECRET, *PASSWORD by default.
R‑SEC‑003  Least‑privilege execution: no sudo/setuid; file perms scripts 0755, configs 0644, secrets 0600; jobs run as submitting user.
R‑SEC‑004  Input validation MUST block path traversal, enforce name regex, and shell‑escape all user inputs.
R‑SEC‑005  Server write endpoints MUST require auth (token or mTLS); tokens hashed; rate limits; CORS off by default; artifact size limits.

Failure Recovery
R‑FAIL‑001  Task retry policy: {max_attempts, backoff} with defaults (1, exponential base 60s); attempts recorded with unique attempt IDs.
R‑FAIL‑002  Suite policy continue_on_failure: default false; see 6.10.
R‑FAIL‑003  Checkpoint/resume via .bp_state/<run_id>.json and `bp suite resume`.
R‑FAIL‑004  Orphaned job cleanup via `bp queue cleanup` (interactive or --force).
R‑FAIL‑005  Local store integrity checks; CAS validation; quarantine corrupt entries; `bp results repair`.

Non‑Functional
R‑PERF‑001  Plan generation ≤100 ms per 100 tasks.
R‑PERF‑002  Submission throughput ≥50 tasks/s when packed into arrays.
R‑OBS‑001   Logs MUST include stable fields: timestamp, level, component, run_id, task_id, job_id, phase, message, error_code, duration_ms.

================================================================================
4) DESIGN DECISIONS (WITH RATIONALE)

D‑001 Daemon optional (on‑demand polling by default). Reduces ops burden; offline‑friendly.
D‑002 Server is archive‑only. Keeps execution local/deterministic; agents interact with CLI; server scales independently.
D‑003 External AI only. Determinism/testability; site constraints. BenchPRO exposes predictable surface for agents.

================================================================================
5) NON‑FUNCTIONAL REQUIREMENTS (DETAIL)

Observability: structured JSON logs (R‑OBS‑001) and human logs; correlation via run_id/task_id/job_id.
Portability: no site‑hardcoding; system/site profiles configure syntax and defaults.
Backward compatibility: legacy <<<var>>> supported; converter CLI for 1.0 cfg (Section 7).
Security: R‑SEC‑001..005 define redaction, allowlists, and server controls.
Retention: server retention policies per site; client local store pruned manually or via `bp results prune` (policy configurable).

================================================================================
6) DETAILED SPECS

6.1 Requirements Resolver — total ordering
When multiple Builds match requirements, resolver MUST apply:
  1) code (must match)
  2) version (exact > wildcard/unspecified)
  3) system (exact > unspecified)
  4) build_label (exact > unspecified)
  5) build_timestamp (newest first)
  6) build_hash (lexicographic final tie‑break)
Selection:
  • selection: latest|first|fail (default latest noninteractive). “first” uses ordering above. “fail” aborts with candidate list.
Recording:
  • Chosen build_id MUST be recorded in run manifest; replay MUST reuse same build_id.

6.2 Packing policy — compatibility & isolation
Compatibility (all must match): partition, account, qos, reservation, constraints, resource shape (nodes/ranks_per_node/threads/gpus), walltime class, mode.
Walltime class bucketing:
  1) Parse walltime to seconds (accepted formats: HH:MM:SS, MM:SS, integer minutes, ISO‑8601 duration).
  2) Default if unspecified: system.default_walltime or 3600 s.
  3) Bucket = ceil(seconds / 300)*300 (5‑min buckets).
  4) Min bucket 300; max bucket system.max_walltime or 86400.
Isolation (defaults):
  • No CPU oversubscription: ranks×threads/node ≤ alloc CPUs.
  • No GPU oversubscription: gpus/node ≤ alloc GPUs.
Steps:
  • --pack-max-parallel limits parallel steps (default 1); arrays run one task per index.
Failures:
  • Incompatible Tasks MUST form separate JobPackages; warnings enumerate reasons.
Binpack (simple):
  • Greedy by largest GPU count then CPU footprint; stop at limits (best‑effort).

6.3 CLI Definition (“2.0‑style”) and exceptions
Shape: bp <noun> <verb> [options]
Verbs: plan, run, watch, list, show, export, render
Nouns: build, task, suite, results, config, pack, queue, daemon
Exceptions (standalone shortcuts):
  • bp init  → workspace bootstrap (no noun)
  • bp watch → shorthand for task watch
  • bp queue → shorthand for queue list
Shortcuts MUST document canonical equivalents in `--help` and share the same flags.

6.4 Results Archive Server (v2) — API & versioning
Ingest:
  • POST /ingest/run (JSON; run metadata, metrics, CAS manifest; idempotency key=(client_uuid, run_id))
  • POST /ingest/artifact (binary; SHA256 path; size limits configurable)
  • POST /ingest/batch (NDJSON or tar of JSON+blobs)
Query:
  • GET /runs, /results: pagination (?limit=&offset= or cursor); filters by system, app, suite, shape, tags, time
  • GET /artifacts/{sha256}; range requests allowed
  • GET /charts/metric-vs-nodes?metric=…&group=…
Versioning:
  • Header X‑BenchPRO‑Schema: vMAJOR.MINOR; server accepts current and N‑1; clients declare schema version.
Security:
  • Write requires token or mTLS; reads may be anonymous or token‑gated per site policy.
Idempotency:
  • Duplicate ingest with same (client_uuid, run_id) MUST NOT duplicate.

6.5 Data Models & Schemas (JSON Schema excerpts; full in /docs/SCHEMAS.md)
build.manifest.json
  required: code, version, build_id (uuid), build_timestamp (RFC3339), activation_script
  fields: build_hash (sha1/sha256), system, build_label, toolchain {compiler, mpi, cuda, flags[]}, app_root, bin[], lib[], include[], exe_paths {name→path}, runtime_env {k→v}

task.json
  task_id, suite_id, parameters{}, resources {nodes, ranks_per_node, threads, gpus, partition, time, account, qos, reservation, mode}, build_ref OR requirements {code, version?, build_label?, system?}, dependencies[]

suite.json
  suite_id, name, tasks[], matrices {nodes[], ranks_per_node[], threads[], gpus[], params{...}}, metadata {tags[], description}

job_package.json
  package_id, scheduler, policy (array|steps|sequential|binpack), jobs[], task_mappings[{task_id, job_id, array_index|step}], compatibility_constraints{...}

run_manifest.json
  run_id (uuid), suite_id, build_id, timestamp, system, resolved_config (flattened), tasks[{task_id, shape, params}], selection_policy, seed

result.json
  run_id, task_id, status (success|failed|timeout|canceled), exit_code, duration_ms, metrics{name→{value, unit, higher_is_better}}, provenance{modules[], env_snapshot{}, slurm{job_id, array_index, step}}, artifacts[{sha256, path, size}], stderr_summary

cas_manifest.json
  sha256_to_path {sha256→relative_path}, artifacts[{sha256, media_type, size, role}]

6.6 Plugin Interfaces
Parser plugins
  Interface:
    class BenchmarkParser:
      def parse(self, stdout: str, stderr: str, exit_code: int, provenance: dict) -> dict:
        return {"metrics": {"name": {"value": float, "unit": str, "higher_is_better": bool}},
                "parser_version": "x.y", "parse_timestamp": ISO8601, "warnings": [str]}
  Discovery: Python entry_points: benchpro.parsers
  Versioning: plugin declares semver; BenchPRO enforces >= min and < next‑major.
  Errors: plugin exceptions are captured; parser failure yields empty metrics + warning.

Scheduler plugins
  Interface:
    class SchedulerBackend:
      def submit_job(self, job_package) -> str: ...
      def query_status(self, job_ids: list[str]) -> dict[str, JobStatus]: ...
      def cancel_job(self, job_id: str) -> bool: ...
  Discovery: entry_points benchpro.schedulers
  Isolation: plugins run in process; errors surface as structured exceptions; version compatibility checked on load.

6.7 Error Taxonomy & Formats
Error message format: `[ERROR_CODE] COMPONENT: Message (context_key=value, …)`
Exit codes:
  0 success; 1 general; 2 config/validation; 3 build/binding; 4 execution/scheduler; 5 server/network; 125‑127 shell/signal.
Validation error JSON (when --json):
  { "valid": false, "errors": [ { "code": "CFG_MERGE_CONFLICT", "path": "suite.tasks[0].nodes",
      "message": "Cannot merge list without strategy", "source_layers": ["system","user"],
      "suggestion": "Add list_strategy: append|replace|unique" } ] }
Log fields (stable): timestamp, level, component, run_id, task_id, job_id, phase, message, error_code, duration_ms.
Secret detection/redaction:
  patterns *_TOKEN, *_KEY, *_SECRET, *PASSWORD, *_CREDENTIAL or config secret:true; redaction “[REDACTED:last4]”.

6.8 Local execution throttling
Default max_concurrent_tasks = min(8, CPU_count); configurable by `--max-concurrent` or system.max_local_tasks.
Concurrency measured by active task processes; worker‑pool blocks at limit; logs a throttling warning.

6.9 Matrix expansion (deterministic)
Expansion order (outer→inner): nodes → ranks_per_node → threads → gpus → named_params (alphabetical).
Default strategy: cross‑product of all dimensions.
Optional zip strategy: list_strategy: zip; iterate in parallel, truncate to shortest list.
Task IDs assigned sequentially: task_0…task_N in the documented order.

6.10 Failure recovery semantics
Retry: per‑task policy, exponential backoff base 60s (configurable).
Suite failure: continue_on_failure true|false; if false, first failure cancels pending (running complete).
Checkpoint/resume: .bp_state/<run_id>.json contains statuses/job_ids; resume skips completed and resubmits failed/pending.
Orphan cleanup: detects scheduler jobs without local state; interactive cancel (or --force).

================================================================================
7) MIGRATION PLAN (FROM 1.0)

M‑001  `bp migrate cfg --in old.cfg --out new.yaml` converts custom cfg + <<<var>>> to YAML + ${var}.
M‑002  Mapping doc and warnings for unsupported directives (Appendix B matrix).
M‑003  `bp config lint` strict validation and deprecation warnings.
M‑004  “compat” template pack for popular apps.
Strategy: pre‑migration validation → parallel operation (side‑by‑side DB paths) → full migration → post‑migration monitoring.
Rollback: keep v1.0 read‑only for 3 months; bidirectional metadata export/import. 

================================================================================
8) CHANGE CONTROL (FOR HEPHAESTUS)

All changes reference requirement IDs (R‑*). Architectural changes use ADRs (Decision/Alternatives/Implications/Revisit).
PR template requires: requirement IDs, acceptance IDs, test IDs, doc updates. Semantic versioning for client and server schema headers.

================================================================================
9) VALIDATION ARTIFACTS

Golden renders: submit scripts and activation snippets hashed; diffs fail CI.
Resolver tests: requirements matrix → chosen build_id; tie‑break verification.
Packing tests: array/steps/sequential/binpack; ensure no oversubscription; correct Task→(job,index|step) mapping.
Server tests: ingest idempotency; pagination; chart aggregation; authorization; artifact retrieval.
E2E tests: build → suite plan → run → watch → export for LAMMPS, WRF, HPCG (local and Slurm mock).

================================================================================
10) CLI SURFACE (REFERENCE)

bp init
bp config show|set|edit [--resolved --source-map]
bp app build|list|delete
bp task  new|plan|run
bp suite plan|run|list  [--pack array|steps|sequential|binpack --nodes ... --ranks-per-node ... --threads ... --gpus ...]
bp pack  plan|apply
bp watch [--follow --tail]                 # shorthand for task watch
bp queue                                   # shorthand for queue list
bp results list|show|export [--filter ... --to CSV|JSON]
bp template render
bp daemon start|stop|status
bp completion install

Examples:
  bp suite plan wrf_scale --nodes 1,2,4,8 --ranks-per-node 64 --pack array --json
  bp suite run  wrf_scale --system stampede3 --reservation WRF_TRAIN --qos normal
  bp results export --filter suite=wrf_scale --to out/wrf.csv
  bp config show --resolved --source-map

================================================================================
11) ACCEPTANCE CRITERIA (AUTHORITATIVE)

A‑CFG‑001  Given conflicting values, `bp config show --resolved --source-map` reports final values/origins for ≥20 keys; higher‑precedence change updates value deterministically.
A‑TPL‑001  Template with undefined variable fails with clear error unless `--allow-missing-vars`; error includes variable and template location.
A‑INT‑001  `gpus: <<<ranks_per_node>>>` resolves across matrices; `${system.name}` resolves; undefined variables fail unless `--allow-missing-vars`.
A‑INT‑002  `${1 + 2}` resolves to "3" with `--allow-expr`; same expression fails without; unsafe `${__import__('os')...}` is rejected with security error even with `--allow-expr`.
A‑BND‑001  With requirements (only code), resolver selects a Build and logs tie‑break steps; with build_ref, chosen Build matches exactly; build_id recorded in run manifest.
A‑RUN‑010  Same Suite locally and on Slurm yields identical post‑activation command lines (scheduler wrappers excluded) and equivalent provenance (excluding scheduler fields).
A‑RUN‑011  Local execution with 100 tasks and `--max-concurrent=4` never exceeds 4 concurrent processes; FIFO ordering within the concurrency limit.
A‑RUN‑020  Matrix expansion order is stable across 10 runs; task_id assignment matches documented algorithm; zip/cross‑product produce expected task counts.
A‑PACK‑001  For 24 identical‑shape Tasks, `--pack=array` produces one Slurm job with `--array=0‑23`; Task mappings persisted; `bp watch` shows per‑Task states.
A‑PACK‑002  `--pack=steps` respects `--pack-max-parallel` and does not oversubscribe CPUs/GPUs.
A‑ENV‑010  `--reservation=XYZ` appears in submit scripts and accounting; `module use` and `module list` snapshots appear in provenance.
A‑MON‑001  Without daemon, `bp watch` polls and reattaches; with daemon, auto‑connects; p50 update latency <300 ms on 500 Tasks.
A‑RES‑001  Parsers populate metrics; `bp results export --filter suite=foo` emits CSV with shape and metric fields, correct units.
A‑RES‑002  Query filters return correct subsets for system/app/suite/nodes range/time range/tags and combinations.
A‑SRV‑002  Disabling server or losing connectivity does not affect local runs; `bp results push` is idempotent; WebUI plots metric vs nodes across systems/time ranges.
A‑PERF‑001  Plan gen ≤100 ms/100 tasks; submission throughput ≥50 tasks/s via arrays; local store queries p50 <150 ms on 50k results.
A‑PERF‑002  Submitting 1000 tasks via arrays achieves ≥50 tasks/s (tasks submitted / wall time); Slurm accepts array job in <1 s (mock).
A‑CLI‑001  `bp --help` indicates shorthand vs canonical forms; completion suggests both; completion works in bash and zsh.
A‑CLI‑005  After `bp completion install`, completion suggests valid subcommands and flag names after `--`.
A‑CLI‑006  `bp help` and every `bp <noun> --help` show ≥2 runnable examples; examples run in CI test env.
A‑API‑030  External agent drives: plan → run → watch (polling) → results export --json; all outputs parse as valid JSON and support agent logic.
A‑SEC‑001  Provenance capture with TOKEN=abc123 in env shows “[REDACTED:c123]”; password in config is not logged; unknown env is blocked unless allowlisted.
A‑FAIL‑001  Task with exit_code=1 and retry_policy {max_attempts:3} retries up to 3 times with exponential backoff; attempts recorded.
A‑FAIL‑002  Suite with continue_on_failure=true completes remaining tasks despite one failure; final exit code 4; results include failed task details.
A‑FAIL‑003  `bp suite resume <run_id>` after simulated crash resumes from checkpoint; skips completed tasks; resubmits failed/pending.

================================================================================
12) DELIVERY PLAN (MILESTONES & GATES)

M1 — Core Orchestrator (v1.0)
  • R‑CFG‑*, R‑INT‑*, R‑TPL‑*, R‑BND‑*, R‑RUN‑*, R‑SLURM‑020, R‑CLI‑001..006, R‑RES‑001..002
  • Gate: A‑CFG‑001, A‑TPL‑001, A‑INT‑001..002, A‑BND‑001, A‑RUN‑010..011, A‑RES‑001..002, A‑PERF‑001, A‑CLI‑005..006

M1.5 — Packing & UX Hardening
  • R‑PACK‑001..004, CLI help/examples, golden renders expanded
  • Gate: A‑PACK‑001..002, A‑MON‑001, A‑RUN‑020, A‑CLI‑001

M1.6 — Modulefile Generation (optional)
  • R‑ENV‑020; modulefiles wrap activate.sh
  • Gate: targeted modulefile tests

M2 — Results Archive Server
  • R‑SRV‑001..003, R‑API‑030 (read/query only)
  • Gate: A‑SRV‑002, A‑API‑030, A‑PERF‑002

================================================================================
APPENDIX A: PERFORMANCE TEST SPECIFICATIONS

A.1 S‑1 Study Shape Coverage
Common shapes: strong scaling (nodes=[1,2,4,8,16,32,64,128]), weak scaling (problem scales with nodes), thread scaling (threads=[1..64]), GPU scaling (gpus=[1,2,4,8]), combined 3D matrices. Dataset: 100 representative studies (LAMMPS, WRF, HPCG). Pass: ≥90 expressible without custom shell.

A.2 Archive Query Performance
Corpus: 100k runs; avg result 50KB; artifacts 3/run, 500KB total; 10 systems, 20 apps, 50 suites.
Filters: single (system, app, suite), time ranges (7/30 days), shape range (nodes 16‑64), combined (system+app+time).
Pass: p50 <300 ms, p95 <800 ms, p99 <2000 ms (cold cache).

A.3 Local Store Query Performance
DB: 50k results. Queries: full scan by system (5k rows), indexed filter by suite+time (500 rows), aggregation by nodes, export 1k rows to CSV. Pass: p50 <150 ms, p95 <500 ms (warm cache allowed).

================================================================================
APPENDIX B: COMPATIBILITY MATRIX (v1.0 → v2.0)

| v1.0 Feature         | v2.0 Equivalent                   | Migration     | Notes                               |
|----------------------|-----------------------------------|---------------|-------------------------------------|
| <<<var>>>            | ${var}                            | Automatic     | Converter handles                    |
| One task = one job   | JobPackage + packing              | Semi‑automatic| Policy selection may be needed       |
| Custom cfg/template  | YAML + Jinja2                     | Manual        | Porting guide provided               |
| Lmod integration     | Lmod integration                  | Transparent   | Snapshot + module use                |
| Suites               | Suites (schema evolved)           | Automatic     |                                     |
| Reservations         | Reservations                      | Transparent   |                                     |

================================================================================
END OF DOCUMENT
