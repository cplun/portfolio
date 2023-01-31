from django.test import TestCase
from django.urls import reverse
from .models import User, Transaction, Portfolio, Cash, Refresh, Realized_Profit, Temporary
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.relative_locator import locate_with
from selenium.webdriver.common.by import By
from datetime import datetime
import time
import finnhub

# Server Side Tests
class ServerSideTests(TestCase):
    
    def setUp(self):
        # setUp is used to create/initialize dummy database objects for testing
        # Create user
        user = User.objects.create_user("user1", "email", "pw1")

        # Create portfolio
        portfolio = Portfolio.objects.create(
            owner=user, 
            symbol="TEST", 
            price=101, 
            change=0.01, 
            cost=100, 
            position=10, 
            pnl=10, 
            pnl_percent=0.01, 
            currency="USD", 
        )

        # Create transaction
        transaction = Transaction.objects.create(
            owner=user, 
            symbol="TEST", 
            cost=100, 
            position=10, 
            currency="USD",
        )

        # Create cash
        cash = Cash.objects.create(
            owner=user,
            default_fx_choice="USD",
            total_cash=0,
            usd=0,
            hkd=0,
            gbp=0,
            eur=0,
        )

        # Create realized profit
        realized_profit = Realized_Profit.objects.create(
            owner=user,
            realized_profit=0,
        )

        # Create temporary 
        temporary = Temporary.objects.create(
            owner=user,
            cost=0,
        )
    
    def test_valid_holdings(self):
        # Test Portfolio model is valid
        holding = Portfolio.objects.get(id=1)
        self.assertTrue(holding.is_valid_holding())
    
    def test_valid_transactions(self):
        # Test Transaction model is valid
        transaction = Transaction.objects.get(id=1)
        self.assertTrue(transaction.is_valid_transaction())
    
    def test_transaction_field_length(self):
        # Test Transaction model fields' length
        transaction = Transaction.objects.get(id=1)
        cost_max_digits = transaction._meta.get_field('cost').max_digits
        currency_max_length = transaction._meta.get_field('currency').max_length
        self.assertEqual(cost_max_digits, 10)
        self.assertEqual(currency_max_length, 3)

    def test_portfolio_field_length(self):
        # Test Portfolio model fields' length
        holding = Portfolio.objects.get(id=1)
        price_max_digits = holding._meta.get_field('price').max_digits
        change_max_digits = holding._meta.get_field('change').max_digits
        cost_max_digits = holding._meta.get_field('cost').max_digits
        pnl_max_digits = holding._meta.get_field('pnl').max_digits
        pnl_percent_max_digits = holding._meta.get_field('pnl_percent').max_digits
        currency_max_length = holding._meta.get_field('currency').max_length
        self.assertEqual(price_max_digits, 10)
        self.assertEqual(change_max_digits, 10)
        self.assertEqual(cost_max_digits, 10)
        self.assertEqual(pnl_max_digits, 10)
        self.assertEqual(pnl_percent_max_digits, 10)
        self.assertEqual(currency_max_length, 3)

    def test_cash_field_length(self):
        # Test Cash model fields' length
        cash = Cash.objects.get(id=1)
        total_cash_max_digits = cash._meta.get_field('total_cash').max_digits
        usd_max_digits = cash._meta.get_field('usd').max_digits
        hkd_max_digits = cash._meta.get_field('hkd').max_digits
        gbp_max_digits = cash._meta.get_field('gbp').max_digits
        eur_max_digits = cash._meta.get_field('eur').max_digits
        self.assertEqual(total_cash_max_digits, 10)
        self.assertEqual(usd_max_digits, 10)
        self.assertEqual(hkd_max_digits, 10)
        self.assertEqual(gbp_max_digits, 10)
        self.assertEqual(eur_max_digits, 10)
    
    def test_realized_profit_field_length(self):
        # Test Realized_Profit model fields' length
        realized_profit = Realized_Profit.objects.get(id=1)
        realized_profit_max_digits = realized_profit._meta.get_field('realized_profit').max_digits
        self.assertEqual(realized_profit_max_digits, 10)
    
    def test_temporary_field_length(self):
        # Test Temporary model fields' length
        temporary = Temporary.objects.get(id=1)
        cost_max_digits = temporary._meta.get_field('cost').max_digits
        self.assertEqual(cost_max_digits, 10)

    def test_redirect_if_not_logged_in(self):
        # Test user is redirected to login page if not logged in yet
        response = self.client.get(reverse('index'))
        # Manually check redirect (Can't use assertRedirect, because the redirect URL is unpredictable)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/login'))
    
    def test_redirect_if_logged_in_but_not_correct_permission(self):
        # Test user is redirected to login page again if username or password is incorrect
        login = self.client.login(username='user1', password='pw2')
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/login'))
    
    def test_logged_in_success(self):
        # Test user is logged in successfully 
        login = self.client.login(username='user1', password='pw1')
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)


def get_datetime_now():
    # This function is used in Client Side Testing's test_deposit_withdraw function to format date for asserting transaction time in transaction record 
    now = datetime.now()
    dt_string = now.strftime("%b. %d, %Y, %I:%M %p")
    return dt_string


