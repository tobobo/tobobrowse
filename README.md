# Tobobrowse

A REST api for interacting with transmission. Can be installed and run without root access.

Uses [gevent](http://www.gevent.org/) to allow non-blocking serving of files, which can be streamed using HTTP Range requests.

## Background

It's convenient to run bittorrent on a remote server to take advantage of the bandwidth available in a typical data center. This API allows one to easily communicate with Transmission via web requests, for instance, to build an interface to access their torrents.

This app interacts both with Transmission and the filesystem to enable simple commands that unify common operations when working with torrents.

## Endpoints
* GET /torrents - get all torrents
* POST /torrents - add a torrent with a magnet link
* GET /torrents/:name - get a torrent by name
* DELETE /torrents/:name - remove a torrent by name
* GET /files/:UID - get a download file from its UID

## File Streaming
I found it surprisingly hard to locate good documentation on how to properly handle ranged HTTP requests. Here's a gist, and [here is the implementation](tobobrowse.py#L372) in this app.

1. A ranged request is performed with the Range header set to a value like `bytes=x-y` to specify the range of data requested.
2. The response status is set to `206 (Partial Content)`.
3. `Content-Range` response header is set to `bytes x-y/z` to indicate the first byte, last byte, and total size.
4. `Accept-Range` header is set to `bytes`.
5. Seek to the requested position in the file (specified by the first value in the Range header) and serve it (in this case in 1 MB chunks).
