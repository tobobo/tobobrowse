from os import path, listdir
from collections import deque

def largestfile(this_path):
  special_files = []

  if not path.isdir(this_path):
    total_size = path.getsize(this_path)
    largest_file_size = total_size
    largest_file_path = this_path
    num_files = 1
    num_directories = 0
  else:
    total_size = 0
    largest_file_size = 0
    largest_file_path = ''
    num_files = 0
    num_directories = 0

    directories = deque([this_path])
    while len(directories) > 0:
      current_directory = directories.popleft()
      contents = listdir(current_directory)
      num_directories += 1
      for this_file in contents:
        try:
          file_path = path.join(current_directory, this_file)
          if path.isdir(file_path):
            directories.append(file_path)
          elif path.isfile(file_path):
            if file_path.endswith(('mp4', 'avi', '3gp', 'mkv', 'zip', 'rar', 'iso', 'dmg')):
              special_files.append(file_path)
            size = path.getsize(file_path)
            total_size += size
            if size > largest_file_size:
              largest_file_size, largest_file_path = size, file_path
            num_files += 1
        except OSError:
          pass


  return {'path': largest_file_path, 'size': largest_file_size, 'total_size': total_size, 'num_files': num_files, 'num_directories': num_directories, 'special_files': special_files}

if __name__ == '__main__':
  print largestfile('.')
