from django.contrib import admin
from .models import User, Transaction, Portfolio, Cash, Refresh, Realized_Profit, Temporary

class TransactionAdmin(admin.ModelAdmin):
    list_display = ('owner', 'symbol', 'cost', 'currency', 'position', 'timestamp')

class PortfolioAdmin(admin.ModelAdmin):
    list_display = ('owner', 'symbol', 'price', 'change', 'cost', 'currency', 'position', 'pnl', 'pnl_percent', 'timestamp')

class CashAdmin(admin.ModelAdmin):
    list_display = ('owner', 'default_fx_choice', 'total_cash', 'usd', 'hkd', 'gbp', 'eur')

# Register your models here.
admin.site.register(User)
admin.site.register(Transaction, TransactionAdmin)
admin.site.register(Portfolio, PortfolioAdmin)
admin.site.register(Cash, CashAdmin)
admin.site.register(Refresh)
admin.site.register(Realized_Profit)
admin.site.register(Temporary)