from django import forms


class ImageCreationForm(forms.Form):
    image = forms.ImageField(label='Image')
