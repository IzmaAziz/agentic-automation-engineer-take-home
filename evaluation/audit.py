import json


class AuditWriter:
    """Writes machine-readable JSONL audit results."""

    def __init__(self, path):
        self.path = path

    def write(self, results, metadata):
        with self.path.open("w", encoding="utf-8") as file:
            for name, result in results.items():
                file.write(json.dumps({**metadata, "variant": name, **result}) + "\n")