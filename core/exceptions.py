class AppError(Exception):
    """Базова помилка застосунку."""


class ConfigError(AppError):
    """Помилка конфігурації."""


class DocxParseError(AppError):
    """Помилка обробки DOCX."""


class StorageError(AppError):
    """Помилка сховища."""
