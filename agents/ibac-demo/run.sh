#!/bin/bash
set -e
exec "$(dirname "$0")/src/agent/run.sh"
