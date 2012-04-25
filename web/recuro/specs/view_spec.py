from recuro.views import notify
from recuro.xero import XeroPrivateClient

import helper
from mock import Mock, patch

recurly_xml = """
    <?xml version="1.0" encoding="UTF-8"?> <new_account_notification> <account> <account_code>3-test-20120424T152301</account_code> <username nil="true"></username> <email>test@testerson.com</email> <first_name>Test</first_name> <last_name>Testerson</last_name> <company_name></company_name> </account> </new_account_notification>
      """

@patch('recuro.recurly_parser.parse')
def it_should_pass_the_notification_to_the_notification_parser(mock_parse):
    rf = helper.RequestFactory()
    mock_request = rf.post('/notify/', dict(body=recurly_xml))
    response = notify(mock_request)
    assert mock_parse.called

@patch.object(XeroPrivateClient, 'save')
def it_should_call_save_on_the_contact(mock_save):
    rf = helper.RequestFactory()
    mock_request = rf.post('/notify/', dict(body=recurly_xml))
    response = notify(mock_request)
    assert mock_save.called

