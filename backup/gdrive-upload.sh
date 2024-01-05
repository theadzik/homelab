#!/bin/bash

set -e
rclone move -v /backup gdrive:backup
echo "$(date "+%F-%H:%M:%S") Files uploaded"
