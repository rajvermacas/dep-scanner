# Security Guide - REST API Server

## Overview

This document provides security guidelines for deploying and operating the Dependency Scanner REST API server. The server has been designed with security-first principles and includes comprehensive protection against common web application vulnerabilities.

## Security Features Implemented

### Authentication & Authorization

- **HTTP Basic Authentication**: All endpoints require authentication
- **Environment-based Credentials**: No hardcoded credentials in source code
- **Secure Headers**: Proper WWW-Authenticate headers for 401 responses
- **Timing-safe Comparison**: Protection against timing attacks

### Input Validation & Injection Prevention

- **Git URL Validation**: Comprehensive validation of Git repository URLs
- **Command Injection Prevention**: Blocks shell metacharacters and dangerous patterns
- **Path Traversal Protection**: Prevents directory traversal attacks
- **Protocol Validation**: Only allows secure Git protocols (HTTPS, SSH, Git)

### SSRF (Server-Side Request Forgery) Protection

- **Private Network Blocking**: Blocks access to private IP ranges (RFC 1918)
- **Metadata Endpoint Blocking**: Prevents access to cloud metadata services
- **Domain Whitelisting**: Only allows trusted Git hosting domains by default
- **Port Restriction**: Limits access to standard Git ports only

### Resource Management & DoS Protection

- **Concurrent Job Limits**: Prevents resource exhaustion with configurable limits
- **Timeout Protection**: All operations have configurable timeout limits
- **Automatic Cleanup**: Temporary files and resources are automatically cleaned up
- **Job Lifecycle Management**: Comprehensive job tracking and resource monitoring

### Secure Git Operations

- **GitPython Integration**: Uses secure GitPython library instead of subprocess
- **Shallow Clones**: Performs shallow clones to reduce resource usage
- **No Interactive Prompts**: Disables all interactive Git prompts
- **Secure SSH Configuration**: Uses strict SSH host key checking

## Deployment Security Configuration

### Required Environment Variables

```bash
# Authentication (REQUIRED - No defaults)
export API_USERNAME="your_secure_username"
export API_PASSWORD="your_secure_password_123!"

# Optional Configuration
export GIT_CLONE_TIMEOUT=300          # Git clone timeout in seconds
export MAX_CONCURRENT_JOBS=5          # Maximum concurrent scan jobs
export JOB_TIMEOUT=1800               # Job timeout in seconds (30 minutes)
export CLEANUP_INTERVAL=300           # Cleanup interval in seconds
```

### Security Configuration Checklist

- [ ] Set strong, unique credentials via environment variables
- [ ] Use HTTPS for all production deployments
- [ ] Configure proper firewall rules to restrict access
- [ ] Enable logging and monitoring for security events
- [ ] Regularly update dependencies and base images
- [ ] Review and test backup/recovery procedures

## Trusted Domains Configuration

By default, the server only allows Git repositories from these trusted domains:

- `github.com`
- `gitlab.com`
- `bitbucket.org`
- `dev.azure.com`
- `ssh.dev.azure.com`
- `source.developers.google.com`

To add additional trusted domains, modify the `TRUSTED_DOMAINS` set in `src/dependency_scanner_tool/api/validation.py`.

## Security Testing

The server includes comprehensive security tests covering:

- **Authentication Tests**: 10 tests covering all authentication scenarios
- **Input Validation Tests**: 4 tests for injection and validation
- **SSRF Protection Tests**: 3 tests for network-based attacks
- **Resource Management Tests**: 4 tests for DoS protection
- **Timeout Protection Tests**: 3 tests for timeout mechanisms

Run security tests with:
```bash
python -m pytest tests/test_api/test_security.py -v
```

## Monitoring & Alerting

### Security Events to Monitor

- **Authentication Failures**: Failed login attempts
- **Invalid URLs**: Attempts to access restricted URLs
- **Resource Exhaustion**: Job queue limits reached
- **Timeout Events**: Operations exceeding time limits
- **Cleanup Failures**: Failed resource cleanup operations

### Recommended Alerts

- Multiple authentication failures from same IP
- Attempts to access private network ranges
- Job queue consistently at maximum capacity
- Frequent timeout events
- Disk space or memory usage warnings

## Incident Response

### Security Incident Types

1. **Authentication Bypass**: Unauthorized access to endpoints
2. **Injection Attacks**: Attempts to execute malicious commands
3. **SSRF Attacks**: Attempts to access internal resources
4. **Resource Exhaustion**: DoS attacks or resource abuse
5. **Data Exfiltration**: Unauthorized access to scan results

### Response Procedures

1. **Immediate Actions**:
   - Identify and block malicious IP addresses
   - Review access logs for scope of compromise
   - Rotate authentication credentials if compromised
   - Scale down or isolate affected instances

2. **Investigation**:
   - Analyze security logs and monitoring data
   - Identify attack vectors and vulnerabilities
   - Assess impact and data exposure
   - Document timeline and actions taken

3. **Recovery**:
   - Apply security patches or configuration changes
   - Restore from clean backups if necessary
   - Implement additional monitoring or controls
   - Update security documentation and procedures

## Security Best Practices

### Development

- Follow secure coding practices
- Use static analysis tools for security scanning
- Implement comprehensive input validation
- Never commit secrets or credentials to version control
- Keep dependencies updated and scan for vulnerabilities

### Deployment

- Use principle of least privilege for service accounts
- Implement network segmentation and access controls
- Enable comprehensive logging and monitoring
- Use infrastructure as code for consistent deployments
- Implement automated security scanning in CI/CD pipelines

### Operations

- Regularly review and rotate credentials
- Monitor for security events and anomalies
- Keep systems and dependencies updated
- Perform regular security assessments
- Maintain incident response procedures

## Security Contacts

For security issues or questions:

- Create an issue in the project repository
- Follow responsible disclosure for vulnerabilities
- Include detailed reproduction steps and impact assessment

## Version History

- **v1.0.0**: Initial security implementation with comprehensive protection
- **v1.1.0**: Added domain whitelisting and enhanced timeout protection
- **v1.2.0**: Implemented resource management and cleanup improvements

---

**Note**: This security guide should be reviewed and updated regularly as the system evolves and new threats emerge.