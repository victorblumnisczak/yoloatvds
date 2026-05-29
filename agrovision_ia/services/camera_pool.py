import random

CAMERAS_POOL: list[str] = [
    # Distrito 11 — San Diego / fronteira México
    "https://wzmedia.dot.ca.gov/D11/C214_SB_5_at_Via_De_San_Ysidro.stream/playlist.m3u8",
    # Distrito 4 — Bay Area
    "https://wzmedia.dot.ca.gov/D4/N101_AT_HARRISON.stream/playlist.m3u8",
    "https://wzmedia.dot.ca.gov/D4/E80_JMT.stream/playlist.m3u8",
    # Distrito 3 — Sacramento
    "https://wzmedia.dot.ca.gov/D3/50_OFF_HOWE.stream/playlist.m3u8",
    # Distrito 12 — Orange County
    "https://wzmedia.dot.ca.gov/D12/N5_JAT_BEACH.stream/playlist.m3u8",
    # Distrito 7 — Los Angeles
    "https://wzmedia.dot.ca.gov/D7/N101_AT_VINELAND.stream/playlist.m3u8",
]


def pick_random() -> str:
    return random.choice(CAMERAS_POOL)


def next_after_failure(current: str) -> str:
    others = [c for c in CAMERAS_POOL if c != current]
    return random.choice(others) if others else current


def list_all() -> list[str]:
    return list(CAMERAS_POOL)
