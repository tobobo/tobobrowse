from bottle import route, run, auth_basic
from daemonize import Daemonize

def check(user, passwd):
  if user == 'tobobo':
    return True
  return False

@route('/')
def index():
  return 'hello, chum'

def main():
  run(host='chips.whatbox.ca', port=8000)

daemon = Daemonize(app='tobobrowse', pid='/tmp/tobobrowse.pid', action=main)
daemon.start()
