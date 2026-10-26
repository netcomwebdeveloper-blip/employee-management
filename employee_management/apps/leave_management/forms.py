from django import forms
from .models import LeaveRequest

class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ['leave_type', 'from_date', 'to_date', 'reason']
        widgets = {
            'leave_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_leave_type', 'onchange': 'if (typeof onLeaveCategoryChange === "function") { onLeaveCategoryChange(); }'}),
            'from_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-input', 'id': 'id_from_date'}),
            'to_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-input', 'id': 'id_to_date'}),
            'reason': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'State purpose of leave application or permission...'}),
        }

    def clean(self):
        cleaned = super().clean()
        leave_type = cleaned.get('leave_type')
        from_date = cleaned.get('from_date')
        to_date = cleaned.get('to_date')

        if leave_type in ('Permission (Up to 2 Hours)', 'Permission'):
            if from_date and not to_date:
                cleaned['to_date'] = from_date
                to_date = from_date

        if from_date and to_date and to_date < from_date:
            raise forms.ValidationError("End date cannot be earlier than start date.")
        return cleaned
