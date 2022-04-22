from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    pass


class Transaction(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    symbol = models.TextField()
    cost = models.DecimalField(max_digits=10, decimal_places=3)
    CURRENCY_CHOICES = [
        ('USD', 'USD'),
        ('HKD', 'HKD'),
        ('GBP', 'GBP'),
        ('EUR', 'EUR'),
    ]
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='USD',
    )
    position = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def serialize(self):
        return {
            "id": self.id,
            "symbol": self.symbol,
            "cost": self.cost,
            "currency": self.currency,
            "position": self.position,
            "timestamp": self.timestamp.strftime("%b. %e, %Y, %I:%M %p"),
        }


class Portfolio(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    symbol = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=3)
    change = models.DecimalField(max_digits=10, decimal_places=4)
    cost = models.DecimalField(max_digits=10, decimal_places=3)
    CURRENCY_CHOICES = [
        ('USD', 'USD'),
        ('HKD', 'HKD'),
        ('GBP', 'GBP'),
        ('EUR', 'EUR'),
    ]
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='USD',
    )
    position = models.IntegerField()
    pnl = models.DecimalField(max_digits=10, decimal_places=3)
    pnl_percent = models.DecimalField(max_digits=10, decimal_places=4)
    timestamp = models.DateTimeField(auto_now_add=True)

    def serialize(self):
        return {
            "id": self.id,
            "symbol": self.symbol,
            "price": self.price,
            "change": self.change,
            "cost": self.cost,
            "currency": self.currency,
            "position": self.position,
            "pnl": self.pnl,
            "pnl_percent": self.pnl_percent,
            "timestamp": self.timestamp.strftime("%b %d %Y, %I:%M %p"),
        }


class Cash(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    default_fx_choice = models.TextField(default='USD')
    total_cash = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    usd = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    hkd = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    gbp = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    eur = models.DecimalField(max_digits=10, decimal_places=3, default=0)

    def serialize(self):
        return {
            "id": self.id,
            "default_fx_choice": self.default_fx_choice,
            "total_cash": self.total_cash,
            "usd": self.usd,
            "hkd": self.hkd,
            "gbp": self.gbp,
            "eur": self.eur,
        }


class Refresh(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(null=True, blank=True)

    def serialize(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.strftime("%b %d %Y, %I:%M %p"),
        }


class Realized_Profit(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    realized_profit = models.DecimalField(max_digits=10, decimal_places=3, default=0)

    def serialize(self):
        return {
            "id": self.id,
            "realized_profit": self.realized_profit,
        }


class Temporary(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    cost = models.DecimalField(max_digits=10, decimal_places=3, default=0)