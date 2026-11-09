from __future__ import annotations
from pathlib import Path
from typing import List, Literal, Optional
import yaml
from pydantic import BaseModel, Field, model_validator


class LLMConfig(BaseModel):
    provider: str
    instruction: str


class TargetConfig(BaseModel):
    name: str
    start_urls: List[str]
    mode: Literal["css", "llm"] = "css"
    schema_file: Optional[str] = None
    llm: Optional[LLMConfig] = None
    rate_limit_seconds: float = Field(default=1.0, ge=0.0)
    scroll_full_page: bool = False
    max_pages: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def validate_mode_dependencies(self) -> TargetConfig:
        if self.mode == "css" and not self.schema_file:
            raise ValueError(f"Target '{self.name}' with mode 'css' must specify 'schema_file'.")
        if self.mode == "llm" and not self.llm:
            raise ValueError(f"Target '{self.name}' with mode 'llm' must specify 'llm' configuration.")
        return self


def load_target_config(path: str | Path) -> TargetConfig:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Config file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Invalid YAML config in {file_path}: root must be a mapping.")

    return TargetConfig(**data)


def load_all_targets(targets_dir: str | Path = "targets") -> List[TargetConfig]:
    dir_path = Path(targets_dir)
    if not dir_path.exists() or not dir_path.is_dir():
        return []

    configs = []
    for yaml_file in sorted(dir_path.glob("*.yaml")):
        # Skip template or hidden files
        if yaml_file.name.startswith("_") or yaml_file.name.startswith("."):
            continue
        configs.append(load_target_config(yaml_file))

    return configs

