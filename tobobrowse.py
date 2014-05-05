from bottle import app, route, run, auth_basic
from transmission import *
import json
import ConfigParser
from largestfile import largestfile
from os import path
import urllib
import urlparse
import tarfile
import requests

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

def get_file(torrent):
  torrent_folder = torrent_folder_path(torrent)
  largest_file = largestfile(torrent_folder)
  largest_file_path = largest_file['path']
  largest_file_name = path.basename(largest_file_path)
  size = largest_file['total_size']
  can_download = True

  if path.samefile(torrent_folder, largest_file_path):
    main_file = largest_file_path
  elif largest_file_name.endswith(('mp4', 'avi', '3gp', 'mkv')):
    main_file = largest_file_path
  elif size < 1073741824: # 1 GB
    main_file = make_tarfile(torrent_folder + ".tar.gz", torrent_folder)
    size = path.getsize(main_file)
  else:
    main_file = largest_file_path
    can_download = False

  return {
    'path': main_file,
    'url': path_to_url(main_file, torrent['downloadDir'], config.get('transmission', 'http_base')),
    'num_files': largest_file['num_files'] + largest_file['num_directories'],
    'size': size, 
    'can_download': can_download
  }

def get_file_and_add_details(torrent):
  main_file = get_file(torrent)
  torrent['downloadUrl'] = main_file['url']
  torrent['numFiles'] = main_file['num_files']
  torrent['downloadSize'] = main_file['size']
  torrent['canDownload'] = main_file['can_download']

  return torrent

def serve():

  transmission_host = 'localhost'
  transmission_port = 30446
  transmission_user = ''
  transmission_passwd = ''

  def transmission():
    print 'transmission deets', transmission_user, transmission_passwd
    return Transmission(transmission_host, transmission_port, '/transmission/rpc', transmission_user, transmission_passwd)
  
  def user_auth(user, passwd):
    nonlocal transmission_user
    nonlocal transmission_passwd
    
    print 'user auth', user, passwd
    transmission_request = requests.get('http://%s:%d' % (transmission_host, transmission_port), auth=(user, passwd), timeout=0.5)
    print 'status code', transmission_request.status_code
    if transmission_request.status_code == 200:
      transmission_user = user
      transmission_passwd = passwd
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

  @route('/torrents/<name>')
  @auth_basic(user_auth)
  def get_torrent_with_file(name):
    torrent = get_torrent_by_name(name)
    if torrent:
      return json.dumps({'torrent': get_file_and_add_details(torrent)})
    else:
      return json.dumps({'meta': 'Torrent not found'})

  tobobrowse = app()
  tobobrowse = StripPathMiddleware(tobobrowse)
  run(host='chips.whatbox.ca', port=8000, app=tobobrowse)

if __name__ == '__main__':
  serve()
