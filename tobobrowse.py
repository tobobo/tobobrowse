from bottle import \
  app, route, post, delete, run, auth_basic, request, response
from transmission import *
import json
import ConfigParser
from largestfile import largestfile
from os import path, remove
import shutil
import urllib
import urlparse
import tarfile
import requests

config = ConfigParser.ConfigParser()

if len(config.read('config')) < 1:
  config.add_section('transmission')
  config.set(
    'transmission', 'http_base',
    os.environ.get('TOBOBROWSE_HTTP_BASE')
  )
  config.set('transmission', 'host', os.environ.get('TOBOBROWSE_HOST'))
  config.set('transmission', 'port', os.environ.get('TOBOBROWSE_PORT'))
  config.set('transmission', 'timeout', os.environ.get('TOBOBROWSE_TIMEOUT'))
  config.set('server', 'port', os.environ.get('PORT'))

class StripTrailingSlash(object):
  def __init__(self, app):
    self.app = app
  def __call__(self, e, h):
    e['PATH_INFO'] = e['PATH_INFO'].rstrip('/')
    return self.app(e,h)

class EnableCors(object):
  name = 'enable_cors'
  api = 2

  def apply(self, fn, context):
    def _enable_cors(*args, **kwargs):
      for header, value in {
        'Access-Control-Allow-Origin': request.headers.get('Origin'),
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Credentials': 'true',
        'Access-Control-Allow-Headers': ', '.join([
          'Origin',
          'Accept',
          'Content-Type',
          'X-Requested-With',
          'X-CSRF-Token',
          'Access-Control-Request-Method'
        ])
      }.iteritems():
        response.headers[header] = value

      if request.method != 'OPTIONS':
        return fn(*args, **kwargs)

    return _enable_cors

def make_tarfile(output_filename, source_dir):
  if not path.isfile(output_filename):
    with tarfile.open(output_filename, "w:gz") as tar:
      tar.add(source_dir, arcname=os.path.basename(source_dir))
  return output_filename

def path_to_url(path, file_base, url_base):
  partial_path = path.split(file_base)[-1]
  quoted_partial_path = urllib.quote(partial_path)
  return urlparse.urljoin(url_base, quoted_partial_path)

def torrent_path(torrent):
  return path.join(torrent['downloadDir'], torrent['name'])

def torrent_gz_path(torrent):
  return torrent_path(torrent) + ".tar.gz"

def get_file(torrent):
  torrent_folder = torrent_path(torrent)
  largest_file = largestfile(torrent_folder)
  largest_file_path = largest_file['path']
  largest_file_size = path.getsize(largest_file['path'])
  largest_file_name = path.basename(largest_file_path)
  special_files = largest_file['special_files']
  size = largest_file['total_size']
  can_download = True
  files = []
  multi_files = False

  is_video = largest_file_name.endswith(('mp4', 'avi', '3gp', 'mkv'))
  if is_video and largest_file_size / size < 0.75:
    files = special_files
  else:
    if path.samefile(torrent_folder, largest_file_path):
      files.append(largest_file_path)
    elif is_video:
      files.append(largest_file_path)
    elif size < 1073741824: # 1 GB
      tarfile = make_tarfile(torrent_gz_path(torrent), torrent_folder)
      files.append(tarfile)
      size = path.getsize(tarfile)
    else:
      files.append(largest_file_path)
      can_download = False

  def generate_file_obj(file_path):
    return {
      'path': file_path,
      'name': path.basename(file_path),
      'url': path_to_url(
        file_path,
        torrent['downloadDir'],
        config.get('transmission', 'http_base')
      )
    }

  return {
    'files': map(generate_file_obj, files),
    'num_files': largest_file['num_files'] + largest_file['num_directories'],
    'size': size,
    'can_download': can_download
  }

def get_file_and_add_details(torrent):
  files = get_file(torrent)
  torrent['files'] = files['files']
  torrent['numFiles'] = files['num_files']
  torrent['downloadSize'] = files['size']
  torrent['canDownload'] = files['can_download']

  return torrent

def remove_files(torrent):
  this_path = torrent_path(torrent)
  if path.isfile(this_path):
    remove(this_path)
  elif path.isdir(this_path):
    shutil.rmtree(this_path)
  gz_path = torrent_gz_path(torrent)
  if path.isfile(gz_path):
    remove(gz_path)



def serve():

  transmission_config = {
    'host': config.get('transmission', 'host'),
    'port': int(config.get('transmission', 'port')),
    'timeout': float(config.get('transmission', 'timeout')),
    'user': '', 'passwd': ''
  }

  def transmission():
    return Transmission(
      transmission_config['host'],
      transmission_config['port'],
      '/transmission/rpc',
      transmission_config['user'],
      transmission_config['passwd']
    )

  def user_auth(user, passwd):
    transmission_request = requests.get(
      'http://%s:%d' % (
        transmission_config['host'],
        transmission_config['port']
      ),
      auth=(user, passwd),
      timeout=transmission_config['timeout']
    )
    if transmission_request.status_code == 200:
      transmission_config['user'] = user
      transmission_config['passwd'] = passwd
      return True
    return False

  def get_torrent_by_name(name):
    torrents = transmission().get_torrent_list([])
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
    return json.dumps({'torrents': transmission().get_torrent_list([])})

  @post('/torrents')
  @auth_basic(user_auth)
  def add_torrent():
    result = transmission().add_torrent(request.forms.get('torrent[url]'))
    return json.dumps({'meta': 'success'})

  @route('/torrents/<name>')
  @auth_basic(user_auth)
  def get_torrent_with_file(name):
    torrent = get_torrent_by_name(name)
    if torrent:
      return json.dumps({'torrent': get_file_and_add_details(torrent)})
    else:
      return json.dumps({'meta': 'Torrent not found'})

  @route('/torrents/<name>', method=['DELETE'])
  @auth_basic(user_auth)
  def delete_torrent(name):
    torrent = get_torrent_by_name(name)
    if torrent:
      transmission().remove_torrent(torrent['id'])
      remove_files(torrent)
      return json.dumps({'meta': 'success'})
    else:
      return json.dumps({'meta': 'Torrent not found'})

  tobobrowse = app()
  tobobrowse.install(EnableCors())
  tobobrowse = StripTrailingSlash(tobobrowse)
  run(
    host='0.0.0.0',
    port=config.get('server', 'port'),
    app=tobobrowse
  )

if __name__ == '__main__':
  serve()
