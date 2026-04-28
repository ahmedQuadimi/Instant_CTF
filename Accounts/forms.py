from django import forms
from .models import User

class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username']

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

from allauth.account.forms import LoginForm, SignupForm

class StandardLoginForm(LoginForm):
    def error_messages(self):
        return {
            "password_mismatch": "Invalid email or password.",
            "user_not_found": "Invalid email or password.",
            "account_inactive": "This account is currently inactive.",
        }

    def clean(self):
        try:
            return super().clean()
        except forms.ValidationError:
            # Allauth throws specific errors; we override to generic message
            raise forms.ValidationError("Invalid email or password.")

class StandardSignupForm(SignupForm):
    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1')
        p2 = cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', "Passwords do not match.")
        
        if p1 and len(p1) < 8:
            self.add_error('password1', "Password must be at least 8 characters long.")
            
        return cleaned_data
