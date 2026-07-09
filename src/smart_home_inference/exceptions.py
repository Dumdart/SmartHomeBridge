class InferenceError(RuntimeError):
    """Base error for inference backend failures."""


class InvalidImageError(InferenceError):
    pass


class ImageTooLargeError(InferenceError):
    pass


class ModelUnavailableError(InferenceError):
    pass


class InferenceExecutionError(InferenceError):
    pass
