import django.forms
from django.conf import settings
from django.forms import ModelForm, ChoiceField
from frontend.models import UserProfile
from contact_form.forms import ContactForm
from registration.forms import RegistrationForm
from django.utils.translation import ugettext_lazy as _


#from django.forms.extras.widgets import Textarea

class UserProfileForm (ModelForm):
    alert_frequency = ChoiceField(choices = ((0, 'Instant'), (3600, 'Once an hour')))
    class Meta:
        model = UserProfile
        fields = ('bio', 'alert_frequency')


class scraperContactForm(ContactForm):
  subject_dropdown = django.forms.ChoiceField(label="Subject type", choices=(('suggestion', 'Suggestion about how we can improve something'),('help', 'Help using ScraperWiki'), ('bug', 'A bug or error')))
  title = django.forms.CharField(widget=django.forms.TextInput(), label=u'Subject')
  recipient_list = ["julian@goatchurch.org.uk"] # temporary save because this isn't set [settings.FEEDBACK_EMAIL]


class RegistrationForm(RegistrationForm):
    """
    Subclass of ``RegistrationForm`` which adds a required checkbox
    for agreeing to a site's Terms of Service and makes sure the email address is unique.

    """
    tos = django.forms.BooleanField(widget=django.forms.CheckboxInput(),
                           label=_(u'I agree to the Scraper Wiki terms and conditions'),
                           error_messages={ 'required': _("You must agree to the ScraperWiki terms and conditions") })


    def clean_email(self):
       """
       Validate that the supplied email address is unique for the
       site.

       """
       if User.objects.filter(email__iexact=self.cleaned_data['email']):
           raise forms.ValidationError(_("This email address is already in use. Please supply a different email address."))
       return self.cleaned_data['email']