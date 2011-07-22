import unittest
from selenium import selenium

class SeleniumTest(unittest.TestCase):

    _valid_username = ''
    _valid_password = ''    

    _selenium_host = ''
    _selenium_port = 4444
    _selenium_browser = None

    _app_url = ''

    def setUp(self, verbosity=1):
        self.verificationErrors = []
        self.selenium = selenium(SeleniumTest._selenium_host, SeleniumTest._selenium_port, 
                                 SeleniumTest._selenium_browser, SeleniumTest._app_url)
        self.selenium.start()
            
            # extract a title for the job from name of test.  must be done in the constructor or after start()
        self.selenium.set_context("sauce:job-name=%s" % self._testMethodName)  
        self.selenium.window_maximize()

        self.verbosity = verbosity

    def wait_for_page(self, doing=None):
        hit_limit = True
        if self.verbosity > 1:
            print "  SeleniumTest: waiting_for_page", self.selenium.get_location()
        try:
            self.selenium.wait_for_page_to_load('30000')
            hit_limit = False
        except:
            print 'Failed to load page in first 30 seconds, adding another 30'
        
        if hit_limit:
            try:
                self.selenium.wait_for_page_to_load('30000')
                hit_limit = False
            except:
                if not doing:
                    msg = 'It took longer than 60 seconds to visit %s, it may have failed' % self.selenium.get_location()
                else:
                    msg = 'It took longer than 60 seconds to: %s' % doing
                self.fail(msg=msg)


    def login(self, username, password):
        s = self.selenium
        s.open("/")
        s.click("link=Sign in or create an account")
        s.wait_for_page_to_load("30000")

        s.type( 'id_user_or_email', username)
        s.type( 'id_password', password)        
        
        s.click('login')
        s.wait_for_page_to_load("30000")                      
        
    def type_dictionary(self, d):
        for k,v in d.iteritems():
            self.selenium.type( k, v )
        
    def tearDown(self):
        self.selenium.stop()
        self.assertEqual([], self.verificationErrors)
