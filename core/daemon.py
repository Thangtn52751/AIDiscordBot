"""Graceful shutdown and a shared lease for overlapping daemon deployments."""
import asyncio
import logging
import signal

logger = logging.getLogger(__name__)
LEASE_KEY = "aidiscordbot:gateway:leader"


async def run_bot(bot, token, redis_url="", stop=None):
    stop = stop or asyncio.Event()
    loop = asyncio.get_running_loop()
    signals = []
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, stop.set)
            signals.append(sig)
        except NotImplementedError:  # Windows uses asyncio.run's Ctrl+C handler.
            pass
    client = lease = None
    acquired = False
    tasks = []
    try:
        if redis_url:
            from redis.asyncio import Redis
            from redis.backoff import NoBackoff
            from redis.retry import Retry
            client = Redis.from_url(redis_url, socket_timeout=3,
                                    socket_connect_timeout=3,
                                    retry=Retry(NoBackoff(), 0))
            lease = client.lock(LEASE_KEY, timeout=90, thread_local=False)
            while not stop.is_set():
                acquired = await lease.acquire(blocking=False)
                if acquired:
                    break
                try:
                    await asyncio.wait_for(stop.wait(), timeout=5)
                except TimeoutError:
                    pass
        if stop.is_set():
            return

        async def renew():
            while True:
                await asyncio.sleep(20)
                if not await lease.extend(90, replace_ttl=True):
                    raise RuntimeError("Lost Discord gateway lease")

        tasks = [asyncio.create_task(bot.start(token)), asyncio.create_task(stop.wait())]
        if lease:
            tasks.append(asyncio.create_task(renew()))
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    finally:
        try:
            await bot.close()
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            if acquired:
                try:
                    await lease.release()
                except Exception:
                    logger.warning("Gateway lease release failed; it will expire automatically")
            if client:
                await client.aclose()
            for sig in signals:
                loop.remove_signal_handler(sig)
