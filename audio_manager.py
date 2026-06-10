from __future__ import annotations
from pathlib import Path
import pygame


class AudioManager:
    """Optional, crash-safe audio wrapper.

    Phase 8 does not require bundled audio. This class lets later asset packs drop
    files into assets/sounds or assets/music without breaking the game when files
    are missing, pygame.mixer is unavailable, or the host has no audio device.
    """

    def __init__(self, asset_dir: Path, music_volume: float = 0.5, sound_volume: float = 0.7) -> None:
        self.asset_dir = asset_dir
        self.music_volume = float(music_volume)
        self.sound_volume = float(sound_volume)
        self.enabled = False
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.set_volume(self.music_volume)
            self.enabled = True
        except pygame.error:
            self.enabled = False

    def set_volumes(self, music_volume: float, sound_volume: float) -> None:
        self.music_volume = max(0.0, min(1.0, float(music_volume)))
        self.sound_volume = max(0.0, min(1.0, float(sound_volume)))
        if self.enabled:
            try:
                pygame.mixer.music.set_volume(self.music_volume)
                for sound in self.sounds.values():
                    sound.set_volume(self.sound_volume)
            except pygame.error:
                self.enabled = False

    def load_sound(self, name: str, relative_path: str) -> None:
        if not self.enabled:
            return
        path = self.asset_dir / relative_path
        if not path.exists():
            return
        try:
            sound = pygame.mixer.Sound(str(path))
            sound.set_volume(self.sound_volume)
            self.sounds[name] = sound
        except pygame.error:
            pass

    def play_sound(self, name: str) -> None:
        if not self.enabled or name not in self.sounds:
            return
        try:
            self.sounds[name].play()
        except pygame.error:
            self.enabled = False

    def play_music(self, relative_path: str, loops: int = -1) -> None:
        if not self.enabled:
            return
        path = self.asset_dir / relative_path
        if not path.exists():
            return
        try:
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.play(loops=loops)
        except pygame.error:
            self.enabled = False
