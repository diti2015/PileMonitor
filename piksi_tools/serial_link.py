#!/usr/bin/env python

"""
The :mod:`piksi_tools.serial_link` module contains functions related to
setting up and running SBP message handling.
"""

import sys
import os
import time
import uuid
import warnings

from sbp.navigation import SBP_MSG_POS_ECEF, SBP_MSG_POS_LLH, SBP_MSG_BASELINE_ECEF, \
  SBP_MSG_BASELINE_NED, SBP_MSG_GPS_TIME
from sbp.piksi                          import MsgReset
from sbp.client.drivers.network_drivers import HTTPDriver
from sbp.client.drivers.pyserial_driver import PySerialDriver
from sbp.client.drivers.pyftdi_driver   import PyFTDIDriver
from sbp.client                         import Handler, Framer, Forwarder
from sbp.client.loggers.null_logger     import NullLogger

SERIAL_PORT  = "/dev/ttyUSB0"
SERIAL_BAUD  = 1000000
CHANNEL_UUID = '118db405-b5de-4a05-87b5-605cc85af924'
DEFAULT_BASE = "http://broker.testing.skylark.swiftnav.com"

def get_ports():
  """
  Get list of serial ports.
  """
  import serial.tools.list_ports
  return [p for p in serial.tools.list_ports.comports() if p[1][0:4] != "ttyS"]

def get_driver(use_ftdi=False, port=SERIAL_PORT, baud=SERIAL_BAUD):
  """
  Get a driver based on configuration options

  Parameters
  ----------
  use_ftdi : bool
    For serial driver, use the pyftdi driver, otherwise use the pyserial driver.
  port : string
    Serial port to read.
  baud : int
    Serial port baud rate to set.
  """
  try:
    if use_ftdi:
      return PyFTDIDriver(baud)
    return PySerialDriver(port, baud)
  # if finding the driver fails we should exit with a return code
  # currently sbp's py serial driver raises SystemExit, so we trap it
  # here
  except SystemExit:
    sys.exit(1)

def get_logger():
  return NullLogger()

def printer(sbp_msg, **metadata):
  """
  Default print callback

  Parameters
  ----------
  sbp_msg: SBP
    SBP Message to print out.
  """
  print sbp_msg.payload,

def get_uuid(channel, serial_id):
  """Returns a namespaced UUID based on the piksi serial number and a
  namespace.

  Parameters
  ----------
  channel : str
    UUID namespace
  serial_id : int
    Piksi unique serial number

  Returns
  ----------
  UUID4 string, or None on invalid input.

  """
  if isinstance(channel, str) and isinstance(serial_id, int) and serial_id > 0:
    return uuid.uuid5(uuid.UUID(channel), str(serial_id))
  else:
    return None

def run(args, link):
  """Spin loop for reading from the serial link.

  Parameters
  ----------
  args : object
    Argparse result.
  link : Handler
    Piksi serial handle

  """
  timeout = args.timeout
  if args.reset:
    link(MsgReset())
  try:
    if args.timeout is not None:
      expire = time.time() + float(args.timeout)
    while True:
      if timeout is None or time.time() < expire:
      # Wait forever until the user presses Ctrl-C
        time.sleep(1)
      else:
        print "Timer expired!"
        break
      if not link.is_alive():
        sys.stderr.write("ERROR: Thread died!")
        sys.exit(1)
  except KeyboardInterrupt:
    # Callbacks call thread.interrupt_main(), which throw a
    # KeyboardInterrupt exception. To get the proper error
    # condition, return exit code of 1. Note that the finally
    # block does get caught since exit itself throws a
    # SystemExit exception.
    sys.exit(1)
