import sys
if 'threading' in sys.modules:
    del sys.modules['threading']
from daemonize import Daemonize
from tobobrowse import serve

daemon = Daemonize(app='tobobrowse', pid='/tmp/tobobrowse.pid', action=serve)
daemon.start()
