## Admin Account Creation

This page creates accounts through the protected `POST /admin/create` API.

<p><a href="/admin">View existing accounts</a></p>

<div class="admin-card">
  <label class="admin-label" for="email">Email</label>
  <input class="admin-input" id="email" type="email" placeholder="abcd12345@{{ config.mail_domain }}" autocomplete="off" />

  <label class="admin-label" for="password">Account password</label>
  <input class="admin-input" id="password" type="text" minlength="{{ config.password_min_length }}" placeholder="StrongPass123!" autocomplete="off" />

  <label class="admin-label" for="admin-user">Admin user (optional)</label>
  <input class="admin-input" id="admin-user" type="text" placeholder="{{ config.admin_create_user or 'relayadmin' }}" autocomplete="username" />

  <label class="admin-label" for="admin-pass">Admin password (optional)</label>
  <input class="admin-input" id="admin-pass" type="password" placeholder="Use browser auth prompt or enter here" autocomplete="current-password" />

  <button class="admin-button" id="create-account" type="button">Create Account</button>
  <pre class="admin-result" id="result"></pre>
</div>

<script>
(() => {
  const createButton = document.getElementById("create-account");
  const result = document.getElementById("result");

  function getValue(id) {
    const elem = document.getElementById(id);
    return elem ? elem.value.trim() : "";
  }

  async function createAccount() {
    const email = getValue("email");
    const password = getValue("password");
    const adminUser = getValue("admin-user");
    const adminPass = getValue("admin-pass");

    if (!email || !password) {
      result.textContent = "Email and account password are required.";
      return;
    }

    const headers = { "Content-Type": "application/json" };
    if (adminUser && adminPass) {
      headers.Authorization = `Basic ${btoa(`${adminUser}:${adminPass}`)}`;
    }

    result.textContent = "Creating account...";
    try {
      const response = await fetch("/admin/create", {
        method: "POST",
        headers,
        body: JSON.stringify({ email, password }),
      });
      const body = await response.text();
      let parsed = body;
      try {
        parsed = JSON.stringify(JSON.parse(body), null, 2);
      } catch (_err) {
        // Keep plain text when response is not JSON.
      }
      result.textContent = `HTTP ${response.status}\n${parsed}`;
    } catch (err) {
      result.textContent = `Request failed: ${err}`;
    }
  }

  createButton.addEventListener("click", createAccount);
})();
</script>
