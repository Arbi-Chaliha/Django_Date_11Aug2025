from django import forms

class TroubleshooterForm(forms.Form):
    """
    A form for the troubleshooting interface.
    The choices will be populated dynamically via JavaScript and API calls.
    """
    # The initial choices are left empty to be populated by JavaScript.
    serial_number = forms.ChoiceField(
        choices=[('', 'Select serial number...')],
        label="Serial Number",
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    job_number = forms.ChoiceField(
        choices=[('', 'Select job number...')],
        label="Job Number",
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    job_start = forms.ChoiceField(
        choices=[('', 'Select start job...')],
        label="Start Job",
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )