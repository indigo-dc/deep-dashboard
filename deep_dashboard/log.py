from oslo_config import cfg
from oslo_log import log

CONF = cfg.CONF
LOG = log.getLogger("deep_dashboard")


def getLogger(name):
    return log.getLogger(name)
