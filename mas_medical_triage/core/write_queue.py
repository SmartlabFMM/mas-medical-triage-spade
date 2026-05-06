"""
core/write_queue.py — WriteQueue async avec priorité compatible SheetsDB.
"""
from __future__ import annotations
import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class Priority(int, Enum):
    CRITICAL = 1
    HIGH     = 2
    NORMAL   = 3
    LOW      = 4

@dataclass(order=True)
class WriteTask:
    priority:   int
    data:       dict = field(compare=False, default_factory=dict)
    task_type:  str  = field(compare=False, default="update_resource")
    patient_id: str  = field(compare=False, default="")
    agent:      str  = field(compare=False, default="")

class WriteQueue:
    def __init__(self, db):
        self._queue    = asyncio.PriorityQueue()
        self._lock     = asyncio.Lock()
        self._db       = db
        self._running  = False
        self._processed= 0
        self._failed   = 0

    async def enqueue(self, data: dict, task_type: str = "update_resource",
                      priority: Priority = Priority.NORMAL,
                      patient_id: str = "", agent: str = "") -> None:
        task = WriteTask(priority=priority.value, data=data,
                         task_type=task_type, patient_id=patient_id, agent=agent)
        await self._queue.put(task)

    async def start(self) -> None:
        self._running = True
        await self._consume()

    def stop(self) -> None:
        self._running = False

    @property
    def stats(self) -> dict:
        return {"processed": self._processed, "failed": self._failed,
                "pending": self._queue.qsize()}

    async def _consume(self) -> None:
        while self._running:
            try:
                task = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await self._process(task)
                self._queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Erreur consommateur : {e}")
                self._failed += 1

    async def _process(self, task: WriteTask) -> None:
        if self._db is None:
            return
        async with self._lock:
            try:
                loop = asyncio.get_event_loop()
                if task.task_type == "update_resource":
                    await loop.run_in_executor(None, self._db.update_resource, task.data)
                elif task.task_type == "append_log":
                    await loop.run_in_executor(
                        None, self._db.log,
                        task.agent, task.data.get("action", ""),
                        task.data.get("details", ""),
                        task.patient_id, task.data.get("niveau", "INFO"))
                self._processed += 1
                logger.info(f"[WriteQueue] #{self._processed} {task.task_type}")
            except Exception as e:
                self._failed += 1
                logger.error(f"Echec tache : {e}")
