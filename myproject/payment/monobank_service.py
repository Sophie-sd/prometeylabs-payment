import requests
import json
import logging
from decimal import Decimal
from django.conf import settings
from django.urls import reverse
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)

class MonobankAcquiringService:
    """
    Сервіс для роботи з monobank acquiring API
    """
    
    def __init__(self, token=None):
        """
        Ініціалізація сервісу
        :param token: Токен для API (якщо не передано, буде взято з settings)
        """
        self.token = token or getattr(settings, 'MONOBANK_TOKEN', None)
        if not self.token:
            raise ImproperlyConfigured("MONOBANK_TOKEN must be set in settings")
        
        self.base_url = "https://api.monobank.ua"
        self.headers = {
            'X-Token': self.token,
            'Content-Type': 'application/json'
        }
    
    def create_invoice(self, payment_link, payment_method='card'):
        """
        Створює інвойс для оплати через monobank
        Згідно з документацією: https://monobank.ua/api-docs/acquiring/metody/internet-ekvairynh/post--api--merchant--invoice--create
        """
        try:
            # Конвертуємо USD в копійки UAH
            amount_kopecks = int(payment_link.final_amount_uah * 100)
            
            # Формуємо коментар залежно від методу оплати
            payment_method_names = {
                'apple_pay': 'Apple Pay',
                'google_pay': 'Google Pay',
                'card': 'Картка'
            }
            method_name = payment_method_names.get(payment_method, 'Картка')
            
            # Формуємо базовий payload згідно з документацією
            payload = {
                "amount": amount_kopecks,
                "ccy": 980,  # UAH (ISO 4217)
                "merchantPaymInfo": {
                    "reference": str(payment_link.unique_id),
                    "destination": f"Оплата {method_name}: {payment_link.description[:50]}",
                    "comment": f"Платіж через {method_name} - {payment_link.client_name}"
                },
                "redirectUrl": self._build_callback_url('payment:payment_success', payment_link.unique_id),
                "webHookUrl": self._build_webhook_url(),
                "validity": 3600,  # 1 година (в секундах)
                "paymentType": "debit"
            }
            
            logger.info(f"Creating monobank invoice for {payment_link.unique_id}: {amount_kopecks} kopecks via {method_name}")
            logger.info(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
            
            response = requests.post(
                f"{self.base_url}/api/merchant/invoice/create",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            logger.info(f"Monobank API response status: {response.status_code}")
            logger.info(f"Monobank API response: {response.text}")
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Monobank API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating monobank invoice: {str(e)}")
            return None
    

    def check_payment_status(self, invoice_id):
        """
        Перевірка статусу платежу
        :param invoice_id: ID інвойсу в monobank
        :return: Словник з даними статусу або None при помилці
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/merchant/invoice/status",
                headers=self.headers,
                params={"invoiceId": invoice_id},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to check payment status: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error checking payment status for invoice {invoice_id}: {str(e)}")
            return None
    
    def _build_callback_url(self, url_name, payment_uuid):
        """
        Побудова повного URL для колбеків
        """
        from django.contrib.sites.models import Site
        try:
            current_site = Site.objects.get_current()
            domain = f"https://{current_site.domain}"
        except:
            # Якщо Site framework не налаштований, використовуємо з settings
            domain = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        
        relative_url = reverse(url_name, kwargs={'link_uuid': payment_uuid})
        return f"{domain}{relative_url}"
    
    def _build_webhook_url(self):
        """
        Побудова URL для webhook
        """
        from django.contrib.sites.models import Site
        try:
            current_site = Site.objects.get_current()
            domain = f"https://{current_site.domain}"
        except:
            domain = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        
        webhook_path = reverse('payment:monobank_webhook')
        return f"{domain}{webhook_path}" 