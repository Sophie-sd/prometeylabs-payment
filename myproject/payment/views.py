from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib import messages
from datetime import timedelta # Додано, якщо раптом було видалено
import json
import logging
from .models import PaymentLink
from .monobank_service import MonobankAcquiringService

logger = logging.getLogger(__name__)

# Create your views here.

def payment_page_view(request, link_uuid):
    # Оптимізовано: використовуємо select_related для майбутніх зв'язків з іншими моделями
    payment_link = get_object_or_404(PaymentLink, unique_id=link_uuid)
    now = timezone.now()

    # Встановлюємо час першого відкриття та кінцевий термін, якщо це перший візит
    # і якщо встановлено тривалість (duration_minutes > 0)
    if payment_link.duration_minutes > 0 and payment_link.first_opened_at is None:
        payment_link.first_opened_at = now
        payment_link.expires_at = now + timedelta(minutes=payment_link.duration_minutes)
        # Змінюємо статус на 'pending' (Очікує оплати), якщо він був 'new'
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


@require_POST
def create_monobank_invoice(request, link_uuid):
    """
    Створення інвойсу в monobank та перенаправлення на сторінку оплати
    """
    payment_link = get_object_or_404(PaymentLink, unique_id=link_uuid)
    
    # Перевіряємо, чи може посилання використовуватися для оплати
    if payment_link.status in ['paid', 'deactivated', 'expired']:
        messages.error(request, 'Це платіжне посилання більше не активне.')
        return redirect('payment:payment_page_view', link_uuid=link_uuid)
    
    # Отримуємо метод оплати з форми
    payment_method = request.POST.get('payment_method', 'card')
    
    try:
        # Ініціалізуємо сервіс monobank
        mono_service = MonobankAcquiringService()
        
        # Якщо це прямий платіж карткою - збираємо дані картки
        if payment_method == 'card' and request.POST.get('card_number'):
            card_data = {
                'pan': request.POST.get('card_number', '').replace(' ', ''),
                'exp': request.POST.get('card_expiry', '').replace('/', ''),
                'cvv': request.POST.get('card_cvv', ''),
                'holder': request.POST.get('card_holder', '')
            }
            
            # Валідація даних картки
            if not all([card_data['pan'], card_data['exp'], card_data['cvv'], card_data['holder']]):
                messages.error(request, 'Будь ласка, заповніть всі поля даних картки.')
                return redirect('payment:payment_page_view', link_uuid=link_uuid)
            
            # Створюємо прямий платіж
            payment_result = mono_service.create_direct_payment(payment_link, card_data)
            
            if payment_result and payment_result.get('status') == 'success':
                # Платіж успішний
                payment_link.monobank_invoice_id = payment_result.get('invoiceId')
                payment_link.status = 'paid'
                payment_link.payment_processed_at = timezone.now()
                payment_link.save(update_fields=['monobank_invoice_id', 'status', 'payment_processed_at'])
                
                return redirect('payment:payment_success', link_uuid=link_uuid)
            elif payment_result and payment_result.get('tdsUrl'):
                # Потрібна 3DS автентифікація
                payment_link.monobank_invoice_id = payment_result.get('invoiceId')
                payment_link.save(update_fields=['monobank_invoice_id'])
                
                return redirect(payment_result.get('tdsUrl'))
            else:
                # Платіж не вдався
                error_message = payment_result.get('failureReason', 'Помилка при обробці платежу')
                messages.error(request, f'Платіж не вдався: {error_message}')
                return redirect('payment:payment_failure', link_uuid=link_uuid)
        else:
            # Створюємо звичайний інвойс з перенаправленням
            invoice_data = mono_service.create_invoice(payment_link, payment_method=payment_method)
            
            if invoice_data:
                # Зберігаємо дані інвойсу
                payment_link.monobank_invoice_id = invoice_data.get('invoiceId')
                payment_link.monobank_invoice_url = invoice_data.get('pageUrl')
                payment_link.save(update_fields=['monobank_invoice_id', 'monobank_invoice_url'])
                
                # Перенаправляємо на сторінку оплати monobank
                return redirect(invoice_data.get('pageUrl'))
            else:
                messages.error(request, 'Помилка при створенні платежу. Спробуйте пізніше.')
                return redirect('payment:payment_page_view', link_uuid=link_uuid)
            
    except Exception as e:
        logger.error(f"Error creating monobank invoice: {str(e)}")
        messages.error(request, 'Помилка при створенні платежу. Спробуйте пізніше.')
        return redirect('payment:payment_page_view', link_uuid=link_uuid)


@csrf_exempt
@require_POST
def monobank_webhook(request):
    """
    Обробка webhook від monobank
    """
    try:
        data = json.loads(request.body)
        invoice_id = data.get('invoiceId')
        status = data.get('status')
        reference = data.get('reference')  # Це наш unique_id
        
        logger.info(f"Monobank webhook received: invoice_id={invoice_id}, status={status}, reference={reference}")
        
        if reference:
            try:
                payment_link = PaymentLink.objects.get(unique_id=reference)
                
                if status == 'success':
                    payment_link.status = 'paid'
                    payment_link.payment_processed_at = timezone.now()
                    payment_link.save(update_fields=['status', 'payment_processed_at'])
                    logger.info(f"Payment successful for {reference}")
                elif status == 'failure':
                    # Платіж не вдався, але посилання залишається активним
                    logger.info(f"Payment failed for {reference}")
                
            except PaymentLink.DoesNotExist:
                logger.error(f"PaymentLink with reference {reference} not found")
        
        return HttpResponse("OK", status=200)
        
    except Exception as e:
        logger.error(f"Error processing monobank webhook: {str(e)}")
        return HttpResponse("Error", status=400)


def payment_success(request, link_uuid):
    """
    Сторінка успішної оплати
    """
    payment_link = get_object_or_404(PaymentLink, unique_id=link_uuid)
    
    context = {
        'payment_link': payment_link,
    }
    return render(request, 'payment/payment_success.html', context)


def payment_failure(request, link_uuid):
    """
    Сторінка неуспішної оплати
    """
    payment_link = get_object_or_404(PaymentLink, unique_id=link_uuid)
    
    context = {
        'payment_link': payment_link,
    }
    return render(request, 'payment/payment_failure.html', context)
