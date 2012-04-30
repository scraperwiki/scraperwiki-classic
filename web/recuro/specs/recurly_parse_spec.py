from nose.tools import assert_equals
from lxml import etree

from recuro.recurly_parser import Contact, Invoice, parse

recurly_contact = """
    <?xml version="1.0" encoding="UTF-8"?> <new_account_notification> <account> <account_code>3-test-20120424T152301</account_code> <username nil="true"></username> <email>test@testerson.com</email> <first_name>Test</first_name> <last_name>Testerson</last_name> <company_name></company_name> </account> </new_account_notification>
      """

recurly_new_sub = """
<?xml version="1.0" encoding="UTF-8"?> <new_subscription_notification> <account> <account_code>3-test-20120424T152301</account_code> <username nil="true"></username> <email>test@testerson.com</email> <first_name>Test</first_name> <last_name>Testerson</last_name> <company_name></company_name> </account> <subscription> <plan> <plan_code>individual</plan_code> <name>Individual</name> </plan> <uuid>1857330d579ebf7a6468454b2bbc812e</uuid> <state>active</state> <quantity type="integer">1</quantity> <total_amount_in_cents type="integer">1080</total_amount_in_cents> <activated_at type="datetime">2012-04-25T07:29:38Z</activated_at> <canceled_at type="datetime"></canceled_at> <expires_at type="datetime"></expires_at> <current_period_started_at type="datetime">2012-04-25T07:29:38Z</current_period_started_at> <current_period_ends_at type="datetime">2012-05-25T07:29:38Z</current_period_ends_at> <trial_started_at type="datetime"></trial_started_at> <trial_ends_at type="datetime"></trial_ends_at> </subscription> </new_subscription_notification>
    """

recurly_successful_payment = """
<?xml version="1.0" encoding="UTF-8"?> <successful_payment_notification> <account> <account_code>3-test-20120424T152301</account_code> <username nil="true"></username> <email>test@testerson.com</email> <first_name>Test</first_name> <last_name>Testerson</last_name> <company_name></company_name> </account> <transaction> <id>18582a537a05caeabd49944608aff282</id> <invoice_id>18582a535e93a28b1473734d758a9b0e</invoice_id> <invoice_number type="integer">1356</invoice_number> <action>purchase</action> <date type="datetime">2012-04-25T11:59:44Z</date> <amount_in_cents type="integer">1080</amount_in_cents> <status>success</status> <message>Test Gateway: Successful test transaction</message> <reference>12345</reference> <source>transaction</source> <cvv_result code="M">Match</cvv_result> <avs_result code="D">Street address and postal code match.</avs_result> <avs_result_street>Y</avs_result_street> <avs_result_postal>Y</avs_result_postal> <test type="boolean">true</test> <voidable type="boolean">true</voidable> <refundable type="boolean">true</refundable> </transaction> </successful_payment_notification>
"""

def it_detects_a_new_account_notification_and_creates_a_contact():
    obj = parse(recurly_contact)
    assert isinstance(obj, Contact)

def it_detects_a_successful_payment_notification_and_creates_an_invoice():
    obj = parse(recurly_successful_payment)
    assert isinstance(obj, Invoice)

def it_should_translate_new_account_in_to_contact_object():
    xero_contact = Contact(recurly_contact)
    assert_equals(xero_contact.number, "3-test-20120424T152301")
    assert_equals(xero_contact.first_name, "Test")
    assert_equals(xero_contact.last_name, "Testerson")
    assert_equals(xero_contact.email, "test@testerson.com")

def it_should_contact_recurly_to_get_further_contact_details():
    xero_contact = Contact(recurly_contact)
    xero_contact.get_address()

    assert_equals(xero_contact.address1, "ScraperWiki Limited")
    assert_equals(xero_contact.address2, "146 Brownlow Hill")
    assert_equals(xero_contact.city, "Liverpool")
    assert_equals(xero_contact.state, "MERSEYSIDE")
    assert_equals(xero_contact.country, "GB")
    assert_equals(xero_contact.zip, "L3 5RF")
    assert_equals(xero_contact.vat_number, "123456")

def it_translates_successful_payment_in_to_invoice_object():
    xero_invoice = Invoice(recurly_successful_payment)
    assert_equals(xero_invoice.amount_in_cents, 1080)
    assert_equals(xero_invoice.contact_number, "3-test-20120424T152301")
    assert_equals(xero_invoice.invoice_date, "2012-04-25T11:59:44Z")
    assert_equals(xero_invoice.status, 'PAID')
    assert_equals(xero_invoice.invoice_ref, 'RECURLY1356')

def it_should_contact_recurly_to_get_further_invoice_details():
    xero_invoice = Invoice(recurly_successful_payment)
    xero_invoice.get_tax_details()

    assert_equals(xero_invoice.vat_number, "123456")
    assert_equals(xero_invoice.subtotal_in_cents, 900)
    assert_equals(xero_invoice.tax_in_cents, 180)
    assert_equals(xero_invoice.total_in_cents, 1080)

def it_should_output_xero_invoice_xml():
    # See http://blog.xero.com/developer/api/invoices/
    xero_invoice = Invoice(recurly_successful_payment)
    xero_xml = xero_invoice.to_xml()
    doc = etree.fromstring(xero_xml)
    assert len(doc) > 0

    # Check the simple elements, which just have plain text as
    # their content, and no nested XML elements.
    simple_elements = dict(
        InvoiceNumber='RECURLY1356',
        Type='ACCREC',
        Date="2012-04-25",
        DueDate="2012-04-25",
        CurrencyCode='USD'
    )
    for element,value in simple_elements.items():
        assert_equals(doc.xpath("//%s" % element)[0].text, value)

    # Check the more complex, nested, elements.
    assert_equals(doc.xpath("//Contact/ContactNumber")[0].text,
        "3-test-20120424T152301")
    assert_equals(len(doc.xpath("//LineItem")), 1)

def it_replaces_company_name_with_customer_name_if_not_present():
    xero_contact = Contact(recurly_contact)
    assert_equals(xero_contact.name, "Test Testerson")

def it_should_output_xero_contact_xml():
    xero_contact = Contact(recurly_contact)
    xero_xml = xero_contact.to_xml()
    doc = etree.fromstring(xero_xml)
    assert len(doc) > 0
    assert_equals(doc.xpath("//Contact/ContactNumber")[0].text,
                    "3-test-20120424T152301")
    assert_equals(doc.xpath("//Contact/Name")[0].text, "Test Testerson")
    assert_equals(doc.xpath("//Contact/FirstName")[0].text, "Test")
    assert_equals(doc.xpath("//Contact/LastName")[0].text, "Testerson")
    assert_equals(doc.xpath("//Contact/EmailAddress")[0].text,
                    "test@testerson.com")
