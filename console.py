#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import piksi_tools.serial_link as s
import sbp.client as sbpc
import signal
import sys

# Shut chaco up for now
import warnings
warnings.simplefilter(action = "ignore", category = FutureWarning)

def get_args():
  import argparse
  parser = argparse.ArgumentParser(description='Swift Nav Console.')
  parser.add_argument('-p', '--port', nargs=1, default=[None],
                      help='specify the serial port to use.')
  parser.add_argument('-b', '--baud', nargs=1, default=[s.SERIAL_BAUD],
                      help='specify the baud rate to use.')
  return parser.parse_args()

args = get_args()
port = args.port[0]
baud = args.baud[0]

from traits.etsconfig.api import ETSConfig
ETSConfig.toolkit = 'qt4'

from piksi_tools.console.utils import determine_path
from traits.api import Bool, Str, Instance, Dict, HasTraits, Int, Button, List, Enum
from traitsui.api import Item, Label, View, HGroup, VGroup, VSplit, HSplit, Tabbed, \
                         InstanceEditor, EnumEditor, ShellEditor, Handler, Spring, \
                         TableEditor, UItem, Action

# When bundled with pyInstaller, PythonLexer can't be found. The problem is
# pygments.lexers is doing some crazy magic to load up all of the available
# lexers at runtime which seems to break when frozen.
#
# The horrible workaround is to load the PythonLexer class explicitly and then
# manually insert it into the pygments.lexers module.
from pygments.lexers.agile import PythonLexer
import pygments.lexers
pygments.lexers.PythonLexer = PythonLexer
try:
  import pygments.lexers.c_cpp
except ImportError:
  pass

# These imports seem to be required to make pyinstaller work?
# (usually traitsui would load them automatically)
if ETSConfig.toolkit == 'qt4':
  import pyface.ui.qt4.resource_manager
  import pyface.ui.qt4.python_shell
from pyface.image_resource import ImageResource

basedir = determine_path()
icon = ImageResource('icon', search_path=['images', os.path.join(basedir, 'images')])

from piksi_tools.console.data_view import DataView
from piksi_tools.console.baseline_view import BaselineView
from piksi_tools.console.summary_view import SummaryView
if ETSConfig.toolkit != 'null':
  from enable.savage.trait_defs.ui.svg_button import SVGButton
else:
  SVGButton = dict

from piksi_tools.console.views_utils import ViewsUtils

CONSOLE_TITLE = u'RTK监控系统'

class SwiftConsole(HasTraits):
  link = Instance(sbpc.Handler)
  data_view = Instance(DataView)
  baseline_view = Instance(BaselineView)
  summary_view = Instance(SummaryView)
  utils = Instance(ViewsUtils)

  view = View(
    VSplit(
      Tabbed(
        Item('data_view', style='custom', label=u'数据采集'),
        Item('baseline_view', style='custom', label=u'实时'),
        Item('summary_view', style='custom', label=u'总结'),
        show_labels=False
      ),
    ),
    icon = icon,
    dock = 'fixed',
    resizable = False,
    width = 800,
    height = 600,
    title = CONSOLE_TITLE,
  )

  def _summary_view_fired(self):
    self.summary_view.position_threshold = self.baseline_view.position_threshold
    self.summary_view.depth_threshold = self.baseline_view.depth_threshold
    self.summary_view.time_threshold = self.baseline_view.time_threshold

  def __init__(self, link):
    try:
      self.link = link
      self.data_view = DataView()
      self.baseline_view = BaselineView(self.link)
      self.summary_view = SummaryView(self.link)
      self.utils = ViewsUtils(self.data_view, self.baseline_view, self.summary_view)
      self.data_view.set_utils(self.utils)
      self.baseline_view.set_utils(self.utils)
      self.summary_view.set_utils(self.utils)
    except:
      import traceback
      traceback.print_exc()

# Make sure that SIGINT (i.e. Ctrl-C from command line) actually stops the
# application event loop (otherwise Qt swallows KeyboardInterrupt exceptions)
signal.signal(signal.SIGINT, signal.SIG_DFL)

# If using a device connected to an actual port, then invoke the
# regular console dialog for port selection
class PortChooser(HasTraits):
  ports = List()
  bauds = List()
  port = Str()
  baud = Int(115200)
  traits_view = View(
    VGroup(
      HGroup(
        Label(u'端口号:'),
        Item('port', editor=EnumEditor(name='ports'), show_label=False),
      ),
      HGroup(
        Label(u'波特率:'),
        Item('baud', editor=EnumEditor(name='bauds'), show_label=False),
      ),
    ),
    buttons = ['OK'],

    close_result=False,
    resizable = False,
    scrollable = False,
    icon = icon,
    width = 250,
    title = u'选择串口设备',
  )

  def __init__(self):
    try:
      self.ports = [p for p, _, _ in s.get_ports()]
      if self.ports:
        self.port = self.ports[0]
      self.bauds = [4800, 9600, 19200, 38400, 43000, 56000, 57600, 115200]
    except TypeError:
      pass

if not port:
  port_chooser = PortChooser()
  is_ok = port_chooser.configure_traits()
  port = port_chooser.port
  baud = port_chooser.baud
  if not port or not is_ok:
    print "No serial device selected!"
    sys.exit(1)
  else:
    print "Using serial device '%s', bauderate %d" % (port, baud)

with s.get_driver(False, port, baud) as driver:
  with sbpc.Handler(sbpc.Framer(driver.read, driver.write, False)) as link:
    with s.get_logger() as logger:
      sbpc.Forwarder(link, logger).start()
      SwiftConsole(link).configure_traits()

# Force exit, even if threads haven't joined
try:
  os._exit(0)
except:
  pass
