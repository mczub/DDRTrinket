import re
from abc import ABCMeta, abstractmethod
from collections import defaultdict
import sched, time
import pygame
import threading


contents = ''


with open('./A.dwi', 'r+') as f:
    contents = f.read()

def convertSteps(steps, bpm, bpmChanges, freezes, gap, stepIndex, holdIndex):
#takes in all these params, returns back a dictionary with: key = offset (in milliseconds) and value = a list of function objects to be called

  mySteps = defaultdict()

  curBPM = float(bpm)
  notesPerMeasure = 8
  curBeat = float(0)
  secPerMeasure = 60*4/curBPM
  curOffset = float(gap)/1000 + 0.4
  prevOffset = curOffset
  nextIsHold = False
  for i, c in enumerate(steps):
    for freeze in freezes:
      if (approx(curBeat, float(freeze[0]))):
        curOffset += float(freeze[1])/1000
    for change in bpmChanges:
      if (approx(curBeat, float(change[0]))):
        print 'found bpm change from ' + str(curBPM) + ' to ' + str(change[1])
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
    return self.__pad
  def Press(self):
    if (not self.__isHeld):
      print 'press ' + self.__pad
    else:
      print 'release ' + self.__pad
      self.__isHeld = False
  def Hold(self):
    print 'started hold ' + self.__pad
    self.__isHeld = True

titleRE = re.compile("#TITLE:(.+);")
title = titleRE.findall(contents)
print 'Title: ' + title[0]

artistRE = re.compile(r'#ARTIST:(.+);')
artist = artistRE.findall(contents)
print 'Artist: ' + artist[0]

bpmRE = re.compile(r'#BPM:(\d+);')
bpm = bpmRE.findall(contents)
print 'BPM: ' + bpm[0]

gapRE = re.compile(r'#GAP:(\d+);')
gap = gapRE.findall(contents)
print 'Gap: ' + gap[0]

stepsRE = re.compile(r'#SINGLE:MANIAC:(\d+):(.+);')
steps = stepsRE.findall(contents)
#print steps
print 'Difficulty: ' + steps[0][0]
print 'Steps: ' + steps[0][1]

bpmChangeRE = re.compile(r"#CHANGEBPM:(.*);")
changes = []
#bpmChangeRE = re.compile(r"#CHANGEBPM:(?:(?:(\d+)=(\d+),?)+);")
bpmChanges = bpmChangeRE.findall(contents)
if (bpmChanges != []):
  changesWithEquals = bpmChanges[0].split(',')
  for i in changesWithEquals:
    changes.append(i.split('='))
  print 'BPM Changes: '
  for change in changes:
    print change[0] + ',' + change[1]

freezeRE = re.compile(r"#FREEZE:(.*);");
#bpmChangeRE = re.compile(r"#CHANGEBPM:(?:(?:(\d+)=(\d+),?)+);")
rawFreezes = []
freezes = freezeRE.findall(contents)
if (freezes != []):
  freezesWE = freezes[0].split(',')
  for i in freezesWE:
    rawFreezes.append(i.split('='))
  print 'Freezes: '
  for freeze in rawFreezes:
    print freeze[0] + ',' + freeze[1]

d = Pad('D')
u = Pad('U')
l = Pad('L')
r = Pad('R')

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

stepsDict = convertSteps(steps[0][1], bpm[0], changes, rawFreezes, gap[0], stepIndex, holdIndex)
#print changes
#for key in sorted(stepsDict):
#  print str(key) + ": " + ''.join(str(e.im_self) for e in stepsDict[key])

#timers = []
s = sched.scheduler(time.time, time.sleep)
for key in stepsDict:
  for call in stepsDict[key]:
    s.enter(key, 1, call, ())

pygame.init()
pygame.display.set_mode((1,1))
pygame.mixer.init()
pygame.mixer.music.load('./A.mp3')
arrows = threading.Thread(target=s.run, args=())
pygame.mixer.music.play()
print 'played'
while not pygame.mixer.music.get_busy():
  pygame.mixer.music.play()
arrows.start()
while pygame.mixer.music.get_busy(): 
  pygame.time.Clock().tick(30)
