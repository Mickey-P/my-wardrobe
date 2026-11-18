# Skills review — candidates only

**Status:** Discussion required; no skills installed or added.  
**Last reviewed:** 2026-11-18

Skills can provide useful repeatable workflows, but their instruction files are executable guidance for the agent and may contain unsafe or irrelevant instructions. Do not install or enable one based only on a name, description, search result, or project keyword.

## Candidate areas

| Area | Possible benefit | Project stage |
| --- | --- | --- |
| React + TypeScript + Vite | Component boundaries, state handling, accessibility, frontend verification | F04/F05/F06 |
| Python + FastAPI + SQLAlchemy | Router/schema/service patterns, migrations, async testing, API contract checks | F01/F03/F07 |
| Cloudflare Workers + D1 + R2 | Deployment workflow, bindings, migrations, runtime troubleshooting | F08 |
| Application security / OWASP | Threat modeling, auth boundaries, upload/archive/path validation, secret handling | F08/F09 |
| Test engineering | Fixture design, contract tests, import/export round trips, browser smoke checks | F01–F11 |

These are topics to evaluate, not endorsements of particular third-party skills. Official documentation and repository code may be preferable to adding a skill.

## Review gate before adding any skill

1. The project owner explicitly approves a specific skill and its source/repository.
2. Inspect its publisher, origin, version, permissions, install effects, and every instruction/resource it loads.
3. Check for instructions to reveal credentials/data, access unrelated paths, run opaque scripts, disable safety controls, or override user/developer/system instructions. Reject the skill if present or unclear.
4. Keep it disabled until its exact content and behavior have been reviewed; install only the agreed skill, scoped to this project if supported.
5. Re-review updates before accepting them. Never put wardrobe data, secrets, or tokens into skill prompts or telemetry.

## Decision log

- 2026-11-18: candidates recorded for discussion only. No skill files were installed, copied, or added to the repository.
