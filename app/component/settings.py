import os
from configobj import ConfigObj
import logging
import urllib


dir_path = os.path.dirname(os.path.realpath(__file__))
CONFIG = ConfigObj(os.path.join(dir_path, "config.ini"))
environ = os.getenv("environ", CONFIG["config"]["environ"])

EVENT_STORE_URL = os.getenv("event_store_url", CONFIG[environ]["event_store_url"])
EVENT_STORE_HTTP_PORT = int(os.getenv("event_store_http_port", config[environ]["event_store_http_port"]))
EVENT_STORE_TCP_PORT = int(os.getenv("event_store_tcp_port", config[environ]["event_store_tcp_port"]))
EVENT_STORE_USER = os.getenv("event_store_user", config[environ]["event_store_user"])
EVENT_STORE_PASS = os.getenv("event_store_pass", config[environ]["event_store_pass"])

MONGO_URL = os.getenv("mongo_url", config[environ]["mongo_url"])
MONGO_PORT = int(os.getenv("mongo_port", config[environ]["mongo_port"]))
MONGO_USER = urllib.parse.quote_plus(os.getenv("mongo_user", config[environ]["mongo_user"]))
MONGO_PASS = urllib.parse.quote_plus(os.getenv("mongo_pass", config[environ]["mongo_pass"]))

LOGGER_LEVEL = int(os.getenv("logger_level", config[environ]["logger_level"]))
LOGGER_FORMAT = '%(asctime)s [%(name)s] %(message)s'

V_MA = CONFIG["version"]["major"]
V_MI = CONFIG["version"]["minor"]
V_RE = CONFIG["version"]["revision"]
V_DATE = CONFIG["version"]["date"]
CODENAME = CONFIG["version"]["codename"]

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
