import asyncio
import logging
import threading
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks
from fastapi import Depends
from app.dto.process import ProcessRequest
from app.services.process_service import ProcessService, get_process_service

"""
Update: due to the rabbitmq addition, this endpoint has become not directly accessed by other microservices
should be deleted but for testing and debug purposes could be useful
"""

logger = logging.getLogger("uvicorn.error")

process_router = APIRouter()

def run_in_thread(target_function):
    """Decorator to run a function in a separate thread."""

    def run(*k, **kw):
        t = threading.Thread(target=target_function, args=k, kwargs=kw)
        t.start()
        return t

    return run

@run_in_thread
def process_files(process_service: ProcessService, request: ProcessRequest):
    """
    Little wrapper to run the whole process in
    """
    try:
        logger.info("Process received, starting...")
        asyncio.run(process_service.process_files(request))
    except Exception:
        logger.exception("General error executing process")

@process_router.post("/process", status_code=202)
async def process(background_tasks: BackgroundTasks,
                  process_service: Annotated[ProcessService, Depends(get_process_service)],
                  request: ProcessRequest):
    background_tasks.add_task(process_files,process_service, request)
    return {
        'message':"Queued"
    }