from frappeclient import FrappeClient
import logging
import pyodbc 
import sys, json
import datetime
from datetime import datetime
from socket import error as SocketError, timeout as SocketTimeout
import settings

"""
    TODO
    - Production readiness
        - Cron job windows - working
        - Payment types: Credit Card
        - Make UOM Tree
        - Document
        - Move API user details to DB
        
    - stock deduction
        - Costing / valuation
        - BOM (Recipe)
        - Stock Entry creation

    - Resilience
        - Error handling
            - User alerts
            - Error Log

    - Issues
        - MenuItemView Price is incorrect - use portion price - Solved

    Roadmap
    - Payment Types
    - Make UOM Tree
    - Updated sql transactions
      - Batch search: Get list to test against: items (done), groups (done), uoms
      - Update atrributes: Price, UOM, Group -> Update
      - Create an ERPNext App to hold configs

    Open source
    - Move configs to file
    - Add to gitignore
    - Automate the DB Setup in Python SQL
"""

chars = ["<", ">", ",", '"', "/", "%", "^", "*", ";"]

# rest connection
def http_connection():

    connection = True

    try:
        connection = FrappeClient(settings.erpnext_host, settings.erpnext_user, settings.erpnext_password )

    except SocketTimeout as st:
        logging.warning("Connection to %s timed out. (timeout=%s)" % (st.host, st.timeout))
        connection = False

    except SocketError as e:
        logging.warning("Failed to establish a network connection")
        connection = False

    return connection

def sql(sql):    
    # db connection

    db = pyodbc.connect("Driver={SQL Server Native Client 11.0}; Server=" + settings.database_host + 
                        "; Database=" + settings.database_name + "; Trusted_Connection=yes;" )
    
    cursor = db.cursor()
    cursor.fast_executemany = True

    result = cursor.execute(sql)

    if (sys._getframe().f_back.f_code.co_name == "finish"):
        cursor.commit()
        cursor.close()
        logging.info("Sync complete  ******************")

    return result

def sql_write(sql):    
    # db connection
    
    cnxn = pyodbc.connect("Driver={SQL Server Native Client 11.0}; Server=" + settings.database_host + 
                        "; Database=" + settings.database_name + "; Trusted_Connection=yes;" )
    cursor = cnxn.cursor()

    result = cursor.execute(sql)
    cursor.commit()

    return result

def is_not_empty(my_string):
    return bool(my_string and my_string.strip())
    

def sync_groups():
    """
    Pulls Groups from SambaPOS and Syncs to ERPNext

    - Only upload groups not in ERPNext
        - Gets ERPNext Group list then compares it to the SQL groups
    """
    
    https = http_connection()

    if (https):
        db_groups = sql('SELECT * FROM dbo.GroupCodesView WHERE [GroupUploaded] <> 1 OR GroupUploaded IS NULL')

        for g in db_groups:

            group = str(g[0])
            
            for s in chars: # remove all the 8s 
                group = group.replace(str(s), '')
           
            group = group.replace("&amp;", "&")
            
            if is_not_empty(group):          

                check_group = group.strip().lower()      

                if check_group not in erp_groups:              
                    resonse = https.insert({"doctype": "Item Group",
                                            "parent": "Foods",
                                            "item_group_name": group
                                        })
                    
                    if resonse['name']:
                        logging.info("item group created - " + group)
                        erp_groups.append(check_group)

                sql_write("UPDATE dbo.MenuItems SET [GroupUploaded] = 1 WHERE [GroupCode] = '" + group + "';")
                sql_write("UPDATE dbo.ScreenMenuCategories SET [GroupUploaded] = 1 WHERE [Name] = '" + group + "';")


def sync_uoms():
    
    https = http_connection()
    if (https):

        for u in sql('SELECT * FROM dbo.UOMView'):        
            uom = str(u[1])

            if is_not_empty(uom):
                
                check_uom = uom.strip().lower()

                # check if doc is already synced
                if check_uom not in erp_uoms:
                    ins = https.insert({"doctype": "UOM",
                                    "uom_name": uom
                                })
                    if ins["uom_name"]:
                        logging.info("UOM created - " + uom)
                        erp_uoms.append(check_uom)


def get_item(item):
    return sql("SELECT Name AS item, GroupCode AS itemgroup, UOM AS uom FROM dbo.PricedUOMItem WHERE Name ='" + item + "';")

