class DomainError(Exception):
    pass

class InvalidSpaceUrl(DomainError):
    pass

class MissingDependency(DomainError):
    pass

class StartFailed(DomainError):
    pass
