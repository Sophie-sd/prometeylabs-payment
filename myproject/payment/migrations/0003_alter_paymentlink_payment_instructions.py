# Generated by Django 4.2.21 on 2025-05-16 05:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payment', '0002_alter_paymentlink_company_info_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymentlink',
            name='payment_instructions',
            field=models.TextField(blank=True, default='<p><strong>Умови оплати</strong><br>\nОплата здійснюється на підставі наданих реквізитів або через інтегровані платіжні системи (Google Pay / Apple Pay). Клієнт погоджується з умовами надання послуг до моменту здійснення платежу.<br>\nПісля підтвердження оплати ви отримаєте відповідне повідомлення, а статус сторінки буде оновлено.</p>\n\n<p><strong>Договір</strong><br>\nУсі послуги надаються відповідно до публічного договору, який доступний для ознайомлення на сторінці перед оплатою. Оплата є підтвердженням вашої згоди з умовами договору.</p>\n\n<p><strong>Політика повернення коштів</strong><br>\nУ разі виникнення спірних питань, ви можете звернутись до нашої служби підтримки протягом 7 календарних днів з моменту оплати.<br>\nПовернення коштів можливе лише у випадках, коли послуга не була надана або не відповідає погодженим умовам договору.<br>\nЗаявки на повернення розглядаються індивідуально, у строк до 5 робочих днів.</p>\n\n<p><strong>Контакти для звернень</strong><br>\nЗ усіх питань, пов\'язаних з оплатою, прохання звертатися на електронну адресу: prometeylabs@gmail.com<br>\nабо в telegram <a href="https://t.me/PrometeyLabs" target="_blank" rel="noopener noreferrer">@PrometeyLabs</a></p>', editable=False, verbose_name='Інформація щодо оплати та повернення'),
        ),
    ]
