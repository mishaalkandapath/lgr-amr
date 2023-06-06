"""
Runs in python 3.10, hence needs to be run using a subprocess call from the main ptython function running in python3.5
"""

import logging
logging.basicConfig(level=logging.DEBUG)

import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

slack_token = os.environ["SLACK_BOT_TOKEN"] 
text = os.environ["SLACK_BOT_TEXT"] #whatever message is there to be sent
client = WebClient(token=slack_token)

try:
    response = client.chat_postMessage(
        channel="D03EGDT9WAF",
        text=text
    )
except SlackApiError as e:
    # You will get a SlackApiError if "ok" is False
    assert e.response["error"]    # str like 'invalid_auth', 'channel_not_found'