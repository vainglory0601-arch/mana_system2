from django.urls import path
from . import views

urlpatterns = [
    path("apply/", views.apply_loan_view, name="apply_loan"),
    path("my-loans/", views.my_loans_view, name="my_loans"),
    path("withdraw/", views.withdraw_view, name="withdraw"),
]
