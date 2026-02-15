#!/usr/local/lib/chatmaild/venv/bin/python3

"""CGI script serving a simple admin UI for account creation."""

import html

from chatmaild.config import read_config

CONFIG_PATH = "/usr/local/lib/chatmaild/chatmail.ini"


def main() -> None:
    config = read_config(CONFIG_PATH)
    domain = html.escape(config.mail_domain)
    uname_min = int(config.username_min_length)
    uname_max = int(config.username_max_length)
    pw_min = int(config.password_min_length)

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
        max-width: 820px;
        margin: 24px auto;
        padding: 0 12px;
        color: #1b2730;
        background: #ffffff;
      }}
      h1 {{ margin: 0 0 12px 0; font-size: 1.6rem; }}
      .hint {{ color: #566b7a; margin: 0 0 18px 0; }}
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
    </style>
  </head>
  <body>
    <h1>Admin Account Creation</h1>
    <p class="hint">
      Creates accounts via <code>POST /admin/create</code> for <strong>{domain}</strong>.
    </p>

    <div class="card">
      <label for="email">Email</label>
      <input id="email" type="email" placeholder="kevin@{domain}" autocomplete="off" />
      <p class="hint" style="margin: 8px 0 0 0;">
        Local part length: {uname_min} to {uname_max} characters.
      </p>

      <label for="password">Account password (min length: {pw_min})</label>
      <input id="password" type="text" minlength="{pw_min}" placeholder="StrongPass123!" autocomplete="off" />

      <button id="create-account" type="button">Create Account</button>
      <pre id="result"></pre>
    </div>

    <script>
      (() => {{
        const createButton = document.getElementById("create-account");
        const result = document.getElementById("result");
        const mailDomain = {config.mail_domain!r};
        const unameMin = {uname_min};
        const unameMax = {uname_max};
        const pwMin = {pw_min};

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
          }} catch (err) {{
            result.textContent = `Request failed: ${{err}}`;
          }}
        }}

        createButton.addEventListener("click", createAccount);
      }})();
    </script>
  </body>
</html>"""
    )


if __name__ == "__main__":
    main()
