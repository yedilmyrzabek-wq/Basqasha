"""Importing this package registers every implemented step handler with the orchestrator."""
from app.pipeline.steps import (s01_source, s02_idea, s03_facts, s04_script, s05_voice,  # noqa: F401
                                s06_storyboard, s07_images, s08_preview, s09_render, s10_metadata,
                                s11_recommendations)
