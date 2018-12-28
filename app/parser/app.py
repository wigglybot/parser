# todo: discard events which are not of type response
# todo: post an event to dialogue describing result of attempting to post to slack

import asyncio
from photonpump import connect, exceptions
import json
import os
import logging
import functools
from configobj import ConfigObj
import uuid
import requests

dir_path = os.path.dirname(os.path.realpath(__file__))
CONFIG = ConfigObj(os.path.join(dir_path, "config.ini"))
ENVIRON = os.getenv("ENVIRON", CONFIG["config"]["ENVIRON"])

EVENT_STORE_URL = os.getenv("EVENT_STORE_URL", CONFIG[ENVIRON]["EVENT_STORE_URL"])
EVENT_STORE_HTTP_PORT = int(os.getenv("EVENT_STORE_HTTP_PORT", CONFIG[ENVIRON]["EVENT_STORE_HTTP_PORT"]))
EVENT_STORE_TCP_PORT = int(os.getenv("EVENT_STORE_TCP_PORT", CONFIG[ENVIRON]["EVENT_STORE_TCP_PORT"]))
EVENT_STORE_USER = os.getenv("EVENT_STORE_USER", CONFIG[ENVIRON]["EVENT_STORE_USER"])
EVENT_STORE_PASS = os.getenv("EVENT_STORE_PASS", CONFIG[ENVIRON]["EVENT_STORE_PASS"])

LOGGER_LEVEL = int(os.getenv("LOGGER_LEVEL", CONFIG[ENVIRON]["LOGGER_LEVEL"]))
LOGGER_FORMAT = '%(asctime)s [%(name)s] %(message)s'

V_MA = CONFIG["version"]["MAJOR"]
V_MI = CONFIG["version"]["MINOR"]
V_RE = CONFIG["version"]["REVISION"]
V_DATE = CONFIG["version"]["DATE"]
CODENAME = CONFIG["version"]["CODENAME"]

logging.basicConfig(format=LOGGER_FORMAT, datefmt='[%H:%M:%S]')
log = logging.getLogger("parser")

"""
CRITICAL 50
ERROR    40
WARNING  30
INFO     20
DEBUG    10
NOTSET    0
"""
log.setLevel(LOGGER_LEVEL)


def version_fancy():
    return ''.join((
        "\n",
        " (  (                       (         (           )", "\n",
        " )\))(   ' (   (  (  (  (   )\ (    ( )\       ( /(", "\n",
        "((_)()\ )  )\  )\))( )\))( ((_))\ ) )((_)  (   )\())", "\n",
        "_(())\_)()((_)((_))\((_))\  _ (()/(((_)_   )\ (_))/", "\n",
        "\ \((_)/ / (_) (()(_)(()(_)| | )(_))| _ ) ((_)| |_ ",
        "         version: {0}".format("v%s.%s.%s" % (V_MA, V_MI, V_RE)), "\n",
        " \ \/\/ /  | |/ _` |/ _` | | || || || _ \/ _ \|  _|",
        "       code name: {0}".format(CODENAME), "\n",
        "  \_/\_/   |_|\__, |\__, | |_| \_, ||___/\___/ \__|",
        "    release date: {0}".format(V_DATE), "\n",
        "              |___/ |___/      |__/", "\n"
    ))


log.info(version_fancy())


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
