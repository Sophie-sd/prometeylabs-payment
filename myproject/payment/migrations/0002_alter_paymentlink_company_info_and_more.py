# Generated by Django 4.2.21 on 2025-05-16 05:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payment', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymentlink',
            name='company_info',
            field=models.TextField(blank=True, default='PrometeyLabs — це українська ІТ-компанія, що спеціалізується на швидкій розробці вебпродуктів, автоматизації процесів, інтеграції ШІ та чат-ботів. Ми працюємо швидко, без зайвих витрат та з фокусом на якість.\n\nОсновні напрямки:\nРозробка сайтів та платформ\nAI-аватари, чат-боти, телеграм-боти\nE-commerce рішення\nФОП Дмитренko Софія Дмитрівна\nІПН: 3770706565\nФОП зареєстровано в Україні, платник єдиного податку 3 групи.', editable=False, verbose_name='Інформація про компанію'),
        ),
        migrations.AlterField(
            model_name='paymentlink',
            name='payment_instructions',
            field=models.TextField(blank=True, default="Умови оплати\nОплата здійснюється на підставі наданих реквізитів або через інтегровані платіжні системи (Google Pay / Apple Pay). Клієнт погоджується з умовами надання послуг до моменту здійснення платежу.\nПісля підтвердження оплати ви отримаєте відповідне повідомлення, а статус сторінки буде оновлено.\n\nДоговір\nУсі послуги надаються відповідно до публічного договору, який доступний для ознайомлення на сторінці перед оплатою. Оплата є підтвердженням вашої згоди з умовами договору.\n\nПолітика повернення коштів\nУ разі виникнення спірних питань, ви можете звернутись до нашої служби підтримки протягом 7 календарних днів з моменту оплати.\nПовернення коштів можливе лише у випадках, коли послуга не була надана або не відповідає погодженим умовам договору.\nЗаявки на повернення розглядаються індивідуально, у строк до 5 робочих днів.\n\nКонтакти для звернень\nЗ усіх питань, пов'язаних з оплатою, прохання звертатися на електронну адресу: prometeylabs@gmail.com\nабо в telegram @PrometeyLabs", editable=False, verbose_name='Інформація щодо оплати та повернення'),
        ),
    ]
