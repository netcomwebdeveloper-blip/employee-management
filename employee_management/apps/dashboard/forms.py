from django import forms
from .models import EmployeeMessage

class EmployeeMessageForm(forms.ModelForm):
    class Meta:
        model = EmployeeMessage
        fields = ['category', 'subject', 'message', 'is_urgent']
        widgets = {
            'category': forms.Select(attrs={
                'class': 'form-select',
                'required': 'required'
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. Enquiry about leave policy, shift timing, or equipment',
                'required': 'required'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 4,
                'placeholder': 'Please describe your enquiry, question, or work-related concern in detail...',
                'required': 'required'
            }),
            'is_urgent': forms.CheckboxInput(attrs={
                'class': 'form-checkbox',
                'id': 'isUrgentMessage'
            }),
        }

class HRMessageResponseForm(forms.ModelForm):
    class Meta:
        model = EmployeeMessage
        fields = ['status', 'hr_response']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'form-select',
                'required': 'required'
            }),
            'hr_response': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 4,
                'placeholder': 'Enter official HR response, clarification, or resolution action taken...',
                'required': 'required'
            }),
        }
