// src/configurator_app/static/js/auth.js

/**
 * Sanitizes and validates internal redirect URLs to prevent open redirection and XSS.
 * @param {string|null|undefined} rawUrl
 * @param {string} [fallback="/"]
 * @returns {string}
 */
function sanitizeRedirectUrl(rawUrl, fallback = "/") {
    if (!rawUrl || typeof rawUrl !== "string") {
        return fallback;
    }
    try {
        const parsed = new URL(rawUrl, window.location.origin);
        if (
            parsed.origin === window.location.origin &&
            parsed.pathname.startsWith("/") &&
            !parsed.pathname.startsWith("//")
        ) {
            return parsed.pathname;
        }
    } catch {
        return fallback;
    }
    return fallback;
}

document.addEventListener("DOMContentLoaded", () => {
    // Password visibility toggle helper
    document.querySelectorAll(".toggle-password-btn").forEach((btn) => {
        btn.addEventListener("click", (e) => {
            e.preventDefault();
            const targetId = btn.getAttribute("data-target");
            if (!targetId) return;
            const input = document.getElementById(targetId);
            if (!input) return;

            const isPassword = input.type === "password";
            input.type = isPassword ? "text" : "password";
            const icon = btn.querySelector("i");
            if (icon) {
                icon.className = isPassword ? "fa-solid fa-eye-slash" : "fa-solid fa-eye";
            }
        });
    });

    // Setup Wizard Form Logic
    const setupForm = document.getElementById("njord-setup-form");
    if (setupForm) {
        const usernameInput = document.getElementById("setup-username");
        const passwordInput = document.getElementById("setup-password");
        const confirmInput = document.getElementById("setup-confirm-password");
        const submitBtn = document.getElementById("setup-submit-btn");
        const alertBox = document.getElementById("setup-alert");
        const lenCheck = document.getElementById("check-length");
        const matchCheck = document.getElementById("check-match");

        const updateChecks = () => {
            const pw = passwordInput ? passwordInput.value : "";
            const conf = confirmInput ? confirmInput.value : "";

            if (lenCheck) {
                if (pw.length >= 8) {
                    lenCheck.classList.remove("text-muted", "text-danger");
                    lenCheck.classList.add("text-success");
                    const icon = lenCheck.querySelector("i");
                    if (icon) icon.className = "fa-solid fa-circle-check me-1";
                } else {
                    lenCheck.classList.remove("text-success");
                    lenCheck.classList.add("text-muted");
                    const icon = lenCheck.querySelector("i");
                    if (icon) icon.className = "fa-regular fa-circle me-1";
                }
            }

            if (matchCheck) {
                if (pw && conf && pw === conf) {
                    matchCheck.classList.remove("text-muted", "text-danger");
                    matchCheck.classList.add("text-success");
                    const icon = matchCheck.querySelector("i");
                    if (icon) icon.className = "fa-solid fa-circle-check me-1";
                } else {
                    matchCheck.classList.remove("text-success");
                    matchCheck.classList.add("text-muted");
                    const icon = matchCheck.querySelector("i");
                    if (icon) icon.className = "fa-regular fa-circle me-1";
                }
            }
        };

        if (passwordInput) passwordInput.addEventListener("input", updateChecks);
        if (confirmInput) confirmInput.addEventListener("input", updateChecks);

        setupForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const username = usernameInput ? usernameInput.value.trim() : "";
            const password = passwordInput ? passwordInput.value : "";
            const confirm = confirmInput ? confirmInput.value : "";

            if (!username || username.length < 3) {
                showAlert(alertBox, "Username must be at least 3 characters long.", "danger");
                return;
            }
            if (password.length < 8) {
                showAlert(alertBox, "Password must be at least 8 characters long.", "danger");
                return;
            }
            if (password !== confirm) {
                showAlert(alertBox, "Passwords do not match.", "danger");
                return;
            }

            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i> Initializing System...';
            }

            try {
                const response = await fetch("/api/setup", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        username: username,
                        password: password,
                        confirm_password: confirm
                    })
                });

                const data = await response.json();

                if (response.ok && data.status === "success") {
                    showAlert(alertBox, "Admin account successfully created! Redirecting...", "success");
                    const setupCard = document.getElementById("setup-card-body");
                    const successCard = document.getElementById("setup-success-card");
                    const apiKeySpan = document.getElementById("setup-generated-api-key");

                    if (setupCard && successCard && apiKeySpan && data.api_key) {
                        apiKeySpan.textContent = data.api_key;
                        setupCard.classList.add("d-none");
                        successCard.classList.remove("d-none");
                    } else {
                        setTimeout(() => {
                            window.location.href = sanitizeRedirectUrl(data.redirect, "/");
                        }, 1200);
                    }
                } else {
                    showAlert(alertBox, data.error || data.message || "Setup failed.", "danger");
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = '<i class="fa-solid fa-check-double me-2"></i> Create Admin Account &amp; Launch';
                    }
                }
            } catch (err) {
                console.error("Setup error:", err);
                showAlert(alertBox, "A network error occurred while completing setup.", "danger");
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<i class="fa-solid fa-check-double me-2"></i> Create Admin Account &amp; Launch';
                }
            }
        });
    }

    // Login Form Logic
    const loginForm = document.getElementById("njord-login-form");
    if (loginForm) {
        const usernameInput = document.getElementById("login-username");
        const passwordInput = document.getElementById("login-password");
        const submitBtn = document.getElementById("login-submit-btn");
        const alertBox = document.getElementById("login-alert");

        loginForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const username = usernameInput ? usernameInput.value.trim() : "";
            const password = passwordInput ? passwordInput.value : "";

            if (!username || !password) {
                showAlert(alertBox, "Please enter both username and password.", "danger");
                return;
            }

            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i> Authenticating...';
            }

            try {
                const params = new URLSearchParams(window.location.search);
                const nextUrl = sanitizeRedirectUrl(params.get("next"), "/");

                const response = await fetch("/api/login", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        username: username,
                        password: password
                    })
                });

                const data = await response.json();

                if (response.ok && data.status === "authenticated") {
                    showAlert(alertBox, "Authentication successful! Redirecting...", "success");
                    setTimeout(() => {
                        window.location.href = nextUrl;
                    }, 500);
                } else if (response.status === 429) {
                    const retry = data.retry_after || 60;
                    showAlert(alertBox, `Too many failed login attempts. Please wait ${retry} seconds before retrying.`, "warning");
                    if (submitBtn) {
                        submitBtn.disabled = true;
                        setTimeout(() => {
                            if (submitBtn) {
                                submitBtn.disabled = false;
                                submitBtn.innerHTML = '<i class="fa-solid fa-right-to-bracket me-2"></i> Sign In';
                            }
                        }, retry * 1000);
                    }
                } else {
                    showAlert(alertBox, data.error || data.message || "Invalid username or password.", "danger");
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = '<i class="fa-solid fa-right-to-bracket me-2"></i> Sign In';
                    }
                }
            } catch (err) {
                console.error("Login error:", err);
                showAlert(alertBox, "A network error occurred while attempting to sign in.", "danger");
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<i class="fa-solid fa-right-to-bracket me-2"></i> Sign In';
                }
            }
        });
    }

    // Copy API Key Helper
    document.querySelectorAll(".btn-copy-token").forEach((btn) => {
        btn.addEventListener("click", (e) => {
            e.preventDefault();
            const targetId = btn.getAttribute("data-target");
            let textToCopy = "";
            if (targetId) {
                const targetElem = document.getElementById(targetId);
                if (targetElem) {
                    textToCopy = targetElem.value || targetElem.textContent || "";
                }
            } else if (btn.getAttribute("data-token")) {
                textToCopy = btn.getAttribute("data-token") || "";
            }

            if (!textToCopy) return;

            navigator.clipboard.writeText(textToCopy.trim()).then(() => {
                const originalHtml = btn.innerHTML;
                btn.innerHTML = '<i class="fa-solid fa-check text-success me-1"></i> Copied!';
                setTimeout(() => {
                    btn.innerHTML = originalHtml;
                }, 2000);
            }).catch((err) => {
                console.error("Clipboard copy failed:", err);
            });
        });
    });

    // Regenerate API Token in Settings
    const regenBtn = document.getElementById("btn-regenerate-token");
    if (regenBtn) {
        regenBtn.addEventListener("click", async (e) => {
            e.preventDefault();
            const confirmed = window.confirm(
                "Are you sure you want to regenerate your API token? Any existing integrations using the old token will need to be updated."
            );
            if (!confirmed) return;

            regenBtn.disabled = true;
            const origHtml = regenBtn.innerHTML;
            regenBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-1"></i>';

            try {
                const response = await fetch("/api/auth/regenerate-api-key", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" }
                });
                const data = await response.json();
                const feedback = document.getElementById("feedback-alert");
                if (response.ok && data.api_key) {
                    const input = document.getElementById("settings-api-key-input");
                    if (input) input.value = data.api_key;
                    showAlert(feedback, "API token successfully regenerated!", "success");
                } else {
                    showAlert(feedback, data.error || "Failed to regenerate API token.", "danger");
                }
            } catch (err) {
                console.error("Regenerate token error:", err);
            } finally {
                regenBtn.disabled = false;
                regenBtn.innerHTML = origHtml;
            }
        });
    }

    // Change Password in Settings
    const savePasswordBtn = document.getElementById("btn-save-new-password");
    if (savePasswordBtn) {
        savePasswordBtn.addEventListener("click", async (e) => {
            e.preventDefault();
            const currInput = document.getElementById("change-curr-pass");
            const newInput = document.getElementById("change-new-pass");
            const confInput = document.getElementById("change-conf-pass");
            const feedback = document.getElementById("feedback-alert");

            const curr = currInput ? currInput.value : "";
            const newPw = newInput ? newInput.value : "";
            const confPw = confInput ? confInput.value : "";

            if (!curr || !newPw || !confPw) {
                showAlert(feedback, "All password fields are required.", "danger");
                return;
            }
            if (newPw.length < 8) {
                showAlert(feedback, "New password must be at least 8 characters long.", "danger");
                return;
            }
            if (newPw !== confPw) {
                showAlert(feedback, "New passwords do not match.", "danger");
                return;
            }

            savePasswordBtn.disabled = true;
            const origHtml = savePasswordBtn.innerHTML;
            savePasswordBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-1"></i> Updating...';

            try {
                const response = await fetch("/api/auth/change-password", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        current_password: curr,
                        new_password: newPw,
                        confirm_password: confPw
                    })
                });
                const data = await response.json();
                if (response.ok && data.status === "success") {
                    showAlert(feedback, "Administrator password successfully updated!", "success");
                    if (currInput) currInput.value = "";
                    if (newInput) newInput.value = "";
                    if (confInput) confInput.value = "";
                } else {
                    showAlert(feedback, data.error || "Failed to update password.", "danger");
                }
            } catch (err) {
                console.error("Password update error:", err);
                showAlert(feedback, "A network error occurred while updating password.", "danger");
            } finally {
                savePasswordBtn.disabled = false;
                savePasswordBtn.innerHTML = origHtml;
            }
        });
    }

    // Helper function to display alerts safely without raw HTML injection
    function showAlert(elem, message, type = "info") {
        if (!elem) return;
        elem.className = `alert alert-${type} shadow-sm`;
        elem.textContent = message;
        elem.classList.remove("d-none");
    }
});
