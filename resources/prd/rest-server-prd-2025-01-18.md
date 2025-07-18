# REST Server API - Product Requirements Document

**Document Version:** 1.0  
**Date:** January 18, 2025  
**Project:** Dependency Scanner Tool REST Server  
**Status:** Draft - Pending Approval

---

## Executive Summary

This PRD outlines the requirements for implementing a REST API server for the Dependency Scanner Tool. The REST server will enable other microservices to programmatically scan Git repositories for dependencies and receive categorized dependency analysis results via HTTP API calls.

The implementation will extend the existing CLI-based dependency scanner with a FastAPI-based web service that maintains all current functionality while providing a modern API interface for integration with other systems.

---

## Problem Statement

The current Dependency Scanner Tool operates exclusively as a CLI application that:
- Requires local file system access to scan projects
- Outputs results to disk as JSON/HTML files
- Cannot be easily integrated into microservice architectures
- Lacks programmatic access for automated workflows

**Business Impact:**
- Other microservices cannot leverage dependency scanning capabilities
- Manual intervention required for dependency analysis
- No standardized API for dependency classification
- Limited scalability for automated scanning workflows

---

## Objectives and Success Metrics

### Primary Objectives
1. **API-First Access**: Provide REST API endpoints for dependency scanning
2. **Microservice Integration**: Enable seamless integration with other services
3. **Backward Compatibility**: Maintain existing CLI functionality unchanged
4. **Standardized Response Format**: Return consistent, category-based dependency analysis

### Success Metrics
- **API Response Time**: < 30 seconds for typical repository scans
- **Concurrent Requests**: Support at least 5 concurrent scan operations
- **Uptime**: 99.9% availability when deployed
- **Error Rate**: < 1% for valid Git repository URLs
- **Integration Success**: Successful integration with at least one consuming microservice

---

## User Stories and Use Cases

### Primary User: **Other Microservices**

#### User Story 1: Repository Dependency Analysis
**As a** microservice developer  
**I want to** submit a Git repository URL and receive categorized dependency analysis  
**So that** I can make automated decisions based on dependency classifications  

**Acceptance Criteria:**
- Submit public Git repository URL via REST API
- Receive job ID for tracking scan progress
- Poll job status until completion
- Retrieve structured dependency analysis results
- Get boolean flags for each configured dependency category

#### User Story 2: Health Monitoring
**As a** system administrator  
**I want to** monitor the health status of the REST server  
**So that** I can ensure the service is operational  

**Acceptance Criteria:**
- Health check endpoint responds with service status
- Response includes basic system information
- Fast response time (< 1 second)

#### User Story 3: Asynchronous Processing
**As a** consuming microservice  
**I want to** submit scan requests asynchronously  
**So that** I don't block waiting for long-running operations  

**Acceptance Criteria:**
- Submit scan request returns immediately with job ID
- Job status endpoint shows current processing state
- Results available via separate endpoint once complete
- Automatic cleanup after successful retrieval

---

## Functional Requirements

### FR1: Repository Scanning API
**Endpoint:** `POST /scan`
- **Input:** JSON payload with `git_url` field
- **Output:** JSON response with `job_id`
- **Behavior:** 
  - Validates Git URL format
  - Clones repository to temporary directory
  - Initiates background scanning process
  - Returns job ID immediately

### FR2: Job Status Monitoring
**Endpoint:** `GET /jobs/{job_id}`
- **Input:** Job ID as path parameter
- **Output:** JSON response with job status
- **Behavior:**
  - Returns status: "pending", "running", "completed", "failed"
  - Includes progress information where available
  - Provides error details for failed jobs

### FR3: Results Retrieval
**Endpoint:** `GET /jobs/{job_id}/results`
- **Input:** Job ID as path parameter
- **Output:** Structured dependency analysis results
- **Behavior:**
  - Returns results only for completed jobs
  - Provides category-based boolean dependency flags
  - Includes original Git URL in response
  - Triggers cleanup after successful retrieval

### FR4: Health Check
**Endpoint:** `GET /health`
- **Input:** None
- **Output:** Service health status
- **Behavior:**
  - Returns HTTP 200 for healthy service
  - Includes basic system information
  - Fast response without heavy processing

### FR5: Basic Authentication
**All Endpoints:** HTTP Basic Authentication
- **Credentials:** Configurable via environment variables
- **Default:** username "admin", password "admin1234"
- **Behavior:**
  - All endpoints require authentication
  - Returns HTTP 401 for invalid credentials
  - Supports single credential set

