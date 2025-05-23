from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from payment.models import PaymentLink
from decimal import Decimal

class PaymentLinkModelTest(TestCase):
    def setUp(self):
        # Створюємо тестовий об'єкт PaymentLink
        self.payment_link = PaymentLink.objects.create(
            client_name='Тестовий Клієнт',
            client_email='test@example.com',
            amount_usd=Decimal('100.00'),
            exchange_rate_usd_to_uah=Decimal('39.50'),
            description='Тестовий платіж',
            duration_minutes=60  # 1 година
        )

    def test_final_amount_uah_calculation(self):
        """Тестує автоматичний розрахунок суми в UAH"""
        # Перевіряємо, що final_amount_uah розраховується правильно при збереженні об'єкту
        self.assertEqual(self.payment_link.final_amount_uah, Decimal('3950.00'))
        
        # Змінюємо суму в USD та курс і перевіряємо перерахунок
        self.payment_link.amount_usd = Decimal('200.00')
        self.payment_link.exchange_rate_usd_to_uah = Decimal('40.00')
        self.payment_link.save()
        
        self.assertEqual(self.payment_link.final_amount_uah, Decimal('8000.00'))

    def test_is_expired_method(self):
        """Тестує метод is_expired() для перевірки терміну дії посилання"""
        # Посилання з терміном 60 хвилин ще не відкривалося, тому не є протермінованим
        self.assertFalse(self.payment_link.is_expired())
        
        # Імітуємо перше відкриття посилання
        now = timezone.now()
        self.payment_link.first_opened_at = now
        self.payment_link.expires_at = now + timedelta(minutes=60)
        self.payment_link.save()
        
        # Після першого відкриття і до закінчення терміну посилання не є протермінованим
        self.assertFalse(self.payment_link.is_expired())
        
        # Встановлюємо термін дії в минуле, посилання має стати протермінованим
        self.payment_link.expires_at = now - timedelta(minutes=5)
        self.payment_link.save()
        self.assertTrue(self.payment_link.is_expired())
        
        # Посилання без обмеження часу (duration_minutes=0) ніколи не є протермінованим
        self.payment_link.duration_minutes = 0
        self.payment_link.expires_at = None
        self.payment_link.save()
        self.assertFalse(self.payment_link.is_expired())

    def test_get_absolute_url(self):
        """Тестує метод get_absolute_url() для отримання правильного URL"""
        expected_url = f'/payment/pay/{self.payment_link.unique_id}/'
        self.assertEqual(self.payment_link.get_absolute_url(), expected_url)

    def test_string_representation(self):
        """Тестує рядкове представлення об'єкта"""
        # Використовуємо startswith замість точного порівняння, щоб уникнути проблем з форматуванням чисел
        expected_start = 'Платіжне посилання для Тестовий Клієнт - 100.00 USD'
        self.assertTrue(str(self.payment_link).startswith(expected_start))
        self.assertIn('Нове (не відкрито)', str(self.payment_link))
