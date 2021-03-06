from gevent import monkey; monkey.patch_all()
from bottle import \
  app, route, post, delete, run, auth_basic, request, response
from transmission import *
from time import sleep
import json
import ConfigParser
from largestfile import largestfile
from os import path, remove
import shutil
import urllib
import urlparse
import tarfile
import requests
import mimetypes
from datetime import datetime, timedelta
from random import choice, randint
import pickle
import re
import string

sessions = {}

mimetypes.add_type('video/x-matroska', '.mkv')

config = ConfigParser.ConfigParser()

# Read config from file

if len(config.read('config')) < 1:
  config.add_section('transmission')
  config.set(
    'transmission', 'http_base',
    os.environ.get('TOBOBROWSE_HTTP_BASE')
  )
  config.set('transmission', 'host', os.environ.get('TOBOBROWSE_HOST'))
  config.set('transmission', 'port', os.environ.get('TOBOBROWSE_PORT'))
  config.set('transmission', 'timeout', os.environ.get('TOBOBROWSE_TIMEOUT'))
  config.set('transmission', 'public_base', os.environ.get('TOBOBROWSE_PUBLIC_BASE'))
  config.set('server', 'port', os.environ.get('PORT'))


## Reading file UIDs from text file

file_ids = {}
file_paths = {}
pickle_file_path = 'file_ids.pickle'

# util for loading saved file IDs, invoked immediately

def load_ids():
  if path.isfile(pickle_file_path):
    pickle_file = open(pickle_file_path, 'r')
    pickled = pickle.load(pickle_file)
    if 'file_ids' in pickled:
      file_ids = pickled['file_ids']
    if 'file_paths' in pickled:
      file_paths = pickled['file_paths']

load_ids()


# util for saving file ids to file

def dump_ids():
  pickle_file = open(pickle_file_path, 'w+')
  pickle.dump({'file_ids': file_ids, 'file_paths': file_paths}, pickle_file)


## Middleware

# middleware to strip trailing slash character

class StripTrailingSlash(object):
  def __init__(self, app):
    self.app = app
  def __call__(self, e, h):
    e['PATH_INFO'] = e['PATH_INFO'].rstrip('/')
    return self.app(e,h)


