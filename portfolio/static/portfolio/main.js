// Below two lines are for crsftoken security purpose - Source: https://docs.djangoproject.com/en/4.0/ref/csrf/
import { getCookie } from './getcookie.js';
const csrftoken = getCookie('csrftoken');

document.addEventListener('DOMContentLoaded', function() {
    
  document.querySelector('#quote-button').addEventListener('click', quote);
  document.querySelector('#manual-add-button').addEventListener('click', add_stock);
  document.querySelector('#cash-button').addEventListener('click', cash_action);
  document.querySelector('#default-fx').addEventListener('change', default_fx);
  document.querySelector('#refresh-button').addEventListener('click', refresh);
  document.querySelector('#transactions-search-bar').addEventListener('keyup', search_transactions);

  load_portfolio_position();
  load_transactions();
  sort_transaction_table();
  refreshed_time();
  quote_entry_validation()
  order_entry_validation();
  cash_deposit_withdraw_validation();
});


function quote() {

  // Clear order inputs
  document.querySelector('#manual-add-symbol').value = "";
  document.querySelector('#manual-add-price').value = "";

  // Get quote input
  let symbol = document.querySelector('#quote-input').value;
  // Display quote block
  document.querySelector('#quote-block').style.display = 'block';
  // Show load icon while loading quote
  document.querySelector('#quote-content').innerHTML = 
    `<div class="spinner-border spinner-border-sm" role="status">
      <span class="visually-hidden">Loading...</span>
    </div>`;
  // If nothing is inputted, ask user to enter a stock symbol
  if (symbol === "") {
    document.querySelector('#quote-content').innerHTML = `<div class="alert alert-danger" role="alert">Please enter a stock symbol.</div>`;
  } else {
    // If something is inputted, continue 
    fetch("/quote/" + symbol).then(function(response) {
      // If cannot find stock, tell user invalid symbol
      if (response.status == "404") {
        document.querySelector('#quote-content').innerHTML = `<div class="alert alert-danger" role="alert">Invalid Symbol.</div>`;
      } else {
        // Quote stock
        fetch("/quote/" + symbol)
        .then(response => response.json())
        .then(quote => {
          if (quote.symbol === "undefined") {
            document.querySelector('#quote-content').innerHTML = "";
          } else {
            // Show quote content if pass validation. Also allow user to transpose quote content
            document.querySelector('#quote-content').innerHTML = 
            `${quote.name} ${quote.symbol} $${quote.price}
            <br>
            <button id="transpose-button" class="btn btn-secondary btn-sm" type="button">Tranpose To Order Entry</button>
            `;
            document.querySelector('#transpose-button').addEventListener('click', () => transpose_details(quote.symbol, quote.price));
          }
        })
      }
    })
  }
  // Clear quote input
  document.querySelector('#quote-input').value = "";
}


function transpose_details(symbol, price) {
  // Tranpose quote details (symbol and price)
  document.querySelector('#manual-add-symbol').value = symbol;
  document.querySelector('#manual-add-price').value = price;
}


