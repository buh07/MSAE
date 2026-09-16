# MSAE v3 gen3 successor after the failed gen2 M4 attempt

## Scope

This continuation preserves `post_m2_gen2` as failed during M4 and implements a
disjoint `post_m2_gen3` M3--M5 successor. It may freeze Stage A and launch only
the calibration replay. It may not score C1/C2, create Stage C, select a paper
branch, or reinterpret v1/v2/gen2.

## Gen2 terminal record

Gen2 M3 remains a valid, non-authorizing M3 state, but its M4 attempt failed
before Stage A or any M4 output was created with the operator-observed error
`ValueError: active protocol config does not reproduce`. The original full
transcript is unavailable and is recorded as `operator_attested`; it is never
manufactured by rerunning gen2. The create-once gen2 `m4_failure.json` separately
binds the independently verifiable M3 bytes/state and a fixed-root reproduction
showing exactly the four stratum `environment_sha256` fields differ because the
generic builder incorporates candidate `ROOT` into its Python path. It records
Stage A/M4/signature/model/GPU/tmux as not created/not run. Gen3 setup may create
this one file only after both pre-M3 review gates pass; it is the sole gen3 write
under a gen2 namespace.

## M2 result gate

M2 is complete only when a create-once completion manifest binds all seven M2
files and closes the four roles, 68 role/task cells, 34,000 maps, 500 finite
draws per cell, and the 36/20/11 correction populations. An independent review
must freeze the completion-manifest digest before M3.

## M3 and successor generation

The older `post_m2_gen1_failed_preflight` remains terminally failed: its
create-once config was generated before the torch no-`RECORD` closure was
repaired. Its existing `m3_preflight_attempt_1.json` binds that historical
config, commitment, public key, private-key lstat identity, M2 pin, exact known
failure, and `model_gpu_tmux=not_run`. The later `post_m2_gen2` M3 is valid but
non-authorizing; only its M4 transition failed, as recorded above. Neither
predecessor is treated as Stage-A-ready.

All new executable continuation state uses the explicit successor generation
`post_m2_gen3`, with separate config, provenance, key, nonce, review, and run
roots. The exact current user instruction is stored verbatim and hashed. Four
exact checkpoint lineages are registered: independent replicate seeds g4/g5/g6
and matched negative control g7.

The endpoint registry is generated from closed family, task, component, metric,
checkpoint, transform/control, and baseline products, then checked by an
independent typed-tuple product. C1 uses only raw/simple G1 operand names. C2
registers g4/g5/g6 and descriptive g7. The registry includes localization,
Tier-2 collateral, functional reproducibility, counterfactual
specificity/mapping controls, and all baselines.

The M2 completion is verified only by the immutable gen2 runtime, while M1 is
verified by the immutable post-M1 controller. The gen3 controller is the sole
post-gen2 command API and calls the immutable controller's
`extend_closure_payload` against candidate-root bytes for every gen3 local
dependency.

The keypair, public commitment, nonce and shared GPU-lock directories are
create-once. A partial state blocks; a complete state is revalidated by object
identity, permissions, public/private agreement, scope, and the verbatim
instruction. No signature or execution authorization exists in M3.

### Machine-enforced plan and implementation reviews

Before implementation, the create-once plan review binds the frozen plan digest
and has exactly one `VERDICT: SHIP` and `REVIEW_SCOPE: plan`. Before any gen3
setup write, a distinct implementation review binds the plan, plan review,
controller, runtime, runner, launcher, this RFC, tests, and predicted gen2
failure payload, with exactly one `VERDICT: SHIP` and
`REVIEW_SCOPE: implementation`. `setup-m3` requires both review-file digests and
validates exact canonical UTF-8 bytes, mode 0644, owner, nlink 1, no symlink, and
the exact unique digest-control set before writing anything. Both review entries
and digests enter config, authorization commitment, and CPU/no-model trace.

After M3, a third create-once `REVIEW_SCOPE: post_m3` review binds config, trace,
commitment, public key, private-key lstat, state/nonce identities, gen2 failure,
both prior reviews, and the exact absence of gen2/gen3 M4, prescore, signature,
run, nonce, build-root, and dedicated tmux outputs. It self-excludes only its own
historical absence observation. `build-m4` requires its exact digest before any
copy/build operation.

## Closure and Stage A