---

## Non-Functional Requirements

### Performance Requirements
- **Response Time:** Health check < 1 second, scan submission < 5 seconds
- **Throughput:** Support minimum 5 concurrent scan operations
- **Scalability:** Designed for single-instance deployment
- **Memory Usage:** Efficient temporary directory management with cleanup

### Security Requirements
- **Authentication:** HTTP Basic Authentication for all endpoints
- **Authorization:** Single credential set for all operations
- **Data Protection:** No persistence of sensitive repository data
- **Access Control:** Public Git repositories only (no private repo support)

### Reliability Requirements
- **Error Handling:** Comprehensive error logging and user-friendly error messages
- **Fault Tolerance:** Graceful handling of Git clone failures and parsing errors
- **Recovery:** Automatic cleanup of temporary resources on failures
- **Monitoring:** Detailed logging for debugging and monitoring

### Compatibility Requirements
- **Python Version:** Python 3.8+ compatibility
- **Dependencies:** Minimal additional dependencies (FastAPI, uvicorn)
- **Platform:** Linux/Windows/macOS support
- **Deployment:** Azure App Service compatible

---

## Technical Constraints

### Infrastructure Constraints
- **Deployment Target:** Azure App Service (single instance)
- **Storage:** Local filesystem only (no external storage)
- **Network:** Outbound Git clone access required
- **Authentication:** Environment variable-based configuration

### Integration Constraints
- **Existing Codebase:** Must wrap existing DependencyScanner without modifications
- **Configuration:** Use existing config.yaml structure
- **Output Format:** Transform existing ScanResult to category-based format
- **CLI Compatibility:** Maintain full CLI functionality alongside REST API

### Technology Constraints
- **Framework:** FastAPI with async support
- **Job Queue:** FastAPI BackgroundTasks (no external queue system)
- **Authentication:** Basic HTTP authentication
- **Logging:** File-based logging to local logs directory

---

## API Specification

### Base URL
```
https://[deployment-host]/api/v1
```

### Authentication
```
Authorization: Basic [base64(username:password)]
```

### Endpoints

#### POST /scan
**Request:**
```json
{
    "git_url": "https://github.com/user/repository.git"
}
```

**Response:**
```json
{
    "job_id": "uuid-string",
    "status": "pending",
    "created_at": "2025-01-18T10:00:00Z"
}
```

#### GET /jobs/{job_id}
**Response:**
```json
{
    "job_id": "uuid-string",
    "status": "completed",
    "created_at": "2025-01-18T10:00:00Z",
    "completed_at": "2025-01-18T10:02:30Z",
    "progress": 100
}
```

#### GET /jobs/{job_id}/results
**Response:**
```json
{
    "git_url": "https://github.com/user/repository.git",
    "dependencies": {
        "Data Science": false,
        "Machine Learning": true,
        "Web Frameworks": true,
        "Database": false,
        "Security": true
    }
}
```

#### GET /health
**Response:**
```json
{
    "status": "healthy",
    "timestamp": "2025-01-18T10:00:00Z",
    "version": "1.0.0"
}
```

---

## Dependencies

### External Dependencies
- **FastAPI:** Web framework for REST API
- **uvicorn:** ASGI server for FastAPI
- **GitPython:** Git repository operations
- **python-multipart:** File upload support (if needed)
- **python-jose:** JWT token handling (if authentication evolves)

### Internal Dependencies
- **DependencyScanner:** Core scanning functionality
- **Configuration System:** Existing config.yaml structure
- **Parser Registry:** Existing language parsers
- **Analyzer Registry:** Existing import analyzers

### System Dependencies
- **Git:** Command-line Git client for repository cloning
- **Python 3.8+:** Runtime environment
- **File System:** Temporary directory support

---

## Data Models

### Job Model
```python
class Job(BaseModel):
    job_id: str
    git_url: str
    status: JobStatus
    created_at: datetime
    completed_at: Optional[datetime]
    error_message: Optional[str]
    progress: int
```

### Scan Request Model
```python
class ScanRequest(BaseModel):
    git_url: str
    
    @validator('git_url')
    def validate_git_url(cls, v):
        # Validate Git URL format
        return v
```

### Scan Result Model
```python
class ScanResult(BaseModel):
    git_url: str
    dependencies: Dict[str, bool]
```

### Job Status Enum
```python
class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
```

---

## Implementation Architecture

