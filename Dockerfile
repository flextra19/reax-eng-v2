# REAX engine track v2 entry (UID 140): Blink text + Jeffan-31b. Both are the pinned REAX reference engines (vLLM 0.30.0, same
# base image) with one change: engine/serve.py hands every queued decision straight to the vLLM client pool instead of waiting
# for the whole step (pool.map) to finish. Same vLLM flags, same requests, same readout -> byte-identical answers in our tests
# (in-container A/B, fresh items, concurrency 16: Blink +47.6 %, Jeffan +22.9 %, 512/512 identical each).
# serve_blink.py / serve_jeffan.py = the reference serve.py of each tree patched by box/xpatch_serve.py (MIT for our changes;
# reference code: REAX Engine License 1.1, notices in /licenses). X_NOBARRIER=ctl switches arms for in-container A/B.
ARG BLINK=ghcr.io/reaxlabs/reax-engine-ref-blink@sha256:ab02e141ffb5672dc68e137736be0a6fa15445c7cc824a51f6ad2a6664c0e10a
ARG GIT_SHA=unknown
ARG JEFFAN=ghcr.io/reaxlabs/reax-engine-ref-jeffan@sha256:e98cc981a40013d243de6ea65147b823fc9cfb5655a00859dbc8de327b2634d6
FROM ${JEFFAN} AS jeffan
# engine/scales holds a calibration JSON (weight-like data for the file screen); the Jeffan path never reads it
RUN rm -rf /opt/reax/engine/scales
FROM ${BLINK}
COPY --from=jeffan /opt/reax /opt/reax-j
COPY --from=jeffan /licenses/jeffan /licenses/jeffan
COPY --from=jeffan /licenses/LICENSE /licenses/NOTICE /licenses/reax-engine-3582925/
COPY serve_blink.py /opt/reax/engine/serve.py
COPY serve_jeffan.py /opt/reax-j/engine/serve.py
COPY dispatch.sh /opt/reax/dispatch.sh
ENV X_NOBARRIER=1
ARG GIT_SHA
LABEL ai.reax.engine.hotkey="5GWdcbe5w4GNPK5eFp8DkoVbBSAGBtZ9GeFvwvR9gkFAbM3z" \
      ai.reax.engine.models="blink,jeffan" \
      ai.reax.engine.commit="${GIT_SHA}" \
      ai.reax.engine.base="ghcr.io/reaxlabs/reax-engine-ref-blink@sha256:ab02e141ffb5672dc68e137736be0a6fa15445c7cc824a51f6ad2a6664c0e10a (engine 4230e50) + ghcr.io/reaxlabs/reax-engine-ref-jeffan@sha256:e98cc981a40013d243de6ea65147b823fc9cfb5655a00859dbc8de327b2634d6 (engine 3582925)" \
      org.opencontainers.image.description="UID 140 engine track v2 entry: REAX reference engines for Blink text + Jeffan-31b with a barrier-free serve.py dispatch (X_NOBARRIER)" \
      org.opencontainers.image.source="https://github.com/flextra19/reax-eng-v2" \
      org.opencontainers.image.revision="${GIT_SHA}" \
      org.opencontainers.image.title="reax-eng-v2 (UID 140): Blink text + Jeffan" \
      org.opencontainers.image.licenses="LicenseRef-REAX-Engine-1.1 AND Apache-2.0 AND MIT"
ENTRYPOINT ["/opt/reax/dispatch.sh"]
