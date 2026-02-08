"""
Forms for user authentication and profile management.
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordResetForm
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser, Team, TeamMembership, Task, TaskComment, TaskAttachment


class CustomUserCreationForm(UserCreationForm):
    """
    Form for user registration with email and role selection.
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address'
        })
    )
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First name'
        })
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last name'
        })
    )
    role = forms.ChoiceField(
        choices=CustomUser.ROLE_CHOICES,
        initial='team_member',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })
    )

    class Meta:
        model = CustomUser
        fields = ('email', 'first_name', 'last_name', 'role', 'password1', 'password2')

    def clean_email(self):
        """Ensure email is unique."""
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('Email address is already registered.')
        return email

    def clean_password1(self):
        """Validate password strength."""
        password = self.cleaned_data.get('password1')
        try:
            validate_password(password)
        except forms.ValidationError as error:
            raise forms.ValidationError(error)
        return password

    def save(self, commit=True):
        """Save user with email and role."""
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']  # Use email as username
        if commit:
            user.save()
        return user


class CustomUserChangeForm(UserChangeForm):
    """
    Form for editing user profile information.
    """
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly'  # Email cannot be changed
        })
    )
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control'
        })
    )
    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control'
        })
    )
    bio = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Tell us about yourself'
        })
    )
    phone = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Phone number'
        })
    )
    profile_picture = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control'
        })
    )

    class Meta:
        model = CustomUser
        fields = ('email', 'first_name', 'last_name', 'phone', 'bio', 'profile_picture')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop('password', None)  # Remove password field


class CustomPasswordResetForm(PasswordResetForm):
    """
    Form for password reset via email.
    """
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address',
            'autofocus': True
        })
    )

    def clean_email(self):
        """Ensure email exists in database."""
        email = self.cleaned_data['email']
        if not CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError(
                'No user found with this email address.'
            )
        return email


class UserLoginForm(forms.Form):
    """
    Custom login form using email instead of username.
    """
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )


class TeamForm(forms.ModelForm):
    """
    Form for creating and editing teams.
    """
    class Meta:
        model = Team
        fields = ('name', 'description')
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Team name',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Team description and purpose',
                'rows': 4
            }),
        }
    
    def clean_name(self):
        """Ensure team name is unique (excluding current team if editing)."""
        name = self.cleaned_data.get('name')
        queryset = Team.objects.filter(name__iexact=name)
        
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise forms.ValidationError('A team with this name already exists.')
        return name


class AddTeamMemberForm(forms.Form):
    """
    Form for adding members to a team by email or username.
    """
    member_email = forms.EmailField(
        label='Member Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter member email address',
            'autofocus': True
        })
    )
    
    def __init__(self, team, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.team = team
    
    def clean_member_email(self):
        """Validate that the user exists and isn't already a member."""
        email = self.cleaned_data.get('member_email')
        
        try:
            user = CustomUser.objects.get(email__iexact=email)
        except CustomUser.DoesNotExist:
            raise forms.ValidationError('No user found with this email address.')
        
        # Check if user is already a member
        if self.team.has_member(user):
            raise forms.ValidationError('This user is already a member of the team.')
        
        # Cannot add team leader
        if user == self.team.leader:
            raise forms.ValidationError('The team leader is already a member.')
        
        return email
    
    def get_user(self):
        """Return the user object after validation."""
        if not self.is_valid():
            return None
        return CustomUser.objects.get(email__iexact=self.cleaned_data['member_email'])


class TaskForm(forms.ModelForm):
    """
    Form for creating and editing tasks.
    """
    class Meta:
        model = Task
        fields = ['title', 'description', 'assigned_to', 'priority', 'due_date', 'tags']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Task title',
                'maxlength': '200'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Task description and details',
                'rows': 4
            }),
            'assigned_to': forms.Select(attrs={
                'class': 'form-select'
            }),
            'priority': forms.Select(attrs={
                'class': 'form-select'
            }),
            'due_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'tags': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Comma-separated tags'
            }),
        }
    
    def __init__(self, team, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.team = team
        
        # Only show team members as options
        team_members = CustomUser.objects.filter(
            team_memberships__team=team
        ).distinct()
        self.fields['assigned_to'].queryset = team_members
        self.fields['assigned_to'].label = 'Assign to'
        self.fields['assigned_to'].required = False
    
    def clean_due_date(self):
        """Validate that due date is in the future."""
        due_date = self.cleaned_data.get('due_date')
        if due_date:
            from django.utils import timezone
            if due_date < timezone.now():
                raise forms.ValidationError('Due date must be in the future.')
        return due_date


class TaskCommentForm(forms.ModelForm):
    """
    Form for adding comments to tasks.
    """
    class Meta:
        model = TaskComment
        fields = ['comment']
        widgets = {
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Add a comment...',
                'rows': 3
            }),
        }


class TaskAttachmentForm(forms.ModelForm):
    """
    Form for uploading attachments to tasks.
    """
    class Meta:
        model = TaskAttachment
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '*/*'
            }),
        }


class TaskFilterForm(forms.Form):
    """
    Form for filtering tasks by various criteria.
    """
    status = forms.MultipleChoiceField(
        choices=Task.STATUS_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        })
    )
    priority = forms.MultipleChoiceField(
        choices=Task.PRIORITY_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        })
    )
    assigned_to = forms.ModelChoiceField(
        queryset=CustomUser.objects.none(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Assigned to'
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by title or description'
        })
    )
    sort_by = forms.ChoiceField(
        choices=[
            ('-due_date', 'Due Date (Nearest)'),
            ('due_date', 'Due Date (Farthest)'),
            ('-priority', 'Priority (High to Low)'),
            ('priority', 'Priority (Low to High)'),
            ('-created_at', 'Newest'),
            ('created_at', 'Oldest'),
        ],
        required=False,
        initial='-due_date',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    def __init__(self, team, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set assignee choices to team members
        team_members = CustomUser.objects.filter(
            team_memberships__team=team
        ).distinct()
        self.fields['assigned_to'].queryset = team_members


class TaskStatusForm(forms.Form):
    """
    Form for quick status updates without editing the task.
    """
    status = forms.ChoiceField(
        choices=Task.STATUS_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
