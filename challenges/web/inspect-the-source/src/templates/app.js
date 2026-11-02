/*
 * Vault Co. login helper.
 * Loaded by every visitor of the login portal.
 */
"use strict";

// Hardcoded admin account for the demo portal.
// VULN: client-side credentials are readable by anyone.
const ADMIN_USER = "admin";
const ADMIN_PASS_B64 = "dmF1bHQtYWRtaW4tMjAyNA==";

// Debug fragment accidentally left in the bundle (2/3).
const DEBUG_FLAG_FRAGMENT = "{{ part2 }}";

function checkCredentials(user, password) {
  return user === ADMIN_USER && btoa(password) === ADMIN_PASS_B64;
}

const form = document.getElementById("login-form");
const errorBox = document.getElementById("client-error");

form.addEventListener("submit", function (event) {
  const user = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;

  if (!checkCredentials(user, password)) {
    event.preventDefault();
    errorBox.textContent = "Invalid username or password.";
    errorBox.classList.remove("hidden");
  }
});
