/**
 * Chatwoot Live Support Widget Integration for NjordDeploy
 * Embeds Chatwoot customer messaging SDK into deploy.njorddeploy.com
 */
(function (d, t) {
    "use strict";
    const BASE_URL = "https://chat.njorddeploy.com";
    const g = d.createElement(t);
    const s = d.getElementsByTagName(t)[0];
    g.src = BASE_URL + "/packs/js/sdk.js";
    g.defer = true;
    g.async = true;
    if (s && s.parentNode) {
        s.parentNode.insertBefore(g, s);
    } else {
        d.head.appendChild(g);
    }
    g.onload = function () {
        if (window.chatwootSDK) {
            window.chatwootSDK.run({
                websiteToken: "KeVGnxhZXVgaCfUt8B2qMkLd",
                baseUrl: BASE_URL
            });
        }
    };
})(document, "script");