function add_stock() {
  
  // Clear any prior error message
  let manual_add_error = document.querySelector('#manual-add-error');
  manual_add_error.innerHTML = "";
  
  // Get symbol
  let get_symbol = document.querySelector('#manual-add-symbol').value;
  let symbol = get_symbol.toUpperCase();
  
  // Quote stock for stock validation
  fetch("/quote/" + symbol)
  .then(function(response) {
    // If invalid stock symbol, show alert 
    if (response.status == "404") {
      manual_add_error.innerHTML = `<div class="alert alert-danger" role="alert">Invalid Symbol.</div>`;
      var error = "Invalid Symbol.";
      return console.log(error);
      // If stock exists, continue
    } else {
      let get_cost = parseFloat(document.querySelector('#manual-add-price').value).toFixed(3);

      // Price validation: must be > 0
      if (get_cost <= 0) {
        manual_add_error.innerHTML = `<div class="alert alert-danger" role="alert">Price must be larger than 0.</div>`;
        var error = "Price must be larger than 0.";
        return console.log(error);
      }

      // Quantity validation: must be an integer
      let check_integer = Number.isInteger(Number(document.querySelector('#manual-add-position').value));
      let get_position;
      if (check_integer) {
        get_position = parseInt(document.querySelector('#manual-add-position').value);
      } else {
        manual_add_error.innerHTML = `<div class="alert alert-danger" role="alert">Quantity must be an integer.</div>`;
        var error = "Quantity must be an integer.";
        return console.log(error);
      }
      
      // Quantity validation: must be at least 1
      if (get_position < 1) {
        manual_add_error.innerHTML = `<div class="alert alert-danger" role="alert">Quantity must be at least 1.</div>`;
        var error = "Quantity must be at least 1.";
        return console.log(error);
      }
      
      // If select buy, position times (1), otherwise, position times (-1)
      if (document.getElementById("btnradio1").checked == true) {
        get_position = Math.abs(get_position);
      } else if (document.getElementById("btnradio2").checked == true) {
        get_position = Math.abs(get_position) * (-1);
      }

      // Get currency 
      let currency_list = document.querySelector('#manual-add-currency');
      let get_currency = currency_list.options[currency_list.selectedIndex].text;
      
      // If all validations pass, add stock to portfolio and transaction record
      fetch("/add_stock/" + symbol, {
        method: 'POST',
        headers: {'X-CSRFToken': csrftoken},
        mode: 'same-origin', 
        body: JSON.stringify({
          cost: get_cost,
          position: get_position,
          currency: get_currency,
        })
      })
      .then(() => {
        // Update realized profit if applicable
        update_realized_profit(symbol, get_cost, get_position);
      })
      .then(() => {
        // Add to transaction record
        add_transaction(symbol, get_cost, get_position, get_currency);
      })
      .then(() => {
        // Break one transaction into two if reverse position and position change > original position
        update_and_add_transaction_if_position_change_exceed_zero(symbol, get_cost, get_position, get_currency);
      })
      .then(() => {
        // Update cash record after adding or reducing the stock position
        update_cash(get_currency, get_cost, get_position);
      })
      .then(() => {
        // Refresh portfolio position after the change
        reload_portfolio_position();
      })
    
      // Reset inputs
      document.querySelector('#manual-add-symbol').value = "";
      document.querySelector('#manual-add-price').value = "";
      document.querySelector('#manual-add-position').value = "";
      document.getElementById("btnradio1").checked = false;
      document.getElementById("btnradio2").checked = false;
      get_currency = "USD";
    }
  })
}


function add_transaction(symbol, get_cost, get_position, get_currency) {
  // Load a new transaction in transaction record
  fetch('/last_transaction')
  .then(response => response.json())
  .then(last_transaction_time => {
    console.log(last_transaction_time);
    const table = document.getElementById("transactions-table");
    const row = table.getElementsByTagName('tbody')[0].insertRow(0);
    var cell1 = row.insertCell(0);
    var cell2 = row.insertCell(1);
    var cell3 = row.insertCell(2);
    var cell4 = row.insertCell(3);
    var cell5 = row.insertCell(4);
    cell1.innerHTML = symbol;
    cell2.innerHTML = parseFloat(get_cost).toLocaleString();
    cell3.innerHTML = parseInt(get_position).toLocaleString();
    cell4.innerHTML = get_currency;
    var date = format_date(last_transaction_time.time)
    cell5.innerHTML = date;
  })
}


function update_and_add_transaction_if_position_change_exceed_zero(symbol, get_cost, get_position, get_currency) {
  const table = document.getElementById("transactions-table");
  fetch('/check_stock/' + symbol)
  .then(response => response.json())
  .then(stock => {
    console.log(stock);
    var original_position = parseInt(stock.latest_position) - get_position;
    // Detect if position change is at reverse direction and that position change is larger than original position (meaning long position become short, short become long)
    // which happens when original position and position change have opposite signs and absolute value of original position is less than absolute value of position change
    // If this happens, break one transactions into two for clarity. Basically, it will be treated as selling the original position (part 1) and entering a new position with the remainder position change (part 2)
    // First, create a new row in transaction record, showing the latest position (part 2)
    if ( (original_position * parseInt(get_position) < 0) && (Math.abs(original_position) < Math.abs(parseInt(get_position))) ) {
      fetch('/last_transaction')
      .then(response => response.json())
      .then(last_transaction_time => {
        console.log(last_transaction_time);
        const row = table.getElementsByTagName('tbody')[0].insertRow(0);
        var cell1 = row.insertCell(0);
        var cell2 = row.insertCell(1);
        var cell3 = row.insertCell(2);
        var cell4 = row.insertCell(3);
        var cell5 = row.insertCell(4);
        cell1.innerHTML = symbol;
        cell2.innerHTML = parseFloat(get_cost).toLocaleString();
        cell3.innerHTML = parseInt(stock.latest_position).toLocaleString();
        cell4.innerHTML = get_currency;
        cell5.innerHTML = format_date(last_transaction_time.time);
      })
      .then(() => {
        // Then update the first (old) transaction position with a opposite sign original position (part 1)
        table.getElementsByTagName('tbody')[0].rows[1].cells[2].innerHTML = parseInt((original_position) * (-1)).toLocaleString();
      })
    }
  })
}


