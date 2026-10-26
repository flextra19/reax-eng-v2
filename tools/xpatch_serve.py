"""xpatch_serve.py SRC DST : copy a reference image's engine/serve.py and add a barrier-free dispatch for thread-pool backends
(vllm_readout: run() = pool.map(_one, batch) waits for the slowest item of a step before the next step starts).
  X_NOBARRIER=1    the scheduler thread hands every queued item straight to backend.pool (backend._one, the same HTTP call
                   to vLLM as the reference); each answer is delivered as soon as it is back. Numerics are untouched.
  X_NOBARRIER=ctl  in-container A/B (sim/ab_arms.py): the arm is read from <dir of RUNTIME_UDS>/ctl (polled every 20 ms);
                   "nobar" = per-item dispatch, anything else = the reference step loop (drain queue, run(batch), deliver).
Mount the result read-only over /opt/reax/engine/serve.py."""
import sys

src, dst = sys.argv[1], sys.argv[2]
t = open(src).read()
anchor = """    def _loop(self):
        be, q = self.backend, self.q
        if self._on_ready:  # warm-up on the thread that serves afterwards (CUDA graphs, compile caches are per thread)
            self._on_ready()
"""
assert t.count(anchor) == 1, "Scheduler._loop anchor"
add = """        xmode = os.environ.get("X_NOBARRIER", "")
        if xmode in ("1", "ctl") and hasattr(be, "pool") and hasattr(be, "_one"):
            print(f"serve: X_NOBARRIER={xmode} - per-item dispatch to the backend pool", flush=True)
            arm = {"v": "nobar"}
            if xmode == "ctl":
                ctl = os.path.join(os.path.dirname(os.environ.get("RUNTIME_UDS", "/run/reax/engine.sock")), "ctl")

                def _poll():
                    while True:
                        try:
                            arm["v"] = open(ctl).read().strip()
                        except OSError:
                            pass
                        time.sleep(0.02)
                threading.Thread(target=_poll, name="x-ctl", daemon=True).start()

            def _done(f, it):
                err = f.exception()
                it[1].call_soon_threadsafe(_deliver, [(it[2], None if err else f.result())], err)

            limit = be.max_batch_tokens
            while True:
                it = q.get()
                if arm["v"] == "nobar":
                    self.steps += 1
                    self.decisions += 1
                    self.tokens += it[0].n_tokens
                    be.pool.submit(be._one, it[0]).add_done_callback(lambda f, it=it: _done(f, it))
                    continue
                batch, n = [it], it[0].n_tokens  # reference step loop (max_wait 0), for the A/B control arm
                while len(batch) < self.max_items:
                    try:
                        nxt = q.get_nowait()
                    except queue.Empty:
                        break
                    if limit and n + nxt[0].n_tokens > limit:
                        q.put(nxt)  # rare (65536-token steps); requeued at the back instead of carried
                        break
                    batch.append(nxt)
                    n += nxt[0].n_tokens
                try:
                    res, err = be.run([b[0] for b in batch]), None
                except Exception as e:  # noqa: BLE001
                    res, err = None, e
                self.steps += 1
                self.decisions += len(batch)
                self.tokens += n
                by_loop: dict = {}
                for i, b in enumerate(batch):
                    by_loop.setdefault(b[1], []).append((b[2], None if err else res[i]))
                for lp, items in by_loop.items():
                    lp.call_soon_threadsafe(_deliver, items, err)
"""
t = t.replace(anchor, anchor + add)
open(dst, "w").write(t)
print("patched ->", dst)
