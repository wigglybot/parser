from .settings import *
import asyncio
from photonpump import connect, exceptions
import json
import functools
import uuid
import requests


def run_in_executor(f):
    """
    wrap a blocking (non-asyncio) func so it is executed in our loop
    """
    @functools.wraps(f)
    def inner(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(None, functools.partial(f, *args, **kwargs))
    return inner


@run_in_executor
def post_to_dialogue_stream(event_id, result):
    headers = {
        "ES-EventType": "text_parsed",
        "ES-EventId": str(uuid.uuid1())
    }
    requests.post(
        "http://%s:%s/streams/dialogue" % (EVENT_STORE_URL, EVENT_STORE_HTTP_PORT),
        headers=headers,
        json={"event_id": event_id, "command": result["command"], "args": result["args"]}
    )


async def create_subscription(subscription_name, stream_name, conn):
    await conn.create_subscription(subscription_name, stream_name)


def parse_text(event_text):
    text_for_chat = event_text.split(' ', 1)[1]  # drop the bot's ID
    t_list = list(text_for_chat.split(' ', ))  # make a list from the remainder
    return {"command": t_list[0], "args": t_list[1:]}


async def parse_fn():
    _loop = asyncio.get_event_loop()
    async with connect(
            host=EVENT_STORE_URL,
            port=EVENT_STORE_TCP_PORT,
            username=EVENT_STORE_USER,
            password=EVENT_STORE_PASS,
            loop=_loop
    ) as c:
        await c.connect()
        try:
            await create_subscription("parser", "dialogue", c)
        except exceptions.SubscriptionCreationFailed as e:
            if e.message.find("already exists."):
                log.info("Parser dialogue subscription found.")
            else:
                raise e
        dialogue_stream = await c.connect_subscription("parser", "dialogue")
        async for event in dialogue_stream.events:
            if event.type == "app_mention":
                event_obj = json.loads(event.event.data)
                log.debug("parse_fn() responding to: %s" % json.dumps(event_obj))
                try:
                    try:
                        result = parse_text(event_obj["event"]["text"])
                        await post_to_dialogue_stream(event_obj["event_id"], result)
                        await dialogue_stream.ack(event)
                    except Exception as e:
                        print(e)
                        pass
                except Exception as e:
                    log.exception(e)
            else:
                await dialogue_stream.ack(event)


if __name__ == "__main__":
    asyncio.set_event_loop(asyncio.new_event_loop())
    mainloop = asyncio.get_event_loop()
    mainloop.run_until_complete(parse_fn())
