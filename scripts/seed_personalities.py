#!/usr/bin/env python3
"""Seed personality profiles from YAML templates."""

import asyncio
from pathlib import Path

import yaml
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import async_session_factory
from app.models import PersonalityProfile
from app.repositories import PersonalityRepository

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "app" / "ai" / "personalities" / "templates"


async def seed(session: AsyncSession) -> None:
    repo = PersonalityRepository(session)
    for path in sorted(TEMPLATES_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text())
        profile = PersonalityProfile(
            key=data["key"],
            display_name=data["display_name"],
            system_prompt=data["system_prompt"],
            tone_rules={
                "voice": data.get("voice"),
                "metaphor_style": data.get("metaphor_style"),
                "challenge_level": data.get("challenge_level"),
                "question_ratio": data.get("question_ratio"),
                "sample_phrases": data.get("sample_phrases", []),
            },
        )
        await repo.upsert(profile)
        print(f"Seeded personality: {data['key']}")


async def main() -> None:
    async with async_session_factory() as session:
        await seed(session)
        await session.commit()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
