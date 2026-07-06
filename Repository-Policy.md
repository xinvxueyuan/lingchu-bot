# Repository Policy — License Compliance

> English | [中文](.github/note/Repository-Policy-zh.md)

This project uses a **phased open-source license stack** with an automatic
transition between two phases. The transition is described under
[License Stack and Transition](#license-stack-and-transition) and is
made legally executable by the relicensing grant in
[`CLA.md`](CLA.md).

## License Stack and Transition

### Current Phase (effective from project inception)

| Subject | License | SPDX identifier |
| --- | --- | --- |
| Software code | GNU Lesser General Public License v3.0 or later | `LGPL-3.0-or-later` |
| Documentation | GNU Free Documentation License v1.3 or later | `GFDL-1.3-or-later` |
| Visual elements | CC0 1.0 Universal Public Domain Dedication | `CC0-1.0` |

### Future Phase

| Subject | License | SPDX identifier |
| --- | --- | --- |
| Software code | MIT License or later, **or** Apache License 2.0 or later (user-elected dual) | `MIT-or-later OR Apache-2.0-or-later` |
| Documentation | Creative Commons Attribution-ShareAlike 4.0 International or later | `CC-BY-SA-4.0-or-later` |
| Visual elements | Creative Commons Attribution-ShareAlike 4.0 International or later | `CC-BY-SA-4.0-or-later` |

> Note: `pyproject.toml` uses the canonical SPDX form (`MIT OR Apache-2.0`, `CC-BY-SA-4.0`) for PEP 639 / `uv build` validation; the `-or-later` form above expresses the project's intended "or later" semantics.

### Transition Rules

- The **transition trigger** is the earlier of:
  1. **One year after the first public release** of the Project (the first
     non-pre-release published, e.g. `1.0.0`, not `0.x` or `rc` / `alpha`
     / `beta`); or
  2. The **first major version bump** of the Project (a SemVer `x.0.0`
     release).
- The transition **only applies to contributions submitted on or after
  the trigger date**. Contributions made before the trigger date remain
  under the license that was in effect at the time of submission.
- The transition is **one-way**: the Project does not return to the
  current-phase stack once the future phase is entered.
- The transition is **legally executable** because each contributor accepts
  the relicensing grant in [`CLA.md`](CLA.md) at submission time. The
  trigger itself does not require a separate re-licensing commit.
- The Project may at any time make the trigger date explicit in this
  document for clarity; the absence of an explicit trigger date does not
  defer the legal effect of the transition once either condition above is
  met.

Users must comply with the terms and conditions of the license that is
in effect for the relevant contribution at the time of its submission.

## Release Records

- `0.0.1` (2026-07-06): first formal 0.x release for the current LGPL/GFDL/CC0 phase. This release does not trigger the future phase because the transition rule treats the first public release example as `1.0.0` and excludes `0.x`.

## Media File Anonymization Requirements

For media files in this project (including but not limited to images, audio, video, etc.) that are not explicitly marked as licensed under CC0 1.0 Universal Public Domain Dedication, anonymization (desensitization) processing is required before use.

Anonymization processing includes but is not limited to:

1. Removing or blurring all personally identifiable information
2. Processing faces, license plates, and other recognizable features
3. Deleting or replacing sensitive location information
4. Anonymizing any data that could identify individuals or entities

## Compliance Guidelines

- Only media files marked as CC0 1.0 may be used directly without anonymization
- When using non-CC0 1.0 media files, anonymization must be completed while complying with the applicable license
- Derivative media files that have been anonymized must still comply with the original license terms
- Users bear full responsibility for the compliance of their anonymization processing

## Disclaimer

Project maintainers are not responsible for any privacy infringement, legal disputes, or losses arising from users' failure to properly anonymize content. Consulting a legal professional before use is recommended.

## License Texts

Full license texts are available at the following files in the repository
root and at the canonical upstream URLs:

### Current phase texts

- LGPL-3.0-or-later: [`LICENSE-code`](LICENSE-code), `https://www.gnu.org/licenses/lgpl-3.0.html`
- FDL-1.3-or-later: [`LICENSE-docs`](LICENSE-docs), `https://www.gnu.org/licenses/fdl-1.3.html`
- CC0 1.0 Universal: [`LICENSE-cc0`](LICENSE-cc0), `https://creativecommons.org/publicdomain/zero/1.0/`

### Future phase texts

- MIT or later: [`LICENSE-mit`](LICENSE-mit), `https://opensource.org/licenses/MIT`
- Apache License 2.0 or later: [`LICENSE-apache`](LICENSE-apache), `https://www.apache.org/licenses/LICENSE-2.0`
- CC BY-SA 4.0 or later: [`LICENSE-cc-by-sa`](LICENSE-cc-by-sa), `https://creativecommons.org/licenses/by-sa/4.0/legalcode`

### Contributor agreement

- [`CLA.md`](CLA.md) (Chinese mirror: [`.github/note/CLA-zh.md`](.github/note/CLA-zh.md))

### REUSE compliance

The repository root contains a [`REUSE.toml`](REUSE.toml) file declaring FSFE REUSE 3.0 license annotations for every file class (source code, documentation, visual elements, configuration, and scripts). The annotations map each glob to the SPDX identifier of its current-phase license and attach a copyright line. Run `uv tool run reuse lint` (or `pipx run reuse lint`) to verify compliance locally before submitting a contribution that adds or moves files.

This anonymization statement is intended to ensure that users respect privacy rights and applicable laws when using media files from this project. For any questions, please contact the project maintainers for more information.
