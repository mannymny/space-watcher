from dataclasses import dataclass
from .validators import is_valid_space_url
from .errors import InvalidSpaceUrl

@dataclass(frozen=True)
class WindowRect:
    x: int
    y: int
    width: int
    height: int

@dataclass(frozen=True)
class SpaceUrl:
    value: str

    def __post_init__(self):
        v = (self.value or "").strip()
        if not is_valid_space_url(v):
            raise InvalidSpaceUrl("Invalid Space URL.")
        object.__setattr__(self, "value", v)

@dataclass(frozen=True)
class RunOptions:
    rect: WindowRect
    mobile_user_agent: str
    record: bool
    try_guest_first: bool = True
    allow_cookies_fallback: bool = True
