import json
from dataclasses import asdict
from typing import Optional

from models.environment import Environment


class EnvironmentRepository:

    def __init__(self, config_file="config/environments.json"):
        self.config_file = config_file

    def get_all(self) -> list[Environment]:
        with open(self.config_file, "r") as f:
            data = json.load(f)
        return [Environment(**item) for item in data]

    def get(self, name: str) -> Optional[Environment]:
        for env in self.get_all():
            if env.name == name:
                return env
        return None

    def save_all(self, environments: list[Environment]) -> None:
        data = []
        for env in environments:
            d = asdict(env)
            # Remove None values to keep JSON clean
            d = {k: v for k, v in d.items() if v is not None}
            data.append(d)
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def create(self, environment: Environment) -> Environment:
        envs = self.get_all()
        if any(e.name == environment.name for e in envs):
            raise ValueError(f"Environment already exists: {environment.name}")
        envs.append(environment)
        self.save_all(envs)
        return environment

    def update(self, name: str, environment: Environment) -> Environment:
        envs = self.get_all()
        for i, env in enumerate(envs):
            if env.name == name:
                envs[i] = environment
                self.save_all(envs)
                return environment
        raise ValueError(f"Environment not found: {name}")

    def delete(self, name: str) -> None:
        envs = self.get_all()
        filtered = [e for e in envs if e.name != name]
        if len(filtered) == len(envs):
            raise ValueError(f"Environment not found: {name}")
        self.save_all(filtered)