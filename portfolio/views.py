import json, requests, datetime
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.core import serializers
from django.utils import timezone
from django.db.models import Avg, Count, Sum, F, ExpressionWrapper, DecimalField, Q, Case, Value, When
from decimal import Decimal
from datetime import datetime

from .models import User, Transaction, Portfolio, Cash, Refresh, Realized_Profit, Temporary


@login_required(login_url='login')
def index(request):
    # Create cash object in the model
    try:
        cash = Cash.objects.get(owner=request.user) 
    except Cash.DoesNotExist: 
        cash = Cash.objects.create(owner=request.user)
        cash.save()
    # Get cash object details for rendering data in cash table
    usd = cash.usd
    hkd = cash.hkd
    gbp = cash.gbp
    eur = cash.eur
    total = cash.total_cash
    default_fx_choice = cash.default_fx_choice
    
    # Create realized profit object in the model
    try:
        realized_profit = Realized_Profit.objects.get(owner=request.user)
    except Realized_Profit.DoesNotExist:
        realized_profit = Realized_Profit.objects.create(owner=request.user)
        realized_profit.save()

    # Create temporary storage object in the model for storing stock cost before a stock is deleted. 
    try:
        temporary = Temporary.objects.get(owner=request.user)
    except Temporary.DoesNotExist:
        temporary = Temporary.objects.create(owner=request.user)
        temporary.save()

    return render(request, "portfolio/index.html", {
        "categories": ['USD'],
        "usd": int(usd),
        "hkd": int(hkd),
        "gbp": int(gbp),
        "eur": int(eur),
        "total": int(total),
        "default_fx_choices": ['USD', 'HKD', 'GBP', 'EUR'],
        "default_fx_chosen": default_fx_choice,
        "deposit_withdraw_fx_choices": ['USD', 'HKD', 'GBP', 'EUR'],
    })


@login_required(login_url='login')
def quote(request, symbol):
    if request.method == "GET":
        try:
            # Quoting stock details through IEX API
            api_key = "pk_eedfeddf0a1a401abab05be8df0d25ed"
            url = f"https://cloud.iexapis.com/stable/stock/{symbol}/quote?token={api_key}"
            response = requests.get(url).json()
            return JsonResponse({
                "name": response["companyName"],
                "symbol": response["symbol"],
                "price": response["latestPrice"],
            }, status=200)
        except:
            return JsonResponse({"error": "Invalid Stock/API."}, status=404)
    
    else:
        return JsonResponse({
            "error": "GET request required."
        }, status=400)


