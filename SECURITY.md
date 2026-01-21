# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | :white_check_mark: |
| < 0.2   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it by:

1. **Do NOT** open a public issue
2. Email the maintainers (if available) or open a private security advisory on GitHub
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will respond within 48 hours and work on a fix as soon as possible.

## Security Updates

### Latest Security Fixes (2024-01-21)

#### Dependency Compatibility Updates (2024-01-21 - Latest)

1. **LangChain Community Compatibility Fix**
   - **Issue**: Dependency conflict between langchain 0.3.15 and langchain-community 0.3.28
   - **Conflict**: langchain-community 0.3.28 requires langchain>=0.3.27, but had langchain 0.3.15
   - **Fixed**: Upgraded langchain from 0.3.15 → 0.3.27
   - **Impact**: All langchain packages now fully compatible with each other

2. **LangSmith Compatibility Fix**
   - **Issue**: Dependency conflict between langchain 0.3.10 and langchain-core 0.3.81
   - **Conflict**: langchain 0.3.10 requires langsmith<0.2.0, but langchain-core 0.3.81 requires langsmith>=0.3.45
   - **Fixed**: Upgraded langchain from 0.3.10 → 0.3.15 (then to 0.3.27)
   - **Impact**: Resolves langsmith version conflict

3. **Pydantic Compatibility Fix**
   - **Issue**: Dependency conflict between pydantic 2.5.3 and langchain 0.3.10
   - **Affected**: pydantic 2.5.3 (too old for langchain 0.3.10)
   - **Fixed**: Upgraded to pydantic 2.10.3
   - **Reason**: langchain requires pydantic>=2.7.4
   - **Impact**: Resolved installation conflicts, ensures compatibility across all packages

#### Fixed Vulnerabilities

1. **FastAPI ReDoS Vulnerability**
   - **CVE**: Content-Type Header ReDoS
   - **Affected**: fastapi <= 0.109.0
   - **Fixed**: Upgraded to fastapi 0.115.0
   - **Impact**: Prevented potential Regular Expression Denial of Service attacks

2. **LangChain Community XXE Vulnerability**
   - **CVE**: XML External Entity (XXE) Attacks
   - **Affected**: langchain-community < 0.3.27
   - **Fixed**: Upgraded to langchain-community 0.3.28
   - **Impact**: Protected against XML-based injection attacks

3. **LangChain Community SSRF Vulnerability**
   - **CVE**: Server-Side Request Forgery in RequestsToolkit
   - **Affected**: langchain-community < 0.0.28
   - **Fixed**: Upgraded to langchain-community 0.3.28
   - **Impact**: Prevented unauthorized server-side requests

4. **LangChain Pickle Deserialization Vulnerability**
   - **CVE**: Unsafe deserialization of untrusted data
   - **Affected**: langchain-community < 0.2.4
   - **Fixed**: Upgraded to langchain-community 0.3.28
   - **Impact**: Prevented arbitrary code execution via malicious pickle data

5. **LangChain Core Template Injection Vulnerability**
   - **CVE**: Template Injection via Attribute Access in Prompt Templates
   - **Affected**: langchain-core <= 0.3.79
   - **Fixed**: Upgraded to langchain-core 0.3.81
   - **Impact**: Prevented template injection attacks that could expose sensitive data

6. **LangChain Core Serialization Injection Vulnerability**
   - **CVE**: Serialization injection enables secret extraction in dumps/loads APIs
   - **Affected**: langchain-core < 0.3.81
   - **Fixed**: Upgraded to langchain-core 0.3.81
   - **Impact**: Protected against secret extraction via malicious serialized objects

## Security Best Practices

### For Developers

1. **Keep Dependencies Updated**
   ```bash
   pip install --upgrade -r requirements.txt
   npm update  # for frontend
   ```

2. **Run Security Scans**
   ```bash
   # Python
   pip install safety
   safety check -r requirements.txt
   
   # Node.js
   npm audit
   ```

3. **Code Review**
   - All PRs require review
   - Security-sensitive changes need extra scrutiny
   - Use static analysis tools

4. **Environment Variables**
   - Never commit `.env` files
   - Use `.env.example` as template
   - Store secrets securely (not in code)

5. **API Keys & Certificates**
   - Keep Vespa certificates secure (chmod 600)
   - Never commit private keys
   - Rotate credentials regularly

### For Deployment

1. **CORS Configuration**
   - Restrict allowed origins in production
   - Don't use `allow_origins=["*"]`
   - Update CORS settings in `backend/app.py`

2. **Rate Limiting**
   - Implement rate limiting in production
   - Use tools like `slowapi` or nginx

3. **Input Validation**
   - All user inputs are validated via Pydantic
   - Sanitize outputs to prevent XSS

4. **HTTPS Only**
   - Use HTTPS in production
   - Ensure Vespa connections use TLS

5. **Secrets Management**
   - Use environment variables
   - Consider tools like HashiCorp Vault
   - Never log sensitive data

## Dependency Management

### Automatic Updates

We use GitHub Dependabot to automatically:
- Detect vulnerable dependencies
- Create PRs for security updates
- Keep dependencies up to date

### Manual Updates

Check for vulnerabilities:
```bash
# Backend
cd backend
pip install safety
safety check -r requirements.txt

# Frontend
cd frontend
npm audit
npm audit fix
```

### Version Pinning

We pin exact versions in `requirements.txt` and `package.json` to ensure:
- Reproducible builds
- Controlled upgrades
- Security traceability

## Security Features in OneSeek

1. **Local-First Architecture**
   - LLM runs locally (no external API calls)
   - User data stays on device
   - No telemetry by default

2. **Input Sanitization**
   - Pydantic validation on all inputs
   - Type checking in TypeScript
   - XSS prevention in React

3. **Secure Connections**
   - TLS for Vespa Cloud
   - Certificate-based auth
   - Encrypted data in transit

4. **No User Authentication (MVP)**
   - Current MVP has no user system
   - Suitable for single-user local development
   - Production deployment should add auth

## Known Limitations (MVP)

⚠️ This is an MVP intended for local development:

1. **No Authentication**
   - No user login system
   - Not suitable for multi-user deployment
   - Add authentication before exposing to internet

2. **No Rate Limiting**
   - Can be abused if exposed publicly
   - Add rate limiting for production

3. **Local Storage Only**
   - Chat history in browser localStorage
   - No server-side session management
   - Consider adding proper backend storage

4. **CORS Wide Open (Dev)**
   - Allows localhost origins
   - Restrict in production

5. **No Input Length Limits**
   - Could cause resource exhaustion
   - Add limits in production

## Roadmap

Future security enhancements:

- [ ] User authentication & authorization
- [ ] Rate limiting
- [ ] Input length limits
- [ ] Audit logging
- [ ] CSP headers
- [ ] API key management
- [ ] Multi-tenancy support
- [ ] Blockchain verification (planned feature)

## Contact

For security concerns, please contact the repository maintainers.

## Acknowledgments

We thank the security researchers and open source community for:
- Identifying vulnerabilities
- Providing patches
- Maintaining security advisories