### Component Overview
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │  Job Manager    │    │ Git Repository  │
│                 │    │                 │    │    Handler      │
│  - Routes       │◄──►│  - Background   │◄──►│                 │
│  - Auth         │    │    Tasks        │    │  - Clone        │
│  - Validation   │    │  - Job Status   │    │  - Cleanup      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Response      │    │ Dependency      │    │  Configuration  │
│   Formatter     │    │   Scanner       │    │    Manager      │
│                 │    │                 │    │                 │
│  - Category     │◄──►│  - Existing     │◄──►│  - config.yaml  │
│    Mapping      │    │    Core Logic   │    │  - Categories   │
│  - JSON Output  │    │  - Scanners     │    │  - Validation   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Processing Flow
1. **Request Reception:** FastAPI receives scan request with Git URL
2. **Job Creation:** Generate UUID and create job entry
3. **Background Task:** Clone repository and initiate scanning
4. **Dependency Analysis:** Use existing DependencyScanner
5. **Result Transformation:** Convert to category-based boolean format
6. **Response Delivery:** Return structured JSON via polling endpoint
7. **Cleanup:** Remove temporary files and job data

---

## Error Handling Strategy

### Error Categories
1. **Validation Errors:** Invalid Git URLs, malformed requests
2. **Authentication Errors:** Invalid credentials, missing authentication
3. **Git Errors:** Repository not found, clone failures, network issues
4. **Scanning Errors:** Parser failures, file access issues
5. **System Errors:** Disk space, memory, temporary directory issues

### Error Response Format
```json
{
    "error": {
        "code": "INVALID_GIT_URL",
        "message": "The provided Git URL is not valid or accessible",
        "details": "Repository not found at https://github.com/invalid/repo.git",
        "timestamp": "2025-01-18T10:00:00Z"
    }
}
```

### Error Codes
- **INVALID_GIT_URL:** Git URL validation failure
- **REPOSITORY_NOT_FOUND:** Repository does not exist or is inaccessible
- **CLONE_FAILED:** Git clone operation failed
- **SCANNING_ERROR:** Dependency scanning process failed
- **JOB_NOT_FOUND:** Requested job ID does not exist
- **INTERNAL_ERROR:** Unexpected system error

---

## Security Considerations

### Authentication
- HTTP Basic Authentication for all endpoints
- Credentials stored in environment variables
- No session management or token expiration

### Data Security
- No persistence of repository data beyond job completion
- Automatic cleanup of temporary directories
- No caching of scan results
- No logging of sensitive information

### Access Control
- Public Git repositories only
- No support for private repository authentication
- Single credential set for all operations

### Network Security
- HTTPS support for production deployment
- Input validation for all API parameters
- Git URL validation to prevent SSRF attacks

---

## Logging and Monitoring

### Logging Strategy
- **Log Level:** DEBUG level for comprehensive debugging
- **Log Location:** Local filesystem in `logs/` directory
- **Log Format:** Structured JSON format with timestamps
- **Log Rotation:** Daily rotation with size limits

### Monitoring Requirements
- **Health Check Endpoint:** `/health` for service monitoring
- **Error Tracking:** Comprehensive error logging
- **Performance Metrics:** Response times and success rates
- **Resource Usage:** Memory and disk space monitoring

### Log Categories
- **API Requests:** All incoming requests and responses
- **Git Operations:** Clone operations and cleanup
- **Scanning Process:** Dependency scanning progress and results
- **Error Events:** All error conditions and stack traces

---

## Testing Strategy

### Unit Testing
- **FastAPI Routes:** Test all endpoint functionality
- **Authentication:** Test basic auth implementation
- **Git Operations:** Test repository cloning and cleanup
- **Result Transformation:** Test category mapping logic

### Integration Testing
- **End-to-End API:** Test complete scan workflow
- **Git Repository Integration:** Test with real repositories
- **Background Task Processing:** Test async job execution
- **Error Scenarios:** Test error handling and recovery

### Performance Testing
- **Concurrent Requests:** Test multiple simultaneous scans
- **Large Repositories:** Test with complex projects
- **Resource Cleanup:** Test memory and disk cleanup
- **Response Times:** Validate performance requirements

### Test Data
- **Public Test Repositories:** Curated set of test repositories
- **Mock Git Servers:** Local test repositories
- **Configuration Files:** Test category configurations
- **Error Scenarios:** Invalid URLs and edge cases

---

## Deployment Strategy