@login_required(login_url='login')
def add_stock(request, symbol):
    if request.method == "POST":
        user = request.user
        # Get order entry input details
        data = json.loads(request.body)
        new_cost = float(data["cost"])
        new_position = data["position"]
        currency = data["currency"]
        
        # Price, quantity and currency validation: reject any of the mentioned is empty 
        if new_cost == "" or new_position == "" or data["currency"] == "":
            return JsonResponse({"error": "Please input a valid price, quantity and currency."}, status=404)
        
        # Price validation: reject if price is negative
        if new_cost <= 0:
            return JsonResponse({"error": "Please input a positive price."}, status=404)

        # Currency validation: reject if currency is not USD
        if data['currency'] != "USD":
            return JsonResponse({"error": "Only USD is accepted."}, status=404)

        # Stock symbol validation: reject if symbol not found
        # If valid, save price and price change data 
        try:
            api_key = "pk_eedfeddf0a1a401abab05be8df0d25ed"
            url = f"https://cloud.iexapis.com/stable/stock/{symbol}/quote?token={api_key}"
            response = requests.get(url).json()
            price = float(response["latestPrice"])
            change = float(response["changePercent"])
        except:
            return JsonResponse({"error": "Invalid Stock/API."}, status=404)

        # Create new transaction to Transaction Record
        transaction = Transaction.objects.create(
            owner=user, symbol=symbol, cost=Decimal(new_cost), position=new_position, currency=currency
        )
        transaction.save()

        this_stock = Portfolio.objects.filter(owner=user, symbol=symbol)
        # If the stock already exists
        if this_stock.exists():
            # Save portfolio cost to Temporary's cost for storage first. This will be used for Realized P&L
            temporary = Temporary.objects.get(owner=user)
            temporary.cost = Portfolio.objects.get(owner=user, symbol=symbol).cost
            temporary.save()
            # 'if' conditions for different scenarios on position numbers
            original_position = this_stock.values_list('position', flat=True)[0]
            # Clear all position: original position + position change = 0 e.g. 5 shares - 5 shares = 0
            if original_position + new_position == 0:
                Portfolio.objects.get(owner=user, symbol=symbol).delete()
            # Clear some position: original position * position change < 0 (opposing direction) and absolute value of original position > absolute value of position change
            elif original_position * new_position < 0 and abs(original_position) > abs(new_position):
                this_stock.update(
                    price=price, 
                    change=change, 
                    position=(F('position')+new_position), 
                    pnl=((price - F('cost'))*(F('position')+new_position)), 
                )
                if this_stock[0].position > 0:
                    this_stock.update(pnl_percent=((price - F('cost'))/F('cost')))
                elif this_stock[0].position < 0: 
                    this_stock.update(pnl_percent=((price - F('cost'))/F('cost')*(-1)))
            # Clear all position and take opposite direction on remaining shares
            elif original_position * new_position < 0 and abs(original_position) < abs(new_position):
                this_stock.update(
                    price=price, 
                    change=change, 
                    cost=new_cost, 
                    position=(F('position')+new_position), 
                    pnl=((price - new_cost) * (F('position')+new_position)), 
                )
                if this_stock[0].position > 0:
                    this_stock.update(pnl_percent=((price - F('cost'))/F('cost')))
                elif this_stock[0].position < 0: 
                    this_stock.update(pnl_percent=((price - F('cost'))/F('cost')*(-1)))
                first_transaction = Transaction.objects.filter(owner=user, symbol=symbol).last()
                first_transaction.position = int(original_position) * (-1)
                first_transaction.save()
                second_transaction = Transaction.objects.create(
                    owner=user, symbol=symbol, cost=new_cost, position=(original_position+new_position), currency=currency
                )
                second_transaction.save()
            # Add more shares / short more shares
            else:
                this_stock.update(
                    price=price, 
                    change=change, 
                    cost=(((F('cost')*F('position'))+(new_cost*new_position))/(F('position')+new_position)), 
                    position=(F('position')+new_position), 
                    pnl=((price - ((F('cost')*F('position'))+(new_cost*new_position))/(F('position')+new_position))*(F('position')+new_position)), 
                )
                if this_stock[0].position > 0:
                    this_stock.update(pnl_percent=((price - F('cost'))/F('cost')))
                elif this_stock[0].position < 0: 
                    this_stock.update(pnl_percent=((price - F('cost'))/F('cost')*(-1)))
        # If the stock does not exist yet
        else:
            holding = Portfolio.objects.create(
                owner=user, 
                symbol=symbol, 
                price=price, 
                change=change, 
                cost=new_cost, 
                position=new_position, 
                pnl=((price - new_cost) * new_position), 
                pnl_percent=((price - new_cost)/new_cost), 
                currency=currency, 
            )
            holding.save()
            if holding.position > 0:
                holding.pnl_percent = ((price - F('cost'))/F('cost'))
            elif holding.position < 0: 
                holding.pnl_percent = ((price - F('cost'))/F('cost') * (-1))
            holding.save()

        cash_change = Decimal(new_cost * new_position * (-1))
        cash = Cash.objects.get(owner=request.user)

        # Add cash to fx involved
        if currency == "USD":
            cash.usd += cash_change
        elif currency == "HKD":
            cash.hkd += cash_change
        elif currency == "GBP":
            cash.gbp += cash_change
        elif currency == "EUR":
            cash.eur += cash_change
        cash.save()

        # Based on the default FX choice, update total cash
        update_total_cash(request.user, cash.default_fx_choice)

        return HttpResponseRedirect(reverse("index"))
    
    else:
        return JsonResponse({
            "error": "POST request required."
        }, status=400)


