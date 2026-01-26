"""
Custom exceptions for PyBase.

Provides a hierarchy of exceptions that map to HTTP status codes
and include structured error information.
"""

from typing import Any


class PyBaseException(Exception):
    """
    Base exception for all PyBase errors.

    All custom exceptions should inherit from this class.
    """

    # Default status code for base exception
    status_code = 500

    def __init__(
        self,
        message: str,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize exception.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
            details: Additional error details
        """
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API response."""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }


# =============================================================================
# HTTP 400 - Bad Request Errors
# =============================================================================


class BadRequestError(PyBaseException):
    """Invalid request parameters or payload."""

    status_code = 400


class ValidationError(BadRequestError):
    """Request validation failed."""

    def __init__(
        self,
        message: str = "Validation error",
        errors: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details={"errors": errors or []},
        )


class InvalidFieldTypeError(BadRequestError):
    """Invalid field type specified."""

    def __init__(self, field_type: str) -> None:
        super().__init__(
            message=f"Invalid field type: {field_type}",
            code="INVALID_FIELD_TYPE",
            details={"field_type": field_type},
        )


class InvalidFieldValueError(BadRequestError):
    """Invalid value for field type."""

    def __init__(self, field_name: str, expected_type: str, received_value: Any) -> None:
        super().__init__(
            message=f"Invalid value for field '{field_name}'. Expected {expected_type}.",
            code="INVALID_FIELD_VALUE",
            details={
                "field_name": field_name,
                "expected_type": expected_type,
                "received_value": str(received_value)[:100],
            },
        )


class DuplicateValueError(BadRequestError):
    """Duplicate value detected for unique field."""

    def __init__(self, field_name: str, value: Any) -> None:
        super().__init__(
            message=f"Duplicate value for field '{field_name}'. Value '{value}' already exists.",
            code="DUPLICATE_VALUE",
            details={
                "field_name": field_name,
                "value": str(value)[:100],
            },
        )


class RequiredFieldError(BadRequestError):
    """Required field is missing."""

    def __init__(self, field_name: str) -> None:
        super().__init__(
            message=f"Required field '{field_name}' is missing",
            code="REQUIRED_FIELD",
            details={
                "field_name": field_name,
            },
        )


# =============================================================================
# HTTP 401 - Authentication Errors
# =============================================================================


class AuthenticationError(PyBaseException):
    """Authentication failed."""

    status_code = 401

    def __init__(
        self,
        message: str = "Authentication required",
        code: str = "AUTHENTICATION_REQUIRED",
    ) -> None:
        super().__init__(message=message, code=code)


class InvalidCredentialsError(AuthenticationError):
    """Invalid username or password."""

    def __init__(self) -> None:
        super().__init__(
            message="Invalid email or password",
            code="INVALID_CREDENTIALS",
        )


class TokenExpiredError(AuthenticationError):
    """JWT token has expired."""

    def __init__(self) -> None:
        super().__init__(
            message="Token has expired",
            code="TOKEN_EXPIRED",
        )


class InvalidTokenError(AuthenticationError):
    """JWT token is invalid."""

    def __init__(self) -> None:
        super().__init__(
            message="Invalid token",
            code="INVALID_TOKEN",
        )


class InvalidAPIKeyError(AuthenticationError):
    """API key is invalid."""

    def __init__(self) -> None:
        super().__init__(
            message="Invalid API key",
            code="INVALID_API_KEY",
        )


# =============================================================================
# HTTP 403 - Authorization Errors
# =============================================================================


class AuthorizationError(PyBaseException):
    """Authorization failed - user lacks permission."""

    status_code = 403

    def __init__(
        self,
        message: str = "You don't have permission to perform this action",
        resource: str | None = None,
        action: str | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="FORBIDDEN",
            details={"resource": resource, "action": action},
        )


class InsufficientPermissionsError(AuthorizationError):
    """User lacks required permissions."""

    def __init__(self, required_permission: str) -> None:
        super().__init__(
            message=f"Insufficient permissions. Required: {required_permission}",
        )
        self.details["required_permission"] = required_permission


class PermissionDeniedError(AuthorizationError):
    """User is not permitted to perform this action."""

    def __init__(
        self,
        message: str = "You don't have permission to perform this action",
    ) -> None:
        super().__init__(message=message)


# =============================================================================
# HTTP 404 - Not Found Errors
# =============================================================================


