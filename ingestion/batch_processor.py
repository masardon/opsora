"""
Batch Processor

Batch processing for historical data and scheduled analysis.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from ingestion.event_validator import EventValidator, EventEnricher, EventType


class BatchSchedule(str, Enum):
    """Batch processing schedules"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ADHOC = "adhoc"


@dataclass
class BatchJob:
    """A batch processing job"""
    job_id: str
    name: str
    schedule: BatchSchedule
    handler: Callable
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    running: bool = False


class BatchProcessor:
    """Processes batch jobs on schedules"""

    def __init__(
        self,
        validator: Optional[EventValidator] = None,
        enricher: Optional[EventEnricher] = None,
        max_concurrent_jobs: int = 5,
    ):
        self.validator = validator or EventValidator()
        self.enricher = enricher or EventEnricher()

        self.max_concurrent_jobs = max_concurrent_jobs
        self._jobs: Dict[str, BatchJob] = {}
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None

        # Metrics
        self._metrics = {
            "jobs_completed": 0,
            "jobs_failed": 0,
            "events_processed": 0,
            "processing_time_seconds": 0,
        }

    def register_job(
        self,
        job_id: str,
        name: str,
        schedule: BatchSchedule,
        handler: Callable,
        enabled: bool = True,
    ) -> BatchJob:
        """Register a batch job"""

        job = BatchJob(
            job_id=job_id,
            name=name,
            schedule=schedule,
            handler=handler,
            enabled=enabled,
            next_run=self._calculate_next_run(schedule),
        )

        self._jobs[job_id] = job
        return job

    def _calculate_next_run(self, schedule: BatchSchedule) -> datetime:
        """Calculate next run time for a schedule"""

        now = datetime.utcnow()

        if schedule == BatchSchedule.HOURLY:
            return now + timedelta(hours=1)
        elif schedule == BatchSchedule.DAILY:
            return now + timedelta(days=1)
        elif schedule == BatchSchedule.WEEKLY:
            return now + timedelta(weeks=1)
        elif schedule == BatchSchedule.MONTHLY:
            return now + timedelta(days=30)
        else:
            return now  # ADHOC runs immediately

    async def start(self):
        """Start batch processor"""

        if self._running:
            return

        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

    async def stop(self):
        """Stop batch processor"""

        self._running = False

        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

    async def _scheduler_loop(self):
        """Main scheduler loop"""

        while self._running:
            try:
                now = datetime.utcnow()

                # Check for jobs to run
                jobs_to_run = []

                for job in self._jobs.values():
                    if (job.enabled and
                        job.next_run and
                        job.next_run <= now and
                        not job.running):

                        jobs_to_run.append(job)

                # Run jobs (limited concurrency)
                if jobs_to_run:
                    await self._run_jobs(jobs_to_run)

                # Sleep until next check
                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                print(f"Scheduler error: {e}")
                await asyncio.sleep(60)

    async def _run_jobs(self, jobs: List[BatchJob]):
        """Run multiple jobs with limited concurrency"""

        semaphore = asyncio.Semaphore(self.max_concurrent_jobs)

        async def run_with_limit(job: BatchJob):
            async with semaphore:
                return await self._run_job(job)

        results = await asyncio.gather(
            *[run_with_limit(job) for job in jobs],
            return_exceptions=True,
        )

        for job, result in zip(jobs, results):
            if isinstance(result, Exception):
                self._metrics["jobs_failed"] += 1
                print(f"Job {job.job_id} failed: {result}")
            else:
                self._metrics["jobs_completed"] += 1

    async def _run_job(self, job: BatchJob) -> Any:
        """Run a single job"""

        job.running = True
        job.last_run = datetime.utcnow()

        try:
            result = await job.handler(self)
            return result

        finally:
            job.running = False
            job.next_run = self._calculate_next_run(job.schedule)

    async def run_job_now(self, job_id: str) -> Any:
        """Run a job immediately (adhoc)"""

        job = self._jobs.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        return await self._run_job(job)

    async def process_batch_events(
        self,
        events: List[Dict[str, Any]],
        event_type: EventType
    ) -> Dict[str, Any]:
        """Process a batch of events"""

        start_time = datetime.utcnow()

        # Validate batch
        valid, invalid = self.validator.validate_batch(events, event_type)

        # Enrich valid events
        enriched = []
        for event in valid:
            enriched_event = await self.enricher.enrich_event(event, event_type)
            enriched.append(enriched_event)

        processing_time = (datetime.utcnow() - start_time).total_seconds()

        # Update metrics
        self._metrics["events_processed"] += len(enriched)
        self._metrics["processing_time_seconds"] += processing_time

        return {
            "processed": len(enriched),
            "invalid": len(invalid),
            "events": enriched,
            "invalid_events": invalid,
            "processing_time_seconds": processing_time,
        }

    async def ingest_from_source(
        self,
        source_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Ingest events from an external source"""

        source_type = source_config.get("type")

        if source_type == "csv":
            return await self._ingest_csv(source_config)
        elif source_type == "api":
            return await self._ingest_api(source_config)
        elif source_type == "database":
            return await self._ingest_database(source_config)
        else:
            raise ValueError(f"Unknown source type: {source_type}")

    async def _ingest_csv(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Ingest from CSV file"""

        import pandas as pd
        from pathlib import Path

        file_path = config.get("path")
        event_type = EventType(config.get("event_type", "system"))

        if not file_path:
            raise ValueError("CSV path is required")

        # Read CSV
        df = pd.read_csv(file_path)

        # Convert to records
        events = df.to_dict("records")

        # Process batch
        return await self.process_batch_events(events, event_type)

    async def _ingest_api(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Ingest from API endpoint"""

        import httpx

        url = config.get("url")
        event_type = EventType(config.get("event_type", "system"))

        if not url:
            raise ValueError("API URL is required")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=config.get("headers", {}),
                timeout=30.0,
            )
            response.raise_for_status()

            events = response.json().get("data", [])

            if not isinstance(events, list):
                events = [events]

            return await self.process_batch_events(events, event_type)

    async def _ingest_database(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Ingest from database query"""

        # Placeholder for database ingestion
        # In production, this would connect to SQL/NoSQL databases

        return {
            "processed": 0,
            "invalid": 0,
            "events": [],
            "note": "Database ingestion not implemented",
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get batch processor metrics"""

        jobs_status = {}

        for job_id, job in self._jobs.items():
            jobs_status[job_id] = {
                "name": job.name,
                "enabled": job.enabled,
                "running": job.running,
                "last_run": job.last_run.isoformat() if job.last_run else None,
                "next_run": job.next_run.isoformat() if job.next_run else None,
            }

        return {
            **self._metrics,
            "jobs": jobs_status,
            "total_jobs": len(self._jobs),
            "active_jobs": sum(1 for j in self._jobs.values() if j.enabled),
        }
