const loginForm = document.querySelector("#loginForm");
const loginButton = document.querySelector("#loginButton");
const loginStatus = document.querySelector("#loginStatus");

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  loginButton.disabled = true;
  loginStatus.textContent = "Signing in...";

  try {
    const response = await fetch("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: document.querySelector("#username").value.trim(),
        password: document.querySelector("#password").value,
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Sign-in failed.");
    }
    window.location.assign(payload.role === "procurement" ? "/" : "/admin");
  } catch (error) {
    loginStatus.textContent = error.message;
    loginButton.disabled = false;
  }
});
