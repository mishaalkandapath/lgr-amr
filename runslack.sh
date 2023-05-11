#!/bin/bash
if `test $1 -eq 1`
then 
    SLACK_BOT_TOKEN=$2 SLACK_BOT_TEXT="AMR & LGR disconnect" python3 sensor_message.py
elif `test $1 -eq 2`
then
    SLACK_BOT_TOKEN=$2 SLACK_BOT_TEXT="AMR disconnect" python3 sensor_message.py
elif `test $1 -eq 3`
then
    SLACK_BOT_TOKEN=$2 SLACK_BOT_TEXT="LGR disconnect" python3 sensor_message.py
else
    echo "invalid arguments"
fi