from smart_home_inference.config import load_inference_config_from_environment


def main():
    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit(
            "Install the inference extra to run the API server: "
            "pip install -e \".[inference]\""
        ) from exc

    config = load_inference_config_from_environment()
    uvicorn.run(
        "smart_home_inference.api:app",
        host=config.http.host,
        port=config.http.port,
    )


if __name__ == "__main__":
    main()
