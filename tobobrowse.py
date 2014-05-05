from bottle import app, route, run, auth_basic
from transmission import *
import json
import ConfigParser
from largestfile import largestfile
from os import path
import urllib
import urlparse

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

def user_auth(user, passwd):
  if user == config.get('transmission', 'user') and passwd == config.get('transmission', 'passwd'):
    return True
  return False

def serve():

  t = Transmission('localhost', 30446, '/transmission/rpc', config.get('transmission', 'user'), config.get('transmission', 'passwd'))

  @route('/')
  @auth_basic(user_auth)
  def index():
    return 'hello, friend!'

  @route('/torrents')
  @auth_basic(user_auth)
  def torrents():
    return json.dumps({'torrents': t.get_torrent_list([])})

  @route('/torrents/<name>')
  @auth_basic(user_auth)
  def get_key_file(name):
    torrents = t.get_torrent_list([])
    for torrent in torrents:
      if torrent['name'] == name:
        main_file_path = largestfile(path.join(torrent['downloadDir'], torrent['name']))[1]
        partial_file_path = main_file_path.split(torrent['downloadDir'])[-1]
        quoted_partial_path = urllib.quote(partial_file_path)
        main_file_url = urlparse.urljoin(config.get('transmission', 'http_base'), quoted_partial_path)
        torrent['downloadURL'] = main_file_url
        return json.dumps({'torrent': torrent})

  tobobrowse = app()
  tobobrowse = StripPathMiddleware(tobobrowse)
  run(host='chips.whatbox.ca', port=8000, app=tobobrowse)

if __name__ == '__main__':
  serve()
