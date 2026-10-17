"""Process configuration from the repo-root .env (secrets + machine paths only)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = ""
    gemini_api_key: str = ""

    model_text: str = "gemini-3.8-flash"
    model_script: str = "gemini-4-argon"
    model_script_fallback: str = "gemini-3.8-flash"
    model_cheap: str = "gemini-3.5-flash-lite"
    model_image: str = "gemini-nano-banana-2.1"
    model_image_fallback: str = "gemini-3.1-flash-image"
    model_pose_sheet: str = "gemini-3-pro-image"
    model_embed: str = "gemini-embedding-2"
    script_writer: str = "gemini"
    claude_cli: str = "claude"
    text_llm: str = "claude_code"          # claude_code | gemini — who does ALL text steps
    claude_model: str = "sonnet"           # idea, facts, judge, checks
    claude_model_script: str = "opus"      # Kazakh script writing / rewriting

    elevenlabs_api_enabled: bool = False
    youtube_api_enabled: bool = False

    data_dir: Path = Path("./data")
    library_dir: Path = Path("./library")
    engine_dir: Path = Path("./engine")

    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    asset_base_url: str = "http://127.0.0.1:8000"
    frontend_port: int = 5173

    budget_project_usd: float = 5.0
    budget_project_warn_usd: float = 2.5
    budget_month_stop_usd: float = 60.0

    default_language: str = "kk"
    default_target_seconds: int = 240
    default_wpm_voice: float = 110

    node_bin: str = "node"
    ffmpeg_bin: str = "ffmpeg"
    ffprobe_bin: str = "ffprobe"
    pg_dump_bin: str = "pg_dump"
    log_level: str = "INFO"

    def _abs(self, p: Path) -> Path:
        return (p if p.is_absolute() else REPO_ROOT / p).resolve()

    @property
    def data_path(self) -> Path:
        return self._abs(self.data_dir)

    @property
    def library_path(self) -> Path:
        return self._abs(self.library_dir)

    @property
    def engine_path(self) -> Path:
        return self._abs(self.engine_dir)


@lru_cache
def get_settings() -> Settings:
    return Settings()
