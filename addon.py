import sys
sys.path.append(r"C:\Program Files (x86)\JetBrains\PyCharm Community Edition 3.4.1\debuging")
import pydevd
pydevd.settrace('localhost', port=5678, stdoutToServer=True, stderrToServer=True)

import xbmc
import xbmcgui

#get actioncodes from https://github.com/xbmc/xbmc/blob/master/xbmc/guilib/Key.h
ACTION_PREVIOUS_MENU = 10


keyboard = xbmc.Keyboard('mytext')
keyboard.doModal()
if (keyboard.isConfirmed()):
  print keyboard.getText()
else:
  print 'user canceled'

