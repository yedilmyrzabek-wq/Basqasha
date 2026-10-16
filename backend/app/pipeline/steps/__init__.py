"""Importing this package registers every implemented step handler with the orchestrator."""
from app.pipeline.steps import s01_source, s02_idea, s03_facts, s04_script  # noqa: F401
