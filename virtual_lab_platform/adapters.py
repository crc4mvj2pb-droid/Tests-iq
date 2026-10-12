from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable

@dataclass(frozen=True)
class SolverAdapter:
    model_id: str
    version: str
    discipline: str
    execute: Callable[[dict[str, Any]], dict[str, Any]]
    validation_level: str
    limitations: tuple[str, ...]

    def run(self, parameters: dict[str, Any]) -> dict[str, Any]:
        result = self.execute(parameters)
        if not isinstance(result, dict) or "rows" not in result:
            raise ValueError(f"Adapter {self.model_id} returned an invalid result contract.")
        return {
            **result,
            "adapter_metadata": {
                "model_id": self.model_id,
                "version": self.version,
                "discipline": self.discipline,
                "validation_level": self.validation_level,
                "limitations": list(self.limitations)
            }
        }

def validate_adapter_metadata(metadata: dict[str, Any]) -> list[str]:
    required = ("model_id", "version", "discipline", "validation_level", "limitations")
    return [f"Missing required adapter field: {key}" for key in required if key not in metadata]
