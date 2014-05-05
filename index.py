from bottle import route, run, auth_basic
from daemonize import Daemonize
from transmission import *

def check(user, passwd):
  if user == 'tobobo':
    return True
  return False

@route('/')
@auth_basic(check)
def index():
  return 'hello, friend!'

@route('/torrents')
@auth_basic(check)
def torrents():
  t = Transmission('localhost', 30446, '/transmission/rpc', 'tobobo')
  return t.get_torrent_list([])

def main():
  run(host='chips.whatbox.ca', port=8000)

daemon = Daemonize(app='tobobrowse', pid='/tmp/tobobrowse.pid', action=main)
daemon.start()
