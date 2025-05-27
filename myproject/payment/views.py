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
from django.conf import settings

logger = logging.getLogger(__name__)

# Create your views here.

def payment_page_view(request, link_uuid):
    payment_link = get_object_or_404(PaymentLink, unique_id=link_uuid)
    now = timezone.now()

    if payment_link.duration_minutes > 0 and payment_link.first_opened_at is None:
        payment_link.first_opened_at = now
        payment_link.expires_at = now + timedelta(minutes=payment_link.duration_minutes)
        if payment_link.status == 'new':
            payment_link.status = 'pending'
        payment_link.save(update_fields=['first_opened_at', 'expires_at', 'status'])
    
    if payment_link.is_expired() and payment_link.status not in ['expired', 'paid', 'deactivated']:
        payment_link.status = 'expired'
        payment_link.save(update_fields=['status'])

    inactive_statuses = ['paid', 'deactivated']
    if payment_link.duration_minutes > 0:
        inactive_statuses.append('expired')
    
    if payment_link.status in inactive_statuses:
        return render(request, 'payment/link_inactive.html', {
            'payment_link': payment_link, 'reason': payment_link.status
        })

    return render(request, 'payment/payment_page.html', {
        'payment_link': payment_link,
        'expires_at_iso': payment_link.expires_at.isoformat() if payment_link.expires_at and payment_link.duration_minutes > 0 else None,
    })


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
        
        # Створюємо інвойс з перенаправленням на платіжну сторінку Monobank
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
    Згідно з документацією: зміст тіла запиту ідентичний відповіді запиту "Статус рахунку"
    """
    try:
        data = json.loads(request.body)
        reference = data.get('merchantPaymInfo', {}).get('reference')
        status = data.get('status')
        
        logger.info(f"Monobank webhook: status={status}, reference={reference}")
        
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
                elif status == 'processing':
                    # Платіж обробляється
                    logger.info(f"Payment processing for {reference}")
                
            except PaymentLink.DoesNotExist:
                logger.error(f"PaymentLink with reference {reference} not found")
        else:
            logger.warning("No reference found in webhook data")
        
        return HttpResponse("OK", status=200)
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in webhook: {str(e)}")
        return HttpResponse("Invalid JSON", status=400)
    except Exception as e:
        logger.error(f"Error processing monobank webhook: {str(e)}")
        return HttpResponse("Error", status=500)


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


def test_monobank_api(request):
    """
    Тестова сторінка для перевірки роботи Monobank API
    """
    if not request.user.is_staff:
        return redirect('/')
    
    context = {
        'token_configured': bool(getattr(settings, 'MONOBANK_TOKEN', None)),
        'site_url': getattr(settings, 'SITE_URL', 'Not configured'),
    }
    
    if request.method == 'POST':
        try:
            test_payment = PaymentLink.objects.create(
                client_name='Тест API', client_email='test@example.com',
                amount_usd=1.00, exchange_rate_usd_to_uah=39.50,
                description='Тестовий платіж для перевірки API Monobank'
            )
            
            invoice_data = MonobankAcquiringService().create_invoice(test_payment)
            
            if invoice_data:
                context.update({'success': True, 'invoice_data': invoice_data, 'test_payment': test_payment})
            else:
                context['error'] = 'Не вдалося створити інвойс'
        except Exception as e:
            context['error'] = f'Помилка: {str(e)}'
    
    return render(request, 'payment/test_monobank_api.html', context)
