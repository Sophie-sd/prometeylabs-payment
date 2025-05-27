from django.urls import path
from . import views

app_name = 'payment'

urlpatterns = [
    path('pay/<uuid:link_uuid>/', views.payment_page_view, name='payment_page_view'),
    path('pay/<uuid:link_uuid>/create-invoice/', views.create_monobank_invoice, name='create_monobank_invoice'),
    path('pay/<uuid:link_uuid>/success/', views.payment_success, name='payment_success'),
    path('pay/<uuid:link_uuid>/failure/', views.payment_failure, name='payment_failure'),
    path('webhook/monobank/', views.monobank_webhook, name='monobank_webhook'),
    path('test/monobank-api/', views.test_monobank_api, name='test_monobank_api'),
] 