class LocalChickenThreadDetector:
    def __init__(self, *args, **kwargs):
        raise RuntimeError(
            "LocalChickenThreadDetector moved to smart_home_inference. "
            "Bridge runtime uses ChickenThreatInferenceClient."
        )

__all__ = ["LocalChickenThreadDetector"]
