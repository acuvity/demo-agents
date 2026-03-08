import os
import yaml

def load_config_yaml(path: str) -> dict:
    config_path = os.environ.get("CONFIG_PATH", path)
    
    if os.path.exists("/app/config.yaml"):
        config_path = "/app/config.yaml"
    
    with open(config_path, "r") as f:
        return yaml.safe_load(f)
