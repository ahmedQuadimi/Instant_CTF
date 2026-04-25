from django import forms
import hashlib
from .models import Challenge

class ChallengeForm(forms.ModelForm):
    flag = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Enter flag'}))

    class Meta:
        model = Challenge
        fields = ['name', 'category', 'description', 'connection_info', 'status', 'release_time']

    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop('event', None)
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['flag'].required = True

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name and self.event:
            query = Challenge.objects.filter(event=self.event, name=name)
            if self.instance.pk:
                query = query.exclude(pk=self.instance.pk)
            if query.exists():
                raise forms.ValidationError("A challenge with this name already exists in this event.")
        return name

    def clean_flag(self):
        flag = self.cleaned_data.get('flag', '').strip()
        if not flag and not self.instance.pk:
            raise forms.ValidationError("Flag is required on create.")
        return flag

    def clean(self):
        cleaned_data = super().clean()
        release_time = cleaned_data.get('release_time')
        if release_time and self.event:
            if release_time < self.event.start_time:
                self.add_error('release_time', "Release time must not be before event start time.")
        
        flag = cleaned_data.get('flag')
        if flag:
            cleaned_data['flag_hash'] = hashlib.sha256(flag.encode()).hexdigest()
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        flag_hash = self.cleaned_data.get('flag_hash')
        if flag_hash:
            instance.flag_hash = flag_hash
        if self.event:
            instance.event = self.event
        if commit:
            instance.save()
        return instance

class FlagSubmissionForm(forms.Form):
    flag = forms.CharField(max_length=255, required=True, label="Flag")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
