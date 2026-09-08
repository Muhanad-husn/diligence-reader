# atlas-names

Written by `python -m rlm.widen names samples/atlas samples/atlas-names`, from
`runs/atlas/sections.jsonl` as `tests/phase1-digests.json` pins it.

The knob is `names`. The room is 100 markdown documents, one section of the source per block,
under `data_room/`. The key keeps the source's ids, required documents, decoys, answer, rubric
and bar, and points its `documents` map at the new paths.

Facts: 53.

Facts dropped: none

## Names

The knob respells 15 names of people and organisations. A name carries a fixed tuple of
spellings and the spelling one document writes is drawn from seed 0, so the room spells every
name below in at least 3 ways. A name is replaced on a whole word only, never inside an email
address, a web address, a file path or any run of characters carrying a figure, so identifiers,
numbers and dates are untouched.

| name | spelling | documents |
|---|---|---|
| `Elena Marquez` | `ELENA MARQUEZ` | DR-006 |
| `Elena Marquez` | `elena marquez` | DR-001 |
| `Elena Marquez` | `E. Marquez` | DR-005 |
| `Elena Marquez` | `Marquez, Elena` | DR-014 |
| `Daniel Cho` | `DANIEL CHO` | DR-006, DR-094, DR-100 |
| `Daniel Cho` | `daniel cho` | DR-001, DR-013, DR-014 |
| `Daniel Cho` | `D. Cho` | DR-029, DR-098 |
| `Daniel Cho` | `Cho, Daniel` | DR-004, DR-018 |
| `Daniel Cho` | `Danile Cho` | DR-075, DR-097 |
| `Priya Raman` | `PRIYA RAMAN` | DR-001, DR-014, DR-069, DR-097, DR-098 |
| `Priya Raman` | `priya raman` | DR-003, DR-062, DR-086, DR-094 |
| `Priya Raman` | `P. Raman` | DR-052, DR-080, DR-082, DR-087 |
| `Priya Raman` | `Raman, Priya` | DR-006, DR-075, DR-088, DR-100 |
| `Priya Raman` | `Priya Ramna` | DR-004, DR-013, DR-029, DR-035 |
| `Owen Bell` | `OWEN BELL` | DR-013, DR-062, DR-100 |
| `Owen Bell` | `owen bell` | DR-004, DR-064 |
| `Owen Bell` | `O. Bell` | DR-001, DR-006 |
| `Owen Bell` | `Bell, Owen` | DR-014, DR-077 |
| `Owen Bell` | `Owen Blel` | DR-075, DR-095 |
| `Karl Webb` | `KARL WEBB` | DR-030, DR-098 |
| `Karl Webb` | `karl webb` | DR-081, DR-100 |
| `Karl Webb` | `K. Webb` | DR-004 |
| `Karl Webb` | `Webb, Karl` | DR-082 |
| `Karl Webb` | `Karl Wbeb` | DR-001 |
| `Grace Okafor` | `GRACE OKAFOR` | DR-051, DR-078, DR-079, DR-083 |
| `Grace Okafor` | `grace okafor` | DR-014, DR-044, DR-053, DR-075 |
| `Grace Okafor` | `G. Okafor` | DR-006, DR-046, DR-098, DR-100 |
| `Grace Okafor` | `Okafor, Grace` | DR-052, DR-061, DR-080, DR-084 |
| `Grace Okafor` | `Grace Okafro` | DR-001, DR-004, DR-013 |
| `Renata Castellano` | `RENATA CASTELLANO` | DR-100 |
| `Renata Castellano` | `renata castellano` | DR-070 |
| `Renata Castellano` | `R. Castellano` | DR-069 |
| `Renata Castellano` | `Castellano, Renata` | DR-001 |
| `VistaPort Media Inc` | `VISTAPORT MEDIA INC` | DR-005, DR-022, DR-029, DR-033, DR-034, DR-045, DR-053, DR-056, DR-066, DR-069, DR-074, DR-076, DR-080, DR-084, DR-086, DR-090 |
| `VistaPort Media Inc` | `vistaport media inc` | DR-002, DR-007, DR-010, DR-011, DR-014, DR-020, DR-031, DR-046, DR-047, DR-058, DR-059, DR-062, DR-070, DR-073, DR-083, DR-089 |
| `VistaPort Media Inc` | `VistaPort Media, Inc.` | DR-003, DR-009, DR-013, DR-016, DR-017, DR-021, DR-039, DR-042, DR-055, DR-057, DR-064, DR-065, DR-068, DR-075, DR-082 |
| `VistaPort Media Inc` | `Vista Port Media Inc` | DR-006, DR-008, DR-015, DR-035, DR-037, DR-040, DR-052, DR-063, DR-072, DR-077, DR-091, DR-092, DR-094, DR-097, DR-098 |
| `VistaPort Media Inc` | `VistaPort Meida Inc` | DR-001, DR-012, DR-018, DR-019, DR-023, DR-051, DR-060, DR-078, DR-079, DR-081, DR-085, DR-087, DR-088, DR-093, DR-095 |
| `VistaPort` | `VISTAPORT` | DR-023, DR-032, DR-046, DR-084, DR-092 |
| `VistaPort` | `vistaport` | DR-005, DR-018, DR-021, DR-080, DR-096 |
| `VistaPort` | `Vista Port` | DR-007, DR-019, DR-040, DR-041, DR-057 |
| `VistaPort` | `Vista-Port` | DR-020, DR-022, DR-035, DR-053, DR-095 |
| `VistaPort` | `Vistaprot` | DR-001, DR-015, DR-034, DR-056 |
| `Northstar Mobile Holdings plc` | `NORTHSTAR MOBILE HOLDINGS PLC` | DR-005 |
| `Northstar Mobile Holdings plc` | `Northstar Mobile Holdings` | DR-097 |
| `Northstar Mobile Holdings plc` | `North Star Mobile Holdings plc` | DR-015 |
| `Northstar Mobile Holdings plc` | `North-star Mobile Holdings plc` | DR-087 |
| `Meridian Media Agency` | `MERIDIAN MEDIA AGENCY` | DR-032, DR-043 |
| `Meridian Media Agency` | `meridian media agency` | DR-001, DR-072 |
| `Meridian Media Agency` | `Meridian Media` | DR-042, DR-085 |
| `Meridian Media Agency` | `Meridian-Media Agency` | DR-084 |
| `Meridian Media Agency` | `Meridian Meida Agency` | DR-035 |
| `Canton Street Capital` | `CANTON STREET CAPITAL` | DR-001 |
| `Canton Street Capital` | `canton street capital` | DR-010 |
| `Canton Street Capital` | `Canton Street` | DR-098 |
| `Canton Street Capital` | `Canton-Street Capital` | DR-002 |
| `Canton Street Capital` | `Cantno Street Capital` | DR-023 |
| `Brandt & Mauer LLP` | `BRANDT & MAUER LLP` | DR-072, DR-098 |
| `Brandt & Mauer LLP` | `brandt & mauer llp` | DR-001 |
| `Brandt & Mauer LLP` | `Brandt & Mauer` | DR-017 |
| `Brandt & Mauer LLP` | `Brandt-Mauer LLP` | DR-016 |
| `Brandt & Mauer LLP` | `Brandt & Muaer LLP` | DR-018 |
| `Helios Retail Group` | `HELIOS RETAIL GROUP` | DR-072, DR-085 |
| `Helios Retail Group` | `helios retail group` | DR-042, DR-084 |
| `Helios Retail Group` | `Helios Retail` | DR-001, DR-036 |
| `Helios Retail Group` | `Helios-Retail Group` | DR-032 |
| `Helios Retail Group` | `Helios Retial Group` | DR-043 |
| `Redbridge Risk Advisors` | `REDBRIDGE RISK ADVISORS` | DR-098 |
| `Redbridge Risk Advisors` | `redbridge risk advisors` | DR-081 |
| `Redbridge Risk Advisors` | `Redbridge Risk` | DR-084 |
| `Redbridge Risk Advisors` | `Redbridge-Risk Advisors` | DR-072 |
