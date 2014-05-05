from bottle import route, run, auth_basic
from daemonize import Daemonize

def check(user, passwd):
  if user == 'tobobo':
    return True
  return False

@route('/')
@auth_basic(check)
def index():
  return 'hello, friend!'

def main():
  run(host='chips.whatbox.ca', port=8000)

daemon = Daemonize(app='tobobrowse', pid='/tmp/tobobrowse.pid', action=main)
daemon.start()
