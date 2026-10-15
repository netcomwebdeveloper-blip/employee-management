from django import forms
from django.contrib.auth.models import User
from .models import EmployeeProfile, DailyWork, LeaveRequest


class DailyWorkForm(forms.ModelForm):
    class Meta:
        model = DailyWork
        fields = ['project_name', 'work_details', 'status']
        widgets = {
            'project_name': forms.TextInput(attrs={'placeholder': 'Enter project name'}),
            'work_details': forms.Textarea(attrs={'placeholder': 'Enter today work update', 'rows': 4}),
        }


class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ['leave_type', 'from_date', 'to_date', 'reason']
        widgets = {
            'from_date': forms.DateInput(attrs={'type': 'date'}),
            'to_date': forms.DateInput(attrs={'type': 'date'}),
            'reason': forms.Textarea(attrs={'placeholder': 'Enter leave reason', 'rows': 4}),
        }

    def clean(self):
        cleaned = super().clean()
        from_date = cleaned.get('from_date')
        to_date = cleaned.get('to_date')
        if from_date and to_date and to_date < from_date:
            raise forms.ValidationError('To date must be greater than or equal to from date.')
        return cleaned


class EmployeeCreateForm(forms.Form):
    username = forms.CharField(max_length=100)
    password = forms.CharField(widget=forms.PasswordInput)
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100, required=False)
    email = forms.EmailField(required=False)
    employee_code = forms.CharField(max_length=20)
    role = forms.ChoiceField(choices=EmployeeProfile.ROLE_CHOICES)
    department = forms.CharField(max_length=100)
    designation = forms.CharField(max_length=100)
    phone = forms.CharField(max_length=15, required=False)
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)
    casual_leave_balance = forms.IntegerField(min_value=0, initial=0)

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Username already exists.')
        return username

    def clean_employee_code(self):
        employee_code = self.cleaned_data['employee_code']
        if EmployeeProfile.objects.filter(employee_code=employee_code).exists():
            raise forms.ValidationError('Employee code already exists.')
        return employee_code

    def save(self):
        is_admin = self.cleaned_data['role'] == 'ADMIN'
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            password=self.cleaned_data['password'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            email=self.cleaned_data['email'],
            is_staff=is_admin,
            is_superuser=is_admin,
        )
        EmployeeProfile.objects.create(
            user=user,
            employee_code=self.cleaned_data['employee_code'],
            role=self.cleaned_data['role'],
            department=self.cleaned_data['department'],
            designation=self.cleaned_data['designation'],
            phone=self.cleaned_data['phone'],
            address=self.cleaned_data['address'],
            casual_leave_balance=self.cleaned_data['casual_leave_balance'],
        )
        return user


class AttendanceUpdateForm(forms.Form):
    employee = forms.ModelChoiceField(queryset=EmployeeProfile.objects.all())
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    in_time = forms.TimeField(required=False, widget=forms.TimeInput(attrs={'type': 'time'}))
    out_time = forms.TimeField(required=False, widget=forms.TimeInput(attrs={'type': 'time'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['employee'].queryset = EmployeeProfile.objects.select_related('user').all().order_by('employee_code')


class PunchMachineUploadForm(forms.Form):
    csv_file = forms.FileField(help_text='CSV format: employee_code,date,time,type')
