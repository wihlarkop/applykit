from app.database import configure_sqlite_security


class FakeCursor:
    def __init__(self):
        self.commands: list[str] = []
        self.closed = False

    def execute(self, command: str) -> None:
        self.commands.append(command)

    def close(self) -> None:
        self.closed = True


class FakeConnection:
    def __init__(self):
        self.cursor_instance = FakeCursor()

    def cursor(self) -> FakeCursor:
        return self.cursor_instance


def test_sqlite_security_enables_secure_delete_and_foreign_keys():
    connection = FakeConnection()

    configure_sqlite_security(connection, None)

    assert connection.cursor_instance.commands == [
        "PRAGMA secure_delete=ON",
        "PRAGMA foreign_keys=ON",
    ]
    assert connection.cursor_instance.closed is True
