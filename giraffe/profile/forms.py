from django import forms


class ProfileForm(forms.Form):

    display_name = forms.CharField(max_length=100)
    email = forms.EmailField(required=False)