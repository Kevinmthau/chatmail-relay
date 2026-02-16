# AGENTS.md instructions for /Users/kevinthau/chatmail-relay

<INSTRUCTIONS>
## Project Goal
- Provide an iMessage-style chat experience where users can share their `@chatmail.fun` address and send/receive both:
  - Regular IMAP email messages
  - Delta Chat messages
  in a single unified inbox.
- Delta Chat functionality is for chat between `@chatmail.fun` addresses and supports additional features such as encryption plus delivered/read/typing indicators.

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
- 2026-02-15: Added admin accounts listing page at `GET /admin/accounts` plus a vmail-run helper (`chatmail-admin-accounts-helper`) and matching sudoers rule deployed by `cmdeploy` for listing existing accounts.
- 2026-02-15: Made `GET /admin` show the accounts list with a "Create new" button; `GET /admin/accounts` now redirects to `/admin`.
- 2026-02-15: Fixed macOS deploy compatibility: made `cmdeploy` a regular package by adding `cmdeploy/src/cmdeploy/__init__.py` (so `importlib.resources` works), and removed rsync `--chown` usage from website deploy (now does a remote `chown -R www-data:www-data /var/www/html` after upload).
- 2026-02-15: Updated `chatmaild` dependency marker so `crypt-r` is only required on Linux (`sys_platform == 'linux'`) to avoid build failures on macOS.
- 2026-02-15: Authorized a new deploy SSH key for `root@chatmail.fun` (added to `/root/.ssh/authorized_keys`) and restored the `/admin` endpoints by setting `admin_create_user` / `admin_create_password_hash` in the deployed `/usr/local/lib/chatmaild/chatmail.ini` and redeploying nginx.
- 2026-02-15: Fixed nginx redirects behind the 443 ALPN stream proxy by setting `port_in_redirect off;` in `cmdeploy/src/cmdeploy/nginx/nginx.conf.j2` (prevents broken `:8443` redirects for `/admin/` and similar paths).
- 2026-02-15: Disabled public/self-serve account creation by default (`public_create_enabled=false` in `chatmaild/src/chatmaild/ini/chatmail.ini.f`), enforced it in `chatmaild.doveauth.is_allowed_to_create()`, and made nginx return 404 for `/new` when disabled (via `cmdeploy/src/cmdeploy/nginx/nginx.conf.j2`).
- 2026-02-15: `cmdeploy` now enforces `public_create_enabled=false` in `chatmail.ini` automatically when running commands that load config (matching "admin-only creation" policy).
- 2026-02-15: Added admin account deletion endpoint `POST /admin/delete` and wired it into the admin accounts UI (`GET /admin`) with per-account Delete buttons; deployed via `cmdeploy` with a new vmail-run helper (`chatmail-admin-delete-helper`) and sudoers rule.
- 2026-02-15: Deployed admin-only account creation policy to live VM `chatmail.fun`: `/new` now returns 404, `public_create_enabled=false` is enforced in `/usr/local/lib/chatmaild/chatmail.ini`, and nginx now supports `POST /admin/delete` (with matching CGI + sudoers).
- 2026-02-15: Added admin endpoint `POST /admin/password` to set/reset an account password from the admin UI (`GET /admin`), backed by a vmail-run helper (`chatmail-admin-password-helper`) and sudoers rule.
- 2026-02-15: Added admin plaintext toggle endpoint `POST /admin/cleartext` (wired into the `/admin` accounts UI) which flips inbound/outbound cleartext mode via mailbox marker files (`enforceE2EEincoming` and new `allowCleartextOutgoing`). Filtermail services now start via a `chatmail-filtermail-wrapper` that dynamically derives `passthrough_senders` from `allowCleartextOutgoing`, and a sudoers rule allows the CGI to restart `filtermail.service` after updates.
- 2026-02-15: Deployed `/admin/cleartext` + filtermail wrapper changes to live VM `chatmail.fun` via `cmdeploy run`, which restarted nginx and filtermail (and updated sudoers to allow restarting `filtermail.service` from the CGI endpoint).
- 2026-02-16: New-account defaults are now email-friendly: account creation (both auto-create on login and admin create) removes `enforceE2EEincoming` and creates `allowCleartextOutgoing` so inbound/outbound cleartext interoperability is enabled by default.
- 2026-02-16: Stopped subject redaction in Postfix submission cleanup (`/etc/postfix/submission_header_cleanup`) so subjects are preserved for normal email UX.
- 2026-02-16: Relaxed inbound DKIM enforcement for compatibility by updating OpenDKIM `final.lua` to no longer reject unsigned/invalid inbound messages; added `rspamd` milter integration (`127.0.0.1:11332`) on Postfix reinjection services for spam/abuse scoring.
- 2026-02-16: Added relay-mediated realtime events service `chatmail-events` (SSE stream + authenticated event submission at `/events/stream` and `/events/send`) and exposed it through nginx for typing/read/delivery-style chat indicators between local accounts.
- 2026-02-16: Deployed the compatibility + events changes to live VM `chatmail.fun` via `cmdeploy run` (updated Postfix `master.cf` + `submission_header_cleanup`, OpenDKIM `final.lua`, nginx `/events/` proxy, and installed/started `chatmail-events` + `rspamd` services).
- 2026-02-16: Fixed live `rspamd` startup regression after deploy by correcting `/etc/rspamd/local.d/actions.conf` format (top-level `add_header` / `reject` keys, no nested `actions {}`), then redeployed; `rspamadm configtest` now reports `syntax OK` and `rspamd.service` is active.

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
