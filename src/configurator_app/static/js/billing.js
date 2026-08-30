/**
 * NjordDeploy Stripe Billing & Subscription Management
 * Handles interactive Checkout sessions and Customer Portal redirects.
 */

document.addEventListener("DOMContentLoaded", () => {
    // 1. Monthly Checkout Handlers
    const monthlyBtns = document.querySelectorAll(".btn-checkout-monthly");
    monthlyBtns.forEach((btn) => {
        btn.addEventListener("click", async (e) => {
            e.preventDefault();
            await startStripeCheckout("monthly", btn);
        });
    });

    // 2. Yearly Checkout Handlers
    const yearlyBtns = document.querySelectorAll(".btn-checkout-yearly");
    yearlyBtns.forEach((btn) => {
        btn.addEventListener("click", async (e) => {
            e.preventDefault();
            await startStripeCheckout("yearly", btn);
        });
    });

    // 3. Customer Portal Handlers
    const portalBtns = document.querySelectorAll(".btn-billing-portal");
    portalBtns.forEach((btn) => {
        btn.addEventListener("click", async (e) => {
            e.preventDefault();
            await openStripePortal(btn);
        });
    });

    // 4. Handle return from Stripe Checkout / Portal
    const urlParams = new URLSearchParams(window.location.search);
    const billingStatus = urlParams.get("billing");
    const hasSession = (
        urlParams.has("stripe_session_id") ||
        urlParams.has("checkout_session_id") ||
        urlParams.has("session_id")
    );

    if (billingStatus === "success" || (billingStatus && hasSession)) {
        showProSuccessCelebration();
        // Clean URL query params without reloading
        const cleanUrl = window.location.pathname;
        window.history.replaceState({}, document.title, cleanUrl);
    } else if (billingStatus === "cancel") {
        console.log("Stripe Checkout cancelled by user.");
        const cleanUrl = window.location.pathname;
        window.history.replaceState({}, document.title, cleanUrl);
    } else if (billingStatus === "portal_return") {
        console.log("Returned from Stripe Customer Portal.");
        const cleanUrl = window.location.pathname;
        window.history.replaceState({}, document.title, cleanUrl);
    }
});

/**
 * Shows the Pro upgrade celebration modal and refreshes active plan badges.
 */
function showProSuccessCelebration() {
    const successModalEl = document.getElementById("proSuccessModal");
    if (successModalEl && typeof bootstrap !== "undefined" && bootstrap.Modal) {
        const modal = new bootstrap.Modal(successModalEl);
        modal.show();
    } else {
        alert("🎉 Gefeliciteerd! Je bent succesvol geüpgraded naar NjordDeploy Pro!");
    }

    // Refresh UI plan badges dynamically
    refreshBillingStatus();
}

/**
 * Refreshes the user's plan status from backend API and updates UI elements.
 */
async function refreshBillingStatus() {
    try {
        const response = await fetch("/api/billing/status");
        if (!response.ok) return;
        const data = await response.json();
        if (data && data.billing && data.billing.plan === "pro") {
            const upgradeBtn = document.querySelector("button[title='Upgrade to NjordDeploy Pro']");
            if (upgradeBtn && upgradeBtn.parentElement) {
                upgradeBtn.parentElement.innerHTML = `
                    <span class="badge bg-primary text-white shadow-sm" title="Active Pro Subscription">
                        <i class="fa-solid fa-crown me-1 text-warning"></i> PRO
                    </span>
                `;
            }
        }
    } catch (e) {
        console.warn("Could not refresh billing status badge:", e);
    }
}

/**
 * Initiates a Stripe Checkout Session for Pro subscription.
 * @param {string} interval - 'monthly' or 'yearly'
 * @param {HTMLElement} buttonElement - The triggering button
 */
async function startStripeCheckout(interval, buttonElement) {
    const originalText = buttonElement.innerHTML;
    buttonElement.disabled = true;
    buttonElement.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-1"></i> Opening Checkout...';

    try {
        const response = await fetch("/api/billing/checkout", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ interval }),
        });

        const data = await response.json();

        if (response.ok && data.checkout_url) {
            window.location.href = data.checkout_url;
        } else {
            alert(data.error || "Could not initialize Stripe Checkout. Please try again.");
            buttonElement.disabled = false;
            buttonElement.innerHTML = originalText;
        }
    } catch (err) {
        console.error("Stripe Checkout error:", err);
        alert("A network error occurred while connecting to the billing service.");
        buttonElement.disabled = false;
        buttonElement.innerHTML = originalText;
    }
}

/**
 * Generates and opens a dynamic Stripe Customer Portal session.
 * @param {HTMLElement} buttonElement - The triggering button
 */
async function openStripePortal(buttonElement) {
    const originalText = buttonElement.innerHTML;
    buttonElement.disabled = true;
    buttonElement.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-1"></i> Loading Portal...';

    try {
        const response = await fetch("/api/billing/portal", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
        });

        const data = await response.json();

        if (response.ok && data.portal_url) {
            window.location.href = data.portal_url;
        } else {
            alert(data.error || "No active billing session found. Please upgrade to Pro first.");
            buttonElement.disabled = false;
            buttonElement.innerHTML = originalText;
        }
    } catch (err) {
        console.error("Stripe Portal error:", err);
        alert("A network error occurred while opening the customer portal.");
        buttonElement.disabled = false;
        buttonElement.innerHTML = originalText;
    }
}
