# Contributing

Thanks for your interest in improving **Altium Designer JLCPCB Libraries**! 🎉
Contributions of every size are welcome. If you're not sure where to start,
[open an issue](https://github.com/rmtech1/altium-designer-jlcpcb-libraries/issues)
and say hi.

## Ways to help

- **Test on your setup.** Report your Altium version, and whether the DbLib,
  update and `fab` output worked for you.
- **Report bugs.** Include the command you ran, the full output, and if
  possible a small sample BOM or Pick & Place CSV with private data removed.
- **Improve parsing.** Upstream JLCPCB data has many description formats.
  Examples where a value or category is parsed wrong are very useful.
- **Add features.** See the roadmap in the README.
- **Improve the docs.** Screenshots of the Altium setup steps would help new
  users a lot.

## Development setup

```bash
git clone https://github.com/<you>/altium-designer-jlcpcb-libraries
cd altium-designer-jlcpcb-libraries
python -m unittest discover -s tests -v
```

Development needs only Python 3.11+. The tool uses the standard library
only, so please keep it that way. Optional integrations, like
`easyeda2kicad`, are called as external tools.

## Project layout

| Path | Purpose |
|---|---|
| `jlc_altium/source.py` | Reads the upstream jlcparts SQLite and CDFER CSV dumps |
| `jlc_altium/categorize.py` | Decides which generic table a part belongs in and parses values |
| `jlc_altium/build.py` | Writes the Altium SQLite database |
| `jlc_altium/dblib.py` | Writes the `.DbLib` file |
| `jlc_altium/parts.py` | `fetch` and `link` for custom parts |
| `jlc_altium/lookup.py` | `search` and `check` |
| `jlc_altium/fab.py` | Converts files to JLCPCB BOM and CPL format |
| `tests/` | Unit tests that run on synthetic data |

## Pull requests

1. Fork the repo and create a branch from `main`.
2. Keep changes focused, one topic per PR.
3. Add or update tests for behaviour changes.
4. Run `python -m unittest discover -s tests` before pushing. CI runs the
   tests on Linux and Windows.
5. Describe *what* changed and *why*, and how you tested it. Mention it if
   you tested in Altium.

## Guidelines

- Correctness over coverage: a part should only get a generic symbol if
  every part in that family is guaranteed to share its pinout.
- Match the existing code style and comment density.
- Don't commit generated files (`library/*.sqlite`, `*.DbLib`, downloads).

By contributing, you agree that your contributions are licensed under the
[MIT License](LICENSE).
