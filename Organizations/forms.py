from django import forms
from .models import Organization

class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ['name', 'description']

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if Organization.objects.filter(name=name).exists():
            raise forms.ValidationError("An organization with this name already exists.")
        return name
