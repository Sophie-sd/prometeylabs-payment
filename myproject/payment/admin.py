from django.contrib import admin, messages
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from .models import PaymentLink

@admin.register(PaymentLink)
class PaymentLinkAdmin(admin.ModelAdmin):
    list_display = (
        'client_name', 'amount', 'currency', 'status', 
        'display_expiration_status',
        'first_opened_at', 'expires_at',
        'created_at', 'get_client_facing_link'
    )
    list_filter = ('status', 'currency', 'created_at', 'expires_at', 'duration_minutes', 'first_opened_at')
    search_fields = ('client_name', 'client_email', 'description', 'unique_id__iexact')
    readonly_fields = (
        'unique_id', 'created_at', 'updated_at', 
        'first_opened_at', 'expires_at',
        'get_client_facing_link_for_form'
    )
    actions = ['deactivate_links']

    fieldsets = (
        (None, {
            'fields': ('client_name', 'client_email')
        }),
        ('Деталі платежу', {
            'fields': ('amount', 'currency', 'description')
        }),
        ('Термін дії посилання', {
            'fields': ('duration_minutes', 'first_opened_at', 'expires_at')
        }),
        ('Договір', {
            'fields': ('contract_file',)
        }),
        ('Статус та Ідентифікатор', {
            'fields': ('status', 'unique_id', 'created_at', 'updated_at', 'get_client_facing_link_for_form')
        }),
    )

    def display_expiration_status(self, obj):
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

                return f"Залишилось: {' '.join(parts)}"
            else:
                return "Термін вийшов"
        return "N/A"
    display_expiration_status.short_description = "Стан терміну дії"

    def get_client_facing_link(self, obj):
        if obj.unique_id:
            link_path = obj.get_absolute_url()
            return format_html("<a href='{}' target='_blank'>{}</a>", link_path, link_path)
        return "-"
    get_client_facing_link.short_description = "Посилання для клієнта (шлях)"

    def get_client_facing_link_for_form(self, obj):
        if obj.unique_id:
            link_path = obj.get_absolute_url()
            full_link_example = f"http://ВАШ_ДОМЕН{link_path}"
            return format_html(
                "<p>Посилання для відправки клієнту:</p>"
                "<a href='{0}' target='_blank'>{0}</a><br>"
                "<small>(Повний URL буде приблизно таким: <code>{1}</code>, де ВАШ_ДОМЕН - це, наприклад, 127.0.0.1:8000 під час розробки)</small>", 
                link_path, 
                full_link_example
            )
        return "Посилання буде доступне після збереження."
    get_client_facing_link_for_form.short_description = "Платіжне посилання для клієнта"

    def deactivate_links(self, request, queryset):
        """Деактивує обрані платіжні посилання."""
        updated_count = queryset.update(status='deactivated')
        self.message_user(request, f'{updated_count} платіжних посилань було успішно деактивовано.', messages.SUCCESS)
    deactivate_links.short_description = "Деактивувати обрані посилання"

    # Якщо потрібно буде кастомна логіка при збереженні (наприклад, генерація link_url)
    # def save_model(self, request, obj, form, change):
    #     super().save_model(request, obj, form, change)
