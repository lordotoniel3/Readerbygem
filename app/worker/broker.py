import logging
from typing import Annotated

from fastapi.params import Depends
from faststream.broker.fastapi.context import Context
from faststream.exceptions import RejectMessage
from faststream.rabbit import RabbitQueue, RabbitExchange, ExchangeType
from faststream.rabbit.fastapi import RabbitRouter

from app.dependencies import RMQSettings
from app.dto.process import ProcessRequest
from app.services.process_service import ProcessService, get_process_service

config = RMQSettings()
logger = logging.getLogger("uvicorn.error")
rmq_router = RabbitRouter(f"amqp://{config.rmq_user}:{config.rmq_pass}@{config.rmq_host}:{config.rmq_port}")
exchange = RabbitExchange(
    "bloocheck",
    durable=True,
    type=ExchangeType.TOPIC
)
queue = RabbitQueue(
    "bloocheck.docs",
    routing_key="process.init",
    robust=True,
    durable=True,
)


@rmq_router.subscriber(queue=queue, exchange=exchange)
#@rmq_router.publisher(routing_key="entity.store", exchange=exchange)
async def process_docs(req: ProcessRequest, process_service: Annotated[ProcessService, Depends(get_process_service)], tenant: str = Context("message.headers.tenant", default=None)):
    # The tenant is received here, the process is agnostic to the tenant, that doesn't matter, the thing is
    # that the result HAS TO BE tied to a header so the orchestator has knowledge of the process which is tied to
    if not tenant:
        logger.error("Message dont have tenant header, cannot proceed")
        raise RejectMessage()
    entities = await process_service.process_files(req)
    await rmq_router.broker.publish(
        message=entities,
        exchange=exchange,
        routing_key="entity.store",
        headers={"tenant": tenant}
    )