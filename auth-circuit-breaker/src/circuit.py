"""Circuit breaker as explicit state objects (closed / open / half-open)."""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class CircuitOpenReason:
    """Request is not forwarded to the auth service."""

    message: str


@dataclass(frozen=True)
class RequestPermission:
    allowed: bool
    reason: CircuitOpenReason | None = None
    next_state: AbstractCBState | None = None


@dataclass
class CircuitContext:
    settings: Settings
    consecutive_failures: int = 0
    open_until_monotonic: float | None = None
    half_open_remaining: int = 0


class AbstractCBState(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def try_get_permission_to_request(
        self, ctx: CircuitContext
    ) -> RequestPermission:
        ...

    @abstractmethod
    def on_success(self, ctx: CircuitContext) -> AbstractCBState:
        ...

    @abstractmethod
    def on_failure(self, ctx: CircuitContext) -> AbstractCBState:
        ...


class ClosedState(AbstractCBState):
    @property
    def name(self) -> str:
        return "closed"

    def try_get_permission_to_request(self, ctx: CircuitContext) -> RequestPermission:
        return RequestPermission(allowed=True)

    def on_success(self, ctx: CircuitContext) -> AbstractCBState:
        ctx.consecutive_failures = 0
        return self

    def on_failure(self, ctx: CircuitContext) -> AbstractCBState:
        ctx.consecutive_failures += 1
        if ctx.consecutive_failures >= ctx.settings.failure_threshold:
            ctx.consecutive_failures = 0
            ctx.open_until_monotonic = (
                # Отвязываемся от календарного времени, фактически, пользуемся таймером
                time.monotonic()
                + ctx.settings.recovery_timeout_seconds
            )
            return OpenState()
        return self


class OpenState(AbstractCBState):
    @property
    def name(self) -> str:
        return "open"

    def try_get_permission_to_request(self, ctx: CircuitContext) -> RequestPermission:
        now = time.monotonic()
        if ctx.open_until_monotonic is not None and now >= ctx.open_until_monotonic:
            ctx.half_open_remaining = ctx.settings.half_open_probes

            return RequestPermission(allowed=True, next_state=HalfOpenState())

        return RequestPermission(
            allowed=False,
            reason=CircuitOpenReason(
                message="Circuit is open: requests to the auth service are not forwarded. "
                "Try again later.",
            ),
        )

    def on_success(self, ctx: CircuitContext) -> AbstractCBState:
        ctx.consecutive_failures = 0
        ctx.open_until_monotonic = None
        ctx.half_open_remaining = 0

        return ClosedState()

    def on_failure(self, ctx: CircuitContext) -> AbstractCBState:
        ctx.open_until_monotonic = (
            time.monotonic() + ctx.settings.recovery_timeout_seconds
        )
        return self


class HalfOpenState(AbstractCBState):
    @property
    def name(self) -> str:
        return "half_open"

    def try_get_permission_to_request(self, ctx: CircuitContext) -> RequestPermission:
        if ctx.half_open_remaining <= 0:
            return RequestPermission(
                allowed=False,
                reason=CircuitOpenReason(
                    message="Circuit is half-open: probe quota for this recovery window is exhausted.",
                ),
            )
        ctx.half_open_remaining -= 1

        return RequestPermission(allowed=True)

    def on_success(self, ctx: CircuitContext) -> AbstractCBState:
        ctx.consecutive_failures = 0
        ctx.open_until_monotonic = None
        ctx.half_open_remaining = 0

        return ClosedState()

    def on_failure(self, ctx: CircuitContext) -> AbstractCBState:
        ctx.open_until_monotonic = (
            time.monotonic() + ctx.settings.recovery_timeout_seconds
        )
        ctx.half_open_remaining = 0
        ctx.consecutive_failures = 0

        return OpenState()


class CircuitBreaker:
    def __init__(self, settings: Settings) -> None:
        self._ctx = CircuitContext(settings=settings)
        self._state: AbstractCBState = ClosedState()
        self._lock = asyncio.Lock()

    @property
    def state(self) -> str:
        return self._state.name

    def _log_state_transition(self, new_state: AbstractCBState) -> None:
        old_name = self._state.name
        self._state = new_state
        new_name = new_state.name
        if new_name != old_name:
            logger.info("Circuit breaker state: %s -> %s", old_name, new_name)

    async def try_get_permission_to_request(self) -> CircuitOpenReason | None:
        async with self._lock:
            outcome = self._state.try_get_permission_to_request(self._ctx)
            if outcome.next_state is not None:
                self._log_state_transition(outcome.next_state)
                outcome = self._state.try_get_permission_to_request(self._ctx)
            if not outcome.allowed:
                return outcome.reason
            return None

    async def on_service_success(self) -> None:
        async with self._lock:
            self._log_state_transition(self._state.on_success(self._ctx))

    async def on_service_failure(self) -> None:
        async with self._lock:
            self._log_state_transition(self._state.on_failure(self._ctx))
