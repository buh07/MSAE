REPRO: OK
  seeds        : ok — config seed 20260803 drives Python random, NumPy, torch CPU, and all CUDA devices in scripts/run_atlas_rope_v4.py:140-147
  determinism  : ok — deterministic algorithms are enabled and runtime-attested; score-bearing inputs use frozen canonical order and contiguous batches
  paths        : ok — no /Users, /home, C:\\, or /mnt literals occur in the attempt-8 technical source/config inventory
  secrets      : ok — no credential literals found; the signer is accepted as a filesystem argument and private-key bytes are never logged
  env pinned   : ok — requirements-atlas.lock.txt SHA-256 fc8cc0ff7551fc7c9d0fd7cdb8b3376f6791ac0a173eec293607bd839afd6834; the no-forward runtime probe binds Python, Torch, Transformers, CUDA, cuDNN, GPU UUID, SDPA flags, and loaded-library hashes
  data version : ok — raw provenance SHA-256 703969c8efc709b195bb2fe01223037e841491ec9beb5165d79d89dc63a0d905; prescore manifest SHA-256 a8e4824589bc4dff9e83a1aa1e5731a097d1a9312c66191a76dec0548f5a340b; independent rebuild report SHA-256 b46de7fe9ab0ab7f77908c12655fc0bf1cc286a6d68ae5e21110052a8b99da6a with zero mismatches

Scope: attempt-8 technical implementation before any model-weight load or neural forward. This hygiene review does not validate scientific claims.
