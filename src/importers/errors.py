from requests import HTTPError


class CopycatImporterError(Exception):
    pass


class CopycatImporterCanceled(CopycatImporterError):
    pass


class CopycatImporterRequestFailed(CopycatImporterError):
    def __init__(self, url: str, exc: HTTPError):
        super().__init__(f"Request to {url} failed: {str(exc)}")
