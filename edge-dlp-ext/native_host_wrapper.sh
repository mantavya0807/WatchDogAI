#!/bin/bash
echo "Wrapper started" >> /tmp/wrapper.log
date >> /tmp/wrapper.log
/usr/bin/python3 /Users/kanikagupta/Documents/GitHub/WatchDogAI/edge-dlp-ext/native_host.py "$@" 2>> /tmp/wrapper.log
echo "Wrapper ended" >> /tmp/wrapper.log
