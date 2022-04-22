from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("register", views.register, name="register"),
    path("quote/<str:symbol>", views.quote, name="quote"),
    path("add_stock/<str:symbol>", views.add_stock, name="add_stock"),
    path("cash", views.cash, name="cash"),
    path("change_default_fx", views.change_default_fx, name="change_default_fx"),
    path("last_transaction", views.last_transaction, name="last_transaction"),
    path("check_stock/<str:symbol>", views.check_stock, name="check_stock"),
    path("portfolio_position", views.portfolio_position, name="portfolio_position"),
    path("transactions/<str:sort_factor>", views.transactions, name="transactions"),
    path("refresh", views.refresh, name="refresh"),
    path("refreshed_time", views.refreshed_time, name="refreshed_time"),
    path("realized_profit", views.realized_profit, name="realized_profit"),
]