def largestfile(this_path):
  from os import path, listdir
  from collections import deque

  total_size = 0
  largest_file_size = 0
  largest_file_path = ''

  directories = deque([this_path])

  while len(directories) > 0:
    current_directory = directories.popleft()
    contents = listdir(current_directory)
    for this_file in contents:
      try:
        file_path = path.join(current_directory, this_file)
        if path.isdir(file_path):
          directories.append(file_path)
        elif path.isfile(file_path):
          size = path.getsize(file_path)
          total_size += size
          if size > largest_file_size:
            largest_file_size, largest_file, path = size, file_path
      except OSError:
        pass

  return {'path': largest_file_path, 'size': largest_file_size, 'total_size': total_size}

if __name__ == '__main__':
  print largestfile('.')
