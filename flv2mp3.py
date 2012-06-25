#!/usr/bin/env python
##
##  flv2mp3.py - a flv to mp3 converter
##
##  Original Author :Yusuke Shinyama
##
##  modified by :lqik2004
##
##  *public domain*
##
##  Usage:
##    $ flv2mp3.py filename.flv
##      (convert filename.flv to filename.mp3)
##
##    $ flv2mp3.py -y XXXXXXXXX
##      (download a youtube video whose id=XXXXXX and save as mp3)
##

import sys
from struct import pack, unpack
stdout = sys.stdout
stderr = sys.stderr


##  FLVReader
##
class FLVReader:

  def __init__(self, fp):
    self.fp = fp
    return
  
  def parse_header(self):
    (F,L,V,ver) = self.read(4)
    if F+L+V != 'FLV': raise ValueError('not a flv file.')
    flv_version = ord(ver)
    flags = self.readui8()
    offset = self.readub32()
    #print 'Header:', (F,L,V,flv_version,flags)
    return

  def scan(self):
    try:
      offset = self.readub32()          # always 0
      while 1:
        tag = self.readui8()
        length = self.readub24()
        timestamp = self.readub24()
        reserved = self.readub32()
        data = self.read(length)
        yield (tag, timestamp, data)
        self.readub32()  # skip PreviousTagSize
    except EOFError:
      pass
    return

  # fixed bytes read
  
  def read(self, n):
    x = self.fp.read(n)
    if len(x) != n:
      raise EOFError
    return x
  
  def readui8(self):
    return ord(self.read(1))
  def readsi8(self):
    return unpack('<b', self.read(1))[0]
  
  def readui16(self):
    return unpack('<H', self.read(2))[0]
  def readub16(self):
    return unpack('>H', self.read(2))[0]
  def readsi16(self):
    return unpack('<h', self.read(2))[0]
  
  def readub24(self):
    return unpack('>L', '\x00'+self.read(3))[0]

  def readui32(self):
    return unpack('<L', self.read(4))[0]
  def readub32(self):
    return unpack('>L', self.read(4))[0]

  def readrgb(self):
    return ( self.readui8(), self.readui8(), self.readui8() )
  def readrgba(self):
    return ( self.readui8(), self.readui8(), self.readui8(), self.readui8() )


# get a youtube flv file for the given video_id
def get_youtube_flv(video_id):
  import re, urllib
  urlpat = re.compile(r'\bv=([-_/a-zA-Z0-9]+)\b')
  m = urlpat.search(video_id)
  if m:
    video_id = m.group(1)
  vidpat = re.compile(r'^\s*var\s+swfArgs\s*=\s*{.*"video_id"\s*:\s*"([^"]+)".*,\s*"t"\s*:\s*"([^"]+)"')
  titlepat = re.compile(r'\s*<meta\s+name\s*=\s*"title"\s+content\s*=\s*"([^"]+)"')
  userpat = re.compile(r"^\s*var\s+watchUsername\s*=\s*'([^']+)'")
  url1 = 'http://www.youtube.com/watch?v=%s' % video_id
  fp = urllib.urlopen(url1)
  t = None
  title = None
  user = None
  for line in fp:
    m = vidpat.match(line)
    if m and m.group(1) == video_id:
      t = m.group(2)
    m = titlepat.match(line)
    if m:
      title = m.group(1)
    m = userpat.match(line)
    if m:
      user = m.group(1)
  fp.close()
  if not t: raise ValueError('video not found')
  url2 = 'http://www.youtube.com/get_video?video_id=%s&t=%s' % (video_id, t)
  filename = re.sub('[^\w\d]+', '_', title)+'.mp3'
  return (url2, filename, title, user, urllib.urlopen(url2))

# generate mp3 ID3 tag
def generate_id3(outfp, title, artist, album, year=None, comment=''):
  import time
  outfp.write('TAG')
  outfp.write((title+' '*30)[:30])
  outfp.write((artist+' '*30)[:30])
  outfp.write((album+' '*30)[:30])
  if not year:
    year = time.localtime()[0]
  outfp.write('%04d' % year)
  outfp.write((comment+' '*28)[:28])
  outfp.write('\xff\x00\xff')
  return

# flv2mp3 converter
def flv2mp3(infp, outfp):
  reader = FLVReader(infp)
  reader.parse_header()
  for (tag, timestamp, data) in reader.scan():
    #print (tag, timestamp, len(data))
    if tag != 8: continue             # audio tag?
    t = ord(data[0]) >> 4
    if t != 2: continue               # mp3 packet?
    outfp.write(data[1:])
  return


# main
def main(argv):
  import getopt
  def usage():
    print 'usage: %s file ...' % argv[0]
    print 'usage: %s -y video_id ...' % argv[0]
    return 100
  try:
    (opts, args) = getopt.getopt(argv[1:], 'y')
  except getopt.GetoptError:
    return usage()
  youtube = False
  for (k, v) in opts:
    if k == '-y': youtube = True
  if not args:
    return usage()
  if youtube:
    for video_id in args:
      (url,filename,title,user,fp) = get_youtube_flv(video_id)
      print >>stderr, 'opening: %s' % url
      print >>stderr, 'saving mp3 as: %s' % filename
      outfp = file(filename, 'wb')
      generate_id3(outfp, title, user, 'YouTube Video')
      flv2mp3(fp, outfp)
      outfp.close()
      fp.close()
  else:
    for fname in args:
      fp = file(fname, 'rb')
      print >>stderr, 'opening: %s' % fname
      outfp = file(fname.replace('.flv', '.mp3'), 'wb')
      flv2mp3(fp, outfp)
      outfp.close()
      fp.close()
  return 0

if __name__ == '__main__': sys.exit(main(sys.argv))