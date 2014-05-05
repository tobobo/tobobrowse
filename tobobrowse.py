from bottle import app, route, run, auth_basic
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

def user_auth(user, pass):
  if user == config.get('transmission', 'user') and pass == config.get('transmission', 'pass'):
    return True
  return False

def serve():

  t = Transmission('localhost', 30446, '/transmission/rpc', config.get('transmission', 'user'), config.get('transmission', 'pass'))

  @route('/')
  @auth_basic(user_auth)
  def index():
    return 'hello, friend!'

  @route('/torrents')
  @auth_basic(user_auth)
  def torrents():
    return json.dumps({'torrents': t.get_torrent_list([])})

  @route('/torrents/<name>/file')
  @auth_basic(user_auth)
  def get_key_file(name):
    torrents = t.get_torrent_list()
    for torrent in torrents:
      if torrent.name == name
      return json.dumps({'torrent': torrent})

  tobobrowse = app()
  tobobrowse = StripPathMiddleware(tobobrowse)
  run(host='chips.whatbox.ca', port=8000, app=tobobrowse)

if __name__ == '__main__':
  serve()
