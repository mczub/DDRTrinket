import re
from abc import ABCMeta, abstractmethod
from collections import defaultdict
import sched, time
import pygame
import threading
import sys
import os
import RPi.GPIO as GPIO
from bibliopixel.led import *
from bibliopixel.drivers.LPD8806 import *

def convertSteps(steps, bpm, bpmChanges, freezes, gap, stepIndex, holdIndex):
#takes in all these params, returns back a dictionary with: key = offset (in milliseconds) and value = a list of function objects to be called

  mySteps = defaultdict()

  curBPM = float(bpm)
  notesPerMeasure = 8
  curBeat = float(0)
  secPerMeasure = 60*4/curBPM
  curOffset = float(gap)/1000 + 0.25
  prevOffset = curOffset
  nextIsHold = False
  for i, c in enumerate(steps):
    for freeze in freezes:
      if (approx(curBeat, float(freeze[0]))):
        curOffset += float(freeze[1])/1000
    for change in bpmChanges:
      if (approx(curBeat, float(change[0]))):
        #print 'found bpm change from ' + str(curBPM) + ' to ' + str(change[1])
        curBPM = float(change[1])
        secPerMeasure = 60*4/curBPM
    if (c == '('):
      notesPerMeasure = 16
    elif (c == ')'):
      notesPerMeasure = 8
    elif (c == '['):
      notesPerMeasure = 24
    elif (c == ']'):
      notesPerMeasure = 8  
    elif (c == '{'):
      notesPerMeasure = 64
    elif (c == '}'):
      notesPerMeasure = 8
    elif (c == '!'):
      nextIsHold = True
    elif (c == '0'):
      prevOffset = curOffset
      curOffset += (secPerMeasure / notesPerMeasure)
      curBeat += 16/float(notesPerMeasure)
      nextIsHold = False
    try:
      if (nextIsHold):
        #print prevOffset
        for press in stepIndex[c]:
          mySteps[prevOffset].remove(press)
        mySteps[prevOffset].extend(holdIndex[c])
        nextIsHold = False
        #print mySteps[prevOffset]
      else:
        mySteps[curOffset] = list(stepIndex[c])
        prevOffset = curOffset
        curOffset += (secPerMeasure / notesPerMeasure)
        curBeat += 16/ float(notesPerMeasure)
        
    except KeyError:
      pass
  return mySteps

def approx(a,b):
  return abs(a - b) < 0.01

class Pad(object):
  def __init__(self, pad):
    self.__pad = pad
    self.__isHeld = False
  def __repr__(self):
    return self.__pad
  def __str__(self):
    return str(self.__pad)
  def Press(self):
    global strip
    if (not self.__isHeld):
      print 'press ' + str(self.__pad)
      strip.set(self.__pad, (100,100,100))
      strip.update()
      time.sleep(0.02)
      strip.set(self.__pad, (0,0,0))
      strip.update()
    else:
      print 'release ' + str(self.__pad)
      strip.set(self.__pad, (0,0,0))
      strip.update()
      self.__isHeld = False
  def Hold(self):
    global strip
    print 'started hold ' + str(self.__pad)
    strip.set(self.__pad, (100,100,100))
    strip.update()
    self.__isHeld = True

def getTitle(dwiFile):
  titleRE = re.compile("#TITLE:(.+);")
  title = titleRE.findall(dwiFile)
  return title[0]
  #print 'Title: ' + title[0]

def getArtist(dwiFile):
  artistRE = re.compile(r'#ARTIST:(.+);')
  artist = artistRE.findall(dwiFile)
  return artist[0]
  #print 'Artist: ' + artist[0]
  
def getBPM(dwiFile):
  bpmRE = re.compile(r'#BPM:(\d+);')
  bpm = bpmRE.findall(dwiFile)
  return bpm[0]
  #print 'BPM: ' + bpm[0]

def getGap(dwiFile):
  gapRE = re.compile(r'#GAP:(\d+);')
  gap = gapRE.findall(dwiFile)
  return gap[0]
  #print 'Gap: ' + gap[0]

def getSteps(dwiFile):
  stepsRE = re.compile(r'#SINGLE:MANIAC:(\d+):(.+);')
  steps = stepsRE.findall(dwiFile)
  return steps[0][1]
  #print 'Difficulty: ' + steps[0][0]
  #print 'Steps: ' + steps[0][1]

def getChanges(dwiFile):
  bpmChangeRE = re.compile(r"#CHANGEBPM:(.*);")
  changes = []
  bpmChanges = bpmChangeRE.findall(dwiFile)
  if (bpmChanges != []):
    changesWithEquals = bpmChanges[0].split(',')
    for i in changesWithEquals:
      changes.append(i.split('='))
  return changes
    #print 'BPM Changes: '
    #for change in changes:
      #print change[0] + ',' + change[1]

