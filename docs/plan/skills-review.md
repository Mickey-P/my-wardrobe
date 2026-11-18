# Skills review

**Status:** Project-local workflows identified; no external skills proposed or installed.

**Last reviewed:** 2026-11-18

Use an existing project-local workflow when it fits the work. Consider adding an external skill only to fill a concrete gap in a roadmap feature. Skill instructions are executable guidance; names and descriptions alone are not evidence of safety or fit.

## Available project-local workflows

| Skill | Use | Project guardrail |
| --- | --- | --- |
| `brainstorming` | Clarify scope and design before new behavior | Get approval before implementation. |
| `writing-plans` | Turn an approved design into a multi-step implementation plan | Keep the plan aligned with the relevant feature plan and its acceptance checks. |
| `executing-plans` | Implement an approved plan task by task | Run the feature's required checks and record evidence before changing status. |
| `cloudflare-deploy` | Guide Cloudflare deployment work | F08 only; do not deploy, use remote bindings, or import personal data without explicit authorization and verified Access protection. |
| `security-best-practices` | Provide language-specific security guidance when explicitly requested | Use alongside F09 acceptance criteria; do not treat it as deployment or security approval. |

These are already available in the project; this review does not install or copy them. Use only relevant workflows, not every skill for every feature.

## Areas to evaluate when a feature needs help

| Area | Potential gap | Roadmap stage |
| --- | --- | --- |
| React + TypeScript + Vite | Component boundaries, state handling, accessibility, frontend verification | F04/F05/F06 |
| Python + FastAPI + SQLAlchemy | Router/schema/service patterns, migrations, async testing, API contract checks | F01/F03/F07 |
| Cloudflare Workers + D1 + R2 | Bindings, migrations, runtime troubleshooting | F08 |
| Application security | Threat modeling, auth boundaries, upload/archive/path validation, secret handling | F08/F09 |
| Test engineering | Fixtures, contract tests, import/export round trips, browser smoke checks | F01–F11 |

These are evaluation areas, not endorsements of third-party skills. Prefer existing project patterns, tests, and official documentation when they cover the need.

## Review gate before adding an external skill

1. Identify a concrete feature need that existing project workflows, code, tests, and official documentation do not cover.
2. The project owner explicitly approves a specific skill and its source/repository.
3. Inspect its publisher, origin, version, permissions, install effects, and every instruction/resource it loads.
4. Reject it if it asks to reveal credentials or data, access unrelated paths, run opaque scripts, disable safety controls, or override higher-priority instructions. Reject it if behavior remains unclear.
5. Keep it disabled until its exact content and behavior have been reviewed; install only the agreed skill, scoped to this project if supported.
6. Re-review updates before accepting them. Never put wardrobe data, secrets, or tokens into skill prompts or telemetry.

## Decision log

- 2026-11-18: recorded project-local workflows and external-skill review criteria. No external skill files were installed, copied, or added to the repository.
- 2026-11-18: removed `web-artifacts-builder` from the project because it targets Claude `claude.ai` HTML artifacts rather than this React/Vite workspace and adds irrelevant setup and bundling workflows.
