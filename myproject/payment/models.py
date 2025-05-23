import uuid
from datetime import timedelta
from django.db import models
from django.urls import reverse
from django.utils import timezone

# Визначимо тексти за замовчуванням тут для кращої читабельності
COMPANY_INFO_DEFAULT = '''PrometeyLabs — це українська ІТ-компанія, що спеціалізується на швидкій розробці вебпродуктів, автоматизації процесів, інтеграції ШІ та чат-ботів. Ми працюємо швидко, без зайвих витрат та з фокусом на якість.

Основні напрямки:
Розробка сайтів та платформ
AI-аватари, чат-боти, телеграм-боти
E-commerce рішення
ФОП Дмитренko Софія Дмитрівна
ІПН: 3770706565
ФОП зареєстровано в Україні, платник єдиного податку 3 групи.'''

# Оновлено: тепер включає HTML для посилання та базового форматування
PAYMENT_INFO_DEFAULT_WITH_HTML = '''<p><strong>Умови оплати</strong><br>
Оплата здійснюється на підставі наданих реквізитів або через інтегровані платіжні системи (Google Pay / Apple Pay). Клієнт погоджується з умовами надання послуг до моменту здійснення платежу.<br>
Після підтвердження оплати ви отримаєте відповідне повідомлення, а статус сторінки буде оновлено.</p>

<p><strong>Договір</strong><br>
Усі послуги надаються відповідно до публічного договору, який доступний для ознайомлення на сторінці перед оплатою. Оплата є підтвердженням вашої згоди з умовами договору.</p>

<p><strong>Політика повернення коштів</strong><br>
У разі виникнення спірних питань, ви можете звернутись до нашої служби підтримки протягом 7 календарних днів з моменту оплати.<br>
Повернення коштів можливе лише у випадках, коли послуга не була надана або не відповідає погодженим умовам договору.<br>
Заявки на повернення розглядаються індивідуально, у строк до 5 робочих днів.</p>

<p><strong>Контакти для звернень</strong><br>
З усіх питань, пов\'язаних з оплатою, прохання звертатися на електронну адресу: prometeylabs@gmail.com<br>
або в telegram <a href="https://t.me/PrometeyLabs" target="_blank" rel="noopener noreferrer">@PrometeyLabs</a></p>'''


class PaymentLink(models.Model):
    DURATION_CHOICES = [
        (30, '30 хвилин'),
        (60, '1 година'),
        (180, '3 години'),
        (540, '9 годин'),
        (900, '15 годин'),
        (1440, '1 день (24 години)'),
        (0, 'Без обмеження часу'),
    ]

    # Унікальний ідентифікатор для посилання
    unique_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    
    # Інформація про клієнта
    client_name = models.CharField(max_length=255, verbose_name="Ім'я клієнта")
    client_email = models.EmailField(verbose_name="Email клієнта", blank=True, null=True)

    # Нова схема оплати USD -> UAH
    amount_usd = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Сума в USD"
    )
    exchange_rate_usd_to_uah = models.DecimalField(
        max_digits=10, 
        decimal_places=4, 
        verbose_name="Курс USD/UAH",
        help_text="Поточний курс обміну долара до гривні (наприклад, 39.50)"
    )
    final_amount_uah = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Кінцева сума до оплати в UAH", 
        blank=True, 
        null=True,
        editable=False, 
        help_text="Автоматично розрахована сума до оплати в гривнях"
    )
    
    description = models.TextField(verbose_name="Опис платежу (для клієнта)")

    # Інформація, що відображається на сторінці оплати
    company_info = models.TextField(
        verbose_name="Інформація про компанію",
        blank=True, 
        default=COMPANY_INFO_DEFAULT,
        editable=False
    )
    payment_instructions = models.TextField(
        verbose_name="Інформація щодо оплати та повернення", 
        blank=True,
        default=PAYMENT_INFO_DEFAULT_WITH_HTML,
        editable=False 
    )

    # Договір
    contract_file = models.FileField(upload_to='contracts/%Y/%m/%d/', verbose_name="Файл договору (PDF)", blank=True, null=True)

    # Статус посилання
    STATUS_CHOICES = [
        ('new', 'Нове (не відкрито)'),
        ('pending', 'Очікує оплати'),
        ('paid', 'Оплачено'),
        ('expired', 'Протерміновано'), 
        ('deactivated', 'Деактивовано'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name="Статус", db_index=True)

    # Технічні поля
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата створення в адмінці", db_index=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата оновлення")
    
    # Термін дії посилання
    duration_minutes = models.IntegerField(
        verbose_name="Термін дії посилання",
        choices=DURATION_CHOICES, 
        default=1440,
        help_text="Відлік починається з моменту першого відкриття посилання клієнтом. Оберіть 'Без обмеження часу' для безстрокового посилання."
    )
    first_opened_at = models.DateTimeField(
        verbose_name="Вперше відкрито", 
        null=True, 
        blank=True, 
        editable=False
    )
    expires_at = models.DateTimeField(
        verbose_name="Дійсне до", 
        null=True, 
        blank=True, 
        editable=False,
        db_index=True
    )

    # Monobank integration fields
    monobank_invoice_id = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name="ID інвойсу в monobank",
        editable=False,
        db_index=True
    )
    monobank_invoice_url = models.URLField(
        blank=True, 
        null=True, 
        verbose_name="URL для оплати в monobank",
        editable=False
    )
    payment_processed_at = models.DateTimeField(
        blank=True, 
        null=True, 
        verbose_name="Дата і час обробки платежу",
        editable=False
    )

    def save(self, *args, **kwargs):
        # Якщо обрано "Без обмеження часу" і є дата expires_at, очистимо її
        if self.duration_minutes == 0 and self.expires_at is not None:
            self.expires_at = None
            
        # Розрахунок кінцевої суми оплати в UAH
        if self.amount_usd is not None and self.exchange_rate_usd_to_uah is not None:
            self.final_amount_uah = self.amount_usd * self.exchange_rate_usd_to_uah

        super().save(*args, **kwargs)

    def is_expired(self):
        if self.duration_minutes == 0:  # Без обмеження часу
            return False
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False 

    def __str__(self):
        details = f"{self.amount_usd} USD"
        if self.final_amount_uah is not None:
            details += f" (екв. {self.final_amount_uah} UAH)"
        return f"Платіжне посилання для {self.client_name} - {details} ({self.get_status_display()})"

    def get_absolute_url(self):
        """Повертає URL-адресу для доступу до сторінки оплати цього посилання."""
        return reverse('payment:payment_page_view', kwargs={'link_uuid': self.unique_id})

    class Meta:
        verbose_name = "Платіжне посилання"
        verbose_name_plural = "Платіжні посилання"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['expires_at']),
        ]
