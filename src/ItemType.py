from enum import Enum


class ItemType(Enum):
    POST = 0
    STORY = 1

    def get_name(self):
        return self.name.lower()