function update_realized_profit(symbol, get_cost, get_position) {
  // Check this stock's latest position and latest cost for updating realized profit
  fetch('/check_stock/' + symbol)
  .then(response => response.json())
  .then(stock => {
    // Reverse calculation of the original position
    var original_position = parseInt(stock.latest_position) - get_position;

    // Reverse direction, position change is larger than original position (meaning long position become short, short become long)
    // This happens when original position and position change have opposite signs and absolute value of original position is less than absolute value of position change
    if ( (original_position * parseInt(get_position) < 0) && (Math.abs(original_position) < Math.abs(parseInt(get_position))) ) {
      var change = (get_cost - stock.latest_cost) * original_position;
      // Update P&L
      fetch('/realized_profit', {
        method: 'PUT',
        headers: {'X-CSRFToken': csrftoken},
        mode: 'same-origin', 
        body: JSON.stringify({
          pnl_change: change,
        })
      })
      .then(() => {
        // Load the latest total Realized P&L
        render_realized_profit();
      })

    // Reverse direction, position change less than original position (meaning reduction of position)
    } else if ( (original_position * parseInt(get_position) < 0) && (Math.abs(original_position) > Math.abs(parseInt(get_position))) ) {
      var change = (get_cost - stock.latest_cost) * get_position * (-1);
      // Update P&L
      fetch('/realized_profit', {
        method: 'PUT',
        headers: {'X-CSRFToken': csrftoken},
        mode: 'same-origin', 
        body: JSON.stringify({
          pnl_change: change,
        })
      })
      .then(() => {
        // Load the latest total Realized P&L
        render_realized_profit();
      })

    // Reverse direction, position change equals original position (meaning clear all position)
    } else if ( (original_position * parseInt(get_position) < 0) && (Math.abs(original_position) == Math.abs(parseInt(get_position))) ) {
      var change = (get_cost - stock.latest_cost) * get_position * (-1);
      // Update P&L
      fetch('/realized_profit', {
        method: 'PUT',
        headers: {'X-CSRFToken': csrftoken},
        mode: 'same-origin', 
        body: JSON.stringify({
          pnl_change: change,
        })
      })
      .then(() => {
        // Load the latest total Realized P&L
        render_realized_profit();
      })
    
    // Other scenarios - basically adding existing position. It won't lead to profit change 
    } else {
      var change = 0;
      // Update P&L, but the P&L won't change
      fetch('/realized_profit', {
        method: 'PUT',
        headers: {'X-CSRFToken': csrftoken},
        mode: 'same-origin', 
        body: JSON.stringify({
          pnl_change: change,
        })
      })
      .then(() => {
        // Load the latest total Realized P&L
        render_realized_profit();
      })
    }

    console.log(change);
    
  })
}


function render_realized_profit() {
  // Render total Realized P&L for Portfolio
  fetch('/realized_profit')
  .then(response => response.json())
  .then(realized_profit => {
    var table = document.getElementById("portfolio-table");
    var realized_profit_row = table.getElementsByTagName('tbody')[0].insertRow(table.rows.length - 1);
    realized_profit_row.id = 'realized_profit';
    var rz_profit_row = document.getElementById("realized_profit");
    for (let i = 0; i < 8; i++) {
      rz_profit_row.insertCell();
    }
    rz_profit_row.cells[0].innerHTML = "Realized P&L";
    rz_profit_row.cells[0].style.fontWeight = "bold"; 
    rz_profit_row.cells[6].innerHTML = parseFloat(realized_profit.realized_profit).toLocaleString(undefined, {maximumFractionDigits: 1});
    rz_profit_row.cells[6].style.fontWeight = "bold"; 
  })
}


