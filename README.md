# KimiOS registry: drivers, controllers and apps, shared on purpose

When an agent on a [KimiOS](https://github.com/kiplabat/KimiOS) machine gets a device working, through a driver it
wrote and tested or a controller the guard accepted, the person can share it here. The next machine that meets
the same model starts from it instead of from nothing.

```
drivers/<model>/driver-<id>.json           a driver manifest that passed its test on a device of that model
controllers/<model>/controller-<id>.json   a controller spec the guard accepted for that model
apps/<name>/app-<id>.json                  a control panel or game built in KimiLM (its files as text)
index.json                                 every entry that passes the checks (rebuilt on main; do not edit)
```

Each entry contains:
- the model;
- the shape it fits (the datasheet's sensor and output names);
- the datasheet it was written for, with the limits the guard holds the device to;
- what showed it works (a passed test, measured time in band, starts per hour…).

`<model>` is the model's name in lower case, with dashes. `<id>` is derived from the driver or controller itself,
so the same one shared twice lands in the same file.

## How it is used

- **Finding.** On a KimiOS machine, agents ask with `driver(action="find")` or `controller(action="find")`.
- **Getting.** `get` downloads an entry and checks it against `index.json`'s sha256. Then:
  - a driver is **tested on the device** first (the test moves nothing) and promoted only if it passes;
  - a controller is checked against the machine's own datasheet, and the guard holds it to that datasheet's
    limits, whatever the entry says.

  So a driver or controller from here never runs without passing on the machine first.
- **Sharing.** `share` writes the entry on the machine and gives the person a link to this repository's "new
  file" page with the entry filled in. They read it and press **Propose changes**, which opens a pull request.
  Nothing is sent without that, and no GitHub sign-in is kept on the machine.

## Apps

[KimiLM](https://github.com/kiplabat/KimiLM) builds **apps**: control panels for devices and games, made by a model
from a description. In an app's bar, **Share** writes its entry (the app's files as text, its name, icon, the
request it was built from and the model that built it) and opens this repository's page for a new file, or the
upload page when the entry is too long for a link; the person proposes it. **Apps → From the registry** lists
what is here and installs it after checking it against `index.json`'s sha256. An installed app runs in KimiLM's
sandbox like any other: no internet, and nothing reaches a device without the person's yes. A control panel names
only the kind and model of device it was made for; it is bound to a device on the machine that installs it.

Apps are checked with KimiLM's own code (`dva/app_share.py`, `dva/apps.py`): place and name, JSON of at most
512 KB, Apache-2.0, text files only with `index.html`, scripts that parse (Node.js), no browser storage, nothing
that reaches the internet.

## What is checked

`tools/check.py` runs on every pull request with KimiOS's own code, so the registry accepts exactly what a KimiOS
machine would use:
- the entry's place and name;
- JSON, at most 64 KB, licensed Apache-2.0;
- the datasheet passes KimiOS's datasheet check and names no machine (no device id, port or serial number);
- a driver passes the manifest check, a controller the spec check;
- a driver for a simulated device is also run against KimiOS's simulator of that model.

A maintainer reviews everything else before merging: does the note say what it is for, and are the datasheet's
limits sensible for that model?

```
git clone https://github.com/kiplabat/KimiOS ../KimiOS
git clone https://github.com/kiplabat/KimiLM ../KimiLM
python3 tools/check.py --kimios ../KimiOS/system_files/usr/libexec/kimios --kimilm ../KimiLM/engine
```

## Licence

Apache-2.0 ([LICENSE](LICENSE)). By proposing an entry you agree to share it under that licence.
