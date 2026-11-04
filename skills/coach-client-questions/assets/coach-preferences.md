# Coach preferences — standing rules

Every coach skill reads this file at the start of a conversation. Rules here count as already
approved, so they skip the Decision Brief. Add rules when the coach says "make that a standing
rule". This copy (in the main `fitness-lifestyle-coach` skill) is the master: phase skills
installed next to it read this one. In Claude Code you can edit it; on claude.ai skill files are
read-only, so keep these rules in your Project instructions instead.

Format: `- <rule> (added <date>)`

## Where client files go

- Google Drive folder for client sheets: _not set yet — paste the folder link here_
- Claude Code with Google Drive for desktop — local path of that synced folder: _not set_ (e.g.
  `~/Library/CloudStorage/GoogleDrive-<you>/My Drive/Clients` on a Mac, `G:\My Drive\Clients` on
  Windows)
- Never save client files inside a git repository.

## Defaults

- Measurements: record in **centimetres or inches** — the client picks either on the Measurements
  tab and the sheet shows both. Default entry unit: cm (set `meta.units.length` to "in" for clients
  who measure in inches). Body weight in kg.
- Default check-in day: Sunday
- Default plan length: _not set_
- Default nutrition style when the intake is unclear: _not set_

## Training rules

- _none yet_

## Nutrition rules

- _none yet_

## Supplements & remedies rules

- _none yet (every supplement and remedy goes through the Decision Brief when a plan is built or
  changed; in answers to client questions they are flagged "Coach to confirm" instead)_

## Communication style

- English, plain and warm; Indian/British spelling.
