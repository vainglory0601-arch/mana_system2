from django import forms
from .models import LoanApplication


class LoanApplicationForm(forms.ModelForm):
    class Meta:
        model = LoanApplication
        fields = [
            "full_name",
            "monthly_income",
            "current_address",
            "amount",
            "term_months",
            "purpose",
            "emergency1_name",
            "emergency1_contact",
            "emergency2_name",
            "emergency2_contact",
            "emergency3_name",
            "emergency3_contact",
            "beneficiary_name",
            "bank_name",
            "account_number",
            "signature_name",
            "id_front",
            "id_back",
            "selfie_with_id",
        ]
        widgets = {
            "full_name": forms.TextInput(attrs={"placeholder": "Full Name", "class": "form-control"}),
            "monthly_income": forms.NumberInput(attrs={"placeholder": "Monthly Income", "class": "form-control"}),
            "current_address": forms.Textarea(attrs={"placeholder": "Current Address", "rows": 3, "class": "form-control"}),
            "amount": forms.NumberInput(attrs={"placeholder": "Loan Amount", "class": "form-control"}),
            "term_months": forms.NumberInput(attrs={"placeholder": "Term (months)", "class": "form-control"}),
            "purpose": forms.TextInput(attrs={"placeholder": "Loan Purpose", "class": "form-control"}),
            "emergency1_name": forms.TextInput(attrs={"placeholder": "Emergency Contact 1 Name", "class": "form-control"}),
            "emergency1_contact": forms.TextInput(attrs={"placeholder": "Emergency Contact 1 Phone", "class": "form-control"}),
            "emergency2_name": forms.TextInput(attrs={"placeholder": "Emergency Contact 2 Name", "class": "form-control"}),
            "emergency2_contact": forms.TextInput(attrs={"placeholder": "Emergency Contact 2 Phone", "class": "form-control"}),
            "emergency3_name": forms.TextInput(attrs={"placeholder": "Emergency Contact 3 Name", "class": "form-control"}),
            "emergency3_contact": forms.TextInput(attrs={"placeholder": "Emergency Contact 3 Phone", "class": "form-control"}),
            "beneficiary_name": forms.TextInput(attrs={"placeholder": "Beneficiary Name", "class": "form-control"}),
            "bank_name": forms.TextInput(attrs={"placeholder": "Bank Name", "class": "form-control"}),
            "account_number": forms.TextInput(attrs={"placeholder": "Account Number", "class": "form-control"}),
            "signature_name": forms.TextInput(attrs={"placeholder": "Signature Name", "class": "form-control"}),
            "id_front": forms.FileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "id_back": forms.FileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "selfie_with_id": forms.FileInput(attrs={"class": "form-control", "accept": "image/*"}),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if amount and amount <= 0:
            raise forms.ValidationError("Loan amount must be greater than 0.")
        return amount

    def clean_monthly_income(self):
        income = self.cleaned_data.get("monthly_income")
        if income and income <= 0:
            raise forms.ValidationError("Monthly income must be greater than 0.")
        return income

    def clean_term_months(self):
        term = self.cleaned_data.get("term_months")
        if term and term <= 0:
            raise forms.ValidationError("Term must be greater than 0.")
        return term
