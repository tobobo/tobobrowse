from bottle import app, route, run, auth_basic
from transmission import *
import json
import ConfigParser
from largestfile import largestfile
from os import path
import urllib
import urlparse
import tarfile

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

def make_tarfile(output_filename, source_dir):
  with tarfile.open(output_filename, "w:gz") as tar:
    tar.add(source_dir, arcname=os.path.basename(source_dir))
  return output_filename

def torrent_folder_path(torrent):
  return path.join(torrent['downloadDir'], torrent['name'])

def path_to_url(path):
  partial_path = path.split(torrent['downloadDir'])[-1]
  quoted_partial_path = urllib.quote(partial_path)
  return urlparse.urljoin(config.get('transmission', 'http_base'), quoted_partial_path)

def get_file_url(torrent):
  main_file_path = largestfile(torrent_folder_path(torrent))
  return path_to_url(main_file_path)

def get_torrent_by_name(name):
  torrents = t.get_torrent_list([])
  for torrent in torrents:
    if torrent['name'] == name:
      return torrent

# def get_file_url(torrent):
#   main_file_path

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
    torrent = get_torrent_by_name(name)
    if torrent:
      return json.dumps({'torrent': torrent})
    else:
      return json.dumps({'meta': 'Torrent not found'})

  tobobrowse = app()
  tobobrowse = StripPathMiddleware(tobobrowse)
  run(host='chips.whatbox.ca', port=8000, app=tobobrowse)

if __name__ == '__main__':
  serve()
