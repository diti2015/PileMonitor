#!/usr/bin/env python
# -*- coding: utf-8 -*-

class ViewsUtils:
  def __init__(self, data_view, baseline_view, summary_view):
    self.data = data_view
    self.baseline = baseline_view
    self.summary = summary_view
  def setDataViewTable(self, table):
    self.data.set_table(table)
