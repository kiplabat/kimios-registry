# Proposing an entry

The easy way is from a KimiOS machine: ask the agent to share the driver or controller. It prepares the entry and
gives you a link. Read the entry on GitHub, then press **Propose changes**.

By hand:
1. Put the file at `drivers/<model>/driver-<id>.json` or `controllers/<model>/controller-<id>.json`. If the name
   is wrong, `tools/check.py` says the right one.
2. Before you propose it, check that it names nothing of yours:
   - no device id, port or serial number in the datasheet;
   - in the note, nothing private about where the device is or who uses it.
3. Open a pull request. The check must pass. A maintainer looks at:
   - the note: does it say what the entry is for?
   - the datasheet's limits: are they sensible for that model?
   - the evidence: what showed it works?

Entries for real devices say so in `evidence.on`. Controllers can carry measured `results` (time in band,
starts per hour, energy) so others can compare.

## Apps

From KimiLM: open the app, press **Share** in its bar, read the entry and propose it. By hand: put the file at
`apps/<name>/app-<id>.json` (`tools/check.py` says the right name). A maintainer plays the game or opens the panel
before merging, and checks that the note and the request say what it does.
