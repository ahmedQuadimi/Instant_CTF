from django import forms


class JoinEventForm(forms.Form):
    access_code = forms.CharField(max_length=50, required=True, label="Access code")


class CreateTeamForm(forms.Form):
    name = forms.CharField(max_length=100, required=True, label="Team name")
    is_public = forms.BooleanField(required=False, initial=True, label="Public team")


class TeamJoinRequestForm(forms.Form):
    pass  # Just a confirmation form, no fields needed
