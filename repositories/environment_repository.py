import json

from models.environment import Environment


class EnvironmentRepository:

    def __init__(self, config_file="config/environments.json"):
        self.config_file = config_file

    def get_all(self) -> list[Environment]:
        with open(self.config_file, "r") as f:
            data = json.load(f)
        return [Environment(**item) for item in data]

    def get(self, name: str) -> Environment | None:
        environments = self.get_all()

        for env in environments:
            if env.name == name:
                return env
        return None