The closure binds all controller/runtime/runner/launcher/RFC/test bytes, every
M0--M2 artifact and selected source alias, all four selected checkpoints and
lineage records, protocol and key commitment, every model-snapshot file, every
invoked executable plus its ELF closure, and every verified distribution file.
When a distribution lacks RECORD, every installed file under every declared
top-level root is inventoried. Every native object is passed through strict ldd
resolution; any `not found` result blocks. Standard extension modules and the
finite system GPU-driver library allowlist are included.

The successor public API is the exact isolated controller CLI
`msae_independent_measurement_v3_post_m2_gen3.py` plus the runtime functions reached
by that CLI. The immutable controller's `__getattr__` compatibility exports of
the pre-continuation base module are historical M2 implementation details, not
public post-M2 commands; they are never named by the signed envelope, launcher,
review commands, or process registry. This prospectively narrows the base RFC's
"every public v3 entry point" wording: the CPU/no-model trace exercises the
controller `main`, runtime `dispatch`, every successor command, and runner, and
the static process registry rejects a base-module CLI route.

`-B` is not treated as a bytecode-read prohibition.  The controller and the
direct worker runner each install, before their first repository-local import,
an exact-name meta-path finder covering every local Python module in the static
closure.  Its `SourceFileLoader` subclass makes `path_stats` fail closed,
rejects every `get_data` request except the exact `.py` path, disables cache
writes, and reads the owned, one-link, non-group/world-writable source through
no-follow directory and file descriptors with before/after identity checks.
All gen3 candidate-root dynamic loads use the same source-only spec.  Therefore
ignored local `scripts/__pycache__/*.pyc` files are deliberately neither copied
nor bound: they are mechanically unreachable.  Before the first local import
and again after immutable predecessor imports, the controller/runner removes
the repository `scripts/` directory from `sys.path`; the successor runtime
never adds it.  Deferred standard-library and third-party imports therefore
cannot be shadowed by ignored sourceless `.pyc`, extension `.so`, or other
unregistered files in `scripts/`.  The static closure requires the
controller and runner source-only registries to equal the complete local-module
set, records every candidate-root dynamic target, and the CPU regression plants
both timestamp-valid malicious bytecode beside unchanged source and a
sourceless third-party-name shadow and proves that controller and runner execute
only registered source/import roots.

Static closure assigns every dynamic file/FD call site an individually frozen
AST-site binding to the exact finite-file registry and derives local wrapper
path parameters to a fixed point, including positional and keyword calls.
Literal and statically assigned absolute paths outside the registry block.
Process argv, UNIX socket construction/connect/bind/transfer methods, and
library loading have separately frozen finite mappings. M3 create-once stores a
reproducing CPU/no-model trace over these registries and planted indirect file,
process, shell, library, and IP-network escapes.

The runner records `/proc/self/maps` before torch import, after torch import,
after model loading, and after all forwards. All four exact realizations are
retained through the terminal transaction. Any absolute mapped file absent
from or different from the allowlist blocks.

The generic protocol adapter is exact and root-independent. For each stratum it
first requires the rooted generic builder's `code_sha256` to equal the rooted
gen2 runner and its `environment_sha256` to equal the rooted `.venv-atlas`
derivation. It then replaces only those two fields with the rooted gen3-runner
digest and canonical external-Python environment digest. Every other field is
unchanged. Config, closure, and environment artifacts cross-bind the external
Python realpath, size, mode, digest, startup digest, determinism/TF32 flags,
model revision/dtype, and cache dtype. Candidate-root `.venv-atlas` fallback,
missing executable records, byte/target drift, or a third-field difference
blocks.

Stage A independently recomputes reviewed M1/M2 completion entries and success
semantics, successor config and authorization commitment, checkpoint and
endpoint registries, closure, environment, exact eight Stage-A requirements,
and every typed digest before wrapping the generic builder. A generic ready
artifact or status string alone is never accepted.

M4 sparse-copies every repository-local closure/Stage-A input, including the
four selected checkpoints, into each of two initially absent temporary trees.
There is no live-repository fallback. Externally installed executables,
distributions, the model cache, security directories, and quarantined lstat
records are re-inventoried as explicit external inputs in each build. M4
computes independently and compares complete directory/file
path/type/mode/size/hash manifests and exact Stage-A/M4 bytes. Only the six
registered M4 outputs are installed through a recoverable create-once
transaction; existing/staged files are accepted only through no-follow FD,
path, type, mode, owner, link-count, size, and byte checks.