# Client Side Tests using Selenium
class ClientSideSeleniumTests(StaticLiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.browser = webdriver.Chrome()

    @classmethod
    def tearDownClass(cls):
        cls.browser.quit()
        super().tearDownClass()
    
    def setUp(self):
        # This function automatically logs user in
        super(ClientSideSeleniumTests, self).setUp()
        self.browser.maximize_window()
        test_user = User.objects.create(username='user1')
        test_user.set_password('pw1')
        test_user.save()
        # Login the user
        self.assertTrue(self.client.login(username='user1', password='pw1'))
        # Add cookie to log in the browser
        cookie = self.client.cookies['sessionid']
        self.browser.get(self.live_server_url) # visit page in the site domain so the page accepts the cookie
        self.browser.add_cookie({'name': 'sessionid', 'value': cookie.value, 'secure': False, 'path': '/'})

    
    def test_deposit_withdraw(self):
        self.browser.get('%s%s' % (self.live_server_url, ''))

        cash_submit = self.browser.find_element(By.ID, "cash-button")

        self.browser.find_element(By.ID, "cash-amount").send_keys('100')
        Select(self.browser.find_element(By.ID, "cash-action")).select_by_value("deposit")
        Select(self.browser.find_element(By.ID, "cash-fx")).select_by_value("USD")
        cash_submit.click()
        time.sleep(0.5)

        # Test first transaction is rendered correctly in Transaction Record
        first_tran_symbol_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-symbol-heading"})).text
        first_tran_transacted_cost_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-transacted-cost-heading"})).text
        first_tran_position_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-position-heading"})).text
        first_tran_currency_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-currency-heading"})).text
        first_tran_transaction_date_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-transaction-date-heading"})).text
        
        self.assertEqual(first_tran_symbol_locator, "USD")
        self.assertEqual(first_tran_transacted_cost_locator, "100")
        self.assertEqual(first_tran_position_locator, "1")
        self.assertEqual(first_tran_currency_locator, "USD")
        self.assertEqual(first_tran_transaction_date_locator, get_datetime_now())

        fx_bases = ['HKD', 'GBP', 'EUR']
        for fx in fx_bases:
            self.browser.find_element(By.ID, "cash-amount").send_keys('100')
            Select(self.browser.find_element(By.ID, "cash-action")).select_by_value("deposit")
            Select(self.browser.find_element(By.ID, "cash-fx")).select_by_value(fx)
            cash_submit.click()
            time.sleep(0.5)

        # Test all cash balance are correctly rendered after deposits
        fx_bases = ['usd', 'hkd', 'gbp', 'eur']
        for fx in fx_bases:
            self.assertEqual(int(self.browser.find_element(By.ID, "cash-table-{}".format(fx)).text), 100)
        self.assertGreater(int(self.browser.find_element(By.ID, "cash-table-total").text), 0)
        
        fx_bases = ['USD', 'HKD', 'GBP', 'EUR']
        for fx in fx_bases:
            self.browser.find_element(By.ID, "cash-amount").send_keys('100')
            Select(self.browser.find_element(By.ID, "cash-action")).select_by_value("withdraw")
            Select(self.browser.find_element(By.ID, "cash-fx")).select_by_value(fx)
            cash_submit.click()
            time.sleep(0.5)
        
        # Test all cash balance are back to 0 after all withdrawals
        fx_bases = ['usd', 'hkd', 'gbp', 'eur', 'total']
        for fx in fx_bases:
            self.assertEqual(int(self.browser.find_element(By.ID, "cash-table-{}".format(fx)).text), 0)
    
        last_tran_symbol_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-symbol-heading"})).text
        last_tran_transacted_cost_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-transacted-cost-heading"})).text
        last_tran_position_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-position-heading"})).text
        last_tran_currency_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-currency-heading"})).text
        last_tran_transaction_date_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-transaction-date-heading"})).text

        # Test last transaction is rendered correctly in Transaction Record    
        self.assertEqual(last_tran_symbol_locator, "EUR")
        self.assertEqual(last_tran_transacted_cost_locator, "100")
        self.assertEqual(last_tran_position_locator, "-1")
        self.assertEqual(last_tran_currency_locator, "EUR")
        self.assertEqual(last_tran_transaction_date_locator, get_datetime_now())
    

    def test_default_fx_change(self):
        self.browser.get('%s%s' % (self.live_server_url, ''))

        cash_submit = self.browser.find_element(By.ID, "cash-button")
        
        # Input all fx data
        fx_bases = ['USD', 'HKD', 'GBP', 'EUR']
        for fx in fx_bases:
            self.browser.find_element(By.ID, "cash-amount").send_keys('100')
            self.browser.find_element(By.ID, "cash-action").send_keys("Deposit")
            self.browser.find_element(By.ID, "cash-fx").send_keys(fx)
            cash_submit.click()
            time.sleep(0.5)

        # Test default fx changes triggers correct change in total cash value and changes default fx choice
        for fx in fx_bases:
            Select(self.browser.find_element(By.ID, "default-fx")).select_by_value(fx)
            time.sleep(0.5)
            total_cash = Cash.objects.get(id=1).total_cash
            default_fx_choice = Cash.objects.get(id=1).default_fx_choice
            self.assertEqual(int(self.browser.find_element(By.ID, "cash-table-total").text.replace(',', '')), int(total_cash))
            self.assertEqual(fx, default_fx_choice)


    def test_quote(self):
        self.browser.get('%s%s' % (self.live_server_url, ''))
        quote_submit = self.browser.find_element(By.ID, "quote-button")
        correct_symbol = 'AAPL'
        incorrect_symbol = 'FAKEQUOTE'

        # Test with invalid quote input
        self.browser.find_element(By.ID, "quote-input").send_keys(incorrect_symbol)
        quote_submit.click()
        time.sleep(2)
        quote_output = self.browser.find_element(By.ID, "quote-content").text
        self.assertEqual(quote_output, "Invalid Symbol.")
        
        # Test with valid quote input
        self.browser.find_element(By.ID, "quote-input").send_keys(correct_symbol)
        quote_submit.click()
        time.sleep(2)

        # Fetch live data to cross check
        finnhub_client = finnhub.Client(api_key="c7nuioqad3idf06mjrtg")
        quote = finnhub_client.quote(correct_symbol)
        company_profile = finnhub_client.company_profile2(symbol=correct_symbol)
        quoted_name = company_profile["name"]
        quoted_symbol = company_profile["ticker"]
        quoted_price = quote["c"]

        validator = "{} {} ${}".format(quoted_name, quoted_symbol, quoted_price)
        quote_output = self.browser.find_element(By.ID, "quote-content").text.split('\n')[0]
        self.assertEqual(quote_output, validator)
        
        # Test transpose button 
        transpose_button = self.browser.find_element(By.ID, "transpose-button")
        transpose_button.click()
        time.sleep(0.5)
        symbol_entry = self.browser.find_element(By.ID, "manual-add-symbol").get_attribute('value')
        price_entry = self.browser.find_element(By.ID, "manual-add-price").get_attribute('value')
        self.assertEqual(symbol_entry, quoted_symbol)
        self.assertEqual(float(price_entry), quoted_price)
    

    def test_order_entry_and_refresh(self):
        self.browser.get('%s%s' % (self.live_server_url, ''))
        
        # Input Keys
        order_symbol_entry = self.browser.find_element(By.ID, "manual-add-symbol")
        order_price_entry = self.browser.find_element(By.ID, "manual-add-price")
        order_position_entry = self.browser.find_element(By.ID, "manual-add-position")
        buy_order = self.browser.find_element(By.ID, "buy_label")
        sell_order = self.browser.find_element(By.ID, "sell_label")
        order_fx = self.browser.find_element(By.ID, "manual-add-currency")
        order_submit = self.browser.find_element(By.ID, "manual-add-button")

        # First input - Initial buy of first ticker 
        symbol = "GS"
        price_entry = 350.21
        position_entry = 100
        fx = "USD"
        order_symbol_entry.send_keys(symbol)
        order_price_entry.send_keys(price_entry)
        order_position_entry.send_keys(position_entry)
        buy_order.click()
        Select(order_fx).select_by_value(fx)
        order_submit.click()
        time.sleep(2)

        # Test last transaction is rendered correctly in Transaction Record    
        last_tran_symbol_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-symbol-heading"})).text
        last_tran_transacted_cost_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-transacted-cost-heading"})).text
        last_tran_position_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-position-heading"})).text
        last_tran_currency_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-currency-heading"})).text
        last_tran_transaction_date_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-transaction-date-heading"})).text
  
        self.assertEqual(last_tran_symbol_locator, symbol)
        self.assertEqual(last_tran_transacted_cost_locator, f"{price_entry}")
        self.assertEqual(last_tran_position_locator, f"{position_entry}")
        self.assertEqual(last_tran_currency_locator, fx)
        self.assertEqual(last_tran_transaction_date_locator, get_datetime_now())

        # Test ticker is rendered at the top in Portfolio table
        last_port_symbol_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "port-symbol-heading"})).text
        self.assertEqual(last_port_symbol_locator, "GS")

        # Test first input's portfolio holding is rendered correctly
        test_1_symbol = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_symbol").text
        test_1_price = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_price").text
        test_1_change = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_change").text
        test_1_cost = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_cost").text
        test_1_position = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_position").text
        test_1_mv = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_mv").text
        test_1_pnl = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_pnl").text
        test_1_pnl_percent = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_pnl_percent").text

        finnhub_client = finnhub.Client(api_key="c7nuioqad3idf06mjrtg")
        quote = finnhub_client.quote(symbol)

        self.assertEqual(test_1_symbol, symbol)
        self.assertEqual(test_1_price, f"{quote['c']:.2f}")
        self.assertEqual(test_1_change, f"{quote['dp']:.2f}%")
        self.assertEqual(test_1_cost, f"{price_entry:.2f}")
        self.assertTrue(int(test_1_position.replace(',', '')) - int(position_entry) <= 1)
        self.assertTrue(int(test_1_mv.replace(',', '')) - int((quote['c'] * position_entry)) <= 1)
        self.assertTrue(int(test_1_pnl.replace(',', '')) - int(((quote['c'] - price_entry) * position_entry)) <= 1)
        self.assertEqual(test_1_pnl_percent, f"{(quote['c'] - price_entry) / price_entry * 100 :.2f}%")

        # Test Total Market Value, P&L, P&L% and Realized P&L are rendered correctly
        total_1_mv = self.browser.find_element(By.ID, "total_mv").text
        total_1_pnl = self.browser.find_element(By.ID, "total_pnl").text
        total_1_pnl_percent = self.browser.find_element(By.ID, "total_pnl_percent").text
        realized_pnl = self.browser.find_element(By.ID, "realized_profit_total").text

        self.assertTrue((int(total_1_mv.replace(',', '')) - int(test_1_mv.replace(',', ''))) <= 1)
        self.assertTrue((int(total_1_pnl.replace(',', '')) - int(test_1_pnl.replace(',', ''))) <= 1)
        self.assertEqual(total_1_pnl_percent, test_1_pnl_percent)
        self.assertEqual(realized_pnl, "0")

        # Test Cash balances are updated correctly
        usd_1_balance = self.browser.find_element(By.ID, "cash-table-usd").text
        total_cash_1_balance = self.browser.find_element(By.ID, "cash-table-total").text

        self.assertEqual(usd_1_balance, f"{int(-(price_entry * position_entry)):,g}")
        self.assertEqual(total_cash_1_balance, f"{int(-(price_entry * position_entry)):,g}")

        # Second input - Initial buy of second ticker
        symbol = "TSLA"
        price_entry = 140.5
        position_entry = 50
        fx = "USD"
        order_symbol_entry.send_keys(symbol)
        order_price_entry.send_keys(price_entry)
        order_position_entry.send_keys(position_entry)
        buy_order.click()
        Select(order_fx).select_by_value(fx)
        order_submit.click()
        time.sleep(2)

        # Test last transaction is rendered correctly in Transaction Record    
        last_tran_symbol_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-symbol-heading"})).text
        last_tran_transacted_cost_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-transacted-cost-heading"})).text
        last_tran_position_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-position-heading"})).text
        last_tran_currency_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-currency-heading"})).text
        last_tran_transaction_date_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-transaction-date-heading"})).text
  
        self.assertEqual(last_tran_symbol_locator, symbol)
        self.assertEqual(last_tran_transacted_cost_locator, f"{price_entry}")
        self.assertEqual(last_tran_position_locator, f"{position_entry}")
        self.assertEqual(last_tran_currency_locator, fx)
        self.assertEqual(last_tran_transaction_date_locator, get_datetime_now())

        # Test "GS" ticker is still rendered at the top in Portfolio table before "TSLA"
        last_port_symbol_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "port-symbol-heading"})).text
        self.assertEqual(last_port_symbol_locator, "GS")

        # Test second input's portfolio holding is rendered correctly
        test_2_symbol = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_symbol").text
        test_2_price = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_price").text
        test_2_change = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_change").text
        test_2_cost = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_cost").text
        test_2_position = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_position").text
        test_2_mv = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_mv").text
        test_2_pnl = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_pnl").text
        test_2_pnl_percent = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_pnl_percent").text

        finnhub_client = finnhub.Client(api_key="c7nuioqad3idf06mjrtg")
        quote = finnhub_client.quote(symbol)

        self.assertEqual(test_2_symbol, symbol)
        self.assertEqual(test_2_price, f"{quote['c']:.2f}")
        self.assertEqual(test_2_change, f"{quote['dp']:.2f}%")
        self.assertEqual(test_2_cost, f"{price_entry:.2f}")
        self.assertTrue(int(test_2_position.replace(',', '')) - int(position_entry) <= 1)
        self.assertTrue(int(test_2_mv.replace(',', '')) - int((quote['c'] * position_entry)) <= 1)
        self.assertTrue(int(test_2_pnl.replace(',', '')) - int(((quote['c'] - price_entry) * position_entry)) <= 1)
        self.assertEqual(test_2_pnl_percent, f"{(quote['c'] - price_entry) / price_entry * 100 :.2f}%")

        # Test Total Market Value, P&L, P&L% and Realized P&L are rendered correctly
        total_2_mv = self.browser.find_element(By.ID, "total_mv").text
        total_2_pnl = self.browser.find_element(By.ID, "total_pnl").text
        total_2_pnl_percent = self.browser.find_element(By.ID, "total_pnl_percent").text
        realized_pnl = self.browser.find_element(By.ID, "realized_profit_total").text

        self.assertTrue((int(total_2_mv.replace(',', '')) - int(test_1_mv.replace(',', '')) - int(test_2_mv.replace(',', ''))) <= 1)
        self.assertTrue((int(total_2_pnl.replace(',', '')) - int(test_1_pnl.replace(',', '')) - int(test_2_pnl.replace(',', ''))) <= 1)
        self.assertEqual(total_2_pnl_percent, f"{(int(total_2_mv.replace(',', ''))/(int(total_2_mv.replace(',', '')) - int(total_2_pnl.replace(',', '')))-1) * 100 :.2f}%")
        self.assertEqual(realized_pnl, "0")

        # Test Cash balances are updated correctly
        usd_2_balance = self.browser.find_element(By.ID, "cash-table-usd").text
        total_cash_2_balance = self.browser.find_element(By.ID, "cash-table-total").text

        self.assertEqual(usd_2_balance, f"{(int(usd_1_balance.replace(',', '')) - int((price_entry * position_entry))):,g}")
        self.assertEqual(total_cash_2_balance, f"{(int(total_cash_1_balance.replace(',', '')) - int((price_entry * position_entry))):,g}")

        # Third input - Initial buy of third ticker
        symbol = "AAPL"
        price_entry = 130
        position_entry = 200
        fx = "USD"
        order_symbol_entry.send_keys(symbol)
        order_price_entry.send_keys(price_entry)
        order_position_entry.send_keys(position_entry)
        buy_order.click()
        Select(order_fx).select_by_value(fx)
        order_submit.click()
        time.sleep(2)

        # Test last transaction is rendered correctly in Transaction Record    
        last_tran_symbol_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-symbol-heading"})).text
        last_tran_transacted_cost_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-transacted-cost-heading"})).text
        last_tran_position_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-position-heading"})).text
        last_tran_currency_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-currency-heading"})).text
        last_tran_transaction_date_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-transaction-date-heading"})).text
  
        self.assertEqual(last_tran_symbol_locator, symbol)
        self.assertEqual(last_tran_transacted_cost_locator, f"{price_entry}")
        self.assertEqual(last_tran_position_locator, f"{position_entry}")
        self.assertEqual(last_tran_currency_locator, fx)
        self.assertEqual(last_tran_transaction_date_locator, get_datetime_now())

        # Test "AAPL" ticker is rendered at the top in Portfolio table, on top of "GS" and "TSLA"
        last_port_symbol_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "port-symbol-heading"})).text
        self.assertEqual(last_port_symbol_locator, "AAPL")

        # Test third input's portfolio holding is rendered correctly
        test_3_symbol = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_symbol").text
        test_3_price = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_price").text
        test_3_change = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_change").text
        test_3_cost = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_cost").text
        test_3_position = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_position").text
        test_3_mv = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_mv").text
        test_3_pnl = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_pnl").text
        test_3_pnl_percent = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_pnl_percent").text

        finnhub_client = finnhub.Client(api_key="c7nuioqad3idf06mjrtg")
        quote = finnhub_client.quote(symbol)

        self.assertEqual(test_3_symbol, symbol)
        self.assertEqual(test_3_price, f"{quote['c']:.2f}")
        self.assertEqual(test_3_change, f"{quote['dp']:.2f}%")
        self.assertEqual(test_3_cost, f"{price_entry:.2f}")
        self.assertTrue(int(test_3_position.replace(',', '')) - int(position_entry) <= 1)
        self.assertTrue(int(test_3_mv.replace(',', '')) - int((quote['c'] * position_entry)) <= 1)
        self.assertTrue(int(test_3_pnl.replace(',', '')) - int(((quote['c'] - price_entry) * position_entry)) <= 1)
        self.assertEqual(test_3_pnl_percent, f"{(quote['c'] - price_entry) / price_entry * 100 :.2f}%")

        # Test Total Market Value, P&L, P&L% and Realized P&L are rendered correctly
        total_3_mv = self.browser.find_element(By.ID, "total_mv").text
        total_3_pnl = self.browser.find_element(By.ID, "total_pnl").text
        total_3_pnl_percent = self.browser.find_element(By.ID, "total_pnl_percent").text
        realized_pnl = self.browser.find_element(By.ID, "realized_profit_total").text

        self.assertTrue((int(total_3_mv.replace(',', '')) - int(test_1_mv.replace(',', '')) - int(test_2_mv.replace(',', '')) - int(test_3_mv.replace(',', ''))) <= 1)
        self.assertTrue((int(total_3_pnl.replace(',', '')) - int(test_1_pnl.replace(',', '')) - int(test_2_pnl.replace(',', '')) - int(test_3_pnl.replace(',', ''))) <= 1)
        self.assertEqual(total_3_pnl_percent, f"{(int(total_3_mv.replace(',', ''))/(int(total_3_mv.replace(',', '')) - int(total_3_pnl.replace(',', '')))-1) * 100 :.2f}%")
        self.assertEqual(realized_pnl, "0")

        # Test Cash balances are updated correctly
        usd_3_balance = self.browser.find_element(By.ID, "cash-table-usd").text
        total_cash_3_balance = self.browser.find_element(By.ID, "cash-table-total").text

        self.assertEqual(usd_3_balance, f"{(int(usd_2_balance.replace(',', '')) - int((price_entry * position_entry))):,g}")
        self.assertEqual(total_cash_3_balance, f"{(int(total_cash_2_balance.replace(',', '')) - int((price_entry * position_entry))):,g}")

        # Test Refresh
        refresh_button = self.browser.find_element(By.ID, "refresh-button")
        refresh_button.click()
        time.sleep(3)

        finnhub_client = finnhub.Client(api_key="c7nuioqad3idf06mjrtg")
        quote_1 = finnhub_client.quote("GS")
        quote_2 = finnhub_client.quote("TSLA")
        quote_3 = finnhub_client.quote("AAPL")

        symbol = "GS"
        test_1_symbol = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_symbol").text
        test_1_price = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_price").text
        test_1_change = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_change").text
        test_1_cost = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_cost").text
        test_1_position = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_position").text
        test_1_mv = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_mv").text
        test_1_pnl = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_pnl").text
        test_1_pnl_percent = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_pnl_percent").text

        symbol = "TSLA"
        test_2_symbol = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_symbol").text
        test_2_price = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_price").text
        test_2_change = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_change").text
        test_2_cost = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_cost").text
        test_2_position = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_position").text
        test_2_mv = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_mv").text
        test_2_pnl = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_pnl").text
        test_2_pnl_percent = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_pnl_percent").text

        symbol = "AAPL"
        test_3_symbol = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_symbol").text
        test_3_price = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_price").text
        test_3_change = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_change").text
        test_3_cost = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_cost").text
        test_3_position = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_position").text
        test_3_mv = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_mv").text
        test_3_pnl = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_pnl").text
        test_3_pnl_percent = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_pnl_percent").text

        # Test portfolio holdings are updated correctly after clicking Refresh button
        self.assertEqual(test_1_price, f"{quote_1['c']:.2f}")
        self.assertEqual(test_1_change, f"{quote_1['dp']:.2f}%")
        self.assertEqual(test_1_mv, f"{(quote_1['c'] * int(test_1_position)):,g}")
        self.assertEqual(test_1_pnl, f"{((quote_1['c'] - float(test_1_cost)) * int(test_1_position)):,g}")
        self.assertEqual(test_1_pnl_percent, f"{(quote_1['c'] - float(test_1_cost)) / float(test_1_cost) * 100 :.2f}%")
        
        self.assertEqual(test_2_price, f"{quote_2['c']:.2f}")
        self.assertEqual(test_2_change, f"{quote_2['dp']:.2f}%")
        self.assertEqual(test_2_mv, f"{(quote_2['c'] * int(test_2_position)):,g}")
        self.assertEqual(test_2_pnl, f"{((quote_2['c'] - float(test_2_cost)) * int(test_2_position)):,g}")
        self.assertEqual(test_2_pnl_percent, f"{(quote_2['c'] - float(test_2_cost)) / float(test_2_cost) * 100 :.2f}%")

        self.assertEqual(test_3_price, f"{quote_3['c']:.2f}")
        self.assertEqual(test_3_change, f"{quote_3['dp']:.2f}%")
        self.assertEqual(test_3_mv, f"{(quote_3['c'] * int(test_3_position)):,g}")
        self.assertEqual(test_3_pnl, f"{((quote_3['c'] - float(test_3_cost)) * int(test_3_position)):,g}")
        self.assertEqual(test_3_pnl_percent, f"{(quote_3['c'] - float(test_3_cost)) / float(test_3_cost) * 100 :.2f}%")

        # Test Total Market Value, P&L and P&L% are rendered correctly after clicking Refresh button
        total_mv = self.browser.find_element(By.ID, "total_mv").text
        total_pnl = self.browser.find_element(By.ID, "total_pnl").text
        total_pnl_percent = self.browser.find_element(By.ID, "total_pnl_percent").text

        self.assertTrue((int(total_mv.replace(',', '')) - int(test_1_mv.replace(',', '')) - int(test_2_mv.replace(',', '')) - int(test_3_mv.replace(',', ''))) <= 1)
        self.assertTrue((int(total_pnl.replace(',', '')) - int(test_1_pnl.replace(',', '')) - int(test_2_pnl.replace(',', '')) - int(test_3_pnl.replace(',', ''))) <= 1)
        self.assertEqual(total_pnl_percent, f"{(int(total_mv.replace(',', ''))/(int(total_mv.replace(',', '')) - int(total_pnl.replace(',', '')))-1) * 100 :.2f}%")
        
        # Fourth input - Subsequent buy of first ticker at higher price
        symbol = "GS"
        price_entry = 360.89
        position_entry = 80
        fx = "USD"
        order_symbol_entry.send_keys(symbol)
        order_price_entry.send_keys(price_entry)
        order_position_entry.send_keys(position_entry)
        buy_order.click()
        Select(order_fx).select_by_value(fx)
        order_submit.click()
        time.sleep(2)

        # Test portfolio holding is rendered correctly
        test_1_symbol = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_symbol").text
        test_1_price = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_price").text
        test_1_change = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_change").text
        test_1_cost = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_cost").text
        test_1_position = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_position").text
        test_1_mv = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_mv").text
        test_1_pnl = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_pnl").text
        test_1_pnl_percent = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_pnl_percent").text

        finnhub_client = finnhub.Client(api_key="c7nuioqad3idf06mjrtg")
        quote = finnhub_client.quote(symbol)

        self.assertEqual(test_1_symbol, symbol)
        self.assertEqual(test_1_price, f"{quote['c']:.2f}")
        self.assertEqual(test_1_change, f"{quote['dp']:.2f}%")
        self.assertEqual(test_1_cost, f"{(((350.21 * 100) + (price_entry  * position_entry)) / (100 + position_entry)):.2f}")
        self.assertTrue(int(test_1_position.replace(',', '')) - int(100 + position_entry) <= 1)
        self.assertTrue(int(test_1_mv.replace(',', '')) - int((quote['c'] * (100 + position_entry))) <= 1)
        self.assertTrue(int(test_1_pnl.replace(',', '')) - int((quote['c'] - float(test_1_cost)) * (100 + position_entry)) <= 1)
        self.assertTrue(float(test_1_pnl_percent.replace('%', '')) - (quote['c'] - float(test_1_cost)) / float(test_1_cost) * 100 <= 0.01)

        # Test Total Market Value, P&L and P&L% are rendered correctly
        total_4_mv = self.browser.find_element(By.ID, "total_mv").text
        total_4_pnl = self.browser.find_element(By.ID, "total_pnl").text
        total_4_pnl_percent = self.browser.find_element(By.ID, "total_pnl_percent").text

        self.assertTrue((int(total_4_mv.replace(',', '')) - int(test_1_mv.replace(',', '')) - int(test_2_mv.replace(',', '')) - int(test_3_mv.replace(',', ''))) <= 1)
        self.assertTrue((int(total_4_pnl.replace(',', '')) - int(test_1_pnl.replace(',', '')) - int(test_2_pnl.replace(',', '')) - int(test_3_pnl.replace(',', ''))) <= 1)
        self.assertEqual(total_4_pnl_percent, f"{(int(total_4_mv.replace(',', ''))/(int(total_4_mv.replace(',', '')) - int(total_4_pnl.replace(',', '')))-1) * 100 :.2f}%")

        # Test Cash balances are updated correctly
        usd_4_balance = self.browser.find_element(By.ID, "cash-table-usd").text
        total_cash_4_balance = self.browser.find_element(By.ID, "cash-table-total").text

        self.assertEqual(usd_4_balance, f"{(int(usd_3_balance.replace(',', '')) - int((price_entry * position_entry))):,g}")
        self.assertEqual(total_cash_4_balance, f"{(int(total_cash_3_balance.replace(',', '')) - int((price_entry * position_entry))):,g}")

        # Fifth input - Subsequent buy of first ticker at lower price
        symbol = "GS"
        price_entry = 330
        position_entry = 120
        fx = "USD"
        order_symbol_entry.send_keys(symbol)
        order_price_entry.send_keys(price_entry)
        order_position_entry.send_keys(position_entry)
        buy_order.click()
        Select(order_fx).select_by_value(fx)
        order_submit.click()
        time.sleep(2)

        # Test portfolio holding is rendered correctly
        test_1_symbol = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_symbol").text
        test_1_price = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_price").text
        test_1_change = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_change").text
        test_1_cost = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_cost").text
        test_1_position = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_position").text
        test_1_mv = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_mv").text
        test_1_pnl = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_pnl").text
        test_1_pnl_percent = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_pnl_percent").text

        finnhub_client = finnhub.Client(api_key="c7nuioqad3idf06mjrtg")
        quote = finnhub_client.quote(symbol)

        self.assertEqual(test_1_symbol, symbol)
        self.assertEqual(test_1_price, f"{quote['c']:.2f}")
        self.assertEqual(test_1_change, f"{quote['dp']:.2f}%")
        self.assertEqual(test_1_cost, f"{(((350.21 * 100) + (360.89 * 80) + (price_entry  * position_entry)) / (100 + 80 + position_entry)):.2f}")
        self.assertTrue(int(test_1_position.replace(',', '')) - int(100 + 80 + position_entry) <= 1)
        self.assertTrue(int(test_1_mv.replace(',', '')) - int((quote['c'] * (100 + 80 + position_entry))) <= 1)
        self.assertTrue(int(test_1_pnl.replace(',', '')) - int((quote['c'] - float(test_1_cost)) * (100 + 80 + position_entry)) <= 1)
        self.assertTrue(float(test_1_pnl_percent.replace('%', '')) - (quote['c'] - float(test_1_cost)) / float(test_1_cost) * 100 <= 0.01)

        # Test Total Market Value, P&L and P&L% are rendered correctly
        total_5_mv = self.browser.find_element(By.ID, "total_mv").text
        total_5_pnl = self.browser.find_element(By.ID, "total_pnl").text
        total_5_pnl_percent = self.browser.find_element(By.ID, "total_pnl_percent").text

        self.assertTrue((int(total_5_mv.replace(',', '')) - int(test_1_mv.replace(',', '')) - int(test_2_mv.replace(',', '')) - int(test_3_mv.replace(',', ''))) <= 1)
        self.assertTrue((int(total_5_pnl.replace(',', '')) - int(test_1_pnl.replace(',', '')) - int(test_2_pnl.replace(',', '')) - int(test_3_pnl.replace(',', ''))) <= 1)
        self.assertEqual(total_5_pnl_percent, f"{(int(total_5_mv.replace(',', ''))/(int(total_5_mv.replace(',', '')) - int(total_5_pnl.replace(',', '')))-1) * 100 :.2f}%")

        # Test Cash balances are updated correctly
        usd_5_balance = self.browser.find_element(By.ID, "cash-table-usd").text
        total_cash_5_balance = self.browser.find_element(By.ID, "cash-table-total").text

        self.assertEqual(usd_5_balance, f"{(int(usd_4_balance.replace(',', '')) - int((price_entry * position_entry))):,g}")
        self.assertEqual(total_cash_5_balance, f"{(int(total_cash_4_balance.replace(',', '')) - int((price_entry * position_entry))):,g}")

        # Sixth input - Subsequent sell of first ticker at higher price
        symbol = "GS"
        price_entry = 375.5
        position_entry = 90
        fx = "USD"
        order_symbol_entry.send_keys(symbol)
        order_price_entry.send_keys(price_entry)
        order_position_entry.send_keys(position_entry)
        sell_order.click()
        Select(order_fx).select_by_value(fx)
        order_submit.click()
        time.sleep(2)
        
        # Test last transaction is rendered correctly in Transaction Record    
        last_tran_symbol_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-symbol-heading"})).text
        last_tran_transacted_cost_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-transacted-cost-heading"})).text
        last_tran_position_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-position-heading"})).text
        last_tran_currency_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-currency-heading"})).text
        last_tran_transaction_date_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-transaction-date-heading"})).text
  
        self.assertEqual(last_tran_symbol_locator, symbol)
        self.assertEqual(last_tran_transacted_cost_locator, f"{price_entry}")
        self.assertEqual(last_tran_position_locator, f"-{position_entry}")
        self.assertEqual(last_tran_currency_locator, fx)
        self.assertEqual(last_tran_transaction_date_locator, get_datetime_now())

        # Test portfolio holding is rendered correctly
        test_1_symbol = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_symbol").text
        test_1_price = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_price").text
        test_1_change = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_change").text
        test_1_cost = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_cost").text
        test_1_position = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_position").text
        test_1_mv = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_mv").text
        test_1_pnl = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_pnl").text
        test_1_pnl_percent = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_pnl_percent").text

        finnhub_client = finnhub.Client(api_key="c7nuioqad3idf06mjrtg")
        quote = finnhub_client.quote(symbol)

        self.assertEqual(test_1_symbol, symbol)
        self.assertEqual(test_1_price, f"{quote['c']:.2f}")
        self.assertEqual(test_1_change, f"{quote['dp']:.2f}%")
        self.assertEqual(test_1_cost, f"{(((350.21 * 100) + (360.89 * 80) + (330 * 120)) / (100 + 80 + 120)):.2f}")
        self.assertTrue(int(test_1_position.replace(',', '')) - int(100 + 80 + 120 - position_entry) <= 1)
        self.assertTrue(int(test_1_mv.replace(',', '')) - int((quote['c'] * (100 + 80 + 120 - position_entry))) <= 1)
        self.assertTrue(int(test_1_pnl.replace(',', '')) - int((quote['c'] - float(test_1_cost)) * (100 + 80 + 120 - position_entry)) <= 1)
        self.assertTrue(float(test_1_pnl_percent.replace('%', '')) - (quote['c'] - float(test_1_cost)) / float(test_1_cost) * 100 <= 0.01)

        # Test Total Market Value, P&L, P&L% and Realized P&L are rendered correctly
        total_6_mv = self.browser.find_element(By.ID, "total_mv").text
        total_6_pnl = self.browser.find_element(By.ID, "total_pnl").text
        total_6_pnl_percent = self.browser.find_element(By.ID, "total_pnl_percent").text
        realized_pnl_1 = self.browser.find_element(By.ID, "realized_profit_total").text

        self.assertTrue((int(total_6_mv.replace(',', '')) - int(test_1_mv.replace(',', '')) - int(test_2_mv.replace(',', '')) - int(test_3_mv.replace(',', ''))) <= 1)
        self.assertTrue((int(total_6_pnl.replace(',', '')) - int(test_1_pnl.replace(',', '')) - int(test_2_pnl.replace(',', '')) - int(test_3_pnl.replace(',', ''))) <= 1)
        self.assertEqual(total_6_pnl_percent, f"{(int(total_6_mv.replace(',', ''))/(int(total_6_mv.replace(',', '')) - int(total_6_pnl.replace(',', '')))-1) * 100 :.2f}%")
        self.assertTrue(int(realized_pnl_1.replace(',', '')) - int((price_entry - float(test_1_cost.replace(',', ''))) * position_entry) <= 1)

        # Test Cash balances are updated correctly
        usd_6_balance = self.browser.find_element(By.ID, "cash-table-usd").text
        total_cash_6_balance = self.browser.find_element(By.ID, "cash-table-total").text

        self.assertEqual(usd_6_balance, f"{(int(usd_5_balance.replace(',', '')) + int((price_entry * position_entry))):,g}")
        self.assertEqual(total_cash_6_balance, f"{(int(total_cash_5_balance.replace(',', '')) + int((price_entry * position_entry))):,g}")

        # Seventh input - Subsequent sell of first ticker at lower price
        symbol = "GS"
        price_entry = 310
        position_entry = 100
        fx = "USD"
        order_symbol_entry.send_keys(symbol)
        order_price_entry.send_keys(price_entry)
        order_position_entry.send_keys(position_entry)
        sell_order.click()
        Select(order_fx).select_by_value(fx)
        order_submit.click()
        time.sleep(2)

        # Test portfolio holding is rendered correctly
        test_1_symbol = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_symbol").text
        test_1_price = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_price").text
        test_1_change = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_change").text
        test_1_cost = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_cost").text
        temp_cost = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_cost").text
        test_1_position = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_position").text
        test_1_mv = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_mv").text
        test_1_pnl = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_pnl").text
        test_1_pnl_percent = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_pnl_percent").text

        finnhub_client = finnhub.Client(api_key="c7nuioqad3idf06mjrtg")
        quote = finnhub_client.quote(symbol)

        self.assertEqual(test_1_symbol, symbol)
        self.assertEqual(test_1_price, f"{quote['c']:.2f}")
        self.assertEqual(test_1_change, f"{quote['dp']:.2f}%")
        self.assertEqual(test_1_cost, f"{(((350.21 * 100) + (360.89 * 80) + (330 * 120)) / (100 + 80 + 120)):.2f}")
        self.assertTrue(int(test_1_position.replace(',', '')) - int(100 + 80 + 120 - 90 - position_entry) <= 1)
        self.assertTrue(int(test_1_mv.replace(',', '')) - int((quote['c'] * (100 + 80 + 120 - 90 - position_entry))) <= 1)
        self.assertTrue(int(test_1_pnl.replace(',', '')) - int((quote['c'] - float(test_1_cost)) * (100 + 80 + 120 - 90 - position_entry)) <= 1)
        self.assertTrue(float(test_1_pnl_percent.replace('%', '')) - (quote['c'] - float(test_1_cost)) / float(test_1_cost) * 100 <= 0.01)

        # Test Total Market Value, P&L, P&L% and Realized P&L are rendered correctly
        total_7_mv = self.browser.find_element(By.ID, "total_mv").text
        total_7_pnl = self.browser.find_element(By.ID, "total_pnl").text
        total_7_pnl_percent = self.browser.find_element(By.ID, "total_pnl_percent").text
        realized_pnl_2 = self.browser.find_element(By.ID, "realized_profit_total").text

        self.assertTrue((int(total_7_mv.replace(',', '')) - int(test_1_mv.replace(',', '')) - int(test_2_mv.replace(',', '')) - int(test_3_mv.replace(',', ''))) <= 1)
        self.assertTrue((int(total_7_pnl.replace(',', '')) - int(test_1_pnl.replace(',', '')) - int(test_2_pnl.replace(',', '')) - int(test_3_pnl.replace(',', ''))) <= 1)
        self.assertEqual(total_7_pnl_percent, f"{(int(total_7_mv.replace(',', ''))/(int(total_7_mv.replace(',', '')) - int(total_7_pnl.replace(',', '')))-1) * 100 :.2f}%")
        self.assertTrue(int(realized_pnl_2.replace(',', '')) - (int(realized_pnl_1.replace(',', '')) + int((price_entry - float(test_1_cost.replace(',', ''))) * position_entry)) <= 1)

        # Test Cash balances are updated correctly
        usd_7_balance = self.browser.find_element(By.ID, "cash-table-usd").text
        total_cash_7_balance = self.browser.find_element(By.ID, "cash-table-total").text

        self.assertEqual(usd_7_balance, f"{(int(usd_6_balance.replace(',', '')) + int((price_entry * position_entry))):,g}")
        self.assertEqual(total_cash_7_balance, f"{(int(total_cash_6_balance.replace(',', '')) + int((price_entry * position_entry))):,g}")

        # Eighth input - Subsequent sell and short of first ticker
        symbol = "GS"
        price_entry = 355
        position_entry = 160
        fx = "USD"
        order_symbol_entry.send_keys(symbol)
        order_price_entry.send_keys(price_entry)
        order_position_entry.send_keys(position_entry)
        sell_order.click()
        Select(order_fx).select_by_value(fx)
        order_submit.click()
        time.sleep(2)

        # Test last transaction is rendered correctly in Transaction Record    
        last_tran_symbol_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-symbol-heading"})).text
        last_tran_transacted_cost_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-transacted-cost-heading"})).text
        last_tran_position_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-position-heading"})).text
        last_tran_currency_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-currency-heading"})).text
        last_tran_transaction_date_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-transaction-date-heading"})).text
  
        self.assertEqual(last_tran_symbol_locator, symbol)
        self.assertEqual(last_tran_transacted_cost_locator, f"{price_entry}")
        self.assertEqual(last_tran_position_locator, f"-{50}")
        self.assertEqual(last_tran_currency_locator, fx)
        self.assertEqual(last_tran_transaction_date_locator, get_datetime_now())

        second_last_tran_symbol_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near(self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-symbol-heading"})))).text
        second_last_tran_transacted_cost_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near(self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-transacted-cost-heading"})))).text
        second_last_tran_position_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near(self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-position-heading"})))).text
        second_last_tran_currency_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near(self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-currency-heading"})))).text
        second_last_tran_transaction_date_locator = self.browser.find_element(locate_with(By.TAG_NAME, "td").near(self.browser.find_element(locate_with(By.TAG_NAME, "td").near({By.ID: "trans-transaction-date-heading"})))).text
  
        self.assertEqual(second_last_tran_symbol_locator, symbol)
        self.assertEqual(second_last_tran_transacted_cost_locator, f"{price_entry}")
        self.assertEqual(second_last_tran_position_locator, f"-{110}")
        self.assertEqual(second_last_tran_currency_locator, fx)
        self.assertEqual(second_last_tran_transaction_date_locator, get_datetime_now())

        # Test portfolio holding is rendered correctly
        test_1_symbol = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_symbol").text
        test_1_price = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_price").text
        test_1_change = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_change").text
        test_1_cost = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_cost").text
        test_1_position = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_position").text
        test_1_mv = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_mv").text
        test_1_pnl = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_pnl").text
        test_1_pnl_percent = self.browser.find_element(By.ID, f"portfolio_row_{symbol}_pnl_percent").text

        finnhub_client = finnhub.Client(api_key="c7nuioqad3idf06mjrtg")
        quote = finnhub_client.quote(symbol)

        self.assertEqual(test_1_symbol, symbol)
        self.assertEqual(test_1_price, f"{quote['c']:.2f}")
        self.assertEqual(test_1_change, f"{quote['dp']:.2f}%")
        self.assertEqual(test_1_cost, f"{price_entry:.2f}")
        self.assertTrue(int(test_1_position.replace(',', '')) - int(100 + 80 + 120 - 90 - 100 - position_entry) <= 1)
        self.assertTrue(int(test_1_mv.replace(',', '')) - int((quote['c'] * (100 + 80 + 120 - 90 - 100 - position_entry))) <= 1)
        self.assertTrue(int(test_1_pnl.replace(',', '')) - int((quote['c'] - float(test_1_cost)) * (100 + 80 + 120 - 90 - 100 - position_entry)) <= 1)
        self.assertTrue(float(test_1_pnl_percent.replace('%', '')) - (quote['c'] - float(test_1_cost)) / float(test_1_cost) * 100 <= 0.01)

        # Test Total Market Value, P&L, P&L% and Realized P&L are rendered correctly
        total_8_mv = self.browser.find_element(By.ID, "total_mv").text
        total_8_pnl = self.browser.find_element(By.ID, "total_pnl").text
        total_8_pnl_percent = self.browser.find_element(By.ID, "total_pnl_percent").text
        realized_pnl_3 = self.browser.find_element(By.ID, "realized_profit_total").text

        self.assertTrue((int(total_8_mv.replace(',', '')) - int(test_1_mv.replace(',', '')) - int(test_2_mv.replace(',', '')) - int(test_3_mv.replace(',', ''))) <= 1)
        self.assertTrue((int(total_8_pnl.replace(',', '')) - int(test_1_pnl.replace(',', '')) - int(test_2_pnl.replace(',', '')) - int(test_3_pnl.replace(',', ''))) <= 1)
        self.assertTrue(float(total_8_pnl_percent.replace('%', '')) - (int(total_8_mv.replace(',', ''))/(int(total_8_mv.replace(',', '')) - int(total_8_pnl.replace(',', '')))-1) * 100 <= 0.01)
        self.assertTrue(int(realized_pnl_3.replace(',', '')) - (int(realized_pnl_2.replace(',', '')) + int((price_entry - float(temp_cost.replace(',', ''))) * 110)) <= 1)

        # Test Cash balances are updated correctly
        usd_8_balance = self.browser.find_element(By.ID, "cash-table-usd").text
        total_cash_8_balance = self.browser.find_element(By.ID, "cash-table-total").text

        self.assertEqual(usd_8_balance, f"{(int(usd_7_balance.replace(',', '')) + int((price_entry * position_entry))):,g}")
        self.assertEqual(total_cash_8_balance, f"{(int(total_cash_7_balance.replace(',', '')) + int((price_entry * position_entry))):,g}")

        # Close all positions

        # Ninth input - Close short position of first ticker
        symbol = "GS"
        price_entry = 380
        position_entry = 50
        fx = "USD"
        order_symbol_entry.send_keys(symbol)
        order_price_entry.send_keys(price_entry)
        order_position_entry.send_keys(position_entry)
        buy_order.click()
        Select(order_fx).select_by_value(fx)
        order_submit.click()
        time.sleep(2)

        # Tenth input - Close long position of second ticker
        symbol = "TSLA"
        price_entry = 150
        position_entry = 50
        fx = "USD"
        order_symbol_entry.send_keys(symbol)
        order_price_entry.send_keys(price_entry)
        order_position_entry.send_keys(position_entry)
        sell_order.click()
        Select(order_fx).select_by_value(fx)
        order_submit.click()
        time.sleep(2)

        # Eleventh input - Close long position of third ticker
        symbol = "AAPL"
        price_entry = 138
        position_entry = 200
        fx = "USD"
        order_symbol_entry.send_keys(symbol)
        order_price_entry.send_keys(price_entry)
        order_position_entry.send_keys(position_entry)
        sell_order.click()
        Select(order_fx).select_by_value(fx)
        order_submit.click()
        time.sleep(2)

        # Test Total Market Value, P&L, P&L% and Realized P&L are rendered correctly
        total_mv = self.browser.find_element(By.ID, "total_mv").text
        total_pnl = self.browser.find_element(By.ID, "total_pnl").text
        total_pnl_percent = self.browser.find_element(By.ID, "total_pnl_percent").text
        realized_pnl_final = self.browser.find_element(By.ID, "realized_profit_total").text

        self.assertEqual(total_mv, "0")
        self.assertEqual(total_pnl, "0")
        self.assertEqual(total_pnl_percent, "0%")
        self.assertTrue(int(realized_pnl_final.replace(',', '')) - (int(realized_pnl_3.replace(',', '')) + (380 - 355) * (-50) + (150 - 140.5) * 50 + (138 - 130) * 200) <= 1)

        # Test Cash balances are updated correctly
        usd_balance = self.browser.find_element(By.ID, "cash-table-usd").text
        total_cash_balance = self.browser.find_element(By.ID, "cash-table-total").text
        
        self.assertEqual(usd_balance, f"{(int(usd_8_balance.replace(',', '')) - (380 * 50) + (150 * 50) + (138 * 200)):,g}")
        self.assertTrue(int(total_cash_balance.replace(',', '')) - (int(total_cash_8_balance.replace(',', '')) - (380 * 50) + (150 * 50) + (138 * 200)) <= 1)