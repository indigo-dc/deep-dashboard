#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2018 Spanish National Research Council (CSIC)
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os
import sys

from aiohttp import web

import deep_dashboard
from deep_dashboard import config
from deep_dashboard import log


CONF = config.CONF

LOG = log.LOG

INTRO = """
         ##         ###
         ##       ######  ##
     .#####   #####   #######.  .#####.
    ##   ## ## //   ##  //  ##  ##   ##
    ##. .##  ###  ###   // ###  ##   ##
      ## ##    ####     ####    #####.
              Hybrid-DataCloud  ##
"""


def main():
    print(INTRO)

    config.configure(sys.argv[1:])

    LOG.info("Starting DEEP dashboard version %s", deep_dashboard.__version__)

    app = deep_dashboard.init(sys.argv[1:])

    try:
        web.run_app(
            app,
            handle_signals=True,
            host=CONF.listen_ip,
            port=CONF.listen_port,
            path=CONF.listen_path
        )
    finally:
        if CONF.listen_path:
            os.remove(CONF.listen_path)


if __name__ == "__main__":
    main()