@login_required(login_url='login')
def cash(request):
    if request.method == "POST":
        # Get cash action details
        data = json.loads(request.body)
        cash_amount = Decimal(data["amount"])
        cash_action = data["action"]
        cash_fx = data["fx"]

        # Cash amount validation: reject negative cash amount
        if cash_amount <= 0:
            return JsonResponse({"error": "Please input a positive amount."}, status=404)    
        
        # Cash action validation: reject anything other than Deposit or Withdraw
        if cash_action not in ["Deposit", "Withdraw"]:
            return JsonResponse({"error": "You can only choose Deposit or Withdraw."}, status=404)
        
        # Cash FX validation: reject anything other than USD, HKD, GBP and EUR
        if cash_fx not in ["USD", "HKD", "GBP", "EUR"]:
            return JsonResponse({"error": "Only USD/HKD/GBP/EUR are accepted."}, status=404)

        # Flip cash amount and cash transaction in transaction record to negative if this is withdrawal
        if cash_action == "Withdraw":
            cash_amount *= (-1)
            transaction_position = (-1)
        else:
            transaction_position = 1
        
        cash = Cash.objects.get(owner=request.user)

        # Add cash to FX involved
        if cash_fx == "USD":
            cash.usd += cash_amount
        elif cash_fx == "HKD":
            cash.hkd += cash_amount
        elif cash_fx == "GBP":
            cash.gbp += cash_amount
        elif cash_fx == "EUR":
            cash.eur += cash_amount
        cash.save()
        
        # Based on the default FX choice, update total cash
        update_total_cash(request.user, cash.default_fx_choice)
        
        # Add transaction
        add_transaction = Transaction.objects.create(
            owner=request.user, symbol=cash_fx, cost=Decimal(data["amount"]), position=transaction_position, currency=cash_fx
        )
        add_transaction.save()

        return HttpResponseRedirect(reverse("index"))
    
    else:
        return JsonResponse({
            "error": "POST request required."
        }, status=400)


@login_required(login_url='login')
def change_default_fx(request):
    if request.method == "POST":
        # Get new default FX choice
        data = json.loads(request.body)
        cash_fx = data["fx"]

        # Default FX choice validation: reject anything other than USD, HKD, GBP and EUR
        if cash_fx not in ["USD", "HKD", "GBP", "EUR"]:
            return JsonResponse({"error": "Only USD/HKD/GBP/EUR are accepted."}, status=404)

        cash = Cash.objects.get(owner=request.user)

        # Change default FX 
        cash.default_fx_choice = cash_fx
        cash.save()

        # Based on the default FX choice, update total cash
        update_total_cash(request.user, cash_fx)

        return HttpResponseRedirect(reverse("index"))

    else:
        return JsonResponse({
            "error": "POST request required."
        }, status=400)


def update_total_cash(requested_user, default_fx_choice):

    # Exchange Rate Assumption (API to be can be used later) - rate as of 20 Feb
    usdhkd = Decimal(7.8)
    gbpusd = Decimal(1.36)
    eurusd = Decimal(1.13)
    gbphkd = Decimal(10.6)
    eurhkd = Decimal(8.83)
    gbpeur = Decimal(1.2)

    cash = Cash.objects.get(owner=requested_user)

    # Based on the default FX choice, update total cash
    if default_fx_choice == "USD":
        usd = Decimal(cash.usd)
        hkd_to_usd = Decimal(cash.hkd) / usdhkd
        gbp_to_usd = Decimal(cash.gbp) * gbpusd
        eur_to_usd = Decimal(cash.eur) * eurusd
        cash.total_cash = usd + hkd_to_usd + gbp_to_usd + eur_to_usd
    elif default_fx_choice == "HKD":
        hkd = Decimal(cash.hkd)
        usd_to_hkd = Decimal(cash.usd) * usdhkd
        gbp_to_hkd = Decimal(cash.gbp) * gbphkd
        eur_to_hkd = Decimal(cash.eur) * eurhkd
        cash.total_cash = hkd + usd_to_hkd + gbp_to_hkd + eur_to_hkd
    elif default_fx_choice == "GBP":
        gbp = Decimal(cash.gbp)
        usd_to_gbp = Decimal(cash.usd) / gbpusd
        hkd_to_gbp = Decimal(cash.hkd) / gbphkd
        eur_to_gbp = Decimal(cash.eur) / gbpeur
        cash.total_cash = gbp + usd_to_gbp + hkd_to_gbp + eur_to_gbp
    elif default_fx_choice == "EUR":
        eur = Decimal(cash.eur)
        usd_to_eur = Decimal(cash.usd) / eurusd
        hkd_to_eur = Decimal(cash.hkd) / eurhkd
        gbp_to_eur = Decimal(cash.gbp) * gbpeur
        cash.total_cash = eur + usd_to_eur + hkd_to_eur + gbp_to_eur
    cash.save()


@login_required(login_url='login')
def portfolio_position(request):
    if request.method == "GET":
        # Load portfolio positions
        positions = Portfolio.objects.filter(owner=request.user).order_by('-symbol').values()
        return JsonResponse([position for position in positions], safe=False)

    else:
        return JsonResponse({
            "error": "GET request required."
        }, status=400)


