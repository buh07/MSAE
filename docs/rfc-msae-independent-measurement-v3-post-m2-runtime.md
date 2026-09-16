# MSAE v3 post-M2 prescore and calibration runtime

## Scope

This continuation implements only M3--M5 of the exposed-source v3 technical
replication. It may freeze Stage A and launch the calibration replay. It may not
score C1/C2, create Stage C, select a paper branch, or reinterpret v1/v2.

## M2 result gate

M2 is complete only when a create-once completion manifest binds all seven M2
files and closes the four roles, 68 role/task cells, 34,000 maps, 500 finite
draws per cell, and the 36/20/11 correction populations. An independent review
must freeze the completion-manifest digest before M3.

## M3 and successor generation

The first post-M2 M3 preflight is terminally failed: its create-once config was
generated before the torch no-`RECORD` closure was repaired. It is never treated
as Stage-A-ready. A create-once `m3_preflight_attempt_1.json` binds the old
config, commitment, public key, private-key lstat identity, M2 pin, exact known
failure, and `model_gpu_tmux=not_run`.

All executable continuation state uses the explicit successor generation
`post_m2_gen2`, with separate config, provenance, key, nonce, review, and run
roots. The exact current user instruction is stored verbatim and hashed. Four
exact checkpoint lineages are registered: independent replicate seeds g4/g5/g6
and matched negative control g7.

The endpoint registry is generated from closed family, task, component, metric,
checkpoint, transform/control, and baseline products, then checked by an
independent typed-tuple product. C1 uses only raw/simple G1 operand names. C2
registers g4/g5/g6 and descriptive g7. The registry includes localization,
Tier-2 collateral, functional reproducibility, counterfactual
specificity/mapping controls, and all baselines.

The keypair, public commitment, nonce and shared GPU-lock directories are
create-once. A partial state blocks; a complete state is revalidated by object
identity, permissions, public/private agreement, scope, and the verbatim
instruction. No signature or execution authorization exists in M3.

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
`msae_independent_measurement_v3_post_m1.py` plus the runtime functions reached
by that CLI. The immutable controller's `__getattr__` compatibility exports of
the pre-continuation base module are historical M2 implementation details, not
public post-M2 commands; they are never named by the signed envelope, launcher,
review commands, or process registry. This prospectively narrows the base RFC's
"every public v3 entry point" wording: the CPU/no-model trace exercises the
controller `main`, runtime `dispatch`, every successor command, and runner, and
the static process registry rejects a base-module CLI route.

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
M=$(.venv-atlas/bin/python -S -B -I -c 'import hashlib; p="reports/provenance/msae_independent_measurement_v3_post_m2_gen2/prescore_candidate_manifest.json"; f=open(p,"rb"); print(hashlib.file_digest(f,"sha256").hexdigest()); f.close()')
[[ "$M" =~ ^[0-9a-f]{64}$ ]]
.venv-atlas/bin/python -S -B -I scripts/msae_independent_measurement_v3_post_m1.py prescore-traced-check \
  --manifest reports/provenance/msae_independent_measurement_v3_post_m2_gen2/prescore_candidate_manifest.json \
  --output "/tmp/msae_independent_measurement_v3_${M}.prescore.check.json" \
  --trace "/tmp/msae_independent_measurement_v3_${M}.prescore.trace.log"
.venv-atlas/bin/python -S -B -I scripts/msae_independent_measurement_v3_post_m1.py verify-prescore-trace \
  --manifest reports/provenance/msae_independent_measurement_v3_post_m2_gen2/prescore_candidate_manifest.json \
  --check "/tmp/msae_independent_measurement_v3_${M}.prescore.check.json" \
  --trace "/tmp/msae_independent_measurement_v3_${M}.prescore.trace.log"
```

Both invocations require isolated, no-site Python (`-S -B -I`). The two output
names are exact functions of the candidate-manifest digest and must be absent
before the first command.

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
