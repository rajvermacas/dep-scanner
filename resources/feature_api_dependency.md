## Feature Requirement: Treat REST API Calls as Categorized Dependencies

This feature aims to integrate REST API calls into the dependency scanning and categorization framework, allowing them to be classified, assigned an allowed/restricted status, and reported consistently with other project dependencies.

### High-Level Technical Design

1.  **API Call as Dependency**: API call URLs will be treated as a distinct type of dependency. The full URL will serve as the primary identifier (name) for categorization.
2.  **Configurable Categorization**: The existing `config.yaml` will be extended to define categories and allowed/restricted statuses for API call URLs using URL patterns (e.g., regex or glob patterns).
3.  **Integrated Classification**: A new or extended classification mechanism will process detected API calls, apply the URL patterns from `config.yaml`, and assign a category and an allowed/restricted status to each API call.
4.  **Enhanced Reporting**: The HTML report will be updated to display the assigned category and status for each API call within its dedicated "REST API Calls" section, mirroring the visual presentation of regular dependencies (e.g., using badges).

### Step-by-Step To-Do List

1.  **Analyze Existing API Analysis**:
    *   Review `src/dependency_scanner_tool/api_analyzers/` to understand the current API call detection and extraction process. Confirm that full URLs are being captured.
2.  **Update `config.yaml` Schema**:
    *   Modify `config.yaml` to introduce a new section (e.g., `api_dependency_patterns`) that allows defining URL patterns for categorization and status. This section will contain lists of patterns for `allowed_api_urls`, `restricted_api_urls`, and `api_categories`.
3.  **Implement API Dependency Classification**:
    *   Create or extend a classification component (e.g., in `src/dependency_scanner_tool/categorization.py` or a new `src/dependency_scanner_tool/api_categorization.py`) responsible for:
        *   Loading URL patterns from the updated `config.yaml`.
        *   Taking a detected API call URL.
        *   Applying the defined patterns to determine its category.
        *   Assigning an `allowed`, `restricted`, or `unknown` status based on the categorization and explicit allowed/restricted lists.
4.  **Integrate API Classification into Scanner**:
    *   Modify `src/dependency_scanner_tool/scanner.py` to:
        *   Call the API analysis component to get raw API calls.
        *   Pass these raw API calls through the new API dependency classification logic.
        *   Store the resulting categorized API dependencies within the `ScanResult` object, potentially in a new dedicated field or by extending the existing dependency list with a `type` attribute.
5.  **Enhance HTML Report Generation**:
    *   Modify `src/dependency_scanner_tool/html_report.py` to:
        *   Retrieve the categorized API dependencies from the `ScanResult`.
        *   Prepare this data for rendering in the HTML template, ensuring category and status information is available for each API call.
    *   Update `src/dependency_scanner_tool/reporters/templates/report.html` to:
        *   Add new columns (e.g., "Category", "Status") to the "REST API Calls" table.
        *   Render the category and status for each API call using appropriate styling (e.g., badges for status) consistent with the main "Dependencies" table.
6.  **Write Comprehensive Tests**:
    *   **Unit Tests**: For the new `config.yaml` parsing logic for URL patterns, and for the API dependency classification logic (e.g., `tests/test_api_categorization.py`).
    *   **Integration Tests**: To verify that the scanner correctly processes API calls, applies categorization, and includes them in the `ScanResult` (e.g., extending `tests/test_scanner.py`).
    *   **UI Tests**: For the HTML report to confirm that API call categories and statuses are displayed correctly and consistently (e.g., extending `tests/test_html_report_ui.py`).

### Files to be Modified/Created and Rationale

*   **`config.yaml` (Modified)**
    *   **Rationale**: To introduce a new configuration structure for defining URL patterns that will be used to categorize API calls and determine their allowed/restricted status. This centralizes the configuration for all dependency types.
    *   **Specific Change**: Add a new top-level key, e.g., `api_dependency_patterns`, which will contain `allowed_urls`, `restricted_urls`, and `categories` (mapping category names to lists of URL patterns).
*   **`src/dependency_scanner_tool/scanner.py` (Modified)**
    *   **Rationale**: To orchestrate the new API dependency classification process by integrating the API analysis results with the categorization logic and updating the `ScanResult`.
    *   **Specific Change**: Add calls to the new API classification component and update the `ScanResult` object to include the categorized API dependencies.
*   **`src/dependency_scanner_tool/categorization.py` (Modified/New `api_categorization.py`)**
    *   **Rationale**: To implement the core logic for classifying API call URLs based on the patterns defined in `config.yaml` and assigning their status. This ensures a modular and testable classification system.
    *   **Specific Change**: If extending `categorization.py`, add methods to handle API-specific classification. If creating a new file, define a class (e.g., `ApiDependencyClassifier`) with methods for `classify_api_call` and `determine_api_status`.
*   **`src/dependency_scanner_tool/html_report.py` (Modified)**
    *   **Rationale**: To adapt the data passed to the HTML template, ensuring that the category and status information for API calls is available for rendering.
    *   **Specific Change**: Modify the data preparation logic to include category and status for each API call entry.
*   **`src/dependency_scanner_tool/reporters/templates/report.html` (Modified)**
    *   **Rationale**: To update the user interface of the generated report, visually presenting the category and status of API calls in a manner consistent with other dependencies.
    *   **Specific Change**: Add new `<th>` and `<td>` elements within the "REST API Calls" table to display "Category" and "Status", utilizing existing badge styles for status.
*   **`src/dependency_scanner_tool/api_analyzers/python_api_analyzer.py` (Review)**
    *   **Rationale**: To confirm that the existing API extraction logic provides the full URL, which is crucial for the new categorization based on URL patterns.
    *   **Specific Change**: Verify that the `ApiCall` object (or equivalent) contains the complete URL string.
*   **`tests/` (New/Modified Test Files)**
    *   **Rationale**: To ensure the correctness, robustness, and maintainability of the new feature by providing comprehensive test coverage for configuration parsing, classification logic, and report generation.
    *   **Specific Change**: Create new test files (e.g., `tests/test_api_categorization.py`) and add test cases for `config.yaml` parsing of URL patterns, API classification logic (including edge cases for patterns), and integration tests for the scanner and HTML report generation.