def sync_items():
    """
    Pulls items from SambaPOS and Syncs to ERPNext

    - Only upload items not in ERPNext
        - Gets ERPNext item list then compares it to the SQL items
    """

    https = http_connection()

    if (https):

        db_items = sql('SELECT * FROM dbo.MenuItemView WHERE ItemUploaded <> 1 OR ItemUploaded IS NULL;')

        for i in db_items:
            item = str(i[0]).strip()
            group = str(i[1]).strip()
            uom = str(i[2]).strip()
            item_id = str(i[4]).strip()
            
            for s in chars: # remove all the 8s 
                item = item.replace(str(s), '')
           
            item = item.replace("&amp;", "&")
        
            if not uom or not is_not_empty(uom) or uom == "None": 
                uom = "Normal"
            elif (uom == "Normal" or uom == "normal"):
                pass
            else:
                # append uom to name
                item = item + " " + uom
                uom = "Normal"

            # Insert group if does not exist 
            if not group or not is_not_empty(group) or group == "None": 
                group = "Others"

            check_item = ""
                    
            if is_not_empty(item):
                
                check_item = item.strip().lower()

                # check if item name is used in groups, if so modify item name
                if (check_item in erp_groups and ("2" not in str(check_item))):
                    item = item + " 2"

                check_item = item.lower()
                
                # check if doc is already synced
                if check_item not in erp_items:
                    
                    ins = https.insert({
                        "doctype": "Item",
                        "item_code": item,
                        "item_group": group,
                        "stock_uom": uom
                    })
                    
                    if ins['name']:
                        logging.info("item created - " + item)
                        erp_items.append(check_item)

                sql_write("UPDATE dbo.MenuItems SET ItemUploaded = 1 WHERE Id = '" + item_id + "';")
                #sql_write("UPDATE dbo.ScreenMenuItems SET ItemUploaded = 1 WHERE MenuItemId = '" + item_id + "';")     
            

def sync_dependancies():
    pass

def update_dependancies():
    pass


def get_invoice_items(ticket_id, income_account, cost_centre):
   
    items = []

    amount = 0
    rate = 0
    item_name = ""

    item_query = sql("SELECT TicketId, MenuItemName, PortionName, Price, Quantity, OrderNumber, oTotal, GroupCode FROM [dbo].[OrdersView] WHERE TicketId ='"+ ticket_id +"';")

    for i in item_query:
        
        item_name = str(i[1])
        uom = str(i[2])
        rate = float(i[3])  
        amount = float(i[6])      
        group = str(i[7])

        chars = ["<", ">", ",", '"', "/", "%", "^", "*", "`", ";"]

        # remove all the special characters
        for s in chars: 
            item_name = item_name.replace(str(s), '') 

        item_name = item_name.replace("&amp;", "&")

        if not uom or not is_not_empty(uom) or uom == "None": 
            uom = "Normal"
        elif (uom == "Normal" or uom == "normal"):
            pass
        else:
            # append uom to name
            item_name = item_name + " " + uom
            uom = "Normal"
            
        # Insert group if does not exist 
        if not group or not is_not_empty(group) or group == "None": 
            group = "Others"

        item_search = item_name.strip().lower()

        # check if doc is already synced
        if item_search in erp_groups:
            item_name = item_name + " 2"

        items.append({            
            "item_name": item_name,
            "item_code": item_name,
            "description": item_name,
            "uom": uom,
            "qty": int(i[4]),
            "stock_qty":int(i[4]),
            "conversion_factor":1,
            "rate": rate,
            "base_rate": rate,
            "amount": amount,
            "base_amount": amount,
            "income_account": income_account,
            "cost_center": cost_centre
        })

    return items

def auto_fiscal_year():
    https = http_connection()
    if (https):
    
        year = "2022" #str(date.year)
        year_start_date = str(datetime.strptime('01-01-' + year, '%d-%m-%Y').date())
        year_end_date = str(datetime.strptime('31-12-' + year, '%d-%m-%Y').date())

        fiscal_year = https.get_list( 'Fiscal Year', fields = ['year', 'year_start_date', 'year_end_date'], filters = {'year': ('Like', '%'+ year + '%') } )

        if not fiscal_year:
            response = https.insert({
                "doctype": "Fiscal Year",
                "year": year,
                "year_start_date": year_start_date,
                "year_end_date": year_end_date
            })

            # fiscal_year = datetime.strptime('01-01-'+ year, '%d-%m-%Y').strftime('%d-%m-%Y')
            fiscal_year = https.get_doc("Fiscal Year", year)      

