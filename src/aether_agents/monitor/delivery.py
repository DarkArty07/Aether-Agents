"""Bounded native Telegram delivery for the monitor outbox.

The monitor owns receipt state, but it does not own Telegram transport, credentials, or
recipient selection.  :class:`TelegramDeliveryAdapter` resolves the already pinned
native home target immediately before a send and calls the maintained Hermes sender
lazily.  A sender is injectable for deterministic tests; no Hermes or gateway module is
imported while this module is loaded.

The adapter deliberately accepts rendered parts from its caller instead of persisting
message text in the monitor database.  It verifies each part against the store's
content hash before claiming a lease, so a restart must re-render the same immutable
outbox rather than silently sending changed text.
"""

from __future__ import annotations

import asyncio
import hashlib
import inspect
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol, cast

from .models import Delivery, DeliveryState, Lease, MonitorSettings
from .store import LeaseLostError, MonitorStore

__all__ = [
    "DeliveryConfigurationError",
    "DeliveryOutcome",
    "DeliveryRun",
    "NativeSender",
    "PinnedTelegramTarget",
    "PreDispatchError",
    "TelegramDeliveryAdapter",
    "TelegramDeliveryError",
    "canonical_target_reference",
]

_MAX_ERROR_CLASS = 96
_MAX_MESSAGE_ID = 256
_MAX_PARTS = 256

# Only these local taxonomy values may cross the durable/public adapter boundary.
# Native error labels are data, not authority: an arbitrary foreign label must never
# become a monitor error class merely because it happens to look like a token.
_SAFE_ERROR_CLASSES = frozenset(
    {
        "ack-missing-message-id",
        "delivery-failure",
        "delivery-lease-busy",
        "destination-changed",
        "destination-invalid",
        "destination-missing",
        "destination-unavailable",
        "destination-unpinned",
        "dispatch-uncertain",
        "monitor-disabled",
        "native-sender-unavailable",
        "outbox-empty",
        "outbox-input-invalid",
        "outbox-missing",
        "outbox-shape-changed",
        "outbox-text-changed",
        "pre-dispatch",
        "pre-dispatch-failure",
        "profile-binding-changed",
        "rate-limit",
        "retry-limit",
        "sender-empty-result",
        "sender-failure",
        "sender-invalid-outcome",
        "sender-invalid-result",
        "service-busy",
        "telegram-disabled",
        "temporary",
        "timeout",
    }
)


class TelegramDeliveryError(RuntimeError):
    """Base class for safe, destination-free adapter errors."""

    def __init__(
        self, error_class: str, *, retryable: bool = False, retry_after: float = 0.0
    ) -> None:
        super().__init__(error_class)
        self.error_class = error_class
        self.retryable = retryable
        self.retry_after = retry_after


class DeliveryConfigurationError(TelegramDeliveryError):
    """The pinned existing destination or native binding is unavailable."""


class PreDispatchError(TelegramDeliveryError):
    """A sender explicitly reports that no network dispatch occurred."""

    def __init__(
        self,
        error_class: str = "pre-dispatch-failure",
        *,
        retry_after: float = 0.0,
    ) -> None:
        super().__init__(error_class, retryable=True, retry_after=retry_after)


class DeliveryOutcome(StrEnum):
    """Aggregate and per-part outcomes exposed by the adapter."""

    CONFIRMED = "confirmed"
    FAILED = "failed"
    UNCERTAIN = "uncertain"
    PARTIAL = "partial"
    SUPPRESSED = "suppressed"


@dataclass(frozen=True, slots=True)
class PinnedTelegramTarget:
    """The exact configured Telegram home chat/thread selected by monitor enrollment.

    ``reference`` is an opaque private binding.  It is compared byte-for-byte with the
    monitor setting and is never included in public errors or evidence.  ``chat_id`` and
    ``thread_id`` are used only by the native sender after the binding check succeeds.
    """

    reference: str
    chat_id: str
    thread_id: str | None = None
    profile_binding: str | None = None


class NativeSender(Protocol):
    """Callable boundary for Hermes' existing sender or a deterministic fake.

    The callable may be synchronous or asynchronous and returns the native result
    mapping.  A successful mapping must contain an explicit message identifier.
    """

    def __call__(self, target: PinnedTelegramTarget, text: str) -> Any: ...


