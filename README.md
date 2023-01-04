# Portfolio

A tracker that enables users to conveniently manage their investments. Users can quote stock price, enter orders as they make investments, track their portfolio, transaction record, monitor cash level as they deposit/withdraw cash or invest. 

**YouTube Demo**

[![YouTube Demo](https://img.youtube.com/vi/GZkPI1YJx1c/default.jpg)](https://youtu.be/GZkPI1YJx1c)

# Distinctiveness and Complexity

This project is sufficiently distinct and complex than other prior projects in CS50 Web course because:
* It uses API to externally connect website that provides financial data such as stock price (Credit to IEX Cloud). In prior projects, we never had to rely on external API to fetch data. However, using external API to fetch data and displaying those data in a format that optimizes the user experience is very common and critical to many websites. Often times, the organization/creator of the website would not have the capability to work on creating the data. In this project, I had to come up with the data I need, look for the vendor that can provide the data I need, think about scalability as my website requires more data in the future, and come up with the right code to display the data, giving the user the best experience. This has never been attempted in prior projects. 
* It requires understanding and integration of the calculation logic behind transactions and portfolio changes. Displaying the right portfolio data and position changes is challenging because a high degree of accuracy is required. Any error in portfolio changes could lead to direct client financial loss if this is ever applied in the real world. This means it requires a lot of trial and error in testing and inputting numbers, applying different scenarios to assess whether the logic is correct. During the process, it heavily leverages Django's models and database to incorporate the portfolio changes and transactions. This adds a lot of complexity to the project. Given we did not have to account for calculations and logic in prior projects, I would argue that this project is sufficiently distinct. 
* It creates multiple instant updates on the web interface as users enter their orders. In prior projects, we often use JavaScript to make only 1 update at a time. However, in this project, you will often see multiple instant updates. For example, when you enter an order, transactions will be updated with a new transaction popping up on top of the transaction table. Simultaneously, portfolio data is also instantly updated with the latest portfolio holdings updated to reflect what the users currently hold. This does not only fetch data from Django model database, it also immediately fetches data via the external API. Given the instant updates and data fetching, I would argue that this is more complex and distinct than other prior projects. 

# Features

## **Quote**
Fetch real time stock price by entering stock symbol. 
Note that due to limitation in API, only US stocks are supported at the moment. 

## **Quote Details Transposition**
After receiving quote details, user can tranpose the stock symbol and current stock price to order entry

## **Order Entry**
User can enter stock symbol, price, quantity, transaction type and currency of the order. As this is a portfolio tracker, user can enter an order that was executed at a price different from the market price. Only USD is supported at the moment. 

Every order entry submission triggers multiple changes on the interface:
* Portfolio interface will be updated depending on different scenarios:
    * If the user has not owned the stock, the stock will be added to the portfolio, with all columns of data populated. 
    * If the user already owns the stock, multiple columns of the stock in the portfolio will be updated according to different circumstances:
        * Adding to existing position in the same direction
            * Price and Change updated to latest market price and change.
            * Cost updated to the new average price
            * Position updated to incorporate the change in quantity
            * Market Value, P&L and P&L% updated to latest record in the portfolio
        * Reducing existing position but user still owns the stock
            * Price and Change updated to latest market price and change.
            * Cost remain unchanged
            * Position updated to incorporate the change in quantity
            * Market Value, P&L and P&L% updated to latest record in the portfolio
        * Exiting all position 
            * Stock removed from portfolio 
        * Exiting all position and enter a new position with an opposite direction
            * Price and Change updated to latest market price and change.
            * Cost updated to price submitted in order entry
            * Position updated to quantity submitted in order entry plus original position (Example: existing position = 5; quantity submitted = -7; new position = 5 + (-7) = -2)
            * Market Value, P&L and P&L% updated to latest record in the portfolio
* Transaction Record will be updated with the submitted latest order added to the top of the Transaction Record table.
* Cash Record will be updated with a 'Buy' order reducing the USD and Total Cash level, and a 'Sell' order increasing the USD and Total Cash level. 

## **Portfolio**
The portfolio table shows the list of stock position that the user owns, including details such as stock symbol, stock price, change, cost, position, market value, P&L, P&L%. It also shows the total market value, total P&L, total P&L% and realized P&L at the bottom. 

## **Portfolio Refresh**
User can refresh the data in the Portfolio table. Live data such as market price and change will be fetched via the market API. Other columns such as market value, P&L and the totals will be updated accordingly. 

## **Transaction Record**
As the user enters order, deposits or withdraws cash, transaction record will be updated with the latest transaction added to the top, showing details such as symbol, transacted cost, position, currency and transaction date. 

## **Transaction Sorting**
User can click on the column names in the transaction table to sort transactions in ascending or descending order. 

## **Transaction Searching**
Enter any keyword of the transaction (i.e. symbol/transacted cost/position/currency/transaction date) in mind, and the user will get the condensed set of data searched for.

## **Cash**
Cash table shows the cash balance of the user in multiple currencies. Only USD, HKD, GBP and EUR are supported currently. The total cash is based on the default currency the user chooses. Every time the user changes the default FX, the total cash will show the total cash balance in the currency the user chooses as default. It will be saved in memory until the user changes it again. 

## **Deposit/Withdraw Cash**
User can choose to deposit/withdraw cash with the amount and currency of their choice. Cash table and transaction record will be updated accordingly. 

## **Mobile Responsiveness**
The page is mobile responsive. The screen will adjust according to the user's window size. 

## **Validations**
Entries in Quote, Order Entry and Deposit/Withdraw Cash will need to pass client side and server side validations in order to update the record permanently. 

# Key Files

### **main.js** 
Javascript for loading portfolio positions, transactions, refreshing portfolio, fetching stock quote, transposing quote details, submitting order entry, sorting and searching transactions, submitting cash deposit/withdraw transaction, changing default currency, adding transaction, updating realized profit, validating quote, order and cash transactions and formatting date. 

### **getcookie.js**
Javascript for getting cookie for csrftoken for POST request.

### sort.png 
Icon for sorting transactions

### **styles.css**
CSS styling all in this file.

### **index.html**
Web structure of the main webpage.

### **layout.html**
General layout of webpage.

### **login.html**
Login page.

### **register.html**
Allowing new user to register.

### **views.py**
Python for rendering data in the page including portfolio position, transactions and cash balance, adding stock to portfolio, refreshing portfolio, fetching stock quote, updating cash transactions, updating cash total, changing default currency, updating and rendering realized profit, managing user login, logout and new user registration.   

### **models.py**
Django models depository.

### **urls.py (under Portfolio folder)**
Django url paths depository.

### **admin.py**
Django Admin site management. Registering different models in admin site. 

### **app.py**
Portfolio configuration

### **tests.py**
For testing different cases and scenarios. Currently left blank. 

### **__init__.py**
For initiation purpose

### **0001_initial.py**
Initial model migration

### **manage.py**
For running Django administrative tasks.

### **db.sqlite3**
Database for storing model data

### **settings.py**
Project settings. Slightly updated to incorporate numbers humanization. 

### **urls.py (under Capstone folder)**
URLs of the whole project, with the URLs of the admin site and the project itself. 

### **asgi.py**
Asynchronous Server Gateway Interface to provide a standard interface between async-capable Python web servers, frameworks, and applications

### **wsgi.py**
Web Server Gateway Interface for web servers to forward requests to web applications or frameworks written in the Python 

# How to Run the Webpage 
1. Go to Terminal
2. Navigate to the capstone folder
3. Initialize database by file migrations, type python3 manage.py makemigrations and then python3 manage.py migrate
4. Create a superuser for admin purpose, python3 manage.py createsuperuser
3. Type python3 manage.py runserver
4. Paste http://127.0.0.1:8000 in your browser

# Technology

#### Framework: Django
#### Library: Bootstrap
#### Language: Python and Javascript