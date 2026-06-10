from __future__ import annotations
from dataclasses import dataclass, field, asdict


@dataclass
class Room:
    id: str
    room_type: str
    title: str
    description: str
    x: int
    y: int
    connections: list[str] = field(default_factory=list)
    enemies: list[dict] = field(default_factory=list)
    loot: list[dict] = field(default_factory=list)
    trap: dict | None = None
    event: dict | None = None
    cleared: bool = False
    visited: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Room":
        allowed = {field_name for field_name in cls.__dataclass_fields__}
        clean = {key: value for key, value in data.items() if key in allowed}
        return cls(**clean)


@dataclass
class Floor:
    floor_number: int
    theme: dict
    rooms: dict[str, Room]
    boss: dict
    lore: dict = field(default_factory=dict)
    generated_by_ollama: bool = False

    def to_dict(self) -> dict:
        return {
            "floor_number": self.floor_number,
            "theme": self.theme,
            "rooms": {room_id: room.to_dict() for room_id, room in self.rooms.items()},
            "boss": self.boss,
            "lore": self.lore,
            "generated_by_ollama": self.generated_by_ollama,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Floor":
        rooms = {room_id: Room.from_dict(room_data) for room_id, room_data in data["rooms"].items()}
        return cls(
            floor_number=data["floor_number"],
            theme=data["theme"],
            rooms=rooms,
            boss=data["boss"],
            lore=data.get("lore", {}),
            generated_by_ollama=data.get("generated_by_ollama", False),
        )
