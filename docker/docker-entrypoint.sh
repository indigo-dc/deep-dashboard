#!/usr/bin/env bash

set -e 

chown nobody -R /srv/deep-dashboard-runtime

exec su-exec nobody $(eval echo "$@")