function load_portfolio_position() {
  fetch('/portfolio_position')
  .then(response => response.json())
  .then(positions => {
      console.log(positions);
      var table = document.getElementById("portfolio-table");
      var mv_count = 0;
      var pnl_count = 0;
      // Load portfolio positions in Portfolio Record, insert row, followed by cells, and repeat
      positions.forEach(position => {
        const row = table.getElementsByTagName('tbody')[0].insertRow(0);
        row.id = `portfolio_row_${position.symbol}`;
        // Calculate market value of each stock by stock price times position
        var mv = parseFloat(position["price"]) * parseFloat(position["position"]);
        // Add up market value of each stock to total market value
        mv_count += mv;
        // Add up each stock's P&L to total P&L
        pnl_count += parseFloat(position["pnl"]);
        table.rows[1].insertCell().innerHTML = position["symbol"];
        table.rows[1].insertCell().innerHTML = parseFloat(position["price"]).toLocaleString();
        table.rows[1].insertCell().innerHTML = parseFloat(position["change"]*100).toFixed(2)+"%";
        table.rows[1].insertCell().innerHTML = parseFloat(position["cost"]).toLocaleString();
        table.rows[1].insertCell().innerHTML = parseInt(position["position"]).toLocaleString();
        table.rows[1].insertCell().innerHTML = mv.toLocaleString();
        table.rows[1].insertCell().innerHTML = parseFloat(position["pnl"]).toLocaleString();
        table.rows[1].insertCell().innerHTML = parseFloat(position["pnl_percent"]*100).toFixed(2)+"%";
      });
      
      // Load Portfolio Total Market Value, P&L and P&L%
      var portfolio_total_row = table.getElementsByTagName('tbody')[0].insertRow(table.rows.length - 1);
      portfolio_total_row.id = 'portfolio_total';
      var port_total_row = document.getElementById("portfolio_total");
      for (let i = 0; i < 8; i++) {
        port_total_row.insertCell();
      }
      port_total_row.cells[0].innerHTML = "Total";
      port_total_row.cells[0].style.fontWeight = "bold"; 
      port_total_row.cells[5].innerHTML = mv_count.toLocaleString();
      port_total_row.cells[5].style.fontWeight = "bold"; 
      port_total_row.cells[6].innerHTML = pnl_count.toLocaleString();
      port_total_row.cells[6].style.fontWeight = "bold"; 
      port_total_row.cells[7].innerHTML = parseFloat(pnl_count/mv_count*100).toFixed(2)+"%";
      port_total_row.cells[7].style.fontWeight = "bold"; 

      // Load realized profit
      render_realized_profit();
  })
}


function reload_portfolio_position() {
  fetch('/portfolio_position')
  .then(response => response.json())
  .then(positions => {
    console.log(positions);
    var table = document.getElementById("portfolio-table");
    // Remove all rows first
    while(table.rows.length > 1) {  
      table.getElementsByTagName('tbody')[0].deleteRow(-1);
    }
    var mv_count = 0;
    var pnl_count = 0;
    // Load portfolio positions in Portfolio Record, insert row, followed by cells, and repeat
    positions.forEach(position => {
      const row = table.getElementsByTagName('tbody')[0].insertRow(0);
      row.id = `portfolio_row_${position.symbol}`;
      // Calculate market value of each stock by stock price times position
      var mv = parseFloat(position["price"]) * parseFloat(position["position"]);
      // Add up market value of each stock to total market value
      mv_count += mv;
      // Add up each stock's P&L to total P&L
      pnl_count += parseFloat(position["pnl"]);
      table.rows[1].insertCell().innerHTML = position["symbol"];
      table.rows[1].insertCell().innerHTML = parseFloat(position["price"]).toLocaleString();
      table.rows[1].insertCell().innerHTML = parseFloat(position["change"]*100).toFixed(2)+"%";
      table.rows[1].insertCell().innerHTML = parseFloat(position["cost"]).toLocaleString();
      table.rows[1].insertCell().innerHTML = parseInt(position["position"]).toLocaleString();
      table.rows[1].insertCell().innerHTML = mv.toLocaleString();
      table.rows[1].insertCell().innerHTML = parseFloat(position["pnl"]).toLocaleString();
      table.rows[1].insertCell().innerHTML = parseFloat(position["pnl_percent"]*100).toFixed(2)+"%";
    });

    // Load Portfolio Total Market Value, P&L and P&L%
    var portfolio_total_row = table.getElementsByTagName('tbody')[0].insertRow(table.rows.length - 1);
    portfolio_total_row.id = 'portfolio_total';
    var port_total_row = document.getElementById("portfolio_total");
    for (let i = 0; i < 8; i++) {
      port_total_row.insertCell();
    }
    port_total_row.cells[0].innerHTML = "Total";
    port_total_row.cells[0].style.fontWeight = "bold"; 
    port_total_row.cells[5].innerHTML = mv_count.toLocaleString();
    port_total_row.cells[5].style.fontWeight = "bold"; 
    port_total_row.cells[6].innerHTML = pnl_count.toLocaleString();
    port_total_row.cells[6].style.fontWeight = "bold"; 
    port_total_row.cells[7].innerHTML = parseFloat(pnl_count/mv_count*100).toFixed(2)+"%";
    port_total_row.cells[7].style.fontWeight = "bold"; 
  })
}


