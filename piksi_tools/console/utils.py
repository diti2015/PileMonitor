# Copyright (C) 2011-2014 Swift Navigation Inc.
# Contact: Gareth McMullin <gareth@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

import sys
import traceback
import os


from traitsui.api import TextEditor

class MultilineTextEditor(TextEditor):
  """
  Override of TextEditor Class for a multi-line read only
  """

  def init(self, parent):
    parent.read_only = True
    parent.multi_line = True

def plot_square_axes(plot, xnames, ynames):
  try:
    minx = 1e6
    maxx = -1e6
    miny = 1e6
    maxy = -1e6
    is_changed = False
    if type(xnames) is str:
      xs = plot.data.get_data(xnames)
      ys = plot.data.get_data(ynames)
      if len(xs) > 0 and len(ys) > 0:
        minx = min(xs); maxx = max(xs)
        miny = min(ys); maxy = max(ys)
        is_changed = True
    else:
      for xname, yname in zip(xnames, ynames):
        xs = plot.data.get_data(xname)
        ys = plot.data.get_data(yname)
        if len(xs) > 0 and len(ys) > 0:
          minx = min(min(xs), minx); maxx = max(max(xs), maxx)
          miny = min(min(ys), miny); maxy = max(max(ys), maxy)
          is_changed = True
    if is_changed:
      minx -= 5; maxx += 5; miny -= 5; maxy += 5;
      rangex = maxx - minx
      rangey = maxy - miny
      try:
        aspect = float(plot.width) / plot.height
      except: aspect = 1
      if aspect * rangey > rangex:
        padding = (aspect * rangey - rangex) / 2
        plot.index_range.low_setting = minx - padding
        plot.index_range.high_setting = maxx + padding
        plot.value_range.low_setting = miny
        plot.value_range.high_setting = maxy
      else:
        padding = (rangex / aspect - rangey) / 2
        plot.index_range.low_setting = minx
        plot.index_range.high_setting = maxx
        plot.value_range.low_setting = miny - padding
        plot.value_range.high_setting = maxy + padding
      dy = plot.value_range.high_setting - plot.value_range.low_setting
      dx = plot.index_range.high_setting - plot.index_range.low_setting
  except Exception as e:
    sys.__stderr__.write(traceback.format_exc() + '\n')

def determine_path ():
    """Borrowed from wxglade.py"""
    try:
        root = __file__
        if os.path.islink (root):
            root = os.path.realpath (root)
        return os.path.dirname (os.path.abspath (root))
    except:
        print "There is no __file__ variable. Please contact the author."

