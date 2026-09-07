#!/usr/bin/env bash

echo "Stopping all ORC UI instances..."

pkill -f 'python.*-m apps\.orcUi' 2>/dev/null || true

sleep 1

# Murder anything that ignored the polite request.
pkill -9 -f 'python.*-m apps\.orcUi' 2>/dev/null || true

echo "ORC UI stopped."