function load_transactions() {
  // Load transactions in Transaction Record, insert row, followed by cells, and repeat
  fetch('/transactions/0')
  .then(response => response.json())
  .then(transactions => {
      console.log(transactions);
      var table = document.getElementById("transactions-table");
      transactions.forEach(transaction => {
        const row = table.getElementsByTagName('tbody')[0].insertRow(0);
        row.id = `transaction_row_${transaction.symbol}`;
        table.rows[1].insertCell().innerHTML = transaction["symbol"];
        table.rows[1].insertCell().innerHTML = parseFloat(transaction["cost"]).toLocaleString();
        table.rows[1].insertCell().innerHTML = parseInt(transaction["position"]).toLocaleString();
        table.rows[1].insertCell().innerHTML = transaction["currency"];
        table.rows[1].insertCell().innerHTML = format_date(transaction["timestamp"]);
      });
  })
}


function sort_transaction_table() {
  // Detect click of each heading in Transactions Record
  document.querySelectorAll('.trans-heading').forEach(heading => {
    heading.onclick = function() {
      var table = document.getElementById("transactions-table");
      // Remove all rows first
      while(table.rows.length > 1) {  
        table.getElementsByTagName('tbody')[0].deleteRow(-1);
      }
      
      // Add/change sort icon
      if (heading.innerHTML == `${this.dataset.heading_name} <i class="fa-solid fa-arrow-down-short-wide"></i>`) {
        // Descending order
        heading.innerHTML = `${this.dataset.heading_name} <i class="fa-solid fa-arrow-down-wide-short"></i>`;
      } else {
        // Ascending order
        heading.innerHTML = `${this.dataset.heading_name} <i class="fa-solid fa-arrow-down-short-wide"></i>`;
      }
      
      // Remove all headings' icons except the one just clicked
      document.querySelectorAll(`.trans-heading:not(#${this.dataset.id})`).forEach(heading => {
        heading.innerHTML = heading.dataset.heading_name;
      });

      // Fetch all rows of data according to sort order chosen
      var this_heading = this.dataset.heading;
      console.log(this_heading);
      fetch('/transactions/' + this_heading)
      .then(response => response.json())
      .then(transactions => {
          console.log(transactions);
          var table = document.getElementById("transactions-table");
          transactions.forEach(transaction => {
            const row = table.getElementsByTagName('tbody')[0].insertRow(0);
            row.id = `transaction_row_${transaction.symbol}`;
            table.rows[1].insertCell().innerHTML = transaction["symbol"];
            table.rows[1].insertCell().innerHTML = parseFloat(transaction["cost"]).toLocaleString();
            table.rows[1].insertCell().innerHTML = parseInt(transaction["position"]).toLocaleString();
            table.rows[1].insertCell().innerHTML = transaction["currency"];
            table.rows[1].insertCell().innerHTML = format_date(transaction["timestamp"]);
          });
      })
      // Detect current heading sort order such that the next time the user clicks the heading, it will sort in opposite direction. 
      if (this_heading.charAt(0) == "+") {
        this.dataset.heading = this.dataset.heading.substring(1);
        this.dataset.heading = "-" + this.dataset.heading;
      } else if (this_heading.charAt(0) == "-") {
        this.dataset.heading = this.dataset.heading.substring(1);
        this.dataset.heading = "+" + this.dataset.heading;
      }
    }
  });
}


