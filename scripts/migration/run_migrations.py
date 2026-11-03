#!/usr/bin/env python3
"""Alembic migration runner for UbuntuCare (Zambia).

Handles database migrations, seeding, and verification.
Can be used standalone or as part of deployment scripts.
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

import alembic.config
import alembic.command

logger = logging.getLogger("migration-runner")

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
MIGRATIONS_DIR = PROJECT_DIR / "data" / "migrations"


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def get_alembic_cfg() -> alembic.config.Config:
    ini_path = PROJECT_DIR / "scripts" / "migration" / "alembic.ini"
    if not ini_path.exists():
        logger.error("alembic.ini not found at %s", ini_path)
        sys.exit(1)

    cfg = alembic.config.Config(str(ini_path))
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    cfg.set_main_option("sqlalchemy.url",
                        os.getenv("DATABASE_URL",
                                  "sqlite:///data/ubuntucare.db"))
    return cfg


def run_migrations(verbose: bool = False) -> None:
    """Run all pending migrations."""
    logger.info("Running database migrations...")
    cfg = get_alembic_cfg()
    try:
        alembic.command.upgrade(cfg, "head")
        logger.info("Migrations completed successfully")
    except Exception as exc:
        logger.error("Migration failed: %s", exc)
        sys.exit(1)


def rollback_migrations(steps: int = 1) -> None:
    """Rollback the last N migrations."""
    logger.info("Rolling back %d migration(s)...", steps)
    cfg = get_alembic_cfg()
    try:
        alembic.command.downgrade(cfg, f"-{steps}" if steps > 1 else "-1")
        logger.info("Rollback completed")
    except Exception as exc:
        logger.error("Rollback failed: %s", exc)
        sys.exit(1)


def show_history() -> None:
    """Display migration history."""
    cfg = get_alembic_cfg()
    alembic.command.history(cfg)


def show_current() -> None:
    """Show current migration version."""
    cfg = get_alembic_cfg()
    alembic.command.current(cfg)


def create_migration(message: str = "") -> None:
    """Auto-generate a new migration revision."""
    cfg = get_alembic_cfg()
    try:
        alembic.command.revision(cfg, autogenerate=True, message=message)
        logger.info("Created new migration revision")
    except Exception as exc:
        logger.error("Failed to create migration: %s", exc)
        sys.exit(1)


def seed_data() -> None:
    """Run seed data scripts."""
    logger.info("Seeding data...")

    seed_migrations = [
        "002_seed_zambia_data",
        "003_seed_knowledge_base",
        "004_rbac_seed",
        "005_seed_demo_data",
    ]

    for seed in seed_migrations:
        seed_path = MIGRATIONS_DIR / f"{seed}.py"
        if not seed_path.exists():
            logger.warning("Seed file not found: %s", seed_path)
            continue

        logger.info("Running seed: %s", seed)
        try:
            result = subprocess.run(
                [sys.executable, str(seed_path)],
                cwd=str(PROJECT_DIR),
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                logger.info("Seed %s completed", seed)
            else:
                logger.warning("Seed %s had issues: %s", seed, result.stderr[:200])
        except Exception as exc:
            logger.error("Seed %s failed: %s", seed, exc)

    logger.info("Data seeding completed")


def verify_migrations() -> bool:
    """Verify all migrations have been applied."""
    cfg = get_alembic_cfg()
    try:
        alembic.command.check(cfg)
        logger.info("All migrations applied and consistent")
        return True
    except SystemExit:
        logger.warning("Migration consistency check failed")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="UbuntuCare — Migration Runner"
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="upgrade",
        choices=["upgrade", "downgrade", "history", "current",
                 "create", "seed", "verify", "all"],
        help="Migration command (default: upgrade)",
    )
    parser.add_argument("--steps", type=int, default=1,
                        help="Number of steps to rollback (default: 1)")
    parser.add_argument("--message", "-m", default="",
                        help="Migration message (for 'create' command)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose output")
    parser.add_argument("--seed", action="store_true",
                        help="Run seed data after migration")

    args = parser.parse_args()
    setup_logging(args.verbose)

    commands = {
        "upgrade": lambda: run_migrations(args.verbose),
        "downgrade": lambda: rollback_migrations(args.steps),
        "history": show_history,
        "current": show_current,
        "create": lambda: create_migration(args.message),
        "seed": seed_data,
        "verify": lambda: verify_migrations(),
        "all": lambda: (run_migrations(args.verbose), seed_data(),
                        verify_migrations()),
    }

    cmd = commands.get(args.command)
    if cmd:
        cmd()
    else:
        parser.print_help()
        sys.exit(1)

    if args.seed and args.command in ("upgrade", "all"):
        seed_data()


if __name__ == "__main__":
    main()
