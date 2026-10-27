# Deployment requirements

Checked 28 October 2026 IST against the current [official academy FAQ](https://academy.genai.works/courses/open-agent-hackathon-2026/details?section=faqs), supplied submission-requirements.md and previously inspected submission form.

The FAQ permits any language, framework or cloud. It requires a 1–4 minute demo, slide deck, public GitHub repository/README and sponsor explanation, including a real Nightshift request and Engine proof. The supplied guide permits recording a workflow from a real run. Neither source establishes a publicly hosted app as mandatory. The **repository** must be public. No hosting vendor is prescribed. Cursor is optional.

The private resource center currently redirects external retrieval to sign-in, and local browser control is disabled in Work settings. This check does not claim to have re-read new private announcements or changed binding rules. Use the earlier 23:45 UTC deadline where the dashboard tile differs.

Public hosting improves independent access but is not established as an eligibility requirement. A frontend-only deployment cannot provide the live product: the backend, PostgreSQL, Zetaris and reachable Nightshift/NVIDIA path must remain available. The existing web build supports Cloudflare. Dockerfile.web builds a Node server for a conventional Docker deployment.

## Prepared deployment

compose.production.yml layers over compose.data.yml with a Node frontend and Caddy reverse proxy. The frontend calls same-origin /api. The backend requires secure cookies and the configured HTTPS origin. Caddy obtains certificates for a real configured domain. Backend ports are removed by the overlay. Source/Zetaris ports still need operator firewall/network restrictions. A remote installation needs a reachable private Nightshift runtime and configured Zetaris network.

```powershell
# Configure the real domain, private credentials and service endpoints first.
docker compose -f compose.data.yml -f compose.production.yml --profile app up -d --build
```

No hosting target/domain has been selected, no cloud spending is authorized and no public deployment has occurred. Compose syntax validation passed. Image/runtime results are recorded separately in RELEASE_VERIFICATION.md. Public release still requires actual endpoint/TLS verification, protected storage and operational checks.