@login_required(login_url='login')
def transactions(request, sort_factor):
    if request.method == "GET":
        # Detect sort
        if sort_factor == "0":
            order_factor = "timestamp"
        elif sort_factor == "+1":
            order_factor = "-symbol"
        elif sort_factor == "-1":
            order_factor = "symbol"
        elif sort_factor == "+2":
            order_factor = "-cost"
        elif sort_factor == "-2":
            order_factor = "cost"
        elif sort_factor == "+3":
            order_factor = "-position"
        elif sort_factor == "-3":
            order_factor = "position"
        elif sort_factor == "+4":
            order_factor = "-currency"
        elif sort_factor == "-4":
            order_factor = "currency"
        elif sort_factor == "+5":
            order_factor = "-timestamp"
        elif sort_factor == "-5":
            order_factor = "timestamp"
        # Render transactions in Transaction Record. If trigger sorting, make change to order of rendering transactions
        transactions = Transaction.objects.filter(owner=request.user).order_by(f'{order_factor}').values()
        return JsonResponse([transaction for transaction in transactions], safe=False)

    else:
        return JsonResponse({
            "error": "GET request required."
        }, status=400)


@login_required(login_url='login')
def check_stock(request, symbol):
    if request.method == "GET":
        # For checking this stock's latest position and cost for updating realized profit and oppositing transaction that exceed original position
        try:
            this_stock = Portfolio.objects.get(owner=request.user, symbol=symbol)
            latest_cost = Temporary.objects.get(owner=request.user).cost
            latest_position = this_stock.position
        except Portfolio.DoesNotExist: 
            latest_position = 0
            latest_cost = Temporary.objects.get(owner=request.user).cost
        return JsonResponse({
            "latest_position": latest_position,
            "latest_cost": Decimal(latest_cost),
            }, safe=False)
    
    else:
        return JsonResponse({
            "error": "GET request required."
        }, status=400)


@login_required(login_url='login')
def last_transaction(request):
    if request.method == "GET":
        # For adding latest transaction to transaction record, fetch timestamp for transaction date
        last_transaction_time = Transaction.objects.filter(owner=request.user).all().order_by('-timestamp')[0].timestamp
        return JsonResponse({"time": last_transaction_time}, safe=False)
    
    else:
        return JsonResponse({
            "error": "GET request required."
        }, status=400)


@login_required(login_url='login')
def realized_profit(request):
    if request.method == "PUT":
        # Updating realized profit
        data = json.loads(request.body)
        this_owner_profit = Realized_Profit.objects.get(owner=request.user)
        this_owner_profit.realized_profit += Decimal(data["pnl_change"])
        this_owner_profit.save()
        return HttpResponseRedirect(reverse("index"))

    elif request.method == "GET":
        # Render realized profit
        realized_profit = Realized_Profit.objects.get(owner=request.user).realized_profit
        return JsonResponse({"realized_profit": realized_profit}, status=200)

    else:
        return JsonResponse({
            "error": "GET or PUT request required."
        }, status=400)


@login_required(login_url='login')
def refresh(request):
    if request.method == "PUT":
        try: 
            portfolio = Portfolio.objects.filter(owner=request.user)
        except: 
            return JsonResponse({"error": "Please create portfolio first."}, status=404)
        
        api_key = "pk_eedfeddf0a1a401abab05be8df0d25ed"

        # Refresh portfolio position details
        for holding in portfolio:
            url = f"https://cloud.iexapis.com/stable/stock/{holding.symbol}/quote?token={api_key}"
            response = requests.get(url).json()
            refreshed_price = Decimal(response["latestPrice"])
            refreshed_change = Decimal(response["changePercent"])
            holding.price = refreshed_price
            holding.change = refreshed_change
            holding.pnl = ((refreshed_price - holding.cost) * holding.position)
            holding.pnl_percent = ((refreshed_price - holding.cost) / holding.cost)
            holding.save()
        return HttpResponseRedirect(reverse("index"))

    else:
        return JsonResponse({
            "error": "PUT request required."
        }, status=400)


@login_required(login_url='login')
def refreshed_time(request):
    if request.method == "PUT":
        # Updating refreshed time
        current_time = timezone.now()
        try:
            refresh = Refresh.objects.get(owner=request.user)
            refresh.timestamp = current_time
            refresh.save()
        except:
            refresh = Refresh.objects.create(owner=request.user, timestamp=current_time)
            refresh.save()
        return HttpResponseRedirect(reverse("index"))

    elif request.method == "GET":
        try:
            refreshed_time = Refresh.objects.get(owner=request.user).timestamp
        except:
            refreshed_time = ""
        return JsonResponse({"refreshed_time": refreshed_time}, status=200)
    
    else:
        return JsonResponse({
            "error": "GET or PUT request required."
        }, status=400)


def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "portfolio/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "portfolio/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "portfolio/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "portfolio/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "portfolio/register.html")
