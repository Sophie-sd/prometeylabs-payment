from django.urls import path
from . import views # Ми створимо views пізніше

app_name = 'payment'

urlpatterns = [
    path('pay/<uuid:link_uuid>/', views.payment_page_view, name='payment_page_view'),
    # Наразі залишимо порожнім, доки не створимо view
] 