from smart_home_bridge.models import ChickenThreadModelConfig

MODEL_CLASS_NAMES = (
    "chicken",
    "other_poultry",
    "person",
    "cat",
    "dog",
    "wild_mammal_threat",
    "rodent",
    "bird",
)

LABEL_ALIASES = {
    "fox": "wild_mammal_threat",
    "marten": "wild_mammal_threat",
    "weasel": "wild_mammal_threat",
    "marten_weasel": "wild_mammal_threat",
    "other_bird": "bird",
    "bird_of_prey": "bird",
}

RISK_BY_LABEL = {
    "chicken": 0.0,
    "other_poultry": 0.0,
    "person": 0.0,
    "cat": 0.55,
    "dog": 0.75,
    "wild_mammal_threat": 0.95,
    "rodent": 0.65,
    "bird": 0.6,
}


def default_model_config(model_path: str = "models/chicken_thread_detector/yolo11s.pt") -> ChickenThreadModelConfig:
    return ChickenThreadModelConfig(
        model_path=model_path,
        class_names=MODEL_CLASS_NAMES,
        risk_by_label=RISK_BY_LABEL,
        label_aliases=LABEL_ALIASES,
        confidence_threshold=0.35,
        image_size=640,
        medium_threshold=0.4,
        high_threshold=0.7,
        critical_threshold=0.9,
    )