function search_transactions(event) {
  // Transaction search bar
  var filter = event.target.value.toUpperCase();
  var rows = document.querySelector("#transactions-table tbody").rows;
  for (var i = 0; i < rows.length; i++) {
      var symbol_col = rows[i].cells[0].textContent.toUpperCase();
      var cost_col = rows[i].cells[1].textContent.toUpperCase();
      var position_col = rows[i].cells[2].textContent.toUpperCase();
      var currency_col = rows[i].cells[3].textContent.toUpperCase();
      var date_col = rows[i].cells[4].textContent.toUpperCase();
      if (symbol_col.indexOf(filter) > -1 || 
          cost_col.indexOf(filter) > -1 || 
          position_col.indexOf(filter) > -1 || 
          currency_col.indexOf(filter) > -1 || 
          date_col.indexOf(filter) > -1) {
          rows[i].style.display = "";
      } else {
          rows[i].style.display = "none";
      }      
  }
}


function cash_action() {
  
  // Clear any prior error in cash
  let cash_error = document.querySelector('#cash-error');
  cash_error.innerHTML = "";

  // Get the new cash change amount
  let get_amount = parseFloat(document.querySelector('#cash-amount').value).toFixed(3);

  // Cash change validation. Show alert message if cash change amount is negative 
  if (get_amount <= 0) {
    cash_error.innerHTML = `<div class="alert alert-danger" role="alert">Amount must be larger than 0.</div>`;
    var error = "Amount must be larger than 0.";
    return console.log(error);
  }

  // Get information of the cash change
  let action_list = document.querySelector('#cash-action');
  let get_action = action_list.options[action_list.selectedIndex].text;
  let currency_list = document.querySelector('#cash-fx');
  let get_fx = currency_list.options[currency_list.selectedIndex].text;
  let default_fx_list = document.querySelector('#default-fx');
  let default_fx = default_fx_list.options[default_fx_list.selectedIndex].text;

  // Update cash based on input
  fetch('/cash', {
    method: 'POST',
    headers: {'X-CSRFToken': csrftoken},
    mode: 'same-origin', 
    body: JSON.stringify({
      amount: get_amount,
      action: get_action,
      fx: get_fx,
    })
  })
  .then(() => {
    // Make the change negative if this is a withdrawal
    if (get_action == "Withdraw") {
      get_amount *= (-1)
    }
    let fx = get_fx.toLowerCase();
    // Change value of FX chosen
    let updated_fx_amount = parseInt(document.querySelector(`#cash-table-${fx}`).dataset.value) + parseInt(get_amount);
    document.querySelector(`#cash-table-${fx}`).dataset.value = updated_fx_amount;
    document.querySelector(`#cash-table-${fx}`).innerHTML = updated_fx_amount.toLocaleString();
    // Change default total FX value
    update_total_cash(default_fx);
  })
  .then(() => {
    // Add cash change to Transaction Record
    if (get_action == "Withdraw") {
      var get_position = (-1)
    } else {
      var get_position = 1
    }
    var amt = Math.abs(get_amount);
    add_transaction(get_fx, amt, get_position, get_fx);
  })

  // Clear inputs
  document.querySelector('#cash-amount').value = "";
  document.querySelector('#cash-action').value = "deposit";
  document.querySelector('#cash-fx').value = "USD";

}


function default_fx() {

  // Default FX is used for load the right Total Cash amount
  // Get the default FX chosen
  let currency_list = document.querySelector('#default-fx');
  let get_fx = currency_list.options[currency_list.selectedIndex].text;

  // Make change to default FX
  // Default FX choice chosen will be saved and used continuously for loading the right Total Cash amount until new change
  fetch('/change_default_fx', {
    method: 'POST',
    headers: {'X-CSRFToken': csrftoken},
    mode: 'same-origin', 
    body: JSON.stringify({
      fx: get_fx,
    })
  })
  .then(() => {    
    // Load the right total cash amount based on the default FX chosen
    update_total_cash(get_fx);
  })

}


function update_cash(get_fx, get_cost, get_position) {
  
  // Get the cash amount change after adding or reducing stock position
  let get_amount = get_cost * get_position * (-1);

  // Get the current default FX for calculating the new Total Cash after change
  let default_fx_list = document.querySelector('#default-fx');
  let default_fx = default_fx_list.options[default_fx_list.selectedIndex].text;

  // Change value of FX change 
  let fx = get_fx.toLowerCase();
  let updated_fx_amount = parseInt(document.querySelector(`#cash-table-${fx}`).dataset.value) + parseInt(get_amount);
  document.querySelector(`#cash-table-${fx}`).dataset.value = updated_fx_amount;
  document.querySelector(`#cash-table-${fx}`).innerHTML = updated_fx_amount.toLocaleString();

  // Change default total FX value
  update_total_cash(default_fx);

}


