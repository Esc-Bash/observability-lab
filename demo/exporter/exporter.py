"""Sample exporter for topic 06: one metric of each type on :9200/metrics.

sample_jobs_processed_total   counter    jobs finished since start
sample_queue_size             gauge      jobs waiting right now
sample_job_duration_seconds   histogram  time per job, buckets 0.1 0.5 1 2 5
"""
import random
import time

from prometheus_client import (
    Counter, Gauge, Histogram, start_http_server, REGISTRY,
    GC_COLLECTOR, PLATFORM_COLLECTOR, PROCESS_COLLECTOR, disable_created_metrics,
)

disable_created_metrics()
for c in (GC_COLLECTOR, PLATFORM_COLLECTOR, PROCESS_COLLECTOR):
    REGISTRY.unregister(c)

JOBS = Counter("sample_jobs_processed_total", "Total number of jobs processed.")
QUEUE = Gauge("sample_queue_size", "Number of jobs waiting in the queue.")
DURATION = Histogram("sample_job_duration_seconds", "Time taken to process one job.",
                     buckets=(0.1, 0.5, 1, 2, 5))


def main():
    start_http_server(9200)
    print("sample-exporter listening on :9200/metrics", flush=True)
    queue = 5
    while True:
        queue = max(0, queue + random.randint(-2, 3))
        QUEUE.set(queue)
        took = random.choice([0.05, 0.2, 0.3, 0.7, 1.5, 3.0]) * random.uniform(0.8, 1.2)
        DURATION.observe(took)
        JOBS.inc()
        if queue:
            queue -= 1
        time.sleep(1)


if __name__ == "__main__":
    main()
