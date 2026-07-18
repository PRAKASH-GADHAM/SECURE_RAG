# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | Yes       |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **DO NOT** open a public GitHub issue
2. Email security@example.com with details
3. Include steps to reproduce
4. Allow 48 hours for initial response

## Security Features

- JWT authentication with short-lived tokens
- Rate limiting on all endpoints
- Input validation and sanitization
- Prompt injection detection
- Output content moderation
- Security headers (HSTS, CSP, etc.)
- Non-root Docker containers
- Encrypted secrets in environment variables

## Security Best Practices

1. Always use strong, unique passwords
2. Rotate JWT secrets regularly
3. Use HTTPS in production
4. Keep dependencies updated
5. Monitor security logs
6. Run regular security scans
