#!/usr/bin/env python3
"""Check every entry in the registry, and build index.json.

    python tools/check.py --kimios ../KimiOS/system_files/usr/libexec/kimios --kimilm ../KimiLM/engine   # check
    python tools/check.py --kimios ../KimiOS/system_files/usr/libexec/kimios --kimilm ../KimiLM/engine --write-index

An entry is checked with KimiOS's own code (kimios_share.py, kimios_envelope.py), so the registry accepts exactly
what a KimiOS machine would use:
- its place: drivers/<model>/driver-<id>.json or controllers/<model>/controller-<id>.json, where <model> is the
  model's name as KimiOS spells it and <id> comes from the driver or controller itself (the same one twice is
  the same file);
- it is JSON, at most 64 KB, licensed Apache-2.0, and its shape is its datasheet's sensors and outputs;
- the datasheet keeps nothing that names a machine (no device id, port or serial number) and passes KimiOS's
  datasheet check;
- a driver passes KimiOS's manifest check against that datasheet, and a controller its spec check;
- for a simulated device, the driver is also run against KimiOS's simulator of that model and must pass its test.
Nothing here runs a real device.

Apps (control panels and games built in KimiLM, apps/<name>/app-<id>.json) are checked with KimiLM's own code
(kimilm/app_share.py, kimilm/apps.py): their place and name, JSON of at most 512 KB, Apache-2.0, text files only with
index.html, a panel's device described by kind and model only, and the same checks as a save in KimiLM (scripts
that do not parse, browser storage, anything that reaches the internet)."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {"schema", "kind", "model", "slug", "shape", "simulated", "driver", "controller", "datasheet", "evidence",
           "note", "kimios", "date", "licence"}


def load_kimios(path):
    sys.path.insert(0, str(Path(path).resolve()))
    import kimios_bench
    import kimios_envelope
    import kimios_share
    return kimios_share, kimios_envelope, kimios_bench


def load_kimilm(path):
    sys.path.insert(0, str(Path(path).resolve()))
    try:
        from kimilm import app_share, apps          # KimiLM 2.37.0 and later
    except ImportError:
        from dva import app_share, apps             # the package's name before 2.37.0
    return app_share, apps


def check_app(path, kimilm):
    """An app entry, with KimiLM's own checks."""
    app_share, apps = kimilm
    rel = path.relative_to(ROOT).as_posix()
    return app_share.check_entry(rel, path.read_bytes(), apps.check_files)


def check_entry(path, share, env, bench):
    rel = path.relative_to(ROOT).as_posix()
    errs = []
    data = path.read_bytes()
    if len(data) > share.MAX_ENTRY:
        return [f"{rel}: larger than 64 KB"]
    try:
        e = json.loads(data)
    except ValueError as exc:
        return [f"{rel}: not JSON ({exc})"]
    kind = e.get("kind")
    if kind not in share.KINDS or not isinstance(e.get(kind), dict):
        return [f"{rel}: kind is driver or controller, with the {kind or 'driver'} itself under that name"]
    extra = set(e) - ALLOWED
    if extra:
        errs.append(f"{rel}: unknown fields {sorted(extra)}")
    ds = e.get("datasheet")
    if not isinstance(ds, dict):
        return errs + [f"{rel}: datasheet is the datasheet the {kind} was written for"]
    try:
        want = f"{kind}s/{share.slug(e.get('model'))}/{share.entry_id(kind, e[kind])}.json"
    except share.ShareError as exc:
        return errs + [f"{rel}: {exc}"]
    if rel != want:
        errs.append(f"{rel}: belongs at {want}")
    if e.get("slug") != share.slug(e.get("model")) or ds.get("model") != e.get("model"):
        errs.append(f"{rel}: model, slug and the datasheet's model disagree")
    if e.get("shape") != share.shape(ds):
        errs.append(f"{rel}: shape is not the datasheet's sensors and outputs")
    if e.get("licence") != "Apache-2.0":
        errs.append(f"{rel}: licence must be Apache-2.0 (the registry's licence)")
    private = set(ds) - set(share.DATASHEET_KEEP) - {"identity"}
    if private:
        errs.append(f"{rel}: the datasheet must not carry {sorted(private)} (it would name a machine)")
    if share.public_datasheet(ds) != ds:
        errs.append(f"{rel}: the datasheet's identity is maker,model,,firmware (no serial number), or left out")
    errs += [f"{rel}: datasheet: {x}" for x in env.check_datasheet({**ds, "id": "registry-check"})]
    if kind == "driver":
        errs += [f"{rel}: driver: {x}" for x in env.check_manifest(e["driver"], ds)]
    else:
        errs += [f"{rel}: controller: {x}" for x in env.check_spec(e["controller"], ds)]
    if not errs and kind == "driver" and e.get("simulated"):
        sims = [n for n, cls in bench.MODELS.items() if cls.model == e["model"]]
        if not sims:
            errs.append(f"{rel}: simulated, but KimiOS has no simulator of {e['model']!r}")
        for name in sims:
            sim = bench.make(name, seed=1)
            res = env.test_driver(e["driver"], sim.datasheet(), env.DirectTransport(sim))
            errs += [f"{rel}: on KimiOS's simulator: {c['what']}: {c['detail']}" for c in res["checks"] if not c["ok"]]
    return errs


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kimios", required=True, help="KimiOS's system_files/usr/libexec/kimios")
    ap.add_argument("--kimilm", help="KimiLM's engine folder (checks apps)")
    ap.add_argument("--write-index", action="store_true")
    a = ap.parse_args(argv)
    share, env, bench = load_kimios(a.kimios)
    kimilm = load_kimilm(a.kimilm) if a.kimilm else None
    files = sorted(p for d in ("drivers", "controllers", "apps") for p in (ROOT / d).rglob("*") if p.is_file()
                   and p.name != ".gitkeep")
    errs, rows = [], []
    for p in files:
        if p.suffix != ".json":
            errs.append(f"{p.relative_to(ROOT)}: only .json entries belong here")
            continue
        if p.relative_to(ROOT).parts[0] == "apps":
            if kimilm is None:
                errs.append(f"{p.relative_to(ROOT)}: apps are checked with KimiLM's code (--kimilm)")
                continue
            found = check_app(p, kimilm)
            errs += found
            if not found:
                rows.append(kimilm[0].index_row(p.relative_to(ROOT).as_posix(), p.read_bytes()))
            continue
        found = check_entry(p, share, env, bench)
        errs += found
        if not found:
            e = json.loads(p.read_bytes())
            rows.append({"path": p.relative_to(ROOT).as_posix(), "kind": e["kind"], "model": e["model"],
                         "slug": e["slug"], "shape": e["shape"], "simulated": bool(e.get("simulated")),
                         "note": e.get("note", ""), "date": e.get("date"), "evidence": e.get("evidence"),
                         "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
    for x in errs:
        print("✗", x)
    print(f"{len(rows)} entries pass, {len(errs)} problems")
    if a.write_index:
        (ROOT / "index.json").write_text(json.dumps({"schema": 1, "entries": rows}, indent=1, ensure_ascii=False)
                                         + "\n", encoding="utf-8")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