# middleware to allow cross-site requests
class EnableCors(object):
  name = 'enable_cors'
  api = 2

  def apply(self, fn, context):
    def _enable_cors(*args, **kwargs):
      for header, value in {
        'Access-Control-Allow-Origin': request.headers.get('Origin') or '*',
        'Access-Control-Allow-Methods': 'OPTIONS, GET, POST, PUT, DELETE',
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


# util for tarfile creation
def make_tarfile(output_filename, source_dir):
  if not path.isfile(output_filename):
    with tarfile.open(output_filename, "w:gz") as tar:
      tar.add(source_dir, arcname=os.path.basename(source_dir))
  return output_filename


## Saving and loading file IDs


# util for determining whether a file is present by path

def has_path(file_path):
  if file_path in file_paths:
    if file_time_is_valid(file_ids[file_paths[file_path]]['time']):
      return True
    else:
      remove_path(file_path)
      return False
  else:
    return False


# similar util, but for IDs

def has_id(file_id):
  file_id = int(file_id)
  if file_id in file_ids:
    if file_time_is_valid(file_ids[file_id]['time']):
      return True
    else:
      remove_path(file_ids[file_id]['path'])
      return false
  else:
    return False

# create a UID for a file

def add_path(file_path):
  if has_path(file_path):
    return file_paths[file_path]
  else:
    while True:
      potential_id = randint(0, 999999)
      if not has_id(potential_id):
        new_id = potential_id
        break
    file_ids[new_id] = {'path': file_path, 'time': datetime.now()}
    file_paths[file_path] = new_id
    dump_ids()
    return new_id


# remove a file UID

def remove_path(file_path):
  file_ids.pop(file_paths[file_path], None)
  file_paths.pop(file_path)


# Get url for UID

def path_to_temp_url(file_path):
  file_id = add_path(file_path)

  return urlparse.urljoin(
    config.get('server', 'url') + config.get('server', 'files_prefix') + '/',
     str(file_id)
    )

# get original HTTP url for file

def path_to_original_url(file_path, file_base):
  partial_path = path.relpath(file_path, file_base)
  quoted_partial_path = urllib.quote(partial_path)
  return urlparse.urljoin(
    config.get('transmission', 'http_base'),
    quoted_partial_path
  )


## Working with torrent objects

# get path from torrent object
def torrent_path(torrent):
  return path.join(torrent['downloadDir'], torrent['name'])

# get path for tarballed torrent
def torrent_gz_path(torrent):
  return torrent_path(torrent) + ".tar.gz"

# get relevant files from torrent
def get_file(torrent):
  torrent_folder = torrent_path(torrent)
  largest_file = largestfile(torrent_folder)
  largest_file_path = largest_file['path']
  largest_file_size = path.getsize(largest_file['path'])
  largest_file_name = path.basename(largest_file_path)
  special_files = largest_file['special_files']
  size = largest_file['total_size']
  files = []
  multi_files = False

  is_video = largest_file_name.endswith(('mp4', 'avi', '3gp', 'mkv', 'm4v'))
  print float(largest_file_size) / float(size)
  print largest_file_size, size
  print is_video
  print largest_file_name
  if is_video and float(largest_file_size) / float(size) < 0.75:
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
      files = special_files

  def generate_file_obj(file_path):
    return {
      'path': file_path,
      'name': path.basename(file_path),
      'url': path_to_temp_url(file_path),
      'original_url': path_to_original_url(file_path, torrent['downloadDir'])
    }

  return {
    'files': map(generate_file_obj, files),
    'num_files': largest_file['num_files'] + largest_file['num_directories'],
    'size': size,
    'can_download': True
  }

# get extra file details from transmission api

def get_file_and_add_details(torrent):
  files = get_file(torrent)
  torrent['files'] = files['files']
  torrent['numFiles'] = files['num_files']
  torrent['downloadSize'] = files['size']
  torrent['canDownload'] = files['can_download']

  return torrent


# remove torrent from transmission

def remove_files(torrent):
  this_path = torrent_path(torrent)
  if path.isfile(this_path):
    remove(this_path)
  elif path.isdir(this_path):
    shutil.rmtree(this_path)
  gz_path = torrent_gz_path(torrent)
  if path.isfile(gz_path):
    remove(gz_path)

# check if time is in past 24 hours

def file_time_is_valid(time):
  return (datetime.now() - time).total_seconds() < 24*60*60

# create random string

def random_string(length):
  return ''.join(
    choice(string.ascii_uppercase + string.digits) for _ in range(length)
  )


## Server code

def serve():

  transmission_config = {
    'host': config.get('transmission', 'host'),
    'port': int(config.get('transmission', 'port')),
    'timeout': float(config.get('transmission', 'timeout')),
    'user': '', 'passwd': ''
  }

  # init transmission
  def transmission():
    return Transmission(
      transmission_config['host'],
      transmission_config['port'],
      '/transmission/rpc',
      transmission_config['user'],
      transmission_config['passwd']
    )

  # function for basic auth, using transmission auth
  def user_auth(user, passwd):
    cookie_name = 'tobobrowsesession'
    session_cookie = request.get_cookie(cookie_name)
    if session_cookie:
      if session_cookie in sessions:
        return True

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
      session_string = random_string(32)
      sessions[session_string] = True
      response.set_cookie(cookie_name, session_string, max_age = 999999999)
      return True
    return False

  # get a single torrent from list
  def get_torrent_by_name(name):
    torrents = transmission().get_torrent_list([])
    for torrent in torrents:
      if torrent['name'] == name:
        return torrent

  ## routing
  @route('/')
  @auth_basic(user_auth)
  def index():
    return 'hello, friend!'

  # get torrent list
  @route('/torrents')
  @auth_basic(user_auth)
  def torrents():
    return json.dumps({'torrents': transmission().get_torrent_list([])})

  # add torrent
  @post('/torrents')
  @auth_basic(user_auth)
  def add_torrent():
    result = transmission().add_torrent(request.forms.get('torrent[url]'))
    return json.dumps({'meta': 'success'})

  # get individual torrent info
  @route('/torrents/<name>')
  @auth_basic(user_auth)
  def get_torrent_with_file(name):
    torrent = get_torrent_by_name(name)
    if torrent:
      return json.dumps({'torrent': get_file_and_add_details(torrent)})
    else:
      return json.dumps({'meta': 'Torrent not found'})

  # delete torrent
  @route('/torrents/<name>', method=['OPTIONS', 'DELETE'])
  @auth_basic(user_auth)
  def delete_torrent(name):
    torrent = get_torrent_by_name(name)
    if torrent:
      transmission().remove_torrent(torrent['id'])
      remove_files(torrent)
      return json.dumps({'meta': 'success'})
    else:
      return json.dumps({'meta': 'Torrent not found'})

  # serve a file
  @route('/' + config.get('server', 'files_prefix') + '/<file_id>')
  def get_file(file_id):
    file_id = int(file_id)
    if has_id(file_id):

      # get file info
      file_id = file_ids[file_id]
      file_path = file_id['path']
      file_handler = open(file_path, 'r')
      file_size = path.getsize(file_path)

      # set headers according to file
      response.set_header('Content-Type', mimetypes.guess_type(file_path)[0])
      response.set_header('Content-Length', file_size)
      response.set_header(
        'Content-Disposition',
        'attachment; filename="{!s}"'.format(path.basename(file_path))
      )

      # respond to ranged requests
      content_range_header = request.get_header('Range')
      if content_range_header:
        response.status = 206

        # get byte number from header
        file_offset = int(
          re.match(r'bytes=([0-9]+)',
          content_range_header).group(1)
        )

        #seek file to position
        file_handler.seek(file_offset)

        #set response headers
        response.set_header(
          'Content-Range',
          'bytes {0}-{1}/{2}'.format(file_offset, file_size, file_size)
        )
        response.set_header('Accept-Range', 'bytes')

      while True:
        # read chunk from file
        data = file.read(file_handler, 1048576)
        if data:
          # return the data
          yield data
        else:
          # close the file when it's done
          file_handler.close()
          break
    else:
      # return 404 if there is no file
      response.status = 404
      yield 'not found'


  # initialize server
  tobobrowse = app()
  tobobrowse.install(EnableCors())
  tobobrowse = StripTrailingSlash(tobobrowse)
  run(
    host='0.0.0.0',
    port=config.get('server', 'port'),
    app=tobobrowse,
    server='gevent'
  )

if __name__ == '__main__':
  serve()
