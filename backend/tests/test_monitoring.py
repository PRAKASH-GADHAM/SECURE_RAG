"""Tests for Phase 10: Observability, Evaluation, and Production Monitoring."""

import pytest
import time
from app.services.monitoring.metrics import metrics_collector, LatencyMetrics, timer
from app.services.monitoring.tracing import Tracer, Trace, TraceSpan, tracer
from app.services.monitoring.profiler import Profiler, CProfiler, profiler
from app.services.monitoring.benchmark import BenchmarkRunner, benchmark_runner
from app.services.monitoring.evaluator import Evaluator, evaluator
from app.services.monitoring.dashboard import Dashboard, dashboard
from app.services.evaluation.retrieval_metrics import RetrievalMetrics, retrieval_metrics
from app.services.evaluation.reranking_metrics import RerankingMetrics, reranking_metrics
from app.services.evaluation.hallucination_metrics import HallucinationMetrics, hallucination_metrics
from app.services.evaluation.citation_metrics import CitationMetrics, citation_metrics
from app.services.evaluation.latency_metrics import LatencyMetricsCalculator, latency_metrics_calculator


# ==================== Metrics Tests ====================

class TestMetricsCollector:
    """Tests for MetricsCollector."""

    def test_increment_counter(self):
        metrics_collector.reset()
        metrics_collector.increment_counter("test_counter", 5)
        metrics = metrics_collector.get_metric("test_counter")
        assert metrics == 5

    def test_increment_counter_default(self):
        metrics_collector.reset()
        metrics_collector.increment_counter("test_default")
        assert metrics_collector.get_metric("test_default") == 1

    def test_decrement_counter(self):
        metrics_collector.reset()
        metrics_collector.increment_counter("test_dec", 10)
        metrics_collector.decrement_counter("test_dec", 3)
        assert metrics_collector.get_metric("test_dec") == 7

    def test_set_gauge(self):
        metrics_collector.reset()
        metrics_collector.set_gauge("test_gauge", 42.5)
        assert metrics_collector.get_metric("test_gauge") == 42.5

    def test_record_latency(self):
        metrics_collector.reset()
        metrics_collector.record_latency("test_component", 100.0)
        metrics_collector.record_latency("test_component", 200.0)
        metrics = metrics_collector.get_latency_metrics("test_component")
        assert metrics["count"] == 2
        assert metrics["average"] == 150.0

    def test_reset(self):
        metrics_collector.increment_counter("to_reset")
        metrics_collector.reset()
        assert metrics_collector.get_metric("to_reset") == 0

    def test_get_all_metrics(self):
        metrics_collector.reset()
        metrics_collector.increment_counter("all_test")
        all_metrics = metrics_collector.get_all_metrics()
        assert "counters" in all_metrics
        assert "gauges" in all_metrics
        assert "latency" in all_metrics


class TestTimerContext:
    """Tests for TimerContext."""

    def test_timer_records_latency(self):
        metrics_collector.reset()
        with timer("timer_test"):
            time.sleep(0.01)
        metrics = metrics_collector.get_latency_metrics("timer_test")
        assert metrics["count"] == 1
        assert metrics["min"] >= 5  # At least 5ms

    def test_timer_records_error(self):
        metrics_collector.reset()
        try:
            with timer("timer_error"):
                raise ValueError("test error")
        except ValueError:
            pass
        metrics = metrics_collector.get_latency_metrics("timer_error")
        assert metrics["count"] == 1


# ==================== Tracing Tests ====================

class TestTracer:
    """Tests for Tracer."""

    def test_start_trace(self):
        trace = tracer.start_trace("test_trace")
        assert trace is not None
        assert trace.operation == "test_trace"
        assert trace.trace_id is not None

    def test_start_span(self):
        trace = tracer.start_trace("parent")
        span = tracer.start_span("child")
        assert span is not None
        assert span.parent_id == trace.span_id

    def test_end_span(self):
        tracer.start_trace("to_end")
        span = tracer.start_span("ending")
        span.end()
        assert span.duration_ms is not None

    def test_get_current_trace(self):
        trace = tracer.start_trace("current")
        current = tracer.get_current_trace()
        assert current is not None
        assert current.trace_id == trace.trace_id


# ==================== Profiler Tests ====================

class TestProfiler:
    """Tests for Profiler."""

    def test_start_stop(self):
        profiler.start()
        assert profiler.is_running
        profiler.stop()
        assert not profiler.is_running

    def test_get_stats(self):
        profiler.start()
        time.sleep(0.01)
        profiler.stop()
        stats = profiler.get_stats()
        assert "cpu_time" in stats
        assert "wall_time" in stats


# ==================== Evaluation Metrics Tests ====================

class TestRetrievalMetrics:
    """Tests for RetrievalMetrics."""

    def test_precision_at_k(self):
        retrieved = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        relevant = ["doc1", "doc3", "doc5"]
        precision = retrieval_metrics.precision_at_k(retrieved, relevant, 5)
        assert precision == 0.6

    def test_recall_at_k(self):
        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        recall = retrieval_metrics.recall_at_k(retrieved, relevant, 5)
        assert recall == 0.6

    def test_mrr(self):
        retrieved = ["doc2", "doc1", "doc3"]
        relevant = ["doc1"]
        mrr = retrieval_metrics.mean_reciprocal_rank(retrieved, relevant)
        assert mrr == 0.5

    def test_ndcg(self):
        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc1", "doc2"]
        ndcg = retrieval_metrics.normalized_discounted_cumulative_gain(retrieved, relevant, 3)
        assert ndcg > 0


