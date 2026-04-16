class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class NotFoundError(AppError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(404, code, message)


class BadRequestError(AppError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(400, code, message)


class ConflictError(AppError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(409, code, message)
