from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from datetime import timedelta # Додано, якщо раптом було видалено
from .models import PaymentLink

# Create your views here.

def payment_page_view(request, link_uuid):
    payment_link = get_object_or_404(PaymentLink, unique_id=link_uuid)
    now = timezone.now()

    # Встановлюємо час першого відкриття та кінцевий термін, якщо це перший візит
    # і якщо встановлено тривалість (duration_minutes > 0)
    if payment_link.duration_minutes > 0 and payment_link.first_opened_at is None:
        payment_link.first_opened_at = now
        payment_link.expires_at = now + timedelta(minutes=payment_link.duration_minutes)
        # Змінюємо статус на 'pending' (Відкрито), якщо він був 'new'
        if payment_link.status == 'new':
            payment_link.status = 'pending'
        payment_link.save(update_fields=['first_opened_at', 'expires_at', 'status'])
    
    current_status = payment_link.status
    is_link_expired = payment_link.is_expired() # Викликаємо метод моделі

    # Якщо посилання протерміновано і статус ще не 'expired', 'paid' або 'deactivated', оновлюємо його
    if is_link_expired and current_status not in ['expired', 'paid', 'deactivated']:
        payment_link.status = 'expired'
        payment_link.save(update_fields=['status']) 
        current_status = 'expired' 

    # Перевірка, чи посилання активне для оплати
    # (не 'paid', не 'deactivated', не 'expired')
    # Також, якщо duration_minutes == 0 (без обмеження), то воно завжди активне, якщо не paid/deactivated
    can_proceed_to_payment = False
    if payment_link.duration_minutes == 0:
        if current_status not in ['paid', 'deactivated']:
            can_proceed_to_payment = True
    elif current_status not in ['paid', 'deactivated', 'expired']:
        can_proceed_to_payment = True

    if not can_proceed_to_payment:
        return render(request, 'payment/link_inactive.html', {
            'payment_link': payment_link,
            'reason': current_status 
        })

    context = {
        'payment_link': payment_link,
        # Передаємо expires_at для таймера, тільки якщо воно встановлено і є тривалість
        'expires_at_iso': payment_link.expires_at.isoformat() if payment_link.expires_at and payment_link.duration_minutes > 0 else None,
    }
    return render(request, 'payment/payment_page.html', context)
