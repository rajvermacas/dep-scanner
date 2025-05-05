"""Custom exceptions for the dependency scanner."""

class DependencyScannerError(Exception):
    """Base exception class for all dependency scanner errors."""
    pass


class FileAccessError(DependencyScannerError):
    """Exception raised when a file cannot be accessed."""
    
    def __init__(self, file_path, message=None):
        self.file_path = file_path
        self.message = message or f"Cannot access file: {file_path}"
        super().__init__(self.message)


class DirectoryAccessError(DependencyScannerError):
    """Exception raised when a directory cannot be accessed."""
    
    def __init__(self, directory_path, message=None):
        self.directory_path = directory_path
        self.message = message or f"Cannot access directory: {directory_path}"
        super().__init__(self.message)


class ParsingError(DependencyScannerError):
    """Exception raised when parsing a file fails."""
    
    def __init__(self, file_path, message=None):
        self.file_path = file_path
        self.message = message or f"Error parsing file: {file_path}"
        super().__init__(self.message)


class ConfigurationError(DependencyScannerError):
    """Exception raised when there's an issue with configuration."""
    pass


class LanguageDetectionError(DependencyScannerError):
    """Exception raised when language detection fails."""
    
    def __init__(self, file_path=None, message=None):
        self.file_path = file_path
        if file_path:
            self.message = message or f"Failed to detect language for: {file_path}"
        else:
            self.message = message or "Language detection failed"
        super().__init__(self.message)


class PackageManagerDetectionError(DependencyScannerError):
    """Exception raised when package manager detection fails."""
    
    def __init__(self, message=None):
        self.message = message or "Package manager detection failed"
        super().__init__(self.message)


class DependencyExtractionError(DependencyScannerError):
    """Exception raised when dependency extraction fails."""
    
    def __init__(self, file_path=None, message=None):
        self.file_path = file_path
        if file_path:
            self.message = message or f"Failed to extract dependencies from: {file_path}"
        else:
            self.message = message or "Dependency extraction failed"
        super().__init__(self.message)
