# -*- coding: utf-8 -*-

from traits.api import Instance, Dict, HasTraits, Array, Float, on_trait_change, List, Int, Button, Bool, Str, Font, Any
from traitsui.api import Item, View, HGroup, VGroup, ArrayEditor, HSplit, TabularEditor, EnumEditor, TextEditor, Spring
from traitsui.tabular_adapter import TabularAdapter
from chaco.api import ArrayPlotData, Plot, DataLabel
from chaco.tools.api import ZoomTool, PanTool
from enable.api import ComponentEditor, BaseTool, AbstractOverlay
from enable.savage.trait_defs.ui.svg_button import SVGButton
from pyface.api import GUI
from piksi_tools.console.utils import plot_square_axes, determine_path

import numpy as np

import copy
from settings_list import SettingsList
import time, os

labelItems = []

class HittestTool(BaseTool, AbstractOverlay):
    pt_plot=Any()
    visible=True
    pt = Any()

    # How many pixels away we may be from the line in order to do
    threshold = Int(20)

    def normal_mouse_move(self, event):
        x,y = event.x, event.y
        if self.pt_plot.orientation == 'h':
          x,y = self.component.map_data((x,y))
        else:
          x,y = self.component.map_data((y,x))
        x,y = self.pt_plot.map_screen((x,y))[0]
        self.pt = self.pt_plot.hittest((x,y), threshold=self.threshold)
        self.request_redraw()

    def overlay(self, plot, gc, view_bounds=None, mode="normal"):
        if self.pt is not None:
            x,y = self.pt_plot.map_data(self.pt)
            #x,y = plot.map_screen((x,y))
            #gc.draw_rect((int(x)-2, int(y)-2, 4, 4))
            d = 0
            t = 0
            if(len(labelItems) > 0):
                for n, e, depth, dtime in labelItems:
                    if np.sqrt(np.add(np.square(x-e),np.square(y-n))) < 1e-3:
                        d = depth
                        t = dtime
                        break
            text = 'Depth & Time (max): %d, %d' % (d, t)

	    label = DataLabel(component=plot, data_point=(x, y),
			       label_position="bottom right",
			       border_visible=False,
			       bgcolor="transparent",
			       marker_color="blue",
			       marker_line_color="transparent",
			       marker="diamond",
                               marker_size=2,
			       font='modern 14',
                               label_text=text,
                               #label_format="%(x).2f, %(y).2f",
                               label_format="",
			       arrow_visible=False)
	    label.overlay(plot, gc)

