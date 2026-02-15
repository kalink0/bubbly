"""Base parser interface used by all messenger-specific parser implementations."""

from abc import ABC, abstractmethod

class BaseParser(ABC):
    """
    Abstract base parser for any messenger.
    Parsers can accept extra options via **kwargs.
    """
    @abstractmethod
    def parse(self, input_path, **kwargs):
        """
        Parse the chat export.
        Returns:
        - messages: list of dicts {id, sender, timestamp, content, media, url}
        - metadata: dict {chat_name, user, source, ...}

        kwargs: parser-specific options
        """