function update_total_cash(default_fx) {

  // Exchange Rate Assumption (API to be used in further development) - rate as of 20 Feb
  let usdhkd = parseFloat(7.8).toFixed(3);
  let gbpusd = parseFloat(1.36).toFixed(3);
  let eurusd = parseFloat(1.13).toFixed(3);
  let gbphkd = parseFloat(10.6).toFixed(3);
  let eurhkd = parseFloat(8.83).toFixed(3);
  let gbpeur = parseFloat(1.2).toFixed(3);
  
  // Update total cash based on default FX chosen
  if (default_fx === "USD") {
    let usd = document.querySelector('#cash-table-usd').dataset.value;
    let hkd = document.querySelector('#cash-table-hkd').dataset.value / usdhkd;
    let gbp = document.querySelector('#cash-table-gbp').dataset.value * gbpusd;
    let eur = document.querySelector('#cash-table-eur').dataset.value * eurusd; 
    let updated_cash_amount = parseFloat(usd) + parseFloat(hkd) + parseFloat(gbp) + parseFloat(eur);
    document.querySelector('#cash-table-total').innerHTML = parseInt(updated_cash_amount).toLocaleString();
    default_fx = "USD";
  } else if (default_fx === "HKD") {
    let usd = document.querySelector('#cash-table-usd').dataset.value * usdhkd;
    let hkd = document.querySelector('#cash-table-hkd').dataset.value;
    let gbp = document.querySelector('#cash-table-gbp').dataset.value * gbphkd;
    let eur = document.querySelector('#cash-table-eur').dataset.value * eurhkd; 
    let updated_cash_amount = parseFloat(usd) + parseFloat(hkd) + parseFloat(gbp) + parseFloat(eur);
    document.querySelector('#cash-table-total').innerHTML = parseInt(updated_cash_amount).toLocaleString();
    default_fx = "HKD";
  } else if (default_fx === "GBP") {
    let usd = document.querySelector('#cash-table-usd').dataset.value / gbpusd;
    let hkd = document.querySelector('#cash-table-hkd').dataset.value / gbphkd;
    let gbp = document.querySelector('#cash-table-gbp').dataset.value;
    let eur = document.querySelector('#cash-table-eur').dataset.value / gbpeur; 
    let updated_cash_amount = parseFloat(usd) + parseFloat(hkd) + parseFloat(gbp) + parseFloat(eur);
    document.querySelector('#cash-table-total').innerHTML = parseInt(updated_cash_amount).toLocaleString();
    default_fx = "GBP";
  } else if (default_fx === "EUR") {
    let usd = document.querySelector('#cash-table-usd').dataset.value / eurusd;
    let hkd = document.querySelector('#cash-table-hkd').dataset.value / eurhkd;
    let gbp = document.querySelector('#cash-table-gbp').dataset.value * gbpeur;
    let eur = document.querySelector('#cash-table-eur').dataset.value; 
    let updated_cash_amount = parseFloat(usd) + parseFloat(hkd) + parseFloat(gbp) + parseFloat(eur);
    document.querySelector('#cash-table-total').innerHTML = parseInt(updated_cash_amount).toLocaleString();
    default_fx = "EUR";
  }
}


function refresh() {
  
  // Show load icon while refreshing
  document.querySelector('#last_refresh_time').innerHTML = 
    `<div class="spinner-border spinner-border-sm" role="status">
        <span class="visually-hidden">Loading...</span>
    </div>`;

  // Refresh
  fetch('/refresh', {
    method: 'PUT',
    headers: {'X-CSRFToken': csrftoken},
    mode: 'same-origin', 
  })
  .then(() => {
    // Refresh portfolio positions
    reload_portfolio_position();
  })
  .then(() => {
    // Update refresh time and realized profit
    update_refreshed_time();
  })
}


