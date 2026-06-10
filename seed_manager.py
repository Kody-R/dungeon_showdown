from __future__ import annotations
import random


def new_seed() -> int:
    return random.randint(100000, 999999)


def seed_filename(seed: int) -> str:
    return f"seed_{seed}.json"
