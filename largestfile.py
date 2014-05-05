from os import path, listdir
from collections import deque
import time

def largestfile(this_path):
  maxFile = [0, '']

  directories = deque([this_path])

  while len(directories) > 0:
    current_directory = directories.popleft()
    contents = listdir(current_directory)
    for thisFile in contents:
      try:
        filePath = path.join(current_directory, thisFile)
        if path.isdir(filePath):
          directories.append(filePath)
        elif path.isfile(filePath):
          size = path.getsize(filePath)
          if size > maxFile[0]:
            maxFile = [size, filePath]
      except OSError:
        pass

  return maxFile

if __name__ == '__main__':
  print largestfile('.')
