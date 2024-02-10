from typing import Any

from anki.collection import Collection


class MockTaskman:
    def run_on_main(self, *args: Any, **kwargs: Any) -> None:
        pass


class MockProgress:
    def want_cancel(self) -> bool:
        return False

    def update(self, *args: Any, **kwargs: Any) -> None:
        pass


class MockAddonManager:
    def addonFromModule(self, *args: Any, **kwargs: Any) -> Any:
        return "copycat_importer"

    def getConfig(self, *args: Any, **kwargs: Any) -> Any:
        return {}

    def addonConfigDefaults(self, *args: Any, **kwargs: Any) -> Any:
        return {}

    def setConfigUpdatedAction(self, *args: Any, **kwargs: Any) -> None:
        pass

    def writeConfig(self, *args: Any, **kwargs: Any) -> None:
        pass


class MockMainWindow:
    col: Collection
    progress: MockProgress
    taskman: MockTaskman
    addonManager: MockAddonManager

    def __init__(self, col_path: str) -> None:
        self.col = Collection(col_path)
        self.progress = MockProgress()
        self.taskman = MockTaskman()
        self.addonManager = MockAddonManager()
