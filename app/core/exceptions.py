from __future__ import annotations


class OrchestratorError(Exception):
    pass


class ValidationError(OrchestratorError):
    pass


class AuthorizationError(OrchestratorError):
    pass


class StateTransitionError(OrchestratorError):
    pass


class NotFoundError(OrchestratorError):
    pass
