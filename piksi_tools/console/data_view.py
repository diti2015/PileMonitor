# -*- coding: utf-8 -*-

from traits.api import Instance, Dict, HasTraits, Array, Float,   on_trait_change, List, Int, Button, Bool
from traitsui.api import Item, View, HGroup, VGroup, ArrayEditor, HSplit, TabularEditor
from traitsui.tabular_adapter import TabularAdapter

class SimpleAdapter(TabularAdapter):
  columns = [('Device ID', 0),
             ('N', 1),
             ('E', 2),
             ('D', 3),
             ('Num. Sats.', 4),
             ('Flags', 5),
             ('Depth', 6)]
  width = (800-6)/7
  alignment = 'right'
  can_edit = False

class DataView(HasTraits):
  table = List()
  table_dict = {}
  view = View(
      Item('table', style = 'readonly', editor = TabularEditor(adapter=SimpleAdapter()), show_label=False),
  )

  def set_table(self, data_dict):
    table = []
    for key in data_dict:
      table.append(data_dict[key])
    self.table = table

  def set_utils(self, utils):
    self.utils = utils

  def __init__(self):
    super(DataView, self).__init__()
