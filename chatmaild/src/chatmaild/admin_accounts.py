#!/usr/local/lib/chatmaild/venv/bin/python3

"""CGI script serving an admin UI for listing accounts and creating new ones."""

from __future__ import annotations

import html
import json
import subprocess

from chatmaild.config import read_config

CONFIG_PATH = "/usr/local/lib/chatmaild/chatmail.ini"
HELPER_BIN = "/usr/local/lib/chatmaild/venv/bin/chatmail-admin-accounts-helper"


def _load_accounts():
    proc = subprocess.run(
        ["sudo", "-n", "-u", "vmail", HELPER_BIN],
        input="",
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )

    raw = (proc.stdout or "").strip()
    if proc.returncode != 0 or not raw:
        return (
            [],
            f"accounts helper failed (rc={proc.returncode})\n{(proc.stderr or '').strip()}",
        )

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return [], f"invalid helper response\n{raw}"

    if not isinstance(payload, dict) or payload.get("status") != "ok":
        return [], f"unexpected helper response\n{raw}"

    accounts = payload.get("accounts") or []
    if not isinstance(accounts, list):
        return [], f"unexpected helper response\n{raw}"

    return accounts, None


def main() -> None:
    config = read_config(CONFIG_PATH)
    domain = html.escape(config.mail_domain)
    uname_min = int(config.username_min_length)
    uname_max = int(config.username_max_length)
    pw_min = int(config.password_min_length)

    accounts, load_error = _load_accounts()
    accounts_json = json.dumps(accounts, ensure_ascii=True)
    load_error_text = load_error or ""

    print("Content-Type: text/html; charset=utf-8")
    print("")
    print(
        f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{domain} admin</title>
    <link rel="icon" href="/logo.svg">
    <style>
      body {{
        font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        line-height: 1.4;
        max-width: 980px;
        margin: 24px auto;
        padding: 0 12px;
        color: #1b2730;
        background: #ffffff;
      }}
      h1 {{ margin: 0 0 12px 0; font-size: 1.6rem; }}
      nav {{
        display: flex;
        gap: 12px;
        align-items: center;
        margin: 0 0 14px 0;
        font-weight: 600;
      }}
      nav a {{
        color: #2a6a90;
        text-decoration: none;
      }}
      nav a:hover {{ text-decoration: underline; }}
      .hint {{ color: #566b7a; margin: 0 0 18px 0; }}
      .grid {{
        display: grid;
        grid-template-columns: 1fr;
        gap: 14px;
      }}
      .card {{
        border: 1px solid #d7e0e8;
        border-radius: 10px;
        padding: 18px;
        background: #f8fbfd;
      }}
      label {{
        display: block;
        font-size: 0.9rem;
        margin-top: 12px;
        margin-bottom: 6px;
        color: #1e2b35;
        font-weight: 600;
      }}
      input {{
        width: 100%;
        box-sizing: border-box;
        border: 1px solid #b8c8d4;
        border-radius: 8px;
        padding: 10px 12px;
        font-size: 1rem;
        background: #fff;
      }}
      input:focus {{ border-color: #327ca8; outline: none; }}
      button {{
        margin-top: 14px;
        border: 1px solid #2f6b8c;
        border-radius: 8px;
        padding: 10px 14px;
        background: #327ca8;
        color: #fff;
        font-weight: 700;
        cursor: pointer;
      }}
      button:hover {{ background: #2a6a90; }}
      .danger {{
        border-color: #8c2f2f;
        background: #a83232;
      }}
      .danger:hover {{ background: #8c2f2f; }}
      pre {{
        margin-top: 16px;
        min-height: 90px;
        border-radius: 8px;
        padding: 12px;
        white-space: pre-wrap;
        background: #0e1a23;
        color: #d9ebf6;
        font-size: 0.95rem;
        overflow-x: auto;
      }}
      code {{
        background: #eef3f6;
        padding: 2px 6px;
        border-radius: 6px;
      }}
      table {{
        width: 100%;
        border-collapse: collapse;
        background: #fff;
        border: 1px solid #d7e0e8;
        border-radius: 10px;
        overflow: hidden;
      }}
      .chk {{
        width: 16px;
        height: 16px;
        accent-color: #327ca8;
      }}
      thead th {{
        text-align: left;
        font-size: 0.9rem;
        padding: 10px 12px;
        background: #eef5fa;
        border-bottom: 1px solid #d7e0e8;
        color: #1e2b35;
      }}
      tbody td {{
        padding: 10px 12px;
        border-bottom: 1px solid #eef3f6;
        vertical-align: top;
        font-size: 0.95rem;
      }}
      tbody tr:last-child td {{ border-bottom: none; }}
      .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace; }}
      .row-muted {{ color: #566b7a; }}
      .split {{
        display: flex;
        justify-content: space-between;
        gap: 10px;
        align-items: baseline;
        flex-wrap: wrap;
      }}
      .badge {{
        display: inline-block;
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 700;
        background: #eef3f6;
        color: #1e2b35;
      }}
      .header-controls {{
        display: flex;
        gap: 10px;
        align-items: center;
        justify-content: flex-end;
        flex: 1;
        flex-wrap: wrap;
      }}
      .header-controls input {{
        min-width: 260px;
        flex: 1;
      }}
      .header-controls button {{
        margin-top: 0;
        white-space: nowrap;
      }}
      .flat-button {{
        margin-top: 0;
      }}
    </style>
  </head>
  <body>
    <nav>
      <span class="badge">Accounts</span>
    </nav>

    <h1>Accounts</h1>
    <p class="hint">
      Listing mailboxes for <strong>{domain}</strong>. Create accounts via <code>POST /admin/create</code>.
    </p>

    <div class="grid">
      <div class="card">
        <div class="split">
          <div>
            <strong>Existing Accounts</strong>
            <div class="hint" style="margin: 6px 0 0 0;">
              <span id="count"></span>
            </div>
          </div>
          <div class="header-controls">
            <input id="filter" type="text" placeholder="Filter (substring match)" autocomplete="off" />
            <button id="delete-selected" class="flat-button danger" type="button" disabled>Delete selected</button>
            <button id="open-create" class="flat-button" type="button">Create new</button>
          </div>
        </div>

        <div id="load-error" class="hint" style="margin-top: 10px; color: #a13b3b; display: none;"></div>

        <div style="margin-top: 12px;">
          <table>
            <thead>
              <tr>
                <th style="width: 1%; white-space: nowrap;">
                  <input id="select-all" class="chk" type="checkbox" title="Select all shown" />
                </th>
                <th>Email</th>
                <th>Last login</th>
                <th style="width: 1%; white-space: nowrap;">Actions</th>
              </tr>
            </thead>
            <tbody id="accounts-body"></tbody>
          </table>
        </div>
      </div>

      <div class="card" id="create-card" hidden>
        <div class="split">
          <div>
            <strong>Create Account</strong>
            <div class="hint" style="margin: 6px 0 0 0;">
              Local part length: {uname_min} to {uname_max}. Password min length: {pw_min}.
            </div>
          </div>
        </div>

        <label for="email">Email</label>
        <input id="email" type="email" placeholder="kevin@{domain}" autocomplete="off" />

        <label for="password">Account password</label>
        <input id="password" type="text" minlength="{pw_min}" placeholder="StrongPass123!" autocomplete="off" />

        <button id="create-account" type="button">Create Account</button>
        <pre id="result"></pre>
      </div>
    </div>

    <script>
      (() => {{
        const mailDomain = {config.mail_domain!r};
        const unameMin = {uname_min};
        const unameMax = {uname_max};
        const pwMin = {pw_min};
        const accounts = {accounts_json};
        const loadError = {load_error_text!r};

        const tbody = document.getElementById("accounts-body");
        const filterInput = document.getElementById("filter");
        const countElem = document.getElementById("count");
        const loadErrorElem = document.getElementById("load-error");
        const openCreateButton = document.getElementById("open-create");
        const createCard = document.getElementById("create-card");
        const selectAllBox = document.getElementById("select-all");
        const deleteSelectedButton = document.getElementById("delete-selected");
        const selected = new Set();
        let lastShown = [];

        function fmtTs(ts) {{
          if (!ts) return "never";
          const d = new Date(ts * 1000);
          return d.toLocaleString();
        }}

        function updateSelectionUi() {{
          const shown = Array.isArray(lastShown) ? lastShown : [];
          const shownCount = shown.length;
          let selectedShown = 0;
          for (const email of shown) {{
            if (selected.has(email)) selectedShown += 1;
          }}

          if (selectAllBox) {{
            selectAllBox.indeterminate = selectedShown > 0 && selectedShown < shownCount;
            selectAllBox.checked = shownCount > 0 && selectedShown === shownCount;
          }}

          if (deleteSelectedButton) {{
            deleteSelectedButton.disabled = selected.size === 0;
            const n = selected.size;
            deleteSelectedButton.textContent = n ? `Delete selected (${{n}})` : "Delete selected";
          }}
        }}

        function render(list, needle) {{
          const n = (needle || "").toLowerCase();
          tbody.textContent = "";
          let shown = 0;
          const shownEmails = [];
          for (const acct of list) {{
            const email = String(acct.email || "");
            if (n && !email.toLowerCase().includes(n)) continue;
            shown += 1;
            shownEmails.push(email);

            const tr = document.createElement("tr");

            const tdSelect = document.createElement("td");
            const cb = document.createElement("input");
            cb.type = "checkbox";
            cb.className = "chk";
            cb.checked = selected.has(email);
            cb.addEventListener("change", () => {{
              if (cb.checked) {{
                selected.add(email);
              }} else {{
                selected.delete(email);
              }}
              updateSelectionUi();
            }});
            tdSelect.appendChild(cb);
            tr.appendChild(tdSelect);

            const tdEmail = document.createElement("td");
            tdEmail.className = "mono";
            tdEmail.textContent = email;
            tr.appendChild(tdEmail);

            const tdLogin = document.createElement("td");
            tdLogin.className = "row-muted";
            tdLogin.textContent = fmtTs(acct.last_login);
            tr.appendChild(tdLogin);

            const tdActions = document.createElement("td");
            const delBtn = document.createElement("button");
            delBtn.type = "button";
            delBtn.className = "danger";
            delBtn.textContent = "Delete";
            delBtn.addEventListener("click", () => deleteAccount(email));
            tdActions.appendChild(delBtn);
            tr.appendChild(tdActions);

            tbody.appendChild(tr);
          }}
          lastShown = shownEmails;
          const total = Array.isArray(list) ? list.length : 0;
          countElem.textContent = `${{shown}} shown / ${{total}} total`;
          updateSelectionUi();
        }}

        if (loadError) {{
          loadErrorElem.style.display = "block";
          loadErrorElem.textContent = loadError;
        }}

        filterInput.addEventListener("input", () => {{
          render(accounts, filterInput.value);
        }});
        render(accounts, "");

        if (selectAllBox) {{
          selectAllBox.addEventListener("change", () => {{
            const want = !!selectAllBox.checked;
            for (const email of lastShown) {{
              if (want) selected.add(email);
              else selected.delete(email);
            }}
            render(accounts, filterInput.value);
          }});
        }}

        function showCreateCard() {{
          if (!createCard) return;
          createCard.hidden = false;
          createCard.scrollIntoView({{ behavior: "smooth", block: "start" }});
          const emailInput = document.getElementById("email");
          if (emailInput) emailInput.focus();
        }}

        if (openCreateButton) {{
          openCreateButton.addEventListener("click", showCreateCard);
        }}

        const createButton = document.getElementById("create-account");
        const result = document.getElementById("result");

        async function createAccount() {{
          const email = (document.getElementById("email").value || "").trim();
          const password = (document.getElementById("password").value || "");

          if (!email || !password) {{
            result.textContent = "Email and account password are required.";
            return;
          }}

          if (!email.endsWith("@" + mailDomain)) {{
            result.textContent = `Email must end with @${{mailDomain}}.`;
            return;
          }}

          const localpart = email.split("@")[0] || "";
          if (localpart.length < unameMin || localpart.length > unameMax) {{
            result.textContent = `Username (before @) must be between ${{unameMin}} and ${{unameMax}} characters.`;
            return;
          }}

          if (password.length < pwMin) {{
            result.textContent = `Password must be at least ${{pwMin}} characters.`;
            return;
          }}

          result.textContent = "Creating account...";
          try {{
            const response = await fetch("/admin/create", {{
              method: "POST",
              headers: {{ "Content-Type": "application/json" }},
              body: JSON.stringify({{ email, password }}),
            }});
            const body = await response.text();
            let parsed = body;
            try {{
              parsed = JSON.stringify(JSON.parse(body), null, 2);
            }} catch (_err) {{}}
            result.textContent = `HTTP ${{response.status}}\\n${{parsed}}`;
            if (response.status === 201) {{
              window.location.reload();
            }}
          }} catch (err) {{
            result.textContent = `Request failed: ${{err}}`;
          }}
        }}

        if (createButton) {{
          createButton.addEventListener("click", createAccount);
        }}

        async function deleteAccountRequest(email) {{
          const response = await fetch("/admin/delete", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{ email }}),
          }});
          const bodyText = await response.text();
          let body = bodyText;
          try {{
            body = JSON.parse(bodyText);
          }} catch (_err) {{}}
          return {{ status: response.status, body }};
        }}

        async function deleteAccount(email) {{
          if (!email) return;
          if (!confirm(`Delete ${{email}}? This removes the mailbox directory and cannot be undone.`)) {{
            return;
          }}
          result.textContent = `Deleting ${{email}}...`;
          try {{
            const res = await deleteAccountRequest(email);
            const parsed = typeof res.body === "string" ? res.body : JSON.stringify(res.body, null, 2);
            result.textContent = `HTTP ${{res.status}}\\n${{parsed}}`;
            if (res.status === 200) {{
              window.location.reload();
            }}
          }} catch (err) {{
            result.textContent = `Request failed: ${{err}}`;
          }}
        }}

        async function deleteSelected() {{
          const emails = Array.from(selected).sort();
          if (!emails.length) return;

          const preview = emails.slice(0, 20).join("\\n") + (emails.length > 20 ? `\\n... and ${{emails.length - 20}} more` : "");
          if (!confirm(`Delete ${{emails.length}} accounts?\\n\\n${{preview}}\\n\\nThis cannot be undone.`)) {{
            return;
          }}

          const lines = [];
          result.textContent = `Deleting ${{emails.length}} accounts...`;
          let ok = 0;
          let fail = 0;
          for (let i = 0; i < emails.length; i++) {{
            const email = emails[i];
            try {{
              const res = await deleteAccountRequest(email);
              if (res.status === 200 || res.status === 404) {{
                ok += 1;
                selected.delete(email);
                lines.push(`[${{i+1}}/${{emails.length}}] OK  HTTP ${{res.status}}  ${{email}}`);
              }} else {{
                fail += 1;
                lines.push(`[${{i+1}}/${{emails.length}}] ERR HTTP ${{res.status}} ${{email}}  ${{typeof res.body === "string" ? res.body : JSON.stringify(res.body)}}`);
              }}
            }} catch (err) {{
              fail += 1;
              lines.push(`[${{i+1}}/${{emails.length}}] ERR ${{email}}  ${{err}}`);
            }}
            result.textContent = lines.slice(-40).join("\\n");
          }}

          lines.push(`\\nSummary: ${{ok}} ok, ${{fail}} failed.`);
          result.textContent = lines.slice(-80).join("\\n");
          updateSelectionUi();
          // Reload to update the accounts list, even if some deletions failed.
          window.location.reload();
        }}

        if (deleteSelectedButton) {{
          deleteSelectedButton.addEventListener("click", deleteSelected);
        }}
      }})();
    </script>
  </body>
</html>"""
    )


if __name__ == "__main__":
    main()