def sync_invoices():
    """              
        get invoices  from db and uses get_items() to get orders for each invoice
        sync_invoices
        update inserted status for ticket
    """
    
    https = http_connection()

    if (https):    

        # get settings
        default_company = settings.default_company
        default_customer = settings.default_customer
        last_update = settings.last_update
        territory = settings.territory
        debit_to = settings.debit_to
        tax_rate = settings.tax_rate
        restaurant = settings.restaurant_name
        income_account = settings.income_account
        cost_centre = settings.cost_centre

        """settings = sql('SELECT * FROM dbo.erpnext_settings')

        for row in settings:
            if (row[0].strip() == "default_company"):
                default_company = str(row[1]).strip()
            elif (row[0].strip() == "default_customer"):
                default_customer = str(row[1]).strip()
            elif (row[0].strip() == "last_update"):
                last_update = str(row[1]).strip()
            elif (row[0].strip() == "territory"):
                territory = str(row[1]).strip()
            elif (row[0].strip() == "debit_to"):
                debit_to = str(row[1]).strip()
            elif (row[0].strip() == "tax_rate"):
                tax_rate = int(row[1])
            elif (row[0].strip() == "restaurant_name"):
                restaurant = str(row[1]).strip()
            elif (row[0].strip() == "income_account"):
                income_account = str(row[1]).strip()
            elif (row[0].strip().strip() == "cost_centre"):
                cost_centre = str(row[1]).strip().strip()
        """

        tickets = sql('SELECT * FROM dbo.PaidTicketView WHERE TicketUploaded <> 1 OR TicketUploaded IS NULL')
        
        for t in tickets:

            ticket_id = str(t[-3])
            items = get_invoice_items(ticket_id, income_account, cost_centre)

            customer_name = str(t[-2]).strip()

            if not is_not_empty(customer_name):
                customer_name = default_customer            
            elif (customer_name == "Walk-in"):
                customer_name = default_customer
            else:
                customer_name = "Walk-in"

            # check customer existence and create customer if required
            customer = https.get_list( 'Customer', fields = ['customer_name'], filters = {'customer_name': customer_name} )

            if not customer:
                response = https.insert({
                    "doctype":"Customer",
                    "customer_name": customer_name,
                    "territory": territory,
                    "customer_group": "Individual",
                    "company": default_company,
                    "mobile_no": "000000"
                })
            
            date = datetime.strptime(str(t[4]), '%b %d %Y %I:%M%p')
            posting_date = date.strftime('%Y-%m-%d')

            grand_total = float(t[7])
            tax = grand_total * (int(tax_rate)/100)
            net_total = grand_total - tax

            restaurant_table = str(t[-1])
            sambapos_ticket = str(t[0])

            resonse = https.insert({
                        
                "doctype": "Sales Invoice",
                "naming_series": "ACC-SINV-.YYYY.-",
                "company": default_company,
                "sambapos_ticket": sambapos_ticket,
                "set_posting_time": "1",
                "posting_date": posting_date,
                "is_pos": "1", 
                "conversion_rate": 1.0, 
                "currency": "ZMW", 
                "debit_to": debit_to,
                "customer": customer_name,
                "customer_name": customer_name,
                "grand_total": grand_total, 
                "base_grand_total": grand_total, 
                "net_total": net_total, 
                "base_net_total": net_total, 
                "base_rounded_total": grand_total,
                "rounded_total": grand_total, 
                "plc_conversion_rate": 1.0, 
                "price_list_currency": "ZMW", 
                "price_list_name": "Standard Selling", 
                "restaurant_name": restaurant,
                "restaurant_table": restaurant_table,
                "docstatus":1,
                "items": items,
                "payments":[{
                    "mode_of_payment":"Cash",
                    "amount":grand_total,
                    "base_amount":grand_total,
                    "account": income_account
                }],
                "taxes": [{
                    "account_head": "VAT - MCB", 
                    "charge_type": "On Net Total", 
                    "description": "VAT @ 16.0",
                    "tax_amount": float(tax),
                    "rate": tax_rate,
                    "included_in_print_rate": "1"
                }],
                
            })

            if resonse['name']:
                
                logging.info(posting_date +" - "+ sambapos_ticket +" - "+ resonse['name']+" - total: "+str(grand_total)+" - restaurant: "+restaurant)
                sql_write("UPDATE dbo.Tickets SET TicketUploaded = 1 WHERE TicketNumber = '" + sambapos_ticket + "';")

# close db connection, update last update time
def finish():
    # set last update time. If needed this can be written to a file, overwritting each time
    # settings.last_update = datetime.now().strftime('%d-%m-%Y %X')

    # hack to close the sql connection
    sql("select top(0) Id from dbo.MenuItems")

    
def start():

    """
    - Get masters: UOM, Group, Item
    - Insert new invoices

    TODO
    - Batch Search: Get list to test against: items, etc
        - get_all list
        -  
    """

    logging.basicConfig(filename='sync.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info("Sync starting  *********************")

    sync_uoms()
    sync_groups()   
    sync_items()
    sync_invoices()
    finish()

def make_list(items):
    lst = []
    for i in items: 
        itm = str(i['name']).lower()

        lst.append(itm)
        lst.append(itm + " 2")
        
    return lst

def make_uom_list(items):
    lst = []
    for i in items: 
        lst.append(str(i['uom_name']).lower())

    return lst


https = http_connection()

# Stop if there's no internet connection
if not https: exit()

erp_groups = make_list(https.get_list('Item Group',
                            fields = ["name"],    
                            filters=None,
                            limit_page_length = 1000
                        ))
                        
erp_items = make_list(https.get_list('Item',
                            fields = ["name"],    
                            filters=None,
                            limit_page_length = 100000
                        ))

erp_uoms = make_uom_list(https.get_list('UOM',
                            fields = ["uom_name"],    
                            filters=None,
                            limit_page_length = 100000
                        ))

start()