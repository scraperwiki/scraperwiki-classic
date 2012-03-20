import re
import sys
import unittest

from django.conf import settings
from frontend.views import subscribe

import helper

def ensure_private_key_is_set():
    assert settings.RECURLY_PRIVATE_KEY != None

def rendered_subscribe_page():
    rf = helper.RequestFactory()
    mock_request = rf.get('/subscribe/')
    response = subscribe(mock_request, 'individual')
    return response

def ensure_rendered_html_contains_signature():
    response = rendered_subscribe_page()
    assert 'signature' in response.content
    assert re.search(r"""signature: *['"][a-fA-F0-9-]+['"]""", response.content)

def ensure_rendered_html_contains_account_code():
    response = rendered_subscribe_page()
    assert re.search(r"""accountCode: *['"].+['"]""", response.content)
