# reax-eng-v2: SN92 engine track v2 entry (UID 140)

An engine for the [REAX engine track v2](https://reax.co/competitions/faq/#faq-engine-v2) that serves **Blink text** and
**Jeffan-31b** (`ai.reax.engine.models=blink,jeffan`).

| | |
|---|---|
| UID / hotkey | 140 / `5GWdcbe5w4GNPK5eFp8DkoVbBSAGBtZ9GeFvwvR9gkFAbM3z` |
| Image | `ghcr.io/flextra19/reax-eng-v2@sha256:d4b5f6342dbd646aaf907fc90bc8169383ae73e52ab9022cce86debd460913bf` |
| Commitment | `reax-eng/1:dm-all:ghcr.io/flextra19/reax-eng-v2@sha256:d4b5f634…` |
| Built from | commit `267cbeb98581537fe7386ee3d1f97a3123b8a69d` of this repository (`ai.reax.engine.commit` label) |
| Parents | none (no files from other entries; the bases are the REAX reference images) |
| Natives | none added (no `.so` / `.cubin` of ours; only Python and shell files) |
| Weight-like data | none added (the copied Jeffan tree's `engine/scales` calibration JSON is removed in the build) |

The files in the image are byte-identical to the files at commit `267cbeb9`: `serve_blink.py` is `/opt/reax/engine/serve.py`,
`serve_jeffan.py` is `/opt/reax-j/engine/serve.py`, `dispatch.sh` is `/opt/reax/dispatch.sh`, and `IMAGE-README.md` is `/README.md` (added as the last layer through the registry API by
`tools/append_layer.py`; all earlier layers are those of the docker build at commit `f9c62c57`).

## What it changes

Both models run on the pinned REAX reference engines (vLLM 0.30.0 behind the REAX server), with the same vLLM flags, presets,
prompts and readout. The only change is in `engine/serve.py`. The reference scheduler thread collects the queued decisions,
calls `backend.run(batch)`, and for the vLLM backends that is `pool.map(_one, batch)`. That blocks until the slowest decision
of the step is back, and only then does it start the next step. With `X_NOBARRIER=1`, every queued decision goes straight to
the same `backend.pool` (the same `_one`, the same HTTP request to the same vLLM server) and is answered as soon as it is back.
Concurrency towards vLLM is still capped by the pool size (`--max-num-seqs`). vLLM keeps batch-invariant kernels
(`VLLM_BATCH_INVARIANT=1`, as in the reference), so the answers do not depend on which decisions are co-scheduled.

`serve_blink.py` and `serve_jeffan.py` are the reference `serve.py` of each tree after `tools/xpatch_serve.py`.
`X_NOBARRIER=ctl` reads the arm (`nobar` or reference) from `<socket dir>/ctl`; that mode is used only for in-container A/B.

## Measured (RTX PRO 6000 Blackwell Server Edition, gVisor, validator docker flags)

In-container A/B in one running engine: fresh validator-style decisions, concurrency 16, arms alternated in random order.

| model | reference | X_NOBARRIER | gain (95 % CI) | answers vs reference (512 fixed items) |
|---|---|---|---|---|
| Blink text | 66.3 dec/s | 97.5 dec/s | +47.6 % (+41.3 .. +53.9) | 512/512 byte-identical |
| Jeffan-31b | 20.8 dec/s | 25.6 dec/s | +22.9 % (+20.5 .. +25.3) | 512/512 byte-identical |

## Build

```
docker build --build-arg GIT_SHA=$(git rev-parse HEAD) -t reax-eng-v2 .
```

The bases are pinned by digest: `ghcr.io/reaxlabs/reax-engine-ref-blink@sha256:ab02e141…` (Blink text reference, engine 4230e50)
and `ghcr.io/reaxlabs/reax-engine-ref-jeffan@sha256:e98cc981…` (Jeffan reference, engine 3582925). `dispatch.sh` picks the tree
from `$REAX_MODEL`.

## Licence

Our changes are MIT (`LICENSE`). The reference engine code is under the REAX Engine License 1.1 (see `NOTICE` and `/licenses` in the image).
