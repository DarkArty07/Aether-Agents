"""Semantic extraction lifecycle, fingerprinting, caching, and auxiliary transport."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import logging
import threading
import time
from pathlib import Path
from typing import Any

from aether_agents.paths import atomic_private_write, ensure_private_dir

from .common import KnowledgeError
from .context import KnowledgeContext
from .graphify import GraphifyBackend

logger = logging.getLogger(__name__)

# Extensions eligible for semantic extraction (docs and source code)
_ELIGIBLE_EXTENSIONS = frozenset(
    ".md .txt .rst .py .js .jsx .ts .tsx .go .rs .java .c .h .cpp .hpp .cs .rb .php .swift .kt .sql .html".split()
)


def compute_chunk_fingerprint(
    scope_version: str,
    prompt_text: str,
    policy: dict[str, Any],
    model_identity_digest: str,
    chunk_file_hashes: dict[str, str],
) -> str:
    """Calculate deterministic chunk fingerprint across all inputs and extraction policies."""
    hasher = hashlib.sha256()
    hasher.update(scope_version.encode("utf-8"))
    hasher.update(prompt_text.encode("utf-8"))
    hasher.update(json.dumps(policy, sort_keys=True).encode("utf-8"))
    hasher.update(model_identity_digest.encode("utf-8"))
    for path, fhash in sorted(chunk_file_hashes.items()):
        hasher.update(f"{path}:{fhash}".encode("utf-8"))
    return hasher.hexdigest()


def get_model_identity_digest(
    task: str,
    provider: str | None = None,
    model: str | None = None,
    api_mode: str | None = None,
) -> str:
    """Non-secret digest of model, provider, api_mode, and task binding."""
    identity = f"{task}:{provider or 'default'}:{model or 'default'}:{api_mode or 'default'}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def resolve_auxiliary_route(
    configuration: dict[str, Any],
    task: str | None = None,
) -> dict[str, str | None]:
    """Resolve non-secret concrete auxiliary route (provider, model, api_mode)."""
    task = task or resolve_auxiliary_task(configuration)
    semantic_cfg = configuration.get("semantic", {})
    if not isinstance(semantic_cfg, dict):
        semantic_cfg = {}

    provider = (
        semantic_cfg.get("provider")
        or configuration.get("semantic_provider")
        or configuration.get("provider")
    )
    model = (
        semantic_cfg.get("model")
        or configuration.get("semantic_model")
        or configuration.get("model")
    )
    api_mode = (
        semantic_cfg.get("api_mode")
        or configuration.get("semantic_api_mode")
        or configuration.get("api_mode")
    )

    if provider is not None:
        provider = str(provider).strip() or None
    if model is not None:
        model = str(model).strip() or None
    if api_mode is not None:
        api_mode = str(api_mode).strip() or None

    # Try resolving via Hermes auxiliary client if available and details are missing
    try:
        from agent.auxiliary_client import (  # type: ignore[import-not-found,import-untyped]  # pyright: ignore[reportMissingImports]
            _read_main_model,
            _read_main_provider,
            _resolve_task_provider_model,
        )

        res_provider, res_model, _base_url, _api_key, res_api_mode = _resolve_task_provider_model(
            task=task,
            provider=provider,
            model=model,
        )
        if provider is None and res_provider:
            if res_provider == "auto":
                main_p = _read_main_provider()
                provider = str(main_p).strip() if main_p else "auto"
            else:
                provider = str(res_provider).strip()

        if model is None and res_model:
            model = str(res_model).strip()
        elif model is None and provider and provider != "auto":
            main_m = _read_main_model()
            if main_m:
                model = str(main_m).strip()

        if api_mode is None and res_api_mode:
            api_mode = str(res_api_mode).strip()
    except Exception:
        pass

    if not api_mode and provider and provider not in ("auto", "unresolved"):
        if provider.lower() in ("anthropic", "claude"):
            api_mode = "anthropic_messages"
        else:
            api_mode = "chat_completions"

    return {
        "provider": provider or "default",
        "model": model or "default",
        "api_mode": api_mode or "default",
    }


def is_route_resolved(route: dict[str, Any] | None) -> bool:
    """Verify that concrete non-secret provider, model, and api_mode are resolved."""
    if not route or not isinstance(route, dict):
        return False
    provider = route.get("provider")
    model = route.get("model")
    api_mode = route.get("api_mode")
    if not provider or not model or not api_mode:
        return False
    unresolved_markers = {"", "none", "null", "auto", "unresolved"}
    if any(str(v).strip().casefold() in unresolved_markers for v in (provider, model, api_mode)):
        return False
    return True


def routes_match(expected: dict[str, Any] | None, actual: dict[str, Any] | None) -> bool:
    """Check if actual route matches expected route."""
    if not expected or not actual or not isinstance(expected, dict) or not isinstance(actual, dict):
        return False
    for k in ("provider", "model", "api_mode"):
        exp_v = expected.get(k)
        act_v = actual.get(k)
        if exp_v and act_v:
            if str(exp_v).strip().casefold() != str(act_v).strip().casefold():
                return False
    return True


def resolve_auxiliary_task(configuration: dict[str, Any]) -> str | None:
    """Resolve auxiliary task name or None if missing/auto/ambiguous."""
    semantic_cfg = configuration.get("semantic", {})
    task_a = None
    if isinstance(semantic_cfg, dict):
        raw_a = semantic_cfg.get("auxiliary_task")
        if raw_a is not None:
            task_a = str(raw_a).strip()
    raw_b = configuration.get("semantic_auxiliary_task")
    task_b = str(raw_b).strip() if raw_b is not None else None

    # Check ambiguity: if both provided and different
    if task_a is not None and task_b is not None and task_a != task_b:
        return None

    task = task_a if task_a is not None else task_b
    if not task:
        return None
    if task.casefold() in ("", "auto", "none", "null"):
        return None
    return task


def _fetch_all_prepared_chunks(
    backend: GraphifyBackend,
    source_root: Path,
    graph_path: Path,
    eligible_files: list[str],
    *,
    page_size: int = 25,
) -> list[dict[str, Any]]:
    """Fetch prepared semantic extraction chunks across bounded pages."""
    all_chunks: list[dict[str, Any]] = []
    offset = 0
    while True:
        prep_res = backend.run(
            "semantic_prepare",
            source_root=source_root,
            graph_path=graph_path,
            arguments={
                "files": eligible_files,
                "offset": offset,
                "limit": page_size,
            },
        )
        chunks = prep_res.get("chunks", [])
        if not chunks:
            break
        all_chunks.extend(chunks)
        total_chunks = prep_res.get("total_chunks")
        has_more = prep_res.get("has_more")
        if total_chunks is not None and len(all_chunks) >= total_chunks:
            break
        if has_more is False:
            break
        if total_chunks is None and len(chunks) < page_size:
            break
        offset += len(chunks)
    return all_chunks


def compute_semantic_fingerprint(
    backend: GraphifyBackend,
    source_root: Path,
    graph_path: Path,
    inputs: dict[str, str],
    configuration: dict[str, Any],
) -> str | None:
    """Deterministic overall fingerprint for configured semantic extraction without calling LLM."""
    aux_task = resolve_auxiliary_task(configuration)
    if not aux_task:
        return None

    eligible_files = sorted(
        [p for p in inputs if Path(p).suffix.casefold() in _ELIGIBLE_EXTENSIONS]
    )
    if not eligible_files:
        return hashlib.sha256(b"no_eligible_files").hexdigest()

    try:
        chunks = _fetch_all_prepared_chunks(
            backend=backend,
            source_root=source_root,
            graph_path=graph_path,
            eligible_files=eligible_files,
        )
    except Exception:
        return None

    if not chunks:
        return hashlib.sha256(b"no_chunks").hexdigest()

    route = resolve_auxiliary_route(configuration, aux_task)
    model_digest = get_model_identity_digest(
        aux_task,
        provider=route.get("provider"),
        model=route.get("model"),
        api_mode=route.get("api_mode"),
    )
    policy = {"deep": False, "token_budget": 4000}
    scope_version = "regular-tracked-v1"

    chunk_fps: list[str] = []
    for chunk in chunks:
        c_files = chunk.get("files", [])
        file_hashes = {f: inputs[f] for f in c_files if f in inputs}
        prompt_text = chunk["system_prompt"] + "\n" + chunk["user_prompt"]
        fp = compute_chunk_fingerprint(
            scope_version, prompt_text, policy, model_digest, file_hashes
        )
        chunk_fps.append(fp)

    return hashlib.sha256("".join(chunk_fps).encode("utf-8")).hexdigest()


class SemanticCache:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        ensure_private_dir(self.cache_dir)

    def get(self, fingerprint: str) -> dict[str, Any] | None:
        entry = self.get_entry(fingerprint)
        if entry is not None and "fragment" in entry:
            return entry["fragment"]
        return None

    def get_entry(self, fingerprint: str) -> dict[str, Any] | None:
        path = self.cache_dir / f"{fingerprint}.json"
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return None

    def put(
        self, fingerprint: str, fragment: dict[str, Any], meta: dict[str, Any] | None = None
    ) -> None:
        path = self.cache_dir / f"{fingerprint}.json"
        payload = {
            "fingerprint": fingerprint,
            "saved_at": time.time(),
            "meta": meta or {},
            "fragment": fragment,
        }
        atomic_private_write(path, json.dumps(payload, indent=2).encode("utf-8"))


def _call_auxiliary_model(
    task: str,
    system_prompt: str,
    user_prompt: str,
    timeout: float = 120.0,
    route_info: dict[str, Any] | None = None,
    api_mode: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """Invoke the Hermes profile-scoped auxiliary client."""
    try:
        from agent.auxiliary_client import (  # type: ignore[import-not-found,import-untyped]  # pyright: ignore[reportMissingImports]
            call_llm,
        )
    except ImportError as exc:
        raise KnowledgeError(
            "COMPONENT_UNAVAILABLE", "Hermes auxiliary client is not available in this environment."
        ) from exc

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    local_route_info: dict[str, str] = {}
    try:
        response = call_llm(
            task=task,
            messages=messages,
            timeout=timeout,
            route_info=local_route_info,
        )
    except TypeError:
        response = call_llm(task=task, messages=messages, timeout=timeout)
    except Exception as exc:
        err_msg = str(exc)
        if "429" in err_msg or "rate" in err_msg.casefold() or "quota" in err_msg.casefold():
            raise KnowledgeError(
                "ROUTER_EXHAUSTION", f"Auxiliary model rate limit/quota: {exc}"
            ) from exc
        raise KnowledgeError("AUXILIARY_FAILED", f"Auxiliary model call failed: {exc}") from exc

    content = ""
    finish_reason = None
    if hasattr(response, "choices") and response.choices:
        msg = response.choices[0].message
        content = getattr(msg, "content", "") or ""
        finish_reason = getattr(response.choices[0], "finish_reason", None)
    elif isinstance(response, dict):
        choices = response.get("choices", [])
        if choices and isinstance(choices[0], dict):
            content = choices[0].get("message", {}).get("content", "")
            finish_reason = choices[0].get("finish_reason")

    usage: dict[str, Any] = {}
    if not isinstance(response, dict) and hasattr(response, "usage") and response.usage:
        usage = {
            "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
            "completion_tokens": getattr(response.usage, "completion_tokens", 0),
            "total_tokens": getattr(response.usage, "total_tokens", 0),
        }
    elif isinstance(response, dict) and "usage" in response:
        usage = dict(response["usage"])

    if finish_reason is not None:
        usage["finish_reason"] = finish_reason

    if local_route_info:
        if api_mode and "api_mode" not in local_route_info:
            local_route_info["api_mode"] = api_mode
        usage["route"] = dict(local_route_info)
        if route_info is not None:
            route_info.update(local_route_info)

    return content, usage


def run_semantic_extraction(
    backend: GraphifyBackend,
    source_root: Path,
    graph_path: Path,
    inputs: dict[str, str],
    cache_root: Path,
    ctx: KnowledgeContext,
    configuration: dict[str, Any],
    *,
    deadline_seconds: float = 600.0,
    cancel_event: threading.Event | None = None,
) -> dict[str, Any]:
    """Orchestrate semantic chunking, auxiliary calls, validation, caching, and graph merging."""
    if cancel_event and cancel_event.is_set():
        raise KnowledgeError("OPERATION_CANCELLED", "Semantic extraction was cancelled.")

    aux_task = resolve_auxiliary_task(configuration)
    if not aux_task:
        return {
            "state": "unavailable",
            "fingerprint": None,
            "covered_paths": [],
            "pending_paths": sorted(
                [p for p in inputs if Path(p).suffix.casefold() in _ELIGIBLE_EXTENSIONS]
            ),
            "failed_paths": [],
            "validated_chunk_ids": [],
            "observed_usage": {
                "total_tokens": 0,
                "model_calls": 0,
                "reason": "unbound_auxiliary_task",
            },
        }

    expected_route = resolve_auxiliary_route(configuration, aux_task)
    model_digest = get_model_identity_digest(
        aux_task,
        provider=expected_route.get("provider"),
        model=expected_route.get("model"),
        api_mode=expected_route.get("api_mode"),
    )
    policy = {"deep": False, "token_budget": 4000}
    scope_version = "regular-tracked-v1"

    # Identify eligible documentation and code files
    eligible_files = sorted(
        [p for p in inputs if Path(p).suffix.casefold() in _ELIGIBLE_EXTENSIONS]
    )
    if not eligible_files:
        return {
            "state": "complete",
            "fingerprint": hashlib.sha256(b"no_eligible_files").hexdigest(),
            "covered_paths": [],
            "pending_paths": [],
            "failed_paths": [],
            "validated_chunk_ids": [],
            "observed_usage": {"total_tokens": 0, "model_calls": 0},
        }

    # Step 1: Prepare chunks in native worker across bounded pages
    try:
        chunks = _fetch_all_prepared_chunks(
            backend=backend,
            source_root=source_root,
            graph_path=graph_path,
            eligible_files=eligible_files,
        )
    except Exception as exc:
        logger.warning("Failed preparing semantic extraction chunks: %s", exc)
        return {
            "state": "unavailable",
            "fingerprint": None,
            "covered_paths": [],
            "pending_paths": sorted(eligible_files),
            "failed_paths": [],
            "validated_chunk_ids": [],
            "observed_usage": {
                "total_tokens": 0,
                "model_calls": 0,
                "error": str(exc),
            },
        }

    if not chunks:
        return {
            "state": "complete",
            "fingerprint": hashlib.sha256(b"no_chunks").hexdigest(),
            "covered_paths": [],
            "pending_paths": [],
            "failed_paths": [],
            "validated_chunk_ids": [],
            "observed_usage": {"total_tokens": 0, "model_calls": 0},
        }

    cache_dir = cache_root / "knowledge" / ctx.project_id / "semantic_cache"
    cache = SemanticCache(cache_dir)

    cfg_deadline = configuration.get(
        "semantic_deadline_seconds", configuration.get("deadline_seconds")
    )
    if cfg_deadline is not None:
        try:
            deadline_seconds = float(cfg_deadline)
        except (ValueError, TypeError):
            pass

    start_time = time.time()
    deadline = start_time + deadline_seconds

    chunk_fingerprints: dict[int, str] = {}
    cached_fragments: dict[int, dict[str, Any]] = {}
    needed_chunks: list[dict[str, Any]] = []

    for chunk in chunks:
        cid = int(chunk["chunk_id"])
        c_files = chunk.get("files", [])
        file_hashes = {f: inputs[f] for f in c_files if f in inputs}
        prompt_text = chunk["system_prompt"] + "\n" + chunk["user_prompt"]
        fp = compute_chunk_fingerprint(
            scope_version, prompt_text, policy, model_digest, file_hashes
        )
        chunk_fingerprints[cid] = fp

        fragment = None
        if is_route_resolved(expected_route):
            cache_entry = cache.get_entry(fp)
            if cache_entry is not None:
                cached_meta = cache_entry.get("meta", {})
                cached_route = cached_meta.get("route")
                if cached_route is None or (
                    is_route_resolved(cached_route) and routes_match(expected_route, cached_route)
                ):
                    fragment = cache_entry.get("fragment")

        if fragment is not None:
            cached_fragments[cid] = fragment
        else:
            needed_chunks.append(chunk)

    total_tokens = 0
    model_calls_made = 0
    newly_validated_fragments: dict[int, dict[str, Any]] = {}
    failed_chunks: set[int] = set()
    pending_chunks: set[int] = set()

    deadline_deferred_chunks: set[int] = set()
    auxiliary_failed_chunks: set[int] = set()
    validation_failed_chunks: set[int] = set()
    apply_failed_chunks: set[int] = set()

    if needed_chunks:
        if time.time() >= deadline:
            for c in needed_chunks:
                cid = int(c["chunk_id"])
                pending_chunks.add(cid)
                deadline_deferred_chunks.add(cid)
        else:
            semaphore = threading.Semaphore(2)  # max_concurrency = 2
            lock = threading.Lock()

            def process_chunk(c: dict[str, Any]) -> None:
                nonlocal total_tokens, model_calls_made
                cid = int(c["chunk_id"])
                fp = chunk_fingerprints[cid]

                if cancel_event and cancel_event.is_set():
                    return

                if time.time() >= deadline:
                    with lock:
                        pending_chunks.add(cid)
                        deadline_deferred_chunks.add(cid)
                    return

                with semaphore:
                    if cancel_event and cancel_event.is_set():
                        return

                    if time.time() >= deadline:
                        with lock:
                            pending_chunks.add(cid)
                            deadline_deferred_chunks.add(cid)
                        return

                    # Up to 1 transient retry per chunk
                    last_err = None
                    raw_text = ""
                    usage: dict[str, Any] = {}
                    chunk_route_info: dict[str, Any] = {}
                    attempts_made = 0
                    for attempt in range(2):
                        if cancel_event and cancel_event.is_set():
                            break
                        if time.time() >= deadline:
                            break

                        remaining_time = deadline - time.time()
                        if remaining_time <= 0:
                            break

                        try:
                            with lock:
                                model_calls_made += 1
                            attempts_made += 1
                            chunk_route_info = {}
                            call_res: Any = None
                            try:
                                call_res = _call_auxiliary_model(
                                    task=aux_task,
                                    system_prompt=c["system_prompt"],
                                    user_prompt=c["user_prompt"],
                                    timeout=min(180.0, max(1.0, remaining_time)),
                                    route_info=chunk_route_info,
                                    api_mode=expected_route.get("api_mode"),
                                )
                            except TypeError:
                                call_res = _call_auxiliary_model(
                                    task=aux_task,
                                    system_prompt=c["system_prompt"],
                                    user_prompt=c["user_prompt"],
                                    timeout=min(180.0, max(1.0, remaining_time)),
                                )

                            if isinstance(call_res, tuple) and len(call_res) == 3:
                                raw_text, usage, call_extra = call_res
                                if isinstance(call_extra, dict):
                                    usage = {**call_extra, **usage}
                            elif isinstance(call_res, tuple) and len(call_res) == 2:
                                raw_text, usage = call_res
                            break
                        except Exception as exc:
                            last_err = exc
                            if isinstance(exc, KnowledgeError) and exc.code == "ROUTER_EXHAUSTION":
                                # Router exhaustion fails immediately without endless retries
                                break
                            time.sleep(0.5)

                    if cancel_event and cancel_event.is_set():
                        return

                    if attempts_made == 0:
                        with lock:
                            pending_chunks.add(cid)
                            deadline_deferred_chunks.add(cid)
                        return

                    if not raw_text:
                        logger.warning("Chunk %d failed auxiliary extraction: %s", cid, last_err)
                        with lock:
                            failed_chunks.add(cid)
                            auxiliary_failed_chunks.add(cid)
                        return

                    # Check finish_reason: incomplete reasons (e.g. length) must not be applied or cached
                    finish_reason = usage.get("finish_reason") if isinstance(usage, dict) else None
                    is_terminal_finish = finish_reason is None or str(
                        finish_reason
                    ).strip().lower() in ("stop", "tool_calls")
                    if not is_terminal_finish:
                        logger.warning(
                            "Chunk %d has non-terminal finish_reason: %s", cid, finish_reason
                        )
                        with lock:
                            failed_chunks.add(cid)
                            validation_failed_chunks.add(cid)
                        return

                    with lock:
                        total_tokens += usage.get("total_tokens", 0)

                    # Determine actual route
                    actual_route = dict(expected_route)
                    if isinstance(usage, dict) and isinstance(usage.get("route"), dict):
                        actual_route.update(usage["route"])
                    if chunk_route_info:
                        actual_route.update(chunk_route_info)

                    # Validate semantic fragment through worker
                    try:
                        val_res = backend.run(
                            "semantic_validate",
                            source_root=source_root,
                            graph_path=graph_path,
                            arguments={
                                "model_text": raw_text,
                                "allowed_sources": c.get("files", []),
                                "allow_empty": False,
                            },
                        )
                        frag = val_res.get("fragment", {})
                        route_ok = is_route_resolved(actual_route) and routes_match(
                            expected_route, actual_route
                        )
                        if route_ok:
                            cache.put(fp, frag, meta={"usage": usage, "route": actual_route})
                        else:
                            logger.info(
                                "Chunk %d skipping cache publication (route unresolved or mismatched: %s vs %s)",
                                cid,
                                expected_route,
                                actual_route,
                            )
                        with lock:
                            newly_validated_fragments[cid] = frag
                    except Exception as exc:
                        logger.warning("Chunk %d failed fragment validation: %s", cid, exc)
                        with lock:
                            failed_chunks.add(cid)
                            validation_failed_chunks.add(cid)

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(process_chunk, c) for c in needed_chunks]
                concurrent.futures.wait(futures)

            if cancel_event and cancel_event.is_set():
                raise KnowledgeError("OPERATION_CANCELLED", "Semantic extraction was cancelled.")

    # Step 3: Apply all validated fragments (cached + newly validated) to graph
    all_valid_fragments = {**cached_fragments, **newly_validated_fragments}
    for cid in sorted(all_valid_fragments.keys()):
        frag = all_valid_fragments[cid]
        try:
            backend.run(
                "semantic_apply",
                source_root=source_root,
                graph_path=graph_path,
                arguments={
                    "fragment": frag,
                    "allowed_sources": list(inputs.keys()),
                    "allow_empty": True,
                },
            )
        except Exception as exc:
            logger.warning("Failed applying fragment for chunk %d: %s", cid, exc)
            failed_chunks.add(cid)
            apply_failed_chunks.add(cid)
            all_valid_fragments.pop(cid, None)

    successful_chunks = set(all_valid_fragments.keys())
    for chunk in chunks:
        cid = int(chunk["chunk_id"])
        if cid not in successful_chunks and cid not in failed_chunks and cid not in pending_chunks:
            pending_chunks.add(cid)
            deadline_deferred_chunks.add(cid)

    # Compute coverage status
    file_to_chunks: dict[str, set[int]] = {p: set() for p in eligible_files}
    for chunk in chunks:
        cid = int(chunk["chunk_id"])
        for p in chunk.get("files", []):
            file_to_chunks.setdefault(p, set()).add(cid)

    covered_paths_set: set[str] = set()
    failed_paths_set: set[str] = set()
    pending_paths_set: set[str] = set()

    for p in sorted(file_to_chunks.keys()):
        cids = file_to_chunks[p]
        if not cids:
            pending_paths_set.add(p)
        elif cids.issubset(successful_chunks):
            covered_paths_set.add(p)
        else:
            if cids & failed_chunks:
                failed_paths_set.add(p)
            if cids & pending_chunks:
                pending_paths_set.add(p)

    # Overall fingerprint
    all_fps = "".join(chunk_fingerprints[int(c["chunk_id"])] for c in chunks)
    overall_fp = hashlib.sha256(all_fps.encode("utf-8")).hexdigest()

    if len(all_valid_fragments) == len(chunks):
        state = "complete"
    elif len(all_valid_fragments) > 0:
        state = "partial"
    elif pending_chunks:
        state = "partial" if failed_chunks else "pending"
    else:
        state = "unavailable"

    return {
        "state": state,
        "fingerprint": overall_fp,
        "covered_paths": sorted(covered_paths_set),
        "pending_paths": sorted(pending_paths_set),
        "failed_paths": sorted(failed_paths_set),
        "validated_chunk_ids": sorted(all_valid_fragments.keys()),
        "observed_usage": {
            "total_tokens": total_tokens,
            "model_calls": model_calls_made,
            "elapsed_seconds": round(time.time() - start_time, 3),
            "chunk_counts": {
                "total": len(chunks),
                "cached": len(cached_fragments),
                "validated": len(newly_validated_fragments),
                "pending": len(pending_chunks),
                "failed": len(failed_chunks),
            },
            "categories": {
                "deadline_deferred": len(deadline_deferred_chunks),
                "auxiliary_failed": len(auxiliary_failed_chunks),
                "validation_failed": len(validation_failed_chunks),
                "apply_failed": len(apply_failed_chunks),
            },
        },
    }
