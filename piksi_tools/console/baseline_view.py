# -*- coding: utf-8 -*-

from traits.api import Instance, Dict, HasTraits, Array, Float, on_trait_change, List, Int, Button, Bool, Str, Font
from traitsui.api import Item, View, HGroup, VGroup, ArrayEditor, HSplit, TabularEditor, EnumEditor, TextEditor, Spring
from traitsui.tabular_adapter import TabularAdapter
from chaco.api import ArrayPlotData, Plot
from chaco.tools.api import ZoomTool, PanTool
from enable.api import ComponentEditor
from enable.savage.trait_defs.ui.svg_button import SVGButton
from pyface.api import GUI
from piksi_tools.console.utils import plot_square_axes, determine_path

import math
import os
import numpy as np
import datetime
import time

from sbp.piksi      import *
from sbp.navigation import *

import copy
from settings_list import SettingsList

class BaselineView(HasTraits):
  python_console_cmds = Dict()

  plot = Instance(Plot)
  plot_data = Instance(ArrayPlotData)

  running = Bool(True)
  zoomall = Bool(False)

  clear_button = SVGButton(
    label='', tooltip='Clear',
    filename=os.path.join(determine_path(), 'images', 'iconic', 'x.svg'),
    width=16, height=16
  )
  zoomall_button = SVGButton(
    label='', tooltip='Zoom All', toggle=True,
    filename=os.path.join(determine_path(), 'images', 'iconic', 'fullscreen.svg'),
    width=16, height=16
  )
  paused_button = SVGButton(
    label='', tooltip='Pause', toggle_tooltip='Run', toggle=True,
    filename=os.path.join(determine_path(), 'images', 'iconic', 'pause.svg'),
    toggle_filename=os.path.join(determine_path(), 'images', 'iconic', 'play.svg'),
    width=16, height=16
  )

  position_threshold = Str()
  depth_threshold = Str()
  time_threshold = Str()

  focused_dev = Str
  dev_all_list = List(['All', 'Preset'])

  traits_view = View(
    HSplit(
      VGroup(
        HGroup(
          Item('paused_button', show_label=False),
          Item('clear_button', show_label=False),
          Item('zoomall_button', show_label=False),
          Item('focused_dev', editor=EnumEditor(name='dev_all_list'), label=u'焦点'),
          Spring(),
          HGroup(
            Item('position_threshold', editor=TextEditor(auto_set=False, enter_set=True), label=u'位置阈值'),
            Item('depth_threshold', editor=TextEditor(), label=u'深度阈值'),
            Item('time_threshold', editor=TextEditor(), label=u'时间阈值'),
          )
        ),
        Item(
          'plot',
          show_label = False,
          editor = ComponentEditor(bgcolor = (0.8,0.8,0.8)),
        )
      )
    ),
  )

  def _position_threshold_changed(self):
    try:
      if int(self.position_threshold) < 0 or int(self.position_threshold) > 1e6:
        self.position_threshold = str(0)
    except:
      self.position_threshold = str(0)
    self.settings_yaml.set_threshold_field('position', int(self.position_threshold))
    self.settings_yaml.dump()

  def _depth_threshold_changed(self):
    try:
      if int(self.depth_threshold) < 0 or int(self.depth_threshold) > self.plot_history_max:
        self.plot_history_max = str(0)
    except:
      self.plot_history_max = str(0)
    self.settings_yaml.set_threshold_field('depth', int(self.depth_threshold))
    self.settings_yaml.dump()

  def _time_threshold_changed(self):
    try:
      if int(self.time_threshold) < 0:
        self.time_threshold = str(0)
    except:
      self.time_threshold = str(0)
    self.settings_yaml.set_threshold_field('time', int(self.time_threshold))
    self.settings_yaml.dump()

  def _focused_dev_changed(self):
    self.zoom_once = True

  def _zoomall_button_fired(self):
    self.zoomall = not self.zoomall

  def _paused_button_fired(self):
    self.running = not self.running

  def _clear_button_fired(self):
    self.neds[:] = np.NAN
    self.fixeds[:] = False
    self.devs[:] = 0
    self.times[:] = 0
    self.plot_data.set_data('n_fixed', [])
    self.plot_data.set_data('e_fixed', [])
    self.plot_data.set_data('d_fixed', [])
    self.plot_data.set_data('n_float', [])
    self.plot_data.set_data('e_float', [])
    self.plot_data.set_data('d_float', [])
    self.plot_data.set_data('n_satisfied', [])
    self.plot_data.set_data('e_satisfied', [])
    self.plot_data.set_data('n_focused', [])
    self.plot_data.set_data('e_focused', [])
    self.plot_data.set_data('t', [])

  def _baseline_callback_ned(self, sbp_msg, **metadata):
    # Updating an ArrayPlotData isn't thread safe (see chaco issue #9), so
    # actually perform the update in the UI thread.
    if self.running:
      #GUI.invoke_later(self.baseline_callback, sbp_msg)

      soln = MsgBaselineNED(sbp_msg)
      GUI.invoke_later(self.baseline_callback, soln)

      cnt = self.cnt % 4
      fake_sbp_msg = copy.copy(soln)
      if cnt == 3:
        fake_sbp_msg.e = 217371
        fake_sbp_msg.n = 100837 - (cnt+1) * 10e3
      else:
        fake_sbp_msg.e = 217371 + cnt * 20e3
        fake_sbp_msg.n = 100837 - cnt * 20e3
      fake_sbp_msg.sender = 100 + cnt
      fake_sbp_msg.flags = cnt
      soln = fake_sbp_msg
      self.cnt += 1
      GUI.invoke_later(self.baseline_callback, soln)

    # _threshold_satisfied()函数计算需要优化
    # 或者保持数据发送频率小于2(/s)
    time.sleep(0.5)

  def baseline_callback(self, sbp_msg):
    #soln = MsgBaselineNED(sbp_msg)
    soln = sbp_msg

    soln.n = soln.n * 1e-3
    soln.e = soln.e * 1e-3
    soln.d = soln.d * 1e-3

    dist = np.sqrt(soln.n**2 + soln.e**2 + soln.d**2)

    tow = soln.tow * 1e-3
    if self.nsec is not None:
      tow += self.nsec * 1e-9

    #row_data = [soln.sender, soln.n, soln.e, soln.d, soln.n_sats, soln.flags, soln.depth]
    row_data = [soln.sender, soln.n, soln.e, soln.d, soln.n_sats, soln.flags]
    try:
      key = int(row_data[0])
      self.data_dict[key] = row_data
    except:
      pass
    self.utils.setDataViewTable(self.data_dict)
    if soln.sender not in self.dev_list:
      self.dev_list.append(soln.sender)
      self.dev_all_list.append(str(soln.sender))

    # Rotate array, deleting oldest entries to maintain
    # no more than N in plot
    self.neds[1:] = self.neds[:-1]
    self.fixeds[1:] = self.fixeds[:-1]
    self.devs[1:] = self.devs[:-1]
    self.times[1:] = self.times[:-1]

    # Insert latest position
    self.neds[0][:] = [soln.n, soln.e, soln.d]
    self.fixeds[0] = (soln.flags & 1) == 1
    self.devs[0] = int(soln.sender)
    self.times[0]= int(time.time())

    neds_all = []
    neds_fixed = []
    neds_float = []
    neds_satisfied = []
    neds_unsatisfied = []
    devs = np.unique(self.devs)
    if devs[0] == 0:
      devs = devs[1:]
    for dev in devs:
      is_dev = np.equal(dev, self.devs)
      neds_all.append(self.neds[is_dev][0])
      try:
        neds_fixed.append(self.neds[np.logical_and(is_dev, self.fixeds)][0])
      except:
        pass
      try:
        neds_float.append(self.neds[np.logical_and(is_dev, np.logical_not(self.fixeds))][0])
      except:
        pass
      position_satisfied, depth_satisfied, time_satisfied = self._threshold_satisfied()
      is_satisfied = np.logical_and(position_satisfied, depth_satisfied, time_satisfied)
      try:
        neds_satisfied.append(self.neds[np.logical_and(is_dev, is_satisfied)][0])
      except:
        pass
      try:
        neds_unsatisfied.append(self.neds[np.logical_and(is_dev, np.logical_not(is_satisfied))][0])
      except:
        pass
    neds_all = np.array(neds_all)
    neds_fixed = np.array(neds_fixed)
    neds_float = np.array(neds_float)
    neds_satisfied = np.array(neds_satisfied)
    neds_unsatisfied = np.array(neds_unsatisfied)
    self.neds_all = neds_all
    self.neds_satisfied = neds_satisfied
    self.neds_unsatisfied = neds_unsatisfied

    neds_focused = np.empty((0, 3))
    if self.focused_dev == '':
      pass
    elif self.focused_dev == 'All':
      neds_focused = neds_all
    elif self.focused_dev != 'Preset':
      neds_focused = np.array([self.neds[np.equal(self.devs, int(self.focused_dev))][0]])

    #if not all(map(any, np.isnan(neds_fixed))):
    if len(neds_fixed) > 0:
      self.plot_data.set_data('n_fixed', neds_fixed.T[0])
      self.plot_data.set_data('e_fixed', neds_fixed.T[1])
      self.plot_data.set_data('d_fixed', neds_fixed.T[2])
    #if not all(map(any, np.isnan(neds_float))):
    if len(neds_float) > 0:
      self.plot_data.set_data('n_float', neds_float.T[0])
      self.plot_data.set_data('e_float', neds_float.T[1])
      self.plot_data.set_data('d_float', neds_float.T[2])
    if len(neds_satisfied) > 0:
      self.plot_data.set_data('n_satisfied', neds_satisfied.T[0])
      self.plot_data.set_data('e_satisfied', neds_satisfied.T[1])
    if len(neds_unsatisfied) > 0:
      self.plot_data.set_data('n_unsatisfied', neds_unsatisfied.T[0])
      self.plot_data.set_data('e_unsatisfied', neds_unsatisfied.T[1])
    if len(self.presets) > 0:
      self.plot_data.set_data('n_preset', self.presets['n'])
      self.plot_data.set_data('e_preset', self.presets['e'])
    if len(neds_focused) > 0:
      self.plot_data.set_data('n_focused', neds_focused.T[0])
      self.plot_data.set_data('e_focused', neds_focused.T[1])

    if self.zoomall:
      self._zoomall()

    if self.zoom_once:
      if self.focused_dev == 'All':
        self._zoomall()
      elif self.focused_dev == 'Preset':
        plot_square_axes(self.plot, 'e_preset', 'n_preset')
      else:
        plot_square_axes(self.plot, 'e_focused', 'n_focused')
      self.zoom_once = False

  # 计算阈值，函数功能待测试
  def _threshold_satisfied(self):
    position_satisfieds = np.zeros(self.plot_history_max, dtype=bool)
    depth_satisfieds = np.ones(self.plot_history_max, dtype=bool)
    time_satisfieds = np.ones(self.plot_history_max, dtype=bool)

    devs = np.unique(self.devs)
    for dev in devs:
      dev_neds = self.neds[np.equal(self.devs, dev)]

      ned_mean = map(np.mean, zip(*dev_neds))
      dn = ned_mean[0] - self.presets['n']
      de = ned_mean[1] - self.presets['e']
      d = np.sqrt(np.add(np.square(dn), np.square(de)))
      dmin = np.min(d)
      if dmin < int(self.position_threshold):
        position_satisfieds[np.equal(dev, self.devs)] = True

    ne_depth = self.neds[0:int(self.depth_threshold)]
    for ned in ne_depth:
      dn = ned[0] - self.presets['n']
      de = ned[1] - self.presets['e']
      d = np.sqrt(np.add(np.square(dn), np.square(de)))
      dmin = np.min(d)
      if dmin > int(self.position_threshold):
        depth_satisfieds[np.equal(dev, self.devs)] = False
        break

    cur_time = time.time()
    for dev, t, ned in zip(self.devs, self.times, self.neds):
      dt = cur_time - t
      if dt > int(self.time_threshold):
        break
      dn = ned[0] - self.presets['n']
      de = ned[1] - self.presets['e']
      d = np.sqrt(np.add(np.square(dn), np.square(de)))
      dmin = np.min(d)
      if dmin > int(self.position_threshold):
        time_satisfieds[np.equal(dev, self.devs)] = False

    return (position_satisfieds, depth_satisfieds, time_satisfieds)

  def _zoomall(self):
    plot_square_axes(self.plot, ('e_fixed', 'e_float', 'e_preset'), ('n_fixed', 'n_float', 'n_preset'))

  def _read_preset_points(self, filename='preset.csv'):
    preset_points = {}
    px = []
    py = []
    try:
      if os.path.isfile(filename):
        path_to_file = filename
      else:
        path_to_file = os.path.join(determine_path(), filename)
      f = open(path_to_file, 'r')
      for i in f.readlines():
        xy = i.split(',')
        if len(xy) < 2:
          continue
        try:
          x = float(xy[0])*1e-3
          y = float(xy[1])*1e-3
          px.append(x)
          py.append(y)
        except:
          continue
    except:
      pass
    preset_points['e'] = px
    preset_points['n'] = py
    return preset_points

  def set_utils(self, utils):
    self.utils = utils

  def __init__(self, link, plot_history_max=1000):
    super(BaselineView, self).__init__()
    self.plot_data = ArrayPlotData(n_fixed=[0.0], e_fixed=[0.0], d_fixed=[0.0],
                                   n_float=[0.0], e_float=[0.0], d_float=[0.0],
                                   n_satisfied=[0.0], e_satisfied=[0.0],
                                   n_unsatisfied=[0.0], e_unsatisfied=[0.0],
                                   n_focused=[0.0], e_focused=[0.0],
                                   t=[0.0],
                                   e_preset=[], n_preset=[])
    self.plot_history_max = plot_history_max

    self.neds = np.empty((plot_history_max, 3))
    self.neds[:] = np.NAN
    self.fixeds = np.zeros(plot_history_max, dtype=bool)
    self.devs = np.zeros(plot_history_max)
    self.times = np.zeros(plot_history_max)

    self.plot = Plot(self.plot_data)
    color_float = (0.5, 0.5, 1.0)
    color_fixed = 'orange'
    color_satisfied = (0.3, 1.0, 0.0)
    pts_float = self.plot.plot(('e_float', 'n_float'),
        type='scatter',
        color=color_float,
        marker='plus',
        line_width=2.0,
        marker_size=8.0)
    pts_fixed = self.plot.plot(('e_fixed', 'n_fixed'),
        type='scatter',
        color=color_fixed,
        marker='plus',
        line_width=2.0,
        marker_size=8.0)
    threshold_satisfied = self.plot.plot(('e_satisfied', 'n_satisfied'),
        type='scatter',
        color=color_satisfied,
        marker='dot',
        line_width=0.0,
        marker_size=4.5)
    threshold_unsatisfied = self.plot.plot(('e_unsatisfied', 'n_unsatisfied'),
        type='scatter',
        color='red',
        marker='dot',
        line_width=0.0,
        marker_size=4.5)
    preset = self.plot.plot(('e_preset', 'n_preset'),
        type='scatter',
        color='black',
        marker='plus',
        marker_size=1.5,
        line_width=0.0)
    pts_focused = self.plot.plot(('e_focused', 'n_focused'),
        type='scatter',
        color='black',
        marker='dot',
        line_width=0.0,
        marker_size=0.0)
    #plot_labels = ['RTK Fixed','RTK Float']
    #plots_legend = dict(zip(plot_labels, [pts_fixed, pts_float]))
    #self.plot.legend.plots = plots_legend
    #self.plot.legend.visible = True
    self.plot.legend.visible = False

    self.plot.index_axis.tick_label_position = 'inside'
    self.plot.index_axis.tick_label_color = 'gray'
    self.plot.index_axis.tick_color = 'gray'
    self.plot.index_axis.title='E (meters)'
    self.plot.index_axis.title_spacing = 5
    self.plot.value_axis.tick_label_position = 'inside'
    self.plot.value_axis.tick_label_color = 'gray'
    self.plot.value_axis.tick_color = 'gray'
    self.plot.value_axis.title='N (meters)'
    self.plot.value_axis.title_spacing = 5
    self.plot.padding = (25, 25, 25, 25)

    self.plot.tools.append(PanTool(self.plot))
    zt = ZoomTool(self.plot, zoom_factor=1.1, tool_mode="box", always_on=False)
    self.plot.overlays.append(zt)

    self.week = None
    self.nsec = 0

    self.link = link
    self.link.add_callback(self._baseline_callback_ned, SBP_MSG_BASELINE_NED)

    self.cnt = 0
    self.dev_list = []
    self.data_dict = {}
    self.presets = self._read_preset_points()

    self.settings_yaml = SettingsList()
    self.position_threshold = str(self.settings_yaml.get_threshold_field('position'))
    self.depth_threshold = str(self.settings_yaml.get_threshold_field('depth'))
    self.time_threshold = str(self.settings_yaml.get_threshold_field('time'))

    self.zoom_once = False

    self.python_console_cmds = {
      'baseline': self
    }