### Azure App Service Configuration
- **Runtime:** Python 3.8+ with FastAPI
- **Startup Command:** `uvicorn main:app --host 0.0.0.0 --port 8000`
- **Environment Variables:** Authentication credentials and configuration
- **Health Check:** Configure health endpoint for monitoring

### Environment Variables
```bash
# Authentication
REST_API_USERNAME=admin
REST_API_PASSWORD=admin1234

# Logging
LOG_LEVEL=DEBUG
LOG_DIR=logs

# Git Operations
GIT_CLONE_TIMEOUT=300
TEMP_DIR=/tmp/repo-scans
```

### Deployment Checklist
- [ ] Configure environment variables
- [ ] Set up health check monitoring
- [ ] Configure log directory permissions
- [ ] Test Git clone functionality
- [ ] Verify configuration file access
- [ ] Validate authentication setup

---

## Timeline and Milestones

### Phase 1: Core Implementation (Week 1-2)
- **Milestone 1.1:** FastAPI application structure
- **Milestone 1.2:** Basic authentication implementation
- **Milestone 1.3:** Git repository cloning functionality
- **Milestone 1.4:** Background task processing

### Phase 2: Scanner Integration (Week 2-3)
- **Milestone 2.1:** DependencyScanner wrapper
- **Milestone 2.2:** Result transformation logic
- **Milestone 2.3:** Category mapping implementation
- **Milestone 2.4:** Error handling and logging

### Phase 3: API Endpoints (Week 3-4)
- **Milestone 3.1:** Scan submission endpoint
- **Milestone 3.2:** Job status monitoring
- **Milestone 3.3:** Results retrieval endpoint
- **Milestone 3.4:** Health check endpoint

### Phase 4: Testing and Deployment (Week 4-5)
- **Milestone 4.1:** Unit and integration tests
- **Milestone 4.2:** Performance testing
- **Milestone 4.3:** Azure deployment preparation
- **Milestone 4.4:** Production deployment

---

## Risk Assessment

### High Risk
- **Git Clone Failures:** Network connectivity or repository access issues
  - *Mitigation:* Comprehensive error handling and retry logic
- **Memory Usage:** Large repositories causing memory exhaustion
  - *Mitigation:* Repository size limits and monitoring
- **Concurrent Processing:** Background tasks overwhelming system resources
  - *Mitigation:* Task queue limits and resource monitoring

### Medium Risk
- **Authentication Security:** Basic auth credential exposure
  - *Mitigation:* Environment variable configuration and HTTPS
- **Temporary Directory Cleanup:** Disk space exhaustion from failed cleanup
  - *Mitigation:* Robust cleanup logic and monitoring
- **Configuration Compatibility:** Changes to existing config.yaml breaking API
  - *Mitigation:* Configuration validation and versioning

### Low Risk
- **FastAPI Learning Curve:** Team familiarity with FastAPI framework
  - *Mitigation:* Documentation and training resources
- **Azure Deployment:** Platform-specific deployment challenges
  - *Mitigation:* Azure documentation and testing in staging environment

---

## Success Criteria

### Technical Success Criteria
- [ ] All API endpoints functional and tested
- [ ] Authentication system working correctly
- [ ] Git repository cloning and cleanup operational
- [ ] Background task processing stable
- [ ] Error handling comprehensive and user-friendly
- [ ] Logging system providing adequate debugging information

### Business Success Criteria
- [ ] Microservice integration successful
- [ ] Performance requirements met
- [ ] Azure deployment successful
- [ ] Category-based dependency analysis accurate
- [ ] CLI functionality preserved unchanged

### Acceptance Criteria
- [ ] Complete API documentation generated
- [ ] All unit and integration tests passing
- [ ] Performance benchmarks met
- [ ] Security requirements satisfied
- [ ] Deployment procedures documented
- [ ] Monitoring and logging operational

---

## Appendices

### Appendix A: Configuration File Structure
Reference to existing `config.yaml` structure with categories and dependency patterns.

### Appendix B: Existing DependencyScanner Integration
Details on how the REST API will integrate with the existing scanner architecture.

### Appendix C: Azure App Service Requirements
Specific configuration requirements for Azure deployment.

### Appendix D: API Testing Examples
Sample API calls and expected responses for testing and integration.

---

**Document Status:** Ready for Review  
**Next Steps:** Stakeholder review and approval for implementation  
**Contact:** Development Team  
**Version Control:** Track changes and approvals in project repository