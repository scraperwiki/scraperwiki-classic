from django import forms
from django.forms import ModelForm, ChoiceField
from django.utils.safestring import mark_safe
from django.contrib.auth.models import User

from market.models import Solicitation
from scraper.models import Scraper

class SolicitationForm (ModelForm):

    title = forms.CharField(max_length=150)
    details = forms.CharField(widget=forms.Textarea)
    link = forms.URLField()
    price = forms.ChoiceField(label="Bounty", choices=((50, mark_safe('&pound;50')),(100, mark_safe('&pound;100')), (250, mark_safe('&pound;250')), (500, mark_safe('&pound;500')), (1000, mark_safe('&pound;1000')), (0, 'Just a suggestion, no bounty')))

    class Meta:
        model = Solicitation
        fields = ('title', 'link', 'details', 'price')

class SolicitationClaimForm (ModelForm):

    def __init__(self, *args, **kwargs):
         user = User.objects.get(id=kwargs.pop('user_id'))
         queryset = user.scraper_set.filter(userscraperrole__role='owner', deleted=False).order_by('-created_at')
         super(SolicitationClaimForm, self).__init__(*args, **kwargs)
         self.fields['scraper'] = forms.ModelChoiceField(
                 required=True,
                 queryset=queryset,)

         self.fields['confirmed'] = forms.BooleanField(widget=forms.CheckboxInput(),
                               required=True, 
                               label= u'I will not breach anyone\'s copyright, privacy or breach any laws including the Data Protection Act 1998',
                               error_messages={ 'required': "You must agree to abide by the Data Protection Act 1998" })                 

