"""
Benchmark vLLM vs Ollama local inference.

F1-T10 records throughput, latency p50/p95, and RTX 3060 VRAM usage. The script
uses only the Python standard library so it can run before dependency changes.

Expected setup:
    vllm serve <model> --host 127.0.0.1 --port 8000
    ollama serve

Examples:
    python tools/test_vllm.py --providers both --model deepseek-r1:8b
    python tools/test_vllm.py --providers vllm --vllm-model TheBloke/Mistral-7B-Instruct-v0.2-GPTQ
    python tools/test_vllm.py --requests 20 --concurrency 2 --max-tokens 64
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / ".tmp"

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")


PROMPTS = [
    "Responde en JSON: {\"averia_grave\": false}. Texto: coche revisado, sin golpes.",
    "Detecta averias en JSON. Texto: motor roto, no arranca, se vende para reparar.",
    "Clasifica el riesgo del anuncio en JSON. Texto: itv al dia, mantenimiento completo.",
    "Extrae si hay siniestro en JSON. Texto: golpe frontal con airbags saltados.",
]


@dataclass
class RequestMetric:
    provider: str
    request_id: int
    ok: bool
    latency_ms: int
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    error: str | None = None


@dataclass
class GpuSnapshot:
    label: str
    timestamp: str
    memory_used_mb: int | None
    memory_total_mb: int | None
    gpu_util_percent: int | None
    name: str | None
    error: str | None = None


def _percentile(values: list[int], percentile: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    index = math.ceil((percentile / 100) * len(ordered)) - 1
    return ordered[max(0, min(index, len(ordered) - 1))]


def _post_json(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _vllm_payload(model: str, prompt: str, max_tokens: int) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": max_tokens,
    }


def _ollama_payload(model: str, prompt: str, max_tokens: int) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0, "num_predict": max_tokens},
    }


def _extract_usage(provider: str, response: dict[str, Any]) -> tuple[int | None, int | None, int | None]:
    if provider == "vllm":
        usage = response.get("usage") or {}
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
        total_tokens = usage.get("total_tokens")
        return prompt_tokens, completion_tokens, total_tokens

    prompt_eval = response.get("prompt_eval_count")
    eval_count = response.get("eval_count")
    total = None
    if isinstance(prompt_eval, int) and isinstance(eval_count, int):
        total = prompt_eval + eval_count
    return prompt_eval, eval_count, total


def _run_one(
    provider: str,
    request_id: int,
    url: str,
    model: str,
    max_tokens: int,
    timeout: float,
) -> RequestMetric:
    prompt = PROMPTS[request_id % len(PROMPTS)]
    payload = (
        _vllm_payload(model, prompt, max_tokens)
        if provider == "vllm"
        else _ollama_payload(model, prompt, max_tokens)
    )
    started = time.perf_counter()
    try:
        response = _post_json(url, payload, timeout=timeout)
        latency_ms = int((time.perf_counter() - started) * 1000)
        prompt_tokens, completion_tokens, total_tokens = _extract_usage(provider, response)
        return RequestMetric(
            provider=provider,
            request_id=request_id,
            ok=True,
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )
    except HTTPError as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        body = exc.read().decode("utf-8", errors="replace")[:300]
        return RequestMetric(provider, request_id, False, latency_ms, error=f"HTTP {exc.code}: {body}")
    except (TimeoutError, URLError, OSError, json.JSONDecodeError) as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        return RequestMetric(provider, request_id, False, latency_ms, error=repr(exc))


def snapshot_gpu(label: str) -> GpuSnapshot:
    timestamp = datetime.now().isoformat(timespec="seconds")
    query = "name,memory.used,memory.total,utilization.gpu"
    try:
        proc = subprocess.run(
            [
                "nvidia-smi",
                f"--query-gpu={query}",
                "--format=csv,noheader,nounits",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        first = proc.stdout.strip().splitlines()[0]
        name, used, total, util = [part.strip() for part in first.split(",")]
        return GpuSnapshot(
            label=label,
            timestamp=timestamp,
            memory_used_mb=int(used),
            memory_total_mb=int(total),
            gpu_util_percent=int(util),
            name=name,
        )
    except Exception as exc:
        return GpuSnapshot(
            label=label,
            timestamp=timestamp,
            memory_used_mb=None,
            memory_total_mb=None,
            gpu_util_percent=None,
            name=None,
            error=repr(exc),
        )


def run_provider(
    provider: str,
    url: str,
    model: str,
    requests_count: int,
    concurrency: int,
    max_tokens: int,
    timeout: float,
) -> dict[str, Any]:
    print(f"\n[{provider}] model={model} url={url}")
    before_gpu = snapshot_gpu(f"{provider}_before")
    started = time.perf_counter()
    metrics: list[RequestMetric] = []

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(_run_one, provider, idx, url, model, max_tokens, timeout)
            for idx in range(requests_count)
        ]
        for future in as_completed(futures):
            metric = future.result()
            metrics.append(metric)
            status = "ok" if metric.ok else "err"
            print(f"  {status} request={metric.request_id} latency_ms={metric.latency_ms}")

    elapsed_s = time.perf_counter() - started
    after_gpu = snapshot_gpu(f"{provider}_after")
    ok_metrics = [metric for metric in metrics if metric.ok]
    latencies = [metric.latency_ms for metric in ok_metrics]
    total_tokens = sum(metric.total_tokens or 0 for metric in ok_metrics)

    summary = {
        "provider": provider,
        "model": model,
        "url": url,
        "requests": requests_count,
        "successful": len(ok_metrics),
        "failed": requests_count - len(ok_metrics),
        "concurrency": concurrency,
        "elapsed_s": round(elapsed_s, 3),
        "throughput_req_s": round(len(ok_metrics) / elapsed_s, 3) if elapsed_s else None,
        "tokens_s": round(total_tokens / elapsed_s, 3) if total_tokens and elapsed_s else None,
        "latency_ms_avg": round(sum(latencies) / len(latencies), 1) if latencies else None,
        "latency_ms_p50": _percentile(latencies, 50),
        "latency_ms_p95": _percentile(latencies, 95),
        "gpu_before": asdict(before_gpu),
        "gpu_after": asdict(after_gpu),
        "metrics": [asdict(metric) for metric in sorted(metrics, key=lambda item: item.request_id)],
    }
    print(
        f"  summary: ok={summary['successful']}/{requests_count} "
        f"req_s={summary['throughput_req_s']} p50={summary['latency_ms_p50']} "
        f"p95={summary['latency_ms_p95']} tokens_s={summary['tokens_s']}"
    )
    return summary


def write_reports(results: list[dict[str, Any]], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"vllm_benchmark_{stamp}.json"
    md_path = output_dir / f"vllm_benchmark_{stamp}.md"

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "results": results,
    }
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# vLLM Benchmark",
        "",
        "| Provider | Model | OK | Req/s | Tokens/s | Avg ms | p50 ms | p95 ms | VRAM before | VRAM after |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        before = result["gpu_before"].get("memory_used_mb")
        after = result["gpu_after"].get("memory_used_mb")
        lines.append(
            "| {provider} | {model} | {successful}/{requests} | {throughput_req_s} | "
            "{tokens_s} | {latency_ms_avg} | {latency_ms_p50} | {latency_ms_p95} | "
            "{before} | {after} |".format(
                before=before if before is not None else "n/a",
                after=after if after is not None else "n/a",
                **result,
            )
        )
    lines.extend(["", f"JSON: `{json_path}`"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark vLLM and/or Ollama local inference.")
    parser.add_argument("--providers", choices=["vllm", "ollama", "both"], default="both")
    parser.add_argument("--vllm-url", default="http://127.0.0.1:8000/v1/chat/completions")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434/api/chat")
    parser.add_argument("--model", default="deepseek-r1:8b", help="Default model for both providers.")
    parser.add_argument("--vllm-model", default=None, help="Override model name sent to vLLM.")
    parser.add_argument("--ollama-model", default=None, help="Override model name sent to Ollama.")
    parser.add_argument("--requests", type=int, default=8)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    providers = ["vllm", "ollama"] if args.providers == "both" else [args.providers]
    results: list[dict[str, Any]] = []

    for provider in providers:
        if provider == "vllm":
            results.append(
                run_provider(
                    provider="vllm",
                    url=args.vllm_url,
                    model=args.vllm_model or args.model,
                    requests_count=args.requests,
                    concurrency=args.concurrency,
                    max_tokens=args.max_tokens,
                    timeout=args.timeout,
                )
            )
        else:
            results.append(
                run_provider(
                    provider="ollama",
                    url=args.ollama_url,
                    model=args.ollama_model or args.model,
                    requests_count=args.requests,
                    concurrency=args.concurrency,
                    max_tokens=args.max_tokens,
                    timeout=args.timeout,
                )
            )

    json_path, md_path = write_reports(results, args.output_dir)
    print(f"\nReports written:\n  {json_path}\n  {md_path}")
    return 0 if any(result["successful"] for result in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
