from bottle import app, route, run, auth_basic
from daemonize import Daemonize
from transmission import *
import json
import ConfigParser

config = ConfigParser.ConfigParser()

if len(config.read('config')) < 1:
  print 'No config file.'
  exit(1)

class StripPathMiddleware(object):
  def __init__(self, app):
    self.app = app
  def __call__(self, e, h):
    e['PATH_INFO'] = e['PATH_INFO'].rstrip('/')
    return self.app(e,h)

def check(user, passwd):
  if user == config.get('transmission', 'user') and passwd == config.get('transmission', 'pass':
    return True
  return False

@route('/')
@auth_basic(check)
def index():
  return 'hello, friend!'

@route('/torrents')
@auth_basic(check)
def torrents():
  t = Transmission('localhost', 30446, '/transmission/rpc', config.get('transmission', 'user'), config.get('transmission', 'pass'))
  return json.dumps({'torrents': t.get_torrent_list([])})

def main():
  tobobrowse = app()
  tobobrowse = StripPathMiddleware(tobobrowse)
  run(host='chips.whatbox.ca', port=8000, app=tobobrowse)

daemon = Daemonize(app='tobobrowse', pid='/tmp/tobobrowse.pid', action=main)
daemon.start()
