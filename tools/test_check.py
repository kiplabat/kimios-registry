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
    for f in failures:
        print("✗", f)
    print("checker self-test:", "ok" if not failures else f"{len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
