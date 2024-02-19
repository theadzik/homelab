#!/bin/bash

set -e
rclone copy /backup gdrive:backup
sudo rm /backup/*
