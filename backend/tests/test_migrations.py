"""
Tests for Alembic Migrations Configuration (Module M03)
Tests Alembic configuration loading, revision tracking, and offline SQL script generation.
"""

import os
from alembic.config import Config
from alembic import command
from app.core.config import get_settings


def test_alembic_config_loads_properly():
    """Verify that alembic.ini points to the correct migration script directory."""
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ini_path = os.path.join(backend_dir, "alembic.ini")
    assert os.path.exists(ini_path)

    alembic_cfg = Config(ini_path)
    script_location = alembic_cfg.get_main_option("script_location")
    assert "migrations" in script_location


def test_alembic_current_and_heads():
    """Verify that Alembic can inspect migration branches and heads without error."""
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ini_path = os.path.join(backend_dir, "alembic.ini")
    alembic_cfg = Config(ini_path)

    from alembic.script import ScriptDirectory
    script = ScriptDirectory.from_config(alembic_cfg)
    heads = script.get_heads()
    assert len(heads) == 1
    assert heads[0] == "d2e5a6f8b901"


def test_alembic_offline_sql_generation(capsys):
    """Verify that Alembic generates valid offline DDL statements for MySQL."""
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ini_path = os.path.join(backend_dir, "alembic.ini")
    alembic_cfg = Config(ini_path)

    # Run upgrade head in offline mode emitting SQL
    command.upgrade(alembic_cfg, "head", sql=True)
    captured = capsys.readouterr()
    assert "CREATE TABLE alembic_version" in captured.out
    assert "INSERT INTO alembic_version" in captured.out
