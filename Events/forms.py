from django import forms
from django.utils import timezone
from .models import Event
from Organizations.models import Organization, OrganizationMembership

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            'title', 'organization', 'visibility', 'scoring_strategy',
            'start_time', 'end_time', 'max_team_size', 'base_points',
            'minimum_points', 'decay_parameter'
        ]
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            # Filter organizations where the user is an owner or admin
            managed_orgs = OrganizationMembership.objects.filter(
                user=self.user,
                role__in=("OWNER", "ADMIN")
            ).values_list('organization_id', flat=True)
            self.fields['organization'].queryset = Organization.objects.filter(id__in=managed_orgs)

    def clean_title(self):
        title = self.cleaned_data.get('title')
        organization = self.cleaned_data.get('organization')
        if title and organization:
            if Event.objects.filter(organization=organization, title=title).exists():
                raise forms.ValidationError("An event with this title already exists in this organization.")
        return title

    def clean_start_time(self):
        start_time = self.cleaned_data.get('start_time')
        if start_time and start_time < timezone.now():
            raise forms.ValidationError("Start time must be in the future.")
        return start_time

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        base_points = cleaned_data.get('base_points')
        minimum_points = cleaned_data.get('minimum_points')
        max_team_size = cleaned_data.get('max_team_size')

        if start_time and end_time and end_time <= start_time:
            self.add_error('end_time', "End time must be after start time.")

        if base_points is not None and base_points <= 0:
            self.add_error('base_points', "Base points must be a positive integer.")

        if minimum_points is not None:
            if minimum_points <= 0:
                self.add_error('minimum_points', "Minimum points must be a positive integer.")
            elif base_points is not None and minimum_points >= base_points:
                self.add_error('minimum_points', "Minimum points must be less than base points.")

        if max_team_size is not None and max_team_size < 0:
            self.add_error('max_team_size', "Max team size must be 0 or a positive integer.")

        return cleaned_data


class JoinEventForm(forms.Form):
    access_code = forms.CharField(max_length=50, required=True, label="Access code")


class CreateTeamForm(forms.Form):
    name = forms.CharField(max_length=100, required=True, label="Team name")
    is_public = forms.BooleanField(required=False, initial=True, label="Public team")


class EventRegistrationForm(forms.Form):
    member_ids = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Select team members to register"
    )

    def __init__(self, *args, **kwargs):
        self.team = kwargs.pop('team', None)
        self.event = kwargs.pop('event', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.team:
            from Teams.models import TeamMembership
            memberships = TeamMembership.objects.filter(team=self.team).select_related('user')
            # Only include members who are not the captain (captain is auto-included)
            other_members = memberships.exclude(user=self.user)
            self.fields['member_ids'].choices = [
                (m.user.id, m.user.username) for m in other_members
            ]

    def clean(self):
        cleaned_data = super().clean()
        member_ids = cleaned_data.get('member_ids', [])
        # Count include captain
        total_selected = len(member_ids) + 1
        
        if self.event.max_team_size > 0 and total_selected > self.event.max_team_size:
            raise forms.ValidationError(f"This event allows a maximum of {self.event.max_team_size} members per team.")

        # Check if any selected member is already registered for this event
        from .models import EventRoster
        selected_uids = [int(uid) for uid in member_ids]
        selected_uids.append(self.user.id)
        
        already_registered = EventRoster.objects.filter(
            event=self.event,
            user_id__in=selected_uids
        ).select_related('user')
        
        if already_registered.exists():
            names = ", ".join([r.user.username for r in already_registered])
            raise forms.ValidationError(f"The following members are already registered for this event: {names}")

        return cleaned_data
