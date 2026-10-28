"""append_layer.py REPO SRC_REF NEW_TAG FILE:PATH_IN_IMAGE LABEL=VALUE ENV:KEY=VALUE... : add one small file layer to an image that is
already in GHCR, entirely through the registry API (no pull, no docker): every existing layer blob stays byte-identical,
the config gets the new diff_id, a history entry and the given label overrides, and the new manifest is pushed as NEW_TAG.
ENV:KEY=VALUE sets (or replaces) one environment variable of the image config. Prints the new manifest digest. Token: /root/.config/registry/ghcr_token (never printed). Only for single-platform
docker v2 / OCI image manifests, as pushed by `docker push`."""
import base64
import gzip
import hashlib
import io
import json
import sys
import tarfile
import urllib.request

REG = "https://ghcr.io"
USER = "flextra19"
repo, src_ref, new_tag = sys.argv[1], sys.argv[2], sys.argv[3]
envs = [a[4:] for a in sys.argv[4:] if a.startswith("ENV:")]
files = [a for a in sys.argv[4:] if not a.startswith("ENV:") and ":" in a and "=" not in a.split(":")[0]]
labels = dict(a.split("=", 1) for a in sys.argv[4:] if a not in files and not a.startswith("ENV:"))
tok = open("/root/.config/registry/ghcr_token").read().strip()


def bearer():
    req = urllib.request.Request(f"{REG}/token?service=ghcr.io&scope=repository:{repo}:pull,push")
    req.add_header("Authorization", "Basic " + base64.b64encode(f"{USER}:{tok}".encode()).decode())
    return json.load(urllib.request.urlopen(req, timeout=60))["token"]


B = bearer()


def call(method, url, data=None, headers=None, raw=False):
    req = urllib.request.Request(url if url.startswith("http") else REG + url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {B}")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    r = urllib.request.urlopen(req, timeout=300)
    return r if raw else r.read()


ACCEPT = ("application/vnd.docker.distribution.manifest.v2+json, application/vnd.oci.image.manifest.v1+json")
r = call("GET", f"/v2/{repo}/manifests/{src_ref}", headers={"Accept": ACCEPT}, raw=True)
mtype = r.headers.get("Content-Type").split(";")[0]
manifest = json.loads(r.read())
assert manifest.get("layers") and manifest.get("config"), "not a single-platform image manifest"
config = json.loads(call("GET", f"/v2/{repo}/blobs/{manifest['config']['digest']}"))

# the new layer: a deterministic tar (fixed mtime/owner/mode) of the given files, gzip with mtime 0
buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tf:
    for spec in files:
        src, dst = spec.split(":", 1)
        data = open(src, "rb").read()
        ti = tarfile.TarInfo(dst.lstrip("/"))
        mode = 0o755 if dst.endswith(".sh") else 0o644  # shell scripts stay executable (entrypoints)
        ti.size, ti.mode, ti.mtime, ti.uid, ti.gid, ti.uname, ti.gname = len(data), mode, 0, 0, 0, "root", "root"
        tf.addfile(ti, io.BytesIO(data))
tar = buf.getvalue()
gz = io.BytesIO()
with gzip.GzipFile(fileobj=gz, mode="wb", mtime=0) as g:
    g.write(tar)
gzb = gz.getvalue()
diff_id = "sha256:" + hashlib.sha256(tar).hexdigest()
blob_digest = "sha256:" + hashlib.sha256(gzb).hexdigest()


def upload(blob: bytes, digest: str):
    r = call("POST", f"/v2/{repo}/blobs/uploads/", data=b"", raw=True)
    loc = r.headers["Location"]
    loc = (loc if loc.startswith("http") else REG + loc) + ("&" if "?" in loc else "?") + f"digest={digest}"
    call("PUT", loc, data=blob, headers={"Content-Type": "application/octet-stream"})


upload(gzb, blob_digest)
config["rootfs"]["diff_ids"].append(diff_id)
config.setdefault("history", []).append({"created": "2026-10-27T00:00:00Z",
                                         "created_by": "COPY " + " ".join(f.split(':', 1)[0] + " " + f.split(':', 1)[1] for f in files),
                                         "comment": "appended via registry API (tools/append_layer.py)"})
config["config"].setdefault("Labels", {}).update(labels)
for kv in envs:
    key = kv.split("=", 1)[0]
    env = [e for e in config["config"].get("Env") or [] if e.split("=", 1)[0] != key]
    config["config"]["Env"] = env + [kv]
if envs:
    config["history"].append({"created": "2026-10-28T00:00:00Z", "created_by": "ENV " + " ".join(envs),
                              "comment": "set via registry API (tools/append_layer.py)", "empty_layer": True})
cfg = json.dumps(config, separators=(",", ":")).encode()
cfg_digest = "sha256:" + hashlib.sha256(cfg).hexdigest()
upload(cfg, cfg_digest)
ltype = manifest["layers"][-1]["mediaType"]
manifest["layers"].append({"mediaType": ltype, "size": len(gzb), "digest": blob_digest})
manifest["config"] = {**manifest["config"], "size": len(cfg), "digest": cfg_digest}
man = json.dumps(manifest, separators=(",", ":"), indent=None).encode()
call("PUT", f"/v2/{repo}/manifests/{new_tag}", data=man, headers={"Content-Type": mtype})
print("layer", blob_digest, "diff_id", diff_id)
print("config", cfg_digest)
print("manifest sha256:" + hashlib.sha256(man).hexdigest(), "tag", new_tag, "type", mtype)
