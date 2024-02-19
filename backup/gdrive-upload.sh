#!/bin/bash

set -e
rclone copy /backup gdrive:backup
echo "$(date "+%F-%H:%M:%S") Files uploaded"
sudo rm /backup/*
echo "$(date "+%F-%H:%M:%S") Files deleted"
