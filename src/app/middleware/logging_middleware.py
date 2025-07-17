import time
import logging

logger = logging.getLogger(__name__)


async def log_requests_middleware(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(
        f"{request.method} {request.url} - {response.status_code} "
        f"- {process_time: .3f}s"
    )
    return response
