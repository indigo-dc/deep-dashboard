# -*- coding: utf-8 -*-

# Copyright 2019 Spanish National Research Council (CSIC)
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

import deep_dashboard.auth
import deep_dashboard.config


def list_opts():
    return [
        ('DEFAULT', deep_dashboard.config.opts),
        ('iam', deep_dashboard.auth.iam_opts),
        ('orchestrator', deep_dashboard.config.orchestrator_opts),
        ('cache', deep_dashboard.config.cache_opts),
    ]
