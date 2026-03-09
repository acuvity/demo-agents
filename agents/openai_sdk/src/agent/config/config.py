import os
import yaml

def load_config_yaml() -> dict:

    config_path = os.environ.get("CONFIG_PATH","/app/config.yaml")

    if not os.path.exists(config_path):
        # if the config path is not set, use the default config path
        _RUNTIME_DIR = os.path.dirname(os.path.abspath(__file__))
        _BACKEND_DIR = os.path.dirname(_RUNTIME_DIR)

        config_path = os.path.join(_BACKEND_DIR, "config.yaml")
    
    with open(config_path, "r") as f:
        return yaml.safe_load(f)