function refreshed_time() {
  // Load latest refresh time
  fetch("/refreshed_time")
  .then(response => response.json())
  .then(refresh => {
    var last_refresh_time = document.querySelector('#last_refresh_time');
    if (refresh.refreshed_time == "") {
      last_refresh_time.innerHTML = "";
    } else {
      var date = format_date(refresh.refreshed_time);
      last_refresh_time.innerHTML = `Last refreshed: ${date}`;
    }
  })
}


function update_refreshed_time() {
  // Update refresh time
  fetch('/refreshed_time', {
    method: 'PUT',
    headers: {'X-CSRFToken': csrftoken},
    mode: 'same-origin', 
  })
  .then(() => {
    // Load latest refresh time
    refreshed_time();
  })
  .then(() => {
    // Render updated total realized profit
    render_realized_profit();
  })
}


function quote_entry_validation() {
  // Quote validation
  // Disable button until something is inputted in quote
  const button = document.querySelector('#quote-button');
  button.disabled = true;
  let quote_entry = document.querySelector('#quote-input');
  quote_entry.onkeyup = () => {
    if (quote_entry.value.length > 0) {
      button.disabled = false;
    }
    else {
      button.disabled = true;
    }
  }
}


function order_entry_validation() {
  // Order entry validation 
  const button = document.querySelector('#manual-add-button');
  button.disabled = true;
  
  // Price validation: value must be > 0, prompt alert box if fail
  const price_input = document.querySelector('#manual-add-price');
  price_input.oninput = (e) => {
    if (e.target.value == 0) {
      e.target.setCustomValidity('Value must be larger than zero.');
      e.target.reportValidity();
    } else {
      e.target.setCustomValidity('');
    }
  } 

  // Quantity validation, prompt alert box if fail
  const quantity_input = document.querySelector('#manual-add-position');
  quantity_input.addEventListener('input', (e) => {
    const isValid = e.target.checkValidity();
    if (!isValid) {
      e.target.reportValidity();
    } else {
    }
  });

  // All (symbol, price, position and buy/sell button) must be inputted to enable the button
  let order_entry = document.querySelectorAll('.order_entry');
  for (var i = 0; i < order_entry.length; i++) {
    order_entry[i].addEventListener('input',() => {
      let values = [];
      order_entry.forEach(v => values.push(v.value))
      button.disabled = values.includes('');
      let radio1 = document.getElementById("btnradio1");
      let radio2 = document.getElementById("btnradio2");
      if (radio1.checked == false && radio2.checked == false) {
        button.disabled = true;
      }
      radio1.addEventListener('click', () => {
        if (values.includes('') == false) {
          button.disabled = false;
        }
      })
      radio2.addEventListener('click', () => {
        if (values.includes('') == false) {
          button.disabled = false;
        }
      })
    })
  }
}


function cash_deposit_withdraw_validation() {
  // Cash validation: value must be larger than 0 to enable the button
  document.querySelector('#cash-amount').oninput = (e) => {
    if (e.target.value == 0) {
      e.target.setCustomValidity('Value must be larger than zero.');
      e.target.reportValidity();
    } else {
      e.target.setCustomValidity('');
    }
  }

  const button = document.querySelector('#cash-button');
  button.disabled = true;
  let cash_entry = document.querySelector('#cash-amount');
  cash_entry.onkeyup = () => {
    if (cash_entry.value.length > 0) {
      button.disabled = false;
    }
    else {
      button.disabled = true;
    }
  }
}


function format_date(date) {
  // Standardizing date formatting
  const d = new Date(date);
  const months = ["Jan.", "Feb.", "Mar.", "Apr.", "May", "Jun.", "Jul.", "Aug.", "Sep.", "Oct.", "Nov.", "Dec."];
  let month = months[d.getMonth()];
  let day = d.getDate();
  let year = d.getFullYear();
  let hr = d.getHours();
  let hour, zero_hour, zero_minute;
  let minute = d.getMinutes();
  let ampm = "AM";
  if (hr > 12) {
    hour = hr - 12;
  } else if (hr < 12 && hr > 0) {
    hour = hr;
  } else {
    hour = 12;
  }
  if (hour < 10) {
    zero_hour = 0;
  } else {
    zero_hour = "";
  }
  if (minute < 10) {
    zero_minute = 0;
  } else {
    zero_minute = "";
  }
  if (hr >= 12) {
    ampm = "PM";
  }
  return `${month} ${day}, ${year}, ${zero_hour}${hour}:${zero_minute}${minute} ${ampm}`;
}