The initial-absence rule applies to a fresh M4 transition.  A crash recovery is
the sole exception and does not create a new review subject.  The public M4 gate
first recognizes only these crash-left objects: either dedicated primary/rebuild
temporary roots, the registered transaction directory and its exact
`transaction.json`/numbered-payload child allowlist, or a prefix of the six
registered M4 destinations.  Temporary and transaction roots must remain real,
UID-owned mode-0700 directories; transaction children must be regular,
UID-owned, nlink-1 mode-0600 files; installed prefix files must be regular,
UID-owned, nlink-1 mode-0644 files.  Any other downstream object or child still
blocks.  Valid temporary roots are removed and rebuilt twice.  Status evidence
is normalized by removing only transaction/M4-prefix rows and then adding the
same two visible provenance rows as a fresh build (the three data rows are Git
ignored and the manifest is self-excluded).  Directory evidence subtracts only
the validated transaction subdirectory's single provenance-root link.  The two
rebuilt complete trees must reproduce the original bytes; the installer then
byte-checks every surviving staged/installed prefix and resumes create-once
installation.  A lost transaction directory with a matching installed prefix
may be recreated from those independently rebuilt bytes.  No prescore review,
authorization, nonce, run, model, GPU, or tmux artifact is recoverable through
this exception.

The plan, plan review, implementation review, post-M3 review, gen2 failure
record, all gen3 code/RFC/tests, and all immutable predecessors are registered
candidate/closure/status/static-surface inputs. The three gen3 M4 data products
live only under `data/msae_independent_measurement_v3_post_m2_gen3/`; shared
M0--M2 data remain at their immutable M2 projection.

## Prescore projection and review

The candidate manifest independently enumerates every candidate path and every
entry under old and successor v3 data/config/provenance roots, binds full
porcelain-v2 status, and rejects any unclassified status path or non-regular
candidate. It requires the review, run root, build roots, tmux socket, and nonce
records absent and validates all bound external state.

The traced check uses manifest-digest-derived, initially absent output paths. It
requires a nonempty newline-complete trace with expected controller, runtime,
manifest, Stage-A, and closure opens, resolves successful `open*` syscall `-yy`
dirfd/result paths, and rejects every quarantined identity. The review
transcript must contain exactly one unindented `VERDICT: SHIP` and exactly one
line for each candidate-manifest, Stage-A, closure, traced-check, and trace
digest, plus `SEALED_PAYLOAD_CONTENT_READS: 0`. Only that exact transcript may
be installed.

The successor generation supersedes the older path spellings in the base RFC.
The exact reviewer commands are:

```bash
M=$(.venv-atlas/bin/python -S -B -I -c 'import hashlib; p="reports/provenance/msae_independent_measurement_v3_post_m2_gen3/prescore_candidate_manifest.json"; f=open(p,"rb"); print(hashlib.file_digest(f,"sha256").hexdigest()); f.close()')
[[ "$M" =~ ^[0-9a-f]{64}$ ]]
.venv-atlas/bin/python -S -B -I scripts/msae_independent_measurement_v3_post_m2_gen3.py prescore-traced-check \
  --manifest reports/provenance/msae_independent_measurement_v3_post_m2_gen3/prescore_candidate_manifest.json \
  --output "/tmp/msae_independent_measurement_v3_post_m2_gen3_${M}.prescore.check.json" \
  --trace "/tmp/msae_independent_measurement_v3_post_m2_gen3_${M}.prescore.trace.log"
.venv-atlas/bin/python -S -B -I scripts/msae_independent_measurement_v3_post_m2_gen3.py verify-prescore-trace \
  --manifest reports/provenance/msae_independent_measurement_v3_post_m2_gen3/prescore_candidate_manifest.json \
  --check "/tmp/msae_independent_measurement_v3_post_m2_gen3_${M}.prescore.check.json" \
  --trace "/tmp/msae_independent_measurement_v3_post_m2_gen3_${M}.prescore.trace.log"
```

Both invocations require isolated, no-site Python (`-S -B -I`). The two output
names are exact functions of the candidate-manifest digest and must be absent
before the first command.

The pre-M3 and pre-M4 transition commands are exact:

