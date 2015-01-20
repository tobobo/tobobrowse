from daemonize import Daemonize, logging
from tobobrowse import serve

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.propagate = False
fh = logging.FileHandler('./log/server.log', 'w')
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)
keep_fds = [fh.stream.fileno()]

daemon = Daemonize(app='tobobrowse', pid='/tmp/tobobrowse.pid', action=serve, keep_fds=keep_fds)
daemon.start()
