# Security

UbuntuCare Health Platform is committed to the security and trust of our software and services.

## Reporting a Security Vulnerability

To report a security vulnerability, please use the following contact:

- **Email**: security@ubuntucare.zm
- Please include:
  - Component/service name and version
  - Type of vulnerability
  - Steps to reproduce
  - Potential impact

We acknowledge reports under coordinated disclosure.

## Security Practices

- UbuntuCare proprietary code is owned by Francis Banda. Third-party dependencies remain governed by their own licenses.
- Dependencies are audited regularly via `pip-audit` and `npm audit`
- Container images are scanned with Trivy in CI
- SAST scanning via Semgrep in CI pipeline
- Secrets are never hardcoded; use environment variables or a secrets manager
- PHI is encrypted at rest (AES-256-GCM) and in transit (TLS 1.3)
- Authentication via Keycloak with MFA support
- Audit logging with tamper-evident hash chains
