# atlas-unnamed

Written by `python -m rlm.widen unnamed samples/atlas samples/atlas-unnamed`, from
`runs/atlas/sections.jsonl` as `tests/phase1-digests.json` pins it.

The knob is `unnamed`. The room is 100 markdown documents, one section of the source per block,
under `data_room/`. The key keeps the source's ids, required documents, decoys, answer, rubric
and bar, and points its `documents` map at the new paths.

Facts: 48.

Facts dropped:

- `backup-object`: the value is the backup object's file name, now written as a phrase.
- `signing-key`: the value is the legacy signing key's name, now written as a phrase.
- `ticket`: the value is the reference the matter is tracked under, now written as a phrase.
- `workstream`: the value is the codename of the forensic workstream, now written as a phrase.
- `programme`: the value is the name of the user-facing programme, now written as a phrase.

## Phrases

The knob takes out the 7 identifiers the matter is named by and writes one plain phrase for
each, the same phrase in every document. Five of the phrases take an article and the two mass
phrases do not. Dates, record counts, amounts, people and organisations are untouched, and so
are the system names the room writes for the profile store and the authentication platform, the
deal codename, and the streaming organisation whose name resembles the codename of the
workstream and is a different organisation.

| phrase | documents |
|---|---|
| workstream | DR-001, DR-012, DR-013, DR-014, DR-030, DR-068, DR-069, DR-070, DR-075, DR-079, DR-080, DR-082, DR-086, DR-088, DR-095, DR-100 |
| ticket | DR-001, DR-013, DR-030, DR-060, DR-067, DR-068 |
| programme | DR-001, DR-004, DR-012, DR-014, DR-018, DR-021, DR-022, DR-023, DR-025, DR-029, DR-032, DR-033, DR-035, DR-036, DR-037, DR-039, DR-042, DR-043, DR-048, DR-050, DR-055, DR-058, DR-059, DR-060, DR-061, DR-080, DR-082, DR-095, DR-096, DR-100 |
| sign-in difficulty | DR-001, DR-048, DR-050, DR-059, DR-060 |
| account-security | DR-004, DR-012, DR-018, DR-023, DR-032, DR-033, DR-035, DR-037, DR-039, DR-042, DR-048, DR-055, DR-059, DR-060, DR-070, DR-080, DR-082, DR-086, DR-087, DR-095, DR-096, DR-100 |
| archive | DR-066, DR-068, DR-069, DR-071, DR-073 |
| signing key | DR-056, DR-065, DR-069, DR-074 |

4 documents are renamed, because a path that carries a name defeats the knob. The document ids
do not change.

- DR-059: `Programme_Project_Brief.pdf.md`
- DR-068: `Network_Quality_Ticket_Redacted.txt.md`
- DR-069: `Workstream_Phase1_Technical_Findings_Draft.pdf.md`
- DR-070: `Workstream_Executive_Summary_Final.pdf.md`
