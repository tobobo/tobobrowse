from daemonize import Daemonize
from tobobrowse import serve

daemon = Daemonize(app='tobobrowse', pid='/tmp/tobobrowse.pid', action=serve)
daemon.start()