```bash
.venv-atlas/bin/python -S -B -I scripts/msae_independent_measurement_v3_post_m2_gen3.py setup-m3 \
  --reviewed-m2-sha256 e593a6283aa5468ddbee1cc755dbe60c4ee503375a0cbce44c52614dd232d737 \
  --plan-review-sha256 <exact-create-once-plan-review-sha256> \
  --implementation-review-sha256 <exact-create-once-implementation-review-sha256>
.venv-atlas/bin/python -S -B -I scripts/msae_independent_measurement_v3_post_m2_gen3.py build-m4 \
  --post-m3-review-sha256 <exact-create-once-post-m3-review-sha256>
```

The first command rejects before its first write unless both prior review
schemas and all transitive digests reproduce. The second rejects before its
first copy/build unless the post-M3 review and exact downstream-absence subject
reproduce. The exact config child set after M3 is
`{protocol.json,authorization_commitment.json,ed25519_public.pem,cpu_no_model_public_entry_trace.json}`;
the provenance and gen3 M4-data roots are empty. After M4 the exact provenance
children are `{stage_a.json,status.json,prescore_candidate_manifest.json}` and
the exact M4-data children are
`{dependency_closure.json,endpoint_registry.json,environment_allowlist.json}`.
Every undeclared config/provenance/state/nonce/M4-data/transaction/run child
blocks.

This successor protocol explicitly supersedes the base RFC's immediate removal
rule for the two digest-derived evidence files. They remain create-once mode
`0600` audit evidence through signing and prelaunch so those transitions can
reverify the typed check and syscall trace. They are never model inputs and are
retained after launch as prescore provenance; no later scientific result may
rewrite or reinterpret them.

No GPU inventory or driver query occurs before this SHIP gate. Prescore binds
the query binary and policy; the realized UUID/driver libraries are bound after
SHIP.

## Signature, lease, readiness, and failure

The signed envelope binds the exact instruction and bytes, candidate manifest,
Stage A, closure, config, commitment, unique nonce, SHIP transcript, scope, and
24-hour interval. The nonce record name is the SHA-256 of the exact canonical
signed authorization file bytes, including the signature. The worker consumes
it once relative to a held directory FD checked against both commitment and
live path before and after creation, before model import.

Only after prescore SHIP may the launcher call `nvidia-smi`. It selects a GPU
with no compute process, <1024 MiB, and <=5% utilization; takes the shared UUID
flock through a held directory FD; then repeats the full GPU/process check.
Launcher, broker, and worker validate the same directory and lock object by
identity, type, mode, owner, and link count. The worker has its own process
group and a broker-death SIGKILL watchdog. The broker enforces a six-hour
deadline starting at worker creation, with TERM/KILL and zombie-aware process
group extinction.

`broker` and `supervise-broker` are internal subcommands, not independently
authorized execution routes. After the repeated idle check and while holding
the UUID lease, the launcher creates a mode-0600 intent binding the exact
socket, GPU UUID/index, lease inode, authorization, Stage A, launcher identity,
and the hash of a fresh 256-bit capability. Both internal processes require the
capability and intent digest, revalidate the live launcher, and the broker
revalidates the received lease FD against the intent before forking. Direct or
stale internal-subcommand invocation therefore fails before GPU/model/tmux
work.

The runner first verifies Stage A, signature, nonce, closure, config, loaded
library subset, and worker/lease lineage, then sends pre-model readiness and
blocks. The launcher verifies the tmux pane and readiness, writes and fsyncs the
live handoff, and only then sends the final model gate through the broker. The
runner acknowledges that gate before importing torch; the broker confirms the
acknowledgement to the launcher. The launcher then returns immediately without
waiting for calibration results.

Any timeout, lease loss, exception, or pre-readiness exit claims a create-once
technical-failure/not-run terminal state. The only final Stage B path is
`terminal_success/stage_b.json`. Stage B, all four native realizations, and
status are hidden in a staging directory and exposed together by one atomic rename.
A failure claim and `terminal_success` cannot coexist.

Stage B is preceded by independent digest/shape/dtype/row/payload reconstruction
of all 16 cached evaluations, all four saved per-unit pooling arrays, all 16
counterfactual pairs, and exact tolerance-selection recomputation. Loaded
libraries are captured again after all forwards immediately before completion.
Confirmation scoring and Stage C remain not run.
