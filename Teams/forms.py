from django import forms
from .models import Team

class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ['name', 'is_public']

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if Team.objects.filter(name=name).exists():
            raise forms.ValidationError("A team with this name already exists.")
        return name

class TeamJoinRequestForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.team = kwargs.pop('team', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        if not self.user or not self.team:
            return cleaned_data

        from .models import TeamMembership, TeamJoinRequest
        if TeamMembership.objects.filter(team=self.team, user=self.user).exists():
            raise forms.ValidationError("You are already a member of this team.")

        if TeamJoinRequest.objects.filter(team=self.team, user=self.user, status="PENDING").exists():
            raise forms.ValidationError("You already have a pending request for this team.")

        return cleaned_data