@dataclass(frozen=True, slots=True)
class DeliveryRun:
    """Sanitized report-level receipt returned by :meth:`deliver_report`."""

    report_id: str
    outcome: DeliveryOutcome
    parts: tuple[dict[str, str], ...]
    coverage_advanced: bool
    error_class: str | None = None

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "report_id": self.report_id,
            "outcome": self.outcome.value,
            "parts": [dict(part) for part in self.parts],
            "coverage_advanced": self.coverage_advanced,
        }
        if self.error_class is not None:
            result["error_class"] = self.error_class
        return result

    # Mapping-like conveniences keep the private result shape easy to consume from
    # callbacks without making a second public schema.
    def __getitem__(self, key: str) -> Any:
        return self.as_dict()[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.as_dict().get(key, default)


@dataclass(frozen=True, slots=True)
class _SenderReceipt:
    outcome: DeliveryOutcome
    message_id: str | None = None
    error_class: str | None = None
    retryable: bool = False
    retry_after: float = 0.0


class _RetryableResult(Exception):
    def __init__(self, error_class: str, retry_after: float) -> None:
        super().__init__(error_class)
        self.error_class = error_class
        self.retry_after = retry_after


class _NoDispatchResult(Exception):
    def __init__(self, error_class: str, retry_after: float = 0.0) -> None:
        super().__init__(error_class)
        self.error_class = error_class
        self.retry_after = retry_after


def _safe_token(value: Any, default: str, *, limit: int = _MAX_ERROR_CLASS) -> str:
    """Return only a known local error class, never arbitrary foreign text."""

    if not isinstance(value, str):
        return default
    raw = value.strip().lower()
    if len(raw) > limit or raw not in _SAFE_ERROR_CLASSES:
        return default
    return raw


def _safe_message_id(value: Any) -> str | None:
    if not isinstance(value, (str, int)) or isinstance(value, bool):
        return None
    text = str(value).strip()
    if not text or len(text) > _MAX_MESSAGE_ID:
        return None
    if any(ord(char) < 0x20 or ord(char) == 0x7F for char in text):
        return None
    return text


def _retry_after(value: Any) -> float:
    try:
        delay = float(value)
    except (TypeError, ValueError):
        return 0.0
    if delay < 0 or delay != delay or delay == float("inf"):
        return 0.0
    return min(delay, 3_600.0)


def canonical_target_reference(chat_id: str, thread_id: str | None = None) -> str:
    """Return the opaque stable reference used to pin a Telegram home target.

    The reference intentionally contains no recipient value.  The monitor's private
    settings can therefore verify a target without exposing a chat/thread in errors or
    public evidence.  Enrollment code can use this helper when it persists the pin.
    """

    if not isinstance(chat_id, str) or not chat_id.strip():
        raise ValueError("chat_id must be a non-empty string")
    if thread_id is not None and (not isinstance(thread_id, str) or not thread_id.strip()):
        raise ValueError("thread_id must be a non-empty string when present")
    material = f"telegram\0{chat_id.strip()}\0{thread_id or ''}".encode("utf-8")
    return "telegram-home-" + hashlib.sha256(material).hexdigest()


def _default_target(settings: MonitorSettings) -> PinnedTelegramTarget | None:
    """Resolve only the current native Telegram home channel, lazily."""

    # These imports are intentionally inside the resolver.  Aether's manager/parser
    # remains Hermes-free and tests can exercise the adapter with no native runtime.
    try:
        from gateway.config import Platform, load_gateway_config  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - exercised by manager-only installs
        raise DeliveryConfigurationError("native-sender-unavailable") from exc

    try:
        config = load_gateway_config()
        home = config.get_home_channel(Platform.TELEGRAM)
    except Exception as exc:  # native config details must not escape the adapter
        raise DeliveryConfigurationError("destination-unavailable") from exc
    if home is None or home.platform is not Platform.TELEGRAM:
        raise DeliveryConfigurationError("destination-missing")
    chat_id = str(getattr(home, "chat_id", "") or "").strip()
    thread_id_raw = getattr(home, "thread_id", None)
    thread_id = str(thread_id_raw).strip() if thread_id_raw is not None else None
    if not chat_id or (thread_id_raw is not None and not thread_id):
        raise DeliveryConfigurationError("destination-invalid")
    reference = canonical_target_reference(chat_id, thread_id)
    if settings.destination_ref != reference:
        raise DeliveryConfigurationError(
            "destination-changed" if settings.destination_ref else "destination-unpinned"
        )
    return PinnedTelegramTarget(reference, chat_id, thread_id, settings.profile_binding)


def _exact_thread_kwargs(target: PinnedTelegramTarget) -> dict[str, int]:
    """Mirror Hermes' exact General-topic mapping for one send attempt.

    Hermes' ``TelegramAdapter._message_thread_id_for_send`` omits ``message_thread_id``
    for the forum General topic (thread ``"1"``) because Bot API ``sendMessage`` rejects
    ``message_thread_id=1`` with "Message thread not found".  Keeping that exact mapping
    preserves the pinned home thread instead of failing or falling back to the chat.
    """

    if target.thread_id is None:
        return {}
    if not isinstance(target.thread_id, str) or not target.thread_id.strip():
        raise DeliveryConfigurationError("destination-invalid")
    raw = target.thread_id.strip()
    if raw == "1":
        return {}
    try:
        thread_id = int(raw)
    except ValueError as exc:
        raise DeliveryConfigurationError("destination-invalid") from exc
    if thread_id <= 0:
        raise DeliveryConfigurationError("destination-invalid")
    return {"message_thread_id": thread_id}


def _configured_telegram_bot(bot_class: Any, token: str) -> Any:
    """Construct the Bot with the same configured proxy the native sender uses."""

    proxy: Any = None
    try:
        from gateway.platforms.base import resolve_proxy_url  # type: ignore[import-not-found]

        proxy = resolve_proxy_url("TELEGRAM_PROXY", target_hosts=["api.telegram.org"])
    except Exception:
        proxy = None
    if proxy:
        try:
            from telegram.request import HTTPXRequest  # type: ignore[import-not-found]

            return bot_class(
                token=token,
                request=HTTPXRequest(proxy=proxy),
                get_updates_request=HTTPXRequest(proxy=proxy),
            )
        except Exception:
            # A broken proxy helper must not silently redirect the send; fall back to
            # the same direct Bot the native path uses.
            pass
    try:
        return bot_class(token=token)
    except Exception as exc:
        raise DeliveryConfigurationError("native-sender-unavailable") from exc


async def _send_exact_native_telegram(
    pconfig: Any, target: PinnedTelegramTarget, text: str
) -> Mapping[str, Any]:
    """Use Hermes' native Bot API helper for exactly one target/send attempt.

    ``_send_to_platform``/``_send_telegram`` are intentionally not used here: the
    selected Hermes release chunks, retries internally, and falls back from a missing
    topic to the general chat.  Its lower-level ``_send_telegram_message_with_retry``
    seam accepts an existing Bot and an explicit attempt count, so ``attempts=1``
    preserves this adapter's ambiguity boundary while retaining Hermes' configured
    Telegram transport family (token, proxy and chat-id normalization included).
    """

    try:
        from plugins.platforms.telegram.telegram_ids import (  # type: ignore[import-not-found]
            normalize_telegram_chat_id,
        )
        from telegram import Bot  # type: ignore[import-not-found]
        from tools.send_message_tool import (  # type: ignore[import-not-found]
            _send_telegram_message_with_retry,
        )
    except ImportError as exc:  # pragma: no cover - manager-only path
        raise DeliveryConfigurationError("native-sender-unavailable") from exc

    token = getattr(pconfig, "token", None)
    if not isinstance(token, str) or not token.strip():
        raise DeliveryConfigurationError("native-sender-unavailable")
    try:
        chat_id = normalize_telegram_chat_id(target.chat_id)
    except Exception as exc:
        raise DeliveryConfigurationError("destination-invalid") from exc

    thread_kwargs = _exact_thread_kwargs(target)
    bot = _configured_telegram_bot(Bot, token)

    # The helper returns the native Message only after one Bot API call.  Do not
    # catch/replay a transport exception here: the adapter records it as uncertain.
    response = await _send_telegram_message_with_retry(
        bot,
        attempts=1,
        chat_id=chat_id,
        text=text,
        **thread_kwargs,
    )
    message_id = (
        response.get("message_id")
        if isinstance(response, Mapping)
        else getattr(response, "message_id", None)
    )
    if message_id is None:
        return {"outcome": "uncertain", "error_class": "ack-missing-message-id"}
    return {"success": True, "message_id": message_id}


async def _default_native_sender(target: PinnedTelegramTarget, text: str) -> Mapping[str, Any]:
    """Call the exact existing Hermes Telegram transport lazily."""

    try:
        from gateway.config import Platform, load_gateway_config  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - manager-only path
        raise DeliveryConfigurationError("native-sender-unavailable") from exc

    try:
        config = load_gateway_config()
        pconfig = config.platforms.get(Platform.TELEGRAM)
    except Exception as exc:  # do not expose config/credential details
        raise DeliveryConfigurationError("native-sender-unavailable") from exc
    if pconfig is None or not getattr(pconfig, "enabled", False):
        raise DeliveryConfigurationError("telegram-disabled")
    return await _send_exact_native_telegram(pconfig, target, text)


def _target_from_value(value: Any) -> PinnedTelegramTarget | None:
    if value is None:
        return None
    if isinstance(value, PinnedTelegramTarget):
        return value
    if isinstance(value, Mapping):
        reference = value.get("reference", value.get("destination_ref"))
        chat_id = value.get("chat_id")
        if not isinstance(reference, str) or not isinstance(chat_id, str):
            return None
        thread_id = value.get("thread_id")
        profile = value.get("profile_binding")
        return PinnedTelegramTarget(
            reference=reference,
            chat_id=chat_id,
            thread_id=thread_id if isinstance(thread_id, str) else None,
            profile_binding=profile if isinstance(profile, str) else None,
        )
    if isinstance(value, tuple) and 2 <= len(value) <= 4:
        reference, chat_id, *rest = value
        thread_id = rest[0] if rest else None
        profile = rest[1] if len(rest) > 1 else None
        if isinstance(reference, str) and isinstance(chat_id, str):
            return PinnedTelegramTarget(
                reference,
                chat_id,
                thread_id if isinstance(thread_id, str) else None,
                profile if isinstance(profile, str) else None,
            )
    return None


def _is_timeout_label(value: Any) -> bool:
    text = str(value or "").lower()
    return any(token in text for token in ("timeout", "timed-out", "timed out", "deadline"))


def _normalize_sender_result(result: Any) -> _SenderReceipt:
    """Interpret only an explicit positive message acknowledgment as confirmed."""

    if not isinstance(result, Mapping):
        error_class = "sender-empty-result" if result is None else "sender-invalid-result"
        return _SenderReceipt(DeliveryOutcome.UNCERTAIN, error_class=error_class)

    raw_outcome = result.get("outcome")
    message_id = _safe_message_id(result.get("message_id"))
    raw_error = result.get("error_class", result.get("error"))
    error_class = _safe_token(raw_error, "sender-failure")
    if raw_outcome is not None:
        outcome = str(raw_outcome).strip().lower()
        if outcome == DeliveryOutcome.CONFIRMED.value:
            if message_id is None:
                return _SenderReceipt(
                    DeliveryOutcome.UNCERTAIN, error_class="ack-missing-message-id"
                )
            return _SenderReceipt(DeliveryOutcome.CONFIRMED, message_id=message_id)
        if outcome == DeliveryOutcome.UNCERTAIN.value or _is_timeout_label(raw_error):
            return _SenderReceipt(DeliveryOutcome.UNCERTAIN, error_class=error_class)
        if outcome == DeliveryOutcome.FAILED.value:
            dispatch = str(result.get("dispatch", "before")).strip().lower()
            if dispatch in {"after", "post", "possible", "unknown", "ambiguous"}:
                return _SenderReceipt(DeliveryOutcome.UNCERTAIN, error_class="dispatch-uncertain")
            return _SenderReceipt(
                DeliveryOutcome.FAILED,
                error_class=error_class,
                retryable=True,
                retry_after=_retry_after(result.get("retry_after")),
            )
        # ``partial`` or any extension outcome has no per-part receipt semantics.
        return _SenderReceipt(DeliveryOutcome.UNCERTAIN, error_class="sender-invalid-outcome")

    # The maintained Hermes sender returns {success, message_id} or {error}.
    if result.get("success") is True and message_id is not None:
        return _SenderReceipt(DeliveryOutcome.CONFIRMED, message_id=message_id)
    if result.get("success") is True:
        return _SenderReceipt(DeliveryOutcome.UNCERTAIN, error_class="ack-missing-message-id")
    if _is_timeout_label(raw_error):
        return _SenderReceipt(DeliveryOutcome.UNCERTAIN, error_class="dispatch-uncertain")
    if "error" in result:
        dispatch = str(result.get("dispatch", "unknown")).strip().lower()
        if dispatch in {"before", "pre", "pre-dispatch", "none"}:
            return _SenderReceipt(
                DeliveryOutcome.FAILED,
                error_class=error_class,
                retryable=True,
                retry_after=_retry_after(result.get("retry_after")),
            )
        # Hermes' standalone sender returns only an ``error`` mapping when it
        # cannot prove a positive response.  That does not identify whether a
        # multipart/native request was partially dispatched, so it is unsafe to
        # replay without an explicit pre-dispatch marker.
        return _SenderReceipt(DeliveryOutcome.UNCERTAIN, error_class="dispatch-uncertain")
    return _SenderReceipt(DeliveryOutcome.UNCERTAIN, error_class="sender-empty-result")


def _part_result(
    receipt: Delivery | _SenderReceipt, *, fallback: str | None = None
) -> dict[str, str]:
    if isinstance(receipt, Delivery):
        outcome = receipt.state.value
        message_id = receipt.message_id
        error_class = receipt.last_error_class or fallback
    else:
        outcome = receipt.outcome.value
        message_id = receipt.message_id
        error_class = receipt.error_class or fallback
    result = {"outcome": outcome}
    if message_id is not None:
        result["message_id"] = message_id
    if error_class is not None:
        result["error_class"] = _safe_token(error_class, "delivery-failure")
    return result


def _aggregate(
    parts: Sequence[dict[str, str]], *, error_class: str | None = None
) -> DeliveryOutcome:
    outcomes = [part.get("outcome") for part in parts]
    if not outcomes:
        return DeliveryOutcome.FAILED
    if all(outcome == DeliveryOutcome.CONFIRMED.value for outcome in outcomes):
        return DeliveryOutcome.CONFIRMED
    if all(outcome == DeliveryOutcome.SUPPRESSED.value for outcome in outcomes):
        return DeliveryOutcome.SUPPRESSED
    if any(outcome == DeliveryOutcome.UNCERTAIN.value for outcome in outcomes):
        return (
            DeliveryOutcome.UNCERTAIN
            if not any(outcome == DeliveryOutcome.CONFIRMED.value for outcome in outcomes)
            else DeliveryOutcome.PARTIAL
        )
    if any(outcome == DeliveryOutcome.CONFIRMED.value for outcome in outcomes):
        return DeliveryOutcome.PARTIAL
    if error_class == "monitor-disabled":
        return DeliveryOutcome.SUPPRESSED
    if any(outcome == DeliveryOutcome.FAILED.value for outcome in outcomes):
        return DeliveryOutcome.FAILED
    return DeliveryOutcome.PARTIAL


class TelegramDeliveryAdapter:
    """Send one immutable monitor outbox through the existing native Telegram path."""

    def __init__(
        self,
        store: MonitorStore,
        *,
        sender: NativeSender | None = None,
        target_resolver: Callable[[MonitorSettings], Any] | Callable[[], Any] | None = None,
        sleep: Callable[[float], None] | None = None,
        async_sleep: Callable[[float], Any] | None = None,
        max_attempts: int = 3,
        owner_id: str = "monitor-delivery",
        lease_ttl_seconds: float = 120.0,
    ) -> None:
        if (
            not isinstance(max_attempts, int)
            or isinstance(max_attempts, bool)
            or not 1 <= max_attempts <= 3
        ):
            raise ValueError("max_attempts must be between one and three")
        if not isinstance(owner_id, str) or not owner_id.strip():
            raise ValueError("owner_id must be a non-empty string")
        self.store = store
        self.sender = sender
        self.target_resolver = target_resolver
        self.sleep = sleep or time.sleep
        self.async_sleep = async_sleep or asyncio.sleep
        self.max_attempts = max_attempts
        self.owner_id = owner_id.strip()
        self.lease_ttl_seconds = lease_ttl_seconds

    def _resolve_target(
        self,
        settings: MonitorSettings,
        *,
        expected_reference: str | None = None,
    ) -> PinnedTelegramTarget:
        if not settings.destination_ref:
            raise DeliveryConfigurationError("destination-unpinned")
        pinned_reference = (
            settings.destination_ref if expected_reference is None else expected_reference
        )
        if settings.destination_ref != pinned_reference:
            raise DeliveryConfigurationError("destination-changed")
        resolver = self.target_resolver
        if resolver is None:
            target = _default_target(settings)
        else:
            try:
                target_value = resolver(settings)  # type: ignore[call-arg]
            except TypeError:
                target_value = cast(Callable[[], Any], resolver)()
            target = _target_from_value(target_value)
        if target is None:
            raise DeliveryConfigurationError("destination-missing")
        if target.reference != pinned_reference:
            raise DeliveryConfigurationError("destination-changed")
        if not target.chat_id.strip() or (
            target.thread_id is not None and not target.thread_id.strip()
        ):
            raise DeliveryConfigurationError("destination-invalid")
        try:
            target_reference = canonical_target_reference(target.chat_id, target.thread_id)
        except ValueError as exc:
            raise DeliveryConfigurationError("destination-invalid") from exc
        if target_reference != pinned_reference:
            raise DeliveryConfigurationError("destination-changed")
        if settings.profile_binding is not None and target.profile_binding not in {
            None,
            settings.profile_binding,
        }:
            raise DeliveryConfigurationError("profile-binding-changed")
        return target

    def _target_for_attempt(
        self,
        *,
        pinned_reference: str,
        pinned_profile: str | None,
    ) -> tuple[PinnedTelegramTarget | None, _SenderReceipt | None]:
        """Re-read settings and resolve the exact pin immediately before transport."""

        settings = self.store.get_settings()
        if not settings.enabled:
            return None, _SenderReceipt(DeliveryOutcome.SUPPRESSED, error_class="monitor-disabled")
        if settings.destination_ref != pinned_reference:
            return None, _SenderReceipt(DeliveryOutcome.FAILED, error_class="destination-changed")
        if settings.profile_binding != pinned_profile:
            return None, _SenderReceipt(
                DeliveryOutcome.FAILED, error_class="profile-binding-changed"
            )
        try:
            return (
                self._resolve_target(settings, expected_reference=pinned_reference),
                None,
            )
        except TelegramDeliveryError as error:
            return None, _SenderReceipt(
                DeliveryOutcome.FAILED,
                error_class=_safe_token(error.error_class, "destination-unavailable"),
            )
        except Exception:
            # A foreign resolver/configuration exception is never allowed to cross
            # the public boundary or to be interpreted as a transport retry.
            return None, _SenderReceipt(
                DeliveryOutcome.FAILED, error_class="destination-unavailable"
            )

    @staticmethod
    def _verify_parts(deliveries: Sequence[Delivery], parts: Sequence[str]) -> str | None:
        if isinstance(parts, (str, bytes, bytearray)):
            return "outbox-input-invalid"
        if len(parts) != len(deliveries) or len(parts) > _MAX_PARTS:
            return "outbox-shape-changed"
        for delivery, text in zip(deliveries, parts):
            if not isinstance(text, str) or not text:
                return "outbox-input-invalid"
            if hashlib.sha256(text.encode("utf-8")).hexdigest() != delivery.text_hash:
                return "outbox-text-changed"
        return None

    @staticmethod
    def _current_part_results(store: MonitorStore, report_id: str) -> list[dict[str, str]]:
        return [_part_result(delivery) for delivery in store.list_deliveries(report_id)]

    def _persist_setup_receipt(self, lease: Lease, receipt: _SenderReceipt) -> Delivery:
        if receipt.outcome is DeliveryOutcome.SUPPRESSED:
            return self.store.suppress_delivery(lease, reason="monitor-disabled")
        return self._complete(lease, receipt)

    def _complete(
        self,
        lease: Lease,
        receipt: _SenderReceipt,
    ) -> Delivery:
        error_class = (
            _safe_token(receipt.error_class, "delivery-failure")
            if receipt.error_class is not None
            else None
        )
        return self.store.complete_delivery(
            lease,
            outcome=receipt.outcome.value,
            message_id=receipt.message_id,
            error_class=error_class,
            error_message=None,
        )

    def _invoke_sender(self, target: PinnedTelegramTarget, text: str) -> Any:
        sender = self.sender
        if sender is None:
            return _run_awaitable(_default_native_sender(target, text))
        result = sender(target, text)
        if inspect.isawaitable(result):
            return _run_awaitable(result)
        return result

    async def _invoke_sender_async(self, target: PinnedTelegramTarget, text: str) -> Any:
        sender = self.sender
        if sender is None:
            return await _default_native_sender(target, text)
        result = sender(target, text)
        if inspect.isawaitable(result):
            return await result
        return result

    def _receipt_from_exception(self, error: BaseException) -> _SenderReceipt:
        if isinstance(error, DeliveryConfigurationError):
            return _SenderReceipt(
                DeliveryOutcome.FAILED,
                error_class=_safe_token(error.error_class, "destination-unavailable"),
            )
        if isinstance(error, PreDispatchError):
            return _SenderReceipt(
                DeliveryOutcome.FAILED,
                error_class=_safe_token(error.error_class, "pre-dispatch-failure"),
                retryable=True,
                retry_after=_retry_after(error.retry_after),
            )
        if isinstance(error, (TimeoutError, asyncio.TimeoutError)):
            return _SenderReceipt(DeliveryOutcome.UNCERTAIN, error_class="dispatch-uncertain")
        # A raised transport exception does not prove that no request left the
        # process.  Never blindly retry an exception whose dispatch point is unknown.
        return _SenderReceipt(DeliveryOutcome.UNCERTAIN, error_class="dispatch-uncertain")

    def _sleep_for_retry(self, delay: float) -> None:
        if delay > 0:
            self.sleep(delay)

    async def _sleep_for_retry_async(self, delay: float) -> None:
        if delay > 0:
            await self.async_sleep(delay)

    def _advance_coverage(self, report_id: str, coverage_markers: Mapping[str, str] | None) -> bool:
        deliveries = self.store.list_deliveries(report_id)
        if not deliveries or any(item.state is not DeliveryState.CONFIRMED for item in deliveries):
            return False
        if coverage_markers is None:
            return False
        for work_key, marker in coverage_markers.items():
            self.store.mark_final_outcome_delivery(work_key, marker)
        return bool(coverage_markers)

    def deliver_report(
        self,
        report_id: str,
        parts: Sequence[str],
        *,
        coverage_markers: Mapping[str, str] | None = None,
    ) -> DeliveryRun:
        """Deliver parts synchronously using at most three pre-dispatch retries each."""

        settings = self.store.get_settings()
        if not settings.enabled:
            return DeliveryRun(
                report_id,
                DeliveryOutcome.SUPPRESSED,
                tuple(self._current_part_results(self.store, report_id)),
                False,
                "monitor-disabled",
            )
        pinned_reference = settings.destination_ref or ""
        pinned_profile = settings.profile_binding
        deliveries = self.store.list_deliveries(report_id)
        mismatch = self._verify_parts(deliveries, parts)
        if mismatch is not None:
            return DeliveryRun(report_id, DeliveryOutcome.FAILED, tuple(), False, mismatch)
        try:
            self._resolve_target(settings, expected_reference=pinned_reference)
        except TelegramDeliveryError as error:
            return DeliveryRun(
                report_id,
                DeliveryOutcome.FAILED,
                tuple(),
                False,
                _safe_token(error.error_class, "destination-unavailable"),
            )
        except Exception:
            return DeliveryRun(
                report_id,
                DeliveryOutcome.FAILED,
                tuple(),
                False,
                "destination-unavailable",
            )
        if not deliveries:
            return DeliveryRun(report_id, DeliveryOutcome.FAILED, tuple(), False, "outbox-empty")

        results: list[dict[str, str]] = []
        for index, text in enumerate(parts):
            delivery = self.store.get_delivery(report_id, index)
            if delivery is None:  # pragma: no cover - guarded by list/hash validation
                return DeliveryRun(
                    report_id, DeliveryOutcome.FAILED, tuple(results), False, "outbox-missing"
                )
            if delivery.state is DeliveryState.CONFIRMED:
                results.append(_part_result(delivery))
                continue
            if delivery.state in {DeliveryState.UNCERTAIN, DeliveryState.SUPPRESSED}:
                results.append(_part_result(delivery))
                break

            part_done = False
            for attempt in range(self.max_attempts):
                lease = self.store.claim_delivery(
                    report_id,
                    index,
                    owner_id=self.owner_id,
                    ttl_seconds=self.lease_ttl_seconds,
                )
                if lease is None:
                    current = self.store.get_delivery(report_id, index)
                    if current is not None and current.state is DeliveryState.CONFIRMED:
                        results.append(_part_result(current))
                    elif not self.store.get_settings().enabled:
                        results.append(
                            {
                                "outcome": DeliveryOutcome.SUPPRESSED.value,
                                "error_class": "monitor-disabled",
                            }
                        )
                    else:
                        results.append(
                            {
                                "outcome": DeliveryOutcome.FAILED.value,
                                "error_class": "delivery-lease-busy",
                            }
                        )
                    part_done = True
                    break
                if not self.store.can_dispatch_delivery(lease):
                    if not self.store.get_settings().enabled:
                        try:
                            current = self.store.suppress_delivery(lease, reason="monitor-disabled")
                            results.append(_part_result(current))
                        except LeaseLostError:
                            results.append(
                                {
                                    "outcome": DeliveryOutcome.UNCERTAIN.value,
                                    "error_class": "dispatch-uncertain",
                                }
                            )
                    else:
                        results.append(
                            {
                                "outcome": DeliveryOutcome.UNCERTAIN.value,
                                "error_class": "dispatch-uncertain",
                            }
                        )
                    part_done = True
                    break
                target, setup_receipt = self._target_for_attempt(
                    pinned_reference=pinned_reference,
                    pinned_profile=pinned_profile,
                )
                if setup_receipt is not None:
                    try:
                        persisted = self._persist_setup_receipt(lease, setup_receipt)
                    except LeaseLostError:
                        results.append(
                            {
                                "outcome": DeliveryOutcome.UNCERTAIN.value,
                                "error_class": "dispatch-uncertain",
                            }
                        )
                    else:
                        results.append(_part_result(persisted))
                    part_done = True
                    break
                assert target is not None
                try:
                    raw = self._invoke_sender(target, text)
                    receipt = _normalize_sender_result(raw)
                except BaseException as error:
                    if isinstance(error, (KeyboardInterrupt, SystemExit)):
                        raise
                    receipt = self._receipt_from_exception(error)
                try:
                    persisted = self._complete(lease, receipt)
                except LeaseLostError:
                    results.append(
                        {
                            "outcome": DeliveryOutcome.UNCERTAIN.value,
                            "error_class": "dispatch-uncertain",
                        }
                    )
                    part_done = True
                    break
                if (
                    receipt.outcome is DeliveryOutcome.FAILED
                    and receipt.retryable
                    and attempt + 1 < self.max_attempts
                ):
                    self._sleep_for_retry(receipt.retry_after)
                    continue
                results.append(_part_result(persisted))
                part_done = True
                break
            if not part_done:
                results.append(
                    {"outcome": DeliveryOutcome.FAILED.value, "error_class": "retry-limit"}
                )
            if results[-1]["outcome"] != DeliveryOutcome.CONFIRMED.value:
                break

        advanced = False
        if results and all(
            item.get("outcome") == DeliveryOutcome.CONFIRMED.value for item in results
        ):
            advanced = self._advance_coverage(report_id, coverage_markers)
        return DeliveryRun(report_id, _aggregate(results), tuple(results), advanced)

    async def deliver_report_async(
        self,
        report_id: str,
        parts: Sequence[str],
        *,
        coverage_markers: Mapping[str, str] | None = None,
    ) -> DeliveryRun:
        """Async counterpart used by native callbacks; semantics match ``deliver_report``."""

        # Keep one implementation of receipt and lease semantics.  The native sender is
        # normally async, so this path mirrors the synchronous loop rather than calling
        # ``asyncio.run`` from an active event loop.
        settings = self.store.get_settings()
        if not settings.enabled:
            return DeliveryRun(
                report_id,
                DeliveryOutcome.SUPPRESSED,
                tuple(self._current_part_results(self.store, report_id)),
                False,
                "monitor-disabled",
            )
        pinned_reference = settings.destination_ref or ""
        pinned_profile = settings.profile_binding
        deliveries = self.store.list_deliveries(report_id)
        mismatch = self._verify_parts(deliveries, parts)
        if mismatch is not None:
            return DeliveryRun(report_id, DeliveryOutcome.FAILED, tuple(), False, mismatch)
        try:
            self._resolve_target(settings, expected_reference=pinned_reference)
        except TelegramDeliveryError as error:
            return DeliveryRun(
                report_id,
                DeliveryOutcome.FAILED,
                tuple(),
                False,
                _safe_token(error.error_class, "destination-unavailable"),
            )
        except Exception:
            return DeliveryRun(
                report_id,
                DeliveryOutcome.FAILED,
                tuple(),
                False,
                "destination-unavailable",
            )
        if not deliveries:
            return DeliveryRun(report_id, DeliveryOutcome.FAILED, tuple(), False, "outbox-empty")

        results: list[dict[str, str]] = []
        for index, text in enumerate(parts):
            delivery = self.store.get_delivery(report_id, index)
            if delivery is None:
                return DeliveryRun(
                    report_id, DeliveryOutcome.FAILED, tuple(results), False, "outbox-missing"
                )
            if delivery.state is DeliveryState.CONFIRMED:
                results.append(_part_result(delivery))
                continue
            if delivery.state in {DeliveryState.UNCERTAIN, DeliveryState.SUPPRESSED}:
                results.append(_part_result(delivery))
                break
            part_done = False
            for attempt in range(self.max_attempts):
                lease = self.store.claim_delivery(
                    report_id,
                    index,
                    owner_id=self.owner_id,
                    ttl_seconds=self.lease_ttl_seconds,
                )
                if lease is None:
                    current = self.store.get_delivery(report_id, index)
                    if current is not None and current.state is DeliveryState.CONFIRMED:
                        results.append(_part_result(current))
                    elif not self.store.get_settings().enabled:
                        results.append(
                            {
                                "outcome": DeliveryOutcome.SUPPRESSED.value,
                                "error_class": "monitor-disabled",
                            }
                        )
                    else:
                        results.append(
                            {
                                "outcome": DeliveryOutcome.FAILED.value,
                                "error_class": "delivery-lease-busy",
                            }
                        )
                    part_done = True
                    break
                if not self.store.can_dispatch_delivery(lease):
                    if not self.store.get_settings().enabled:
                        try:
                            current = self.store.suppress_delivery(lease, reason="monitor-disabled")
                            results.append(_part_result(current))
                        except LeaseLostError:
                            results.append(
                                {
                                    "outcome": DeliveryOutcome.UNCERTAIN.value,
                                    "error_class": "dispatch-uncertain",
                                }
                            )
                    else:
                        results.append(
                            {
                                "outcome": DeliveryOutcome.UNCERTAIN.value,
                                "error_class": "dispatch-uncertain",
                            }
                        )
                    part_done = True
                    break
                target, setup_receipt = self._target_for_attempt(
                    pinned_reference=pinned_reference,
                    pinned_profile=pinned_profile,
                )
                if setup_receipt is not None:
                    try:
                        persisted = self._persist_setup_receipt(lease, setup_receipt)
                    except LeaseLostError:
                        results.append(
                            {
                                "outcome": DeliveryOutcome.UNCERTAIN.value,
                                "error_class": "dispatch-uncertain",
                            }
                        )
                    else:
                        results.append(_part_result(persisted))
                    part_done = True
                    break
                assert target is not None
                try:
                    raw = await self._invoke_sender_async(target, text)
                    receipt = _normalize_sender_result(raw)
                except BaseException as error:
                    if isinstance(error, (KeyboardInterrupt, SystemExit)):
                        raise
                    receipt = self._receipt_from_exception(error)
                try:
                    persisted = self._complete(lease, receipt)
                except LeaseLostError:
                    results.append(
                        {
                            "outcome": DeliveryOutcome.UNCERTAIN.value,
                            "error_class": "dispatch-uncertain",
                        }
                    )
                    part_done = True
                    break
                if (
                    receipt.outcome is DeliveryOutcome.FAILED
                    and receipt.retryable
                    and attempt + 1 < self.max_attempts
                ):
                    await self._sleep_for_retry_async(receipt.retry_after)
                    continue
                results.append(_part_result(persisted))
                part_done = True
                break
            if not part_done:
                results.append(
                    {"outcome": DeliveryOutcome.FAILED.value, "error_class": "retry-limit"}
                )
            if results[-1]["outcome"] != DeliveryOutcome.CONFIRMED.value:
                break

        advanced = False
        if results and all(
            item.get("outcome") == DeliveryOutcome.CONFIRMED.value for item in results
        ):
            advanced = self._advance_coverage(report_id, coverage_markers)
        return DeliveryRun(report_id, _aggregate(results), tuple(results), advanced)

    # Concise aliases for native callback integration and deterministic callers.
    deliver = deliver_report
    send_report = deliver_report
    deliver_async = deliver_report_async


def _run_awaitable(awaitable: Any) -> Any:
    """Run an awaitable for the sync adapter without leaking an event loop."""

    if not inspect.isawaitable(awaitable):
        return awaitable
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_await_once(awaitable))
    close = getattr(awaitable, "close", None)
    if callable(close):
        close()
    raise RuntimeError("use deliver_report_async from a running event loop")


async def _await_once(awaitable: Any) -> Any:
    return await awaitable