def getFreezes(dwiFile):
  freezeRE = re.compile(r"#FREEZE:(.*);");
  rawFreezes = []
  freezes = freezeRE.findall(dwiFile)
  if (freezes != []):
    freezesWE = freezes[0].split(',')
    for i in freezesWE:
      rawFreezes.append(i.split('='))
  return rawFreezes
    #print 'Freezes: '
    #for freeze in rawFreezes:
      #print freeze[0] + ',' + freeze[1]


def run(name, s):
  d = Pad(1)
  u = Pad(2)
  l = Pad(0)
  r = Pad(3)

  stepIndex = {
    '1' : [d.Press, l.Press],
    '2' : [d.Press],
    '3' : [d.Press, r.Press],
    '4' : [l.Press],
    '6' : [r.Press],
    '7' : [u.Press, l.Press],
    '8' : [u.Press],
    '9' : [u.Press, r.Press],
    'A' : [u.Press, d.Press],
    'B' : [l.Press, r.Press]
  }

  holdIndex = {
    '1' : [d.Hold, l.Hold],
    '2' : [d.Hold],
    '3' : [d.Hold, r.Hold],
    '4' : [l.Hold],
    '6' : [r.Hold],
    '7' : [u.Hold, l.Hold],
    '8' : [u.Hold],
    '9' : [u.Hold, r.Hold],
    'A' : [u.Hold, d.Hold],
    'B' : [l.Hold, r.Hold]
  }

  contents = ''

  with open('./' + name + '.dwi', 'r+') as f:
      contents = f.read()

  steps = getSteps(contents)
  bpm = getBPM(contents)
  changes = getChanges(contents)
  freezes = getFreezes(contents)
  gap = getGap(contents)
  stepsDict = convertSteps(steps, bpm, changes, freezes, gap, stepIndex, holdIndex)
  #print changes
  #for key in sorted(stepsDict):
  #  print str(key) + ": " + ''.join(str(e.im_self) for e in stepsDict[key])

  for e in s.queue:
    s.cancel(e)
  
  for key in stepsDict:
    for call in stepsDict[key]:
      s.enter(key, 1, call, ())

  #pygame.init()
  #pygame.display.set_mode((1,1))
  #pygame.mixer.init()
  pygame.mixer.music.load('./' + name + '.mp3')
  arrows = threading.Thread(target=s.run, args=())
  pygame.mixer.music.play()
  while not pygame.mixer.music.get_busy():
    pygame.mixer.music.play()
  pygame.mixer.music.rewind()
  arrows.daemon = True
  arrows.start()
  
def clearQueue(s):
  for e in s.queue:
    s.cancel(e)

def nextSong(channel):
  global curSong
  global songNames
  global s
  curSong += 1
  curSong %= len(songNames)
  print 'playing ' + songNames[curSong]
  run(songNames[curSong],s)
#run("Healing Vision (Angelic mix)")
END_MUSIC_EVENT = pygame.USEREVENT + 0
s = sched.scheduler(time.time, time.sleep)
files = [f for f in os.listdir('.') if os.path.isfile(f)]
#songNames = []
dwiNames = []
mp3Names = []
for f in files:
  dwiRE = re.compile('(.+)\.dwi')
  mp3RE = re.compile('(.+)\.mp3')
  dwiName = dwiRE.findall(f)
  mp3Name = mp3RE.findall(f)
  if (dwiName != []): dwiNames.append(dwiName[0])
  if (mp3Name != []): mp3Names.append(mp3Name[0])
songNames = sorted(list(set(dwiNames) & set(mp3Names)))
#print songNames
curSong = 0
paused = False
GPIO.setmode(GPIO.BCM)
GPIO.setup(4, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.add_event_detect(4, GPIO.FALLING, callback=nextSong, bouncetime=500)
driver = DriverLPD8806(4)
strip = LEDStrip(driver)
strip.fill((0,0,0))
pygame.init()
#pygame.display.set_mode((1,1))
pygame.mixer.init()
pygame.mixer.music.set_endevent(END_MUSIC_EVENT)
eventloop = True
while eventloop:
  try:  
    pygame.time.Clock().tick(30)
    paused = False
    for event in pygame.event.get():
      if event.type == END_MUSIC_EVENT:
        nextSong(0)
    keydown = raw_input()
    keydown = keydown.lower()
    buttonstate = GPIO.input(4)
    if "n" in keydown:
      curSong += 1
      curSong %= len(songNames)
      print 'playing ' + songNames[curSong]
      run(songNames[curSong],s)
    elif "s" in keydown:
      pygame.mixer.music.stop()
      clearQueue(s)
    elif buttonstate == False:
      print 'playing ' + songNames[curSong]
      run(songNames[curSong],s)
  except (KeyboardInterrupt, SystemExit):
      eventloop = False
pygame.quit()
sys.exit()
