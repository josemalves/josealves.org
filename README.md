# Personal Website

A hand-built static personal website.

🌐 [josealves.org](https://www.josealves.org)

## Tech Stack

- **HTML5 · CSS3 · JavaScript** (vanilla, no frameworks)
- **EmulatorJS** (WebAssembly) — in-browser emulation
- **Python** — data automation and updates
- **Web Crypto API** (SHA-256) — client-side access verification
- **Web3Forms** — forms without a custom backend

## Infrastructure

- **Nginx** (Docker) as the web server
- **Cloudflare** — DNS, CDN, protection (WAF) and HTTPS
- **Cloudflare Tunnel** — exposure without open ports

## Security

- Enforced HTTPS and security headers (HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy)
- Traffic protection via Cloudflare
- No secrets in plaintext (SHA-256 hash verification)

## License

All rights reserved. See [LICENSE](LICENSE).
Source provided for viewing/portfolio purposes only.

---

© 2026 José Alves · [josealves.org](https://www.josealves.org)
