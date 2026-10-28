# Security policy

## Supported use

Invoice Agent is currently a local MVP. The supported configuration binds the
server to `127.0.0.1` and processes documents on the same machine.

Do not expose the development server directly to the Internet and do not process
documents from untrusted users without an additional sandbox, authentication,
antivirus scanning and resource isolation.

## Sensitive documents

- Never commit real invoices, credentials, bank statements or customer data.
- Use only anonymized or synthetic fixtures.
- Keep OCR models, temporary uploads and generated exports outside Git.
- Delete temporary and exported files according to the organization's retention
  policy.

## Production requirements

A production deployment must add:

- authenticated users and authorization boundaries;
- TLS through a maintained reverse proxy;
- a dedicated unprivileged OS/container user;
- read-only application filesystem where practical;
- antivirus/content scanning before parsing;
- CPU, memory, file-size and execution-time limits;
- isolated temporary storage with automatic deletion;
- dependency and container image scanning;
- audit logs that do not contain document bodies or credentials.

## Reporting a vulnerability

Please report vulnerabilities privately to the repository owner. Include the
affected version, minimal reproduction and expected impact. Do not include real
customer documents or secrets in the report.

