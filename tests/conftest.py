class FakeProvider:
    """Returns canned responses in order; raises items that are exceptions."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item
