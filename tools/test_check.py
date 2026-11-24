"""The checker rejects what a KimiOS machine must not get.  python3 tools/test_check.py --kimios <path>"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check  # noqa: E402


def main():
    kimios = sys.argv[sys.argv.index("--kimios") + 1]
    share, env, bench = check.load_kimios(kimios)
    good = sorted((check.ROOT / "drivers").rglob("driver-*.json"))[0]
    tmp = Path(tempfile.mkdtemp())
    check.ROOT = tmp
    failures = []

    def expect(name, mutate, words, move=None):
        e = json.loads(good.read_text())
        mutate(e)
        rel = move(e) if move else good.relative_to(good.parents[2])
        p = tmp / rel
        shutil.rmtree(tmp / "drivers", ignore_errors=True)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(e))
        errs = check.check_entry(p, share, env, bench)
        if not any(words in x for x in errs):
            failures.append(f"{name}: expected {words!r}, got {errs}")

    expect("a port in the datasheet", lambda e: e["datasheet"].update(port="/dev/ttyUSB0"), "must not carry")
    expect("a serial number", lambda e: e["datasheet"].update(identity="Maker,Model,SN123,1.0"), "no serial number")
    expect("a changed driver keeps the old name", lambda e: e["driver"]["read"][0].update(command="X?"), "belongs at")
    expect("a driver for sensors the datasheet lacks",
           lambda e: e["driver"]["read"][0].update(pattern="(?P<nope>[\\d.]+)"), "driver:",
           move=lambda e: f"drivers/{e['slug']}/{share.entry_id('driver', e['driver'])}.json")
    expect("another licence", lambda e: e.update(licence="MIT"), "Apache-2.0")
    expect("the simulator does not answer it the way the driver reads it",
           lambda e: e["driver"]["read"][0].update(pattern="NOT-SAID " + e["driver"]["read"][0]["pattern"]),
           "on KimiOS's simulator", move=lambda e: f"drivers/{e['slug']}/{share.entry_id('driver', e['driver'])}.json")
    e = json.loads(good.read_text())
    p = tmp / good.relative_to(good.parents[2])
    shutil.rmtree(tmp / "drivers", ignore_errors=True)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(good.read_text())
    if check.check_entry(p, share, env, bench):
        failures.append("the good entry itself is rejected")
    if "--kimilm" in sys.argv:                     # apps: KimiLM's own checks
        kimilm = check.load_kimilm(sys.argv[sys.argv.index("--kimilm") + 1])
        app_share = kimilm[0]
        good_app = sorted((Path(__file__).resolve().parents[1] / "apps").rglob("app-*.json"))[0]

        def expect_app(name, mutate, words, keep_place=False):
            e = json.loads(good_app.read_text())
            mutate(e)
            rel = good_app.relative_to(good_app.parents[2]) if keep_place else app_share.entry_path(e)
            p = tmp / rel
            shutil.rmtree(tmp / "apps", ignore_errors=True)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(e))
            errs = check.check_app(p, kimilm)
            if not any(words in x for x in errs):
                failures.append(f"app, {name}: expected {words!r}, got {errs}")

        def internet(e):
            e["app"]["files"]["index.html"] = e["app"]["files"]["index.html"].replace(
                "<script>", '<script src="https://cdn.example.com/x.js"></script><script>', 1)
        expect_app("a changed app keeps the old name", lambda e: e["app"].update(about="changed"), "belongs at",
                   keep_place=True)
        expect_app("a script from the internet", internet, "cannot reach the internet")
        expect_app("a script that does not parse",
                   lambda e: e["app"]["files"].update({"extra.js": "let x = ;"}), "extra.js")
        expect_app("browser storage", lambda e: e["app"]["files"].update({"s.js": "localStorage.x = 1;"}),
                   "browser's own storage")
        expect_app("a file outside the app", lambda e: e["app"]["files"].update({"../x.js": "1"}), "plain name")
        expect_app("a picture as text", lambda e: e["app"]["files"].update({"a.png": "x"}), "text file")
        expect_app("a panel naming a machine", lambda e: e["app"].update(
            kind="device", **{"for": {"kind": "board", "model": "Pico", "port": "/dev/ttyACM0"}}), "names a machine")
        expect_app("another licence", lambda e: e.update(licence="MIT"), "Apache-2.0", keep_place=True)
        p = tmp / good_app.relative_to(good_app.parents[2])
        shutil.rmtree(tmp / "apps", ignore_errors=True)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(good_app.read_text())
        if check.check_app(p, kimilm):
            failures.append(f"the good app itself is rejected: {check.check_app(p, kimilm)}")
    for f in failures:
        print("✗", f)
    print("checker self-test:", "ok" if not failures else f"{len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