class TestRerankingMetrics:
    """Tests for RerankingMetrics."""

    def test_calculate_improvement(self):
        pre_ranked = ["doc3", "doc1", "doc2"]
        post_ranked = ["doc1", "doc2", "doc3"]
        relevant = ["doc1", "doc2"]
        improvement = reranking_metrics.calculate_improvement(pre_ranked, post_ranked, relevant)
        assert "position_changes" in improvement
        assert "improvement_rate" in improvement


class TestHallucinationMetrics:
    """Tests for HallucinationMetrics."""

    def test_calculate_groundedness(self):
        response = "The capital of France is Paris."
        context = "Paris is the capital of France."
        groundedness = hallucination_metrics.calculate_groundedness(response, context)
        assert groundedness > 0.5

    def test_calculate_all_metrics(self):
        response = "Python is a programming language created by Guido van Rossum."
        context = "Python was created by Guido van Rossum in 1991."
        metrics = hallucination_metrics.calculate_all_metrics(response, context)
        assert "groundedness_score" in metrics
        assert "confidence_score" in metrics


class TestCitationMetrics:
    """Tests for CitationMetrics."""

    def test_calculate_coverage(self):
        statements = ["Statement 1", "Statement 2", "Statement 3"]
        citations = ["Source 1", "Source 2"]
        coverage = citation_metrics.calculate_coverage(statements, citations)
        assert coverage == 2 / 3

    def test_calculate_accuracy(self):
        citations = ["Source 1", "Source 2"]
        valid_sources = ["Source 1", "Source 2", "Source 3"]
        accuracy = citation_metrics.calculate_accuracy(citations, valid_sources)
        assert accuracy == 1.0


class TestLatencyMetricsCalculator:
    """Tests for LatencyMetricsCalculator."""

    def test_calculate_percentiles(self):
        latencies = [100, 200, 300, 400, 500]
        percentiles = latency_metrics_calculator.calculate_percentiles(latencies)
        assert percentiles["p50"] == 300
        assert percentiles["p95"] == 500
        assert percentiles["average"] == 300.0

    def test_empty_latencies(self):
        percentiles = latency_metrics_calculator.calculate_percentiles([])
        assert percentiles["count"] == 0
        assert percentiles["p50"] == 0.0


# ==================== Benchmark Tests ====================

class TestBenchmarkRunner:
    """Tests for BenchmarkRunner."""

    def test_run_benchmark(self):
        def dummy_func():
            time.sleep(0.001)

        result = benchmark_runner.run_benchmark("test_bench", dummy_func, iterations=5, warmup=1)
        assert result.iterations == 5
        assert result.average_time_ms > 0

    def test_get_benchmark(self):
        def dummy():
            pass

        benchmark_runner.run_benchmark("get_test", dummy, iterations=3, warmup=1)
        result = benchmark_runner.get_benchmark("get_test")
        assert result is not None

    def test_generate_report(self):
        report = benchmark_runner.generate_report()
        assert isinstance(report, str)


# ==================== Dashboard Tests ====================

class TestDashboard:
    """Tests for Dashboard."""

    def test_get_metrics_summary(self):
        summary = dashboard.get_metrics_summary()
        assert "timestamp" in summary
        assert "metrics" in summary

    def test_get_latency_dashboard(self):
        latency_dash = dashboard.get_latency_dashboard()
        assert "timestamp" in latency_dash
        assert "latency" in latency_dash

    def test_get_performance_dashboard(self):
        perf_dash = dashboard.get_performance_dashboard()
        assert "timestamp" in perf_dash


# ==================== Evaluator Tests ====================

class TestEvaluator:
    """Tests for Evaluator."""

    def test_evaluate_retrieval(self):
        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc1", "doc2"]
        metrics = evaluator.evaluate_retrieval(retrieved, relevant, 3)
        assert "precision_at_3" in metrics

    def test_evaluate_hallucination(self):
        response = "Python is a language."
        context = "Python is a programming language."
        metrics = evaluator.evaluate_hallucination(response, context)
        assert "groundedness_score" in metrics

    def test_evaluate_citation(self):
        statements = ["Statement 1"]
        citations = ["Source 1"]
        valid_sources = ["Source 1"]
        metrics = evaluator.evaluate_citation(statements, citations, valid_sources)
        assert "coverage" in metrics


# ==================== API Endpoint Tests ====================

class TestMonitoringAPI:
    """Tests for Monitoring API endpoints."""

    def test_get_metrics(self):
        from app.api.v1.monitoring import get_metrics
        result = get_metrics()
        assert result["status"] == "success"

    def test_get_latency_metrics(self):
        from app.api.v1.monitoring import get_latency_metrics
        result = get_latency_metrics()
        assert result["status"] == "success"

    def test_get_benchmarks(self):
        from app.api.v1.monitoring import get_benchmarks
        result = get_benchmarks()
        assert result["status"] == "success"

    def test_get_dashboard(self):
        from app.api.v1.monitoring import get_dashboard
        result = get_dashboard()
        assert result["status"] == "success"

    def test_reset_metrics(self):
        from app.api.v1.monitoring import reset_metrics
        result = reset_metrics()
        assert result["status"] == "success"