class SummaryView(HasTraits):
  python_console_cmds = Dict()

  plot = Instance(Plot)
  plot_data = Instance(ArrayPlotData)

  position_threshold = Str()
  depth_threshold = Str()
  time_threshold = Str()

  focused_dev = Str
  dev_all_list = List(['All'])

  refresh = Button(u'刷新')

  traits_view = View(
    HSplit(
      VGroup(
        HGroup(
          Item('refresh', show_label = False),
          Item('focused_dev', editor=EnumEditor(name='dev_all_list'), label=u'焦点'),
          Spring(),
          HGroup(
            Item('position_threshold', editor=TextEditor(auto_set=False, enter_set=True), label=u'位置阈值', style='readonly'),
            Item('depth_threshold', editor=TextEditor(), label=u'深度阈值', style='readonly'),
            Item('time_threshold', editor=TextEditor(), label=u'时间阈值', style='readonly'),
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

  def _refresh_fired(self):
    global labelItems
    self.dev_all_list = self.utils.baseline.dev_all_list
    self.dev_all_list.remove('Preset')
    self.neds_all = self.utils.baseline.neds_all
    self.neds_satisfied = self.utils.baseline.neds_satisfied
    self.neds_unsatisfied = self.utils.baseline.neds_unsatisfied
    self.neds = self.utils.baseline.neds
    self.devs = self.utils.baseline.devs
    self.times = self.utils.baseline.times
    self.presets = self.utils.baseline.presets
    self.time = time.time()

    if len(self.neds_all) > 0:
      self.plot_data.set_data('n_all', self.neds_all.T[0])
      self.plot_data.set_data('e_all', self.neds_all.T[1])
    if len(self.neds_satisfied) > 0:
      self.plot_data.set_data('n_satisfied', self.neds_satisfied.T[0])
      self.plot_data.set_data('e_satisfied', self.neds_satisfied.T[1])
    if len(self.neds_unsatisfied) > 0:
      self.plot_data.set_data('n_unsatisfied', self.neds_unsatisfied.T[0])
      self.plot_data.set_data('e_unsatisfied', self.neds_unsatisfied.T[1])
    labelItems, csv_text = self._max_depth_time()

    path_to_file = os.path.join(determine_path(), 'summary.csv')
    summary_file = open(path_to_file, 'w')
    summary_file.write(csv_text)
    summary_file.close()

  def _focused_dev_changed(self):
    neds_focused = np.empty((0, 3))
    if self.focused_dev == '':
      pass
    elif self.focused_dev == 'All':
      self._zoomall()
    else:
      neds_focused = np.array([self.neds[np.equal(self.devs, int(self.   focused_dev))][0]])
    if len(neds_focused) > 0:
      self.plot_data.set_data('n_focused', neds_focused.T[0])
      self.plot_data.set_data('e_focused', neds_focused.T[1])
    if self.focused_dev == 'All':
      self._zoomall()
    else:
      plot_square_axes(self.plot, 'e_focused', 'n_focused')

  def _zoomall(self):
    plot_square_axes(self.plot, ('e_satisfied', 'e_unsatisfied'), ('n_satisfied', 'e_unsatisfied'))

  def _max_depth_time(self):
    pt_label_items = []
    csv_text = 'ID, N, E, Depth, Time\n'
    dtime = 0
    depth = 0
    devs = np.unique(self.devs)
    if devs[0] == 0:
      devs = devs[1:]
    for dev in devs:
      dev_neds = self.neds[np.equal(self.devs, dev)]
      dev_times = self.times[np.equal(self.devs, dev)]
      for t, ned in zip(dev_times, dev_neds):
        dn = ned[0] - self.presets['n']
        de = ned[1] - self.presets['e']
        d = min(np.sqrt(np.add(np.square(dn), np.square(de))))
        if d > int(self.position_threshold):
          break
        dtime = self.time - t
        depth += 1
      pt_label_items.append((dev_neds[0].T[0], dev_neds[0].T[1], depth, int(dtime)))
      text = "%d, %.3f, %.3f, %d, %d\n" % (dev, dev_neds[0].T[0], dev_neds[0].T[1], depth, int(dtime))
      csv_text +=text
    return pt_label_items, csv_text

  def set_utils(self, utils):
    self.utils = utils

  def __init__(self, plot_history_max=1000):
    self.plot_data = ArrayPlotData(n_satisfied=[0.0], e_satisfied=[0.0],
                                   n_unsatisfied=[0.0], e_unsatisfied=[0.0],
                                   n_all=[0.0], e_all=[0.0],
                                   n_focused=[0.0], e_focused=[0.0])
    self.plot_history_max = plot_history_max

    self.plot = Plot(self.plot_data)
    color_float = (0.5, 0.5, 1.0)
    color_fixed = 'orange'
    color_satisfied = (0.3, 1.0, 0.0)
    neds_all = self.plot.plot(('e_all', 'n_all'),
        type='scatter',
        color='red',
        marker='plus',
        line_width=0.0,
        marker_size=0.0)
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
    pts_focused = self.plot.plot(('e_focused', 'n_focused'),
        type='scatter',
        color='black',
        marker='dot',
        line_width=0.0,
        marker_size=0.0)
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
    self.hittest_tool = HittestTool(component=self.plot, pt_plot=neds_all[0])
    self.plot.tools.append(self.hittest_tool)
    self.plot.overlays.append(self.hittest_tool)

    self.zoom_once = False

    self.python_console_cmds = {
      'summary': self
    }
