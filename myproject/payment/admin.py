from django.contrib import admin, messages
from django.utils.html import format_html, mark_safe
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.contrib.admin.widgets import AdminTextInputWidget
from django.forms import ModelForm, DecimalField
from django import forms
from .models import PaymentLink

class PaymentLinkAdminForm(forms.ModelForm):
    """Оптимізована форма для моделі PaymentLink."""
    
    # Поле для відображення кінцевої суми в UAH
    final_amount_uah_display = forms.CharField(
        required=False,
        label="Кінцева сума до оплати в UAH",
        widget=forms.TextInput(attrs={
            'readonly': 'readonly',
            'style': 'background-color: #f8f8f8; border: 1px solid #ddd; padding: 6px 8px; font-weight: bold; color: #4CAF50;',
        })
    )
    

    

    
    class Meta:
        model = PaymentLink
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        
        # Встановлюємо початкові значення для відображуваних полів
        if instance and instance.final_amount_uah:
                self.fields['final_amount_uah_display'].initial = f"{instance.final_amount_uah} UAH"

@admin.register(PaymentLink)
class PaymentLinkAdmin(admin.ModelAdmin):
    form = PaymentLinkAdminForm
    list_display = (
        'client_name', 
        'amount_usd',
        'exchange_rate_usd_to_uah',
        'final_amount_uah',
        'status', 
        'created_at',
        'expires_at',
        'payment_link_button'
    )
    list_filter = ('status', 'created_at', 'duration_minutes')
    search_fields = ('client_name', 'client_email', 'description', 'unique_id')
    readonly_fields = (
        'unique_id', 'created_at', 'updated_at', 
        'first_opened_at', 'expires_at', 'company_info', 'payment_instructions',
        'final_amount_uah'
    )
    actions = ['deactivate_links']

    fieldsets = (
        (None, {
            'fields': ('unique_id', 'client_name', 'client_email', 'description')
        }),
        ('Деталі платежу (USD -> UAH)', {
            'fields': (
                'amount_usd', 'exchange_rate_usd_to_uah', 
                'final_amount_uah_display'
            )
        }),
        ('Налаштування посилання', {
            'fields': ('status', 'duration_minutes', 'first_opened_at', 'expires_at')
        }),
        ('Додаткова інформація', {
            'fields': ('contract_file',),
            'classes': ('collapse',)
        }),
        ('Технічна інформація', {
            'fields': ('created_at', 'updated_at', 'company_info', 'payment_instructions'),
            'classes': ('collapse',)
        }),
        ('Технічні поля (не редагувати)', {
            'fields': ('final_amount_uah',),
            'classes': ('collapse',)
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields
        
    def payment_link_button(self, obj):
        """Додає кнопку для перегляду та копіювання посилання на сторінку оплати."""
        if obj.pk:
            url = obj.get_absolute_url()
            base_url = "https://pay.prometeylabs.com"  # Змініть на ваш домен
            full_url = f"{base_url}{url}"
            
            # Створюємо унікальний ID для кожного посилання
            button_id = f"copy_btn_{obj.pk}"
            
            # HTML та JavaScript для кнопок
            buttons_html = f'''
                <div style="display: flex; align-items: center;">
                    <a href="{url}" target="_blank" class="button" style="background-color: #4CAF50; color: white; border: none; border-radius: 4px; padding: 5px 10px; text-decoration: none; font-size: 11px; margin-right: 5px;">Відкрити</a>
                    <button type="button" id="{button_id}" onclick="copyUrl('{full_url}', '{button_id}')" style="background-color: #2196F3; color: white; border: none; border-radius: 4px; padding: 5px 10px; font-size: 11px; cursor: pointer;">Скопіювати</button>
                </div>
                
                <script>
                    function copyUrl(text, buttonId) {{
                        navigator.clipboard.writeText(text)
                            .then(() => {{
                                var btn = document.getElementById(buttonId);
                                btn.innerHTML = 'Скопійовано!';
                                setTimeout(function() {{ btn.innerHTML = 'Скопіювати'; }}, 2000);
                            }})
                            .catch(err => {{
                                console.error('Помилка копіювання: ', err);
                            }});
                    }}
                </script>
            '''
            
            return mark_safe(buttons_html)
        return '-'
    payment_link_button.short_description = 'Сторінка оплати'

    def display_expiration_status(self, obj):
        """Відображення статусу терміну дії посилання."""
        if obj.duration_minutes == 0:
            return "Без обмеження часу"
        
        if not obj.first_opened_at:
            return obj.get_duration_minutes_display()

        if obj.expires_at:
            now = timezone.now()
            if now < obj.expires_at:
                remaining = obj.expires_at - now
                parts = []
                days = remaining.days
                if days > 0:
                    parts.append(f"{days}д")
                
                seconds = remaining.seconds
                hours = seconds // 3600
                minutes = (seconds % 3600) // 60
                secs = seconds % 60
                
                if hours > 0:
                    parts.append(f"{hours:02d}г")
                if minutes > 0 or hours > 0:
                    parts.append(f"{minutes:02d}хв")
                if not parts:
                     parts.append(f"{secs:02d}с")
                elif len(parts) < 3:
                    parts.append(f"{secs:02d}с")

                return " ".join(parts)
            else:
                return "Термін дії минув"
        return "Не відкрито"
    display_expiration_status.short_description = "Залишилось часу"
    
    def get_client_facing_link(self, obj):
        """Генерує абсолютний URL для перегляду посилання."""
        if obj.pk:
            base_url = "https://pay.prometeylabs.com"  # Змініть на ваш домен
            relative_url = obj.get_absolute_url()
            absolute_url = f"{base_url}{relative_url}"
            return format_html('<a href="{0}" target="_blank">{0}</a>', absolute_url)
        return "Посилання ще не створено. Збережіть запис."
    get_client_facing_link.short_description = "Посилання для клієнта"
    


    def deactivate_links(self, request, queryset):
        """Деактивує вибрані посилання."""
        updated = queryset.update(status='deactivated')
        self.message_user(
            request, 
            f"{updated} посилань було деактивовано.", 
            level=messages.SUCCESS
        )
    deactivate_links.short_description = "Деактивувати вибрані посилання"
    
    def save_model(self, request, obj, form, change):
        """Додаткова логіка при збереженні моделі."""
        super().save_model(request, obj, form, change)
