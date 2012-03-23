import splinter
from lettuce import step,before,world,after

@step(u'(?:When|And) I click the vault members button')
def i_click_the_vault_members_button(step):
    world.browser.find_by_css('div.vault').first.find_by_css('a.vault_users').first.click()
    world.wait_for_fx()

@step(u'(?:Then|And) I type "([^"]*)" into the username box$')
def i_type_into_the_username_box(step, text):
    world.browser.find_by_css('div.vault').first.find_by_css('#username').first.fill(text)
