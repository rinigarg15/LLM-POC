from enum import Enum

class ExtendedEnum(Enum):

    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))

class Topics(ExtendedEnum):
    RAG = "RAG"
    TREATY_OF_VERSAILLES = "Treaty of Versailles"

topics_list = Topics.list()