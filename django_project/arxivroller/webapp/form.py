from django import forms

class ProfileForm(forms.Form):
    email = forms.EmailField(label='email', required=False)