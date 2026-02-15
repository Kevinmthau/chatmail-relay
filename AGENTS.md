# AGENTS.md instructions for /Users/kevinthau/chatmail-relay

<INSTRUCTIONS>
## Repo Rules (Do Not Ask User To Manually Edit Things)
- If the user requests a behavior/policy change, implement all required code/config/test/deploy changes in-repo. Avoid telling the user to "edit X config" or "restart Y" as a manual step.
- If a server-side change is required and the SSH target is known/configured, apply it via SSH and record what changed in **Critical Updates** below.

## Account Creation Policy (Critical)
- Username (email localpart before `@`) length must be **2 to 9 characters**.
  - This is enforced via `username_min_length` / `username_max_length` in the generated `chatmail.ini` defaults and by `chatmaild.doveauth.is_allowed_to_create()`.

## Critical Updates (Append-Only Log)
- 2026-02-15: Set default username length limits to **2..9** (was 3..32) by updating `chatmaild/src/chatmaild/ini/chatmail.ini.f` and adjusting related tests.
- 2026-02-15: `cmdeploy` now enforces `username_min_length=2` and `username_max_length=9` in `chatmail.ini` automatically when running commands that load config.
- 2026-02-15: Updated live VM `chatmail.fun` config `/usr/local/lib/chatmaild/chatmail.ini` from `username_min_length=9` to `2` (kept `username_max_length=9`) and restarted `doveauth`.

## Keeping This File Updated
- When making a critical change (security, account creation/auth, deploy behavior, config defaults, data migrations), add a dated entry to **Critical Updates** in the same PR/commit.

## Skills
A skill is a set of local instructions to follow that is stored in a `SKILL.md` file. Below is the list of skills that can be used. Each entry includes a name, description, and file path so you can open the source for full instructions when using a specific skill.
### Available skills
- skill-creator: Guide for creating effective skills. This skill should be used when users want to create a new skill (or update an existing skill) that extends Codex's capabilities with specialized knowledge, workflows, or tool integrations. (file: /Users/kevinthau/.codex/skills/.system/skill-creator/SKILL.md)
- skill-installer: Install Codex skills into $CODEX_HOME/skills from a curated list or a GitHub repo path. Use when a user asks to list installable skills, install a curated skill, or install a skill from another repo (including private repos). (file: /Users/kevinthau/.codex/skills/.system/skill-installer/SKILL.md)
### How to use skills
- Discovery: The list above is the skills available in this session (name + description + file path). Skill bodies live on disk at the listed paths.
- Trigger rules: If the user names a skill (with `$SkillName` or plain text) OR the task clearly matches a skill's description shown above, you must use that skill for that turn. Multiple mentions mean use them all. Do not carry skills across turns unless re-mentioned.
- Missing/blocked: If a named skill isn't in the list or the path can't be read, say so briefly and continue with the best fallback.
- How to use a skill (progressive disclosure):
  1) After deciding to use a skill, open its `SKILL.md`. Read only enough to follow the workflow.
  2) When `SKILL.md` references relative paths (e.g., `scripts/foo.py`), resolve them relative to the skill directory listed above first, and only consider other paths if needed.
  3) If `SKILL.md` points to extra folders such as `references/`, load only the specific files needed for the request; don't bulk-load everything.
  4) If `scripts/` exist, prefer running or patching them instead of retyping large code blocks.
  5) If `assets/` or templates exist, reuse them instead of recreating from scratch.
- Coordination and sequencing:
  - If multiple skills apply, choose the minimal set that covers the request and state the order you'll use them.
  - Announce which skill(s) you're using and why (one short line). If you skip an obvious skill, say why.
- Context hygiene:
  - Keep context small: summarize long sections instead of pasting them; only load extra files when needed.
  - Avoid deep reference-chasing: prefer opening only files directly linked from `SKILL.md` unless you're blocked.
  - When variants exist (frameworks, providers, domains), pick only the relevant reference file(s) and note that choice.
- Safety and fallback: If a skill can't be applied cleanly (missing files, unclear instructions), state the issue, pick the next-best approach, and continue.
</INSTRUCTIONS>
