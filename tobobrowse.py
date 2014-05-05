from bottle import app, route, run, auth_basic
from transmission import *
import json
import ConfigParser
from largestfile import largestfile
from os import path
import urllib
import urlparse
import tarfile
import re

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
  if not path.isfile(output_filename):
    with tarfile.open(output_filename, "w:gz") as tar:
      tar.add(source_dir, arcname=os.path.basename(source_dir))
  return output_filename

def path_to_url(path, file_base, url_base):
  partial_path = path.split(file_base)[-1]
  quoted_partial_path = urllib.quote(partial_path)
  return urlparse.urljoin(url_base, quoted_partial_path)

def torrent_folder_path(torrent):
  return path.join(torrent['downloadDir'], torrent['name'])

def get_file_url(torrent):
  torrent_folder = torrent_folder_path(torrent)
  largest_file = largestfile(torrent_folder)
  largest_file_name = path.basename(largest_file)
  if path.samefile(torrent_folder, largest_file):
    main_file = largest_file
  elif re.match(r'(\.mp4|\.avi|\.3gp|\.mkv)$', largest_file_name):
    main_file = largest_file
  else:
    print 'going to tar'
    main_file = largest_file
    # main_file = make_tarfile(torrent_folder + ".tar.gz", torrent_folder)

  return path_to_url(main_file, torrent['downloadDir'], config.get('transmission', 'http_base'))

def user_auth(user, passwd):
  if user == config.get('transmission', 'user') and passwd == config.get('transmission', 'passwd'):
    return True
  return False

def serve():

  t = Transmission('localhost', 30446, '/transmission/rpc', config.get('transmission', 'user'), config.get('transmission', 'passwd'))

  def get_torrent_by_name(name):
    torrents = t.get_torrent_list([])
    for torrent in torrents:
      if torrent['name'] == name:
        return torrent

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
  def get_torrent_with_file(name):
    torrent = get_torrent_by_name(name)
    if torrent:
      torrent['downloadUrl'] = get_file_url(torrent)
      return json.dumps({'torrent': torrent})
    else:
      return json.dumps({'meta': 'Torrent not found'})

  tobobrowse = app()
  tobobrowse = StripPathMiddleware(tobobrowse)
  run(host='chips.whatbox.ca', port=8000, app=tobobrowse)

if __name__ == '__main__':
  serve()
