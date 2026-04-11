"""Global exception hierarchy."""


class AppError(Exception):
    """Base application exception."""

    def __init__(self, message: str, *, code: str = "app_error") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class ConfigError(AppError):
    """Configuration related exception."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="config_error")


class ValidationError(AppError):
    """Input validation exception."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="validation_error")


class InfrastructureError(AppError):
    """Infrastructure component exception."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="infrastructure_error")
