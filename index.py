from bottle import app, route, run, auth_basic
from daemonize import Daemonize
from transmission import *
import json

class StripPathMiddleware(object):
  def __init__(self, app):
    self.app = app
  def __call__(self, e, h):
    e['PATH_INFO'] = e['PATH_INFO'].rstrip('/')
    return self.app(e,h)

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
  t = Transmission('localhost', 30446, '/transmission/rpc', 'tobobo', '')
  return json.dumps({'torrents': t.get_torrent_list([])})

def main():
  tobobrowse = bottle.app()
  tobobrowse = StripPathMiddleware(tobobrowse)
  run(host='chips.whatbox.ca', port=8000, app=tobobrowse)

daemon = Daemonize(app='tobobrowse', pid='/tmp/tobobrowse.pid', action=main)
daemon.start()