class NotFoundError(PyBaseException):
    """Requested resource not found."""

    status_code = 404

    def __init__(
        self,
        resource: str,
        identifier: str | None = None,
    ) -> None:
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} with ID '{identifier}' not found"

        super().__init__(
            message=message,
            code="NOT_FOUND",
            details={"resource": resource, "identifier": identifier},
        )


class UserNotFoundError(NotFoundError):
    """User not found."""

    def __init__(self, user_id: str | None = None) -> None:
        super().__init__(resource="User", identifier=user_id)


class WorkspaceNotFoundError(NotFoundError):
    """Workspace not found."""

    def __init__(self, workspace_id: str | None = None) -> None:
        super().__init__(resource="Workspace", identifier=workspace_id)


class BaseNotFoundError(NotFoundError):
    """Base not found."""

    def __init__(self, base_id: str | None = None) -> None:
        super().__init__(resource="Base", identifier=base_id)


class TableNotFoundError(NotFoundError):
    """Table not found."""

    def __init__(self, table_id: str | None = None) -> None:
        super().__init__(resource="Table", identifier=table_id)


class FieldNotFoundError(NotFoundError):
    """Field not found."""

    def __init__(self, field_id: str | None = None) -> None:
        super().__init__(resource="Field", identifier=field_id)


class RecordNotFoundError(NotFoundError):
    """Record not found."""

    def __init__(self, record_id: str | None = None) -> None:
        super().__init__(resource="Record", identifier=record_id)


class ViewNotFoundError(NotFoundError):
    """View not found."""

    def __init__(self, view_id: str | None = None) -> None:
        super().__init__(resource="View", identifier=view_id)


# =============================================================================
# HTTP 409 - Conflict Errors
# =============================================================================


class ConflictError(PyBaseException):
    """Resource conflict."""

    status_code = 409

    def __init__(
        self,
        message: str,
        resource: str | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="CONFLICT",
            details={"resource": resource},
        )


class DuplicateError(ConflictError):
    """Duplicate resource."""

    def __init__(self, resource: str, field: str, value: str) -> None:
        super().__init__(
            message=f"{resource} with {field} '{value}' already exists",
            resource=resource,
        )
        self.details["field"] = field
        self.details["value"] = value


class EmailAlreadyExistsError(DuplicateError):
    """Email already registered."""

    def __init__(self, email: str) -> None:
        super().__init__(resource="User", field="email", value=email)


# =============================================================================
# HTTP 422 - Unprocessable Entity
# =============================================================================


class UnprocessableEntityError(PyBaseException):
    """Request cannot be processed."""

    status_code = 422


class FormulaError(UnprocessableEntityError):
    """Formula parsing or execution error."""

    def __init__(self, formula: str, error: str) -> None:
        super().__init__(
            message=f"Formula error: {error}",
            code="FORMULA_ERROR",
            details={"formula": formula, "error": error},
        )


# =============================================================================
# HTTP 429 - Rate Limit Errors
# =============================================================================


class RateLimitError(PyBaseException):
    """Rate limit exceeded."""

    status_code = 429

    def __init__(self, retry_after: int | None = None) -> None:
        super().__init__(
            message="Rate limit exceeded. Please try again later.",
            code="RATE_LIMIT_EXCEEDED",
            details={"retry_after": retry_after},
        )


# =============================================================================
# HTTP 500 - Internal Server Errors
# =============================================================================


class InternalError(PyBaseException):
    """Internal server error."""

    status_code = 500

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        original_error: Exception | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="INTERNAL_ERROR",
        )
        self.original_error = original_error


class DatabaseError(InternalError):
    """Database operation failed."""

    def __init__(self, message: str = "Database operation failed") -> None:
        super().__init__(message=message)
        self.code = "DATABASE_ERROR"


class ExtractionError(InternalError):
    """CAD/PDF extraction failed."""

    def __init__(self, message: str, file_type: str | None = None) -> None:
        super().__init__(message=message)
        self.code = "EXTRACTION_ERROR"
        self.details["file_type"] = file_type


# =============================================================================
# HTTP 503 - Service Unavailable
# =============================================================================


class ServiceUnavailableError(PyBaseException):
    """External service unavailable."""

    status_code = 503

    def __init__(self, service: str) -> None:
        super().__init__(
            message=f"Service '{service}' is currently unavailable",
            code="SERVICE_UNAVAILABLE",
            details={"service": service},
        )
