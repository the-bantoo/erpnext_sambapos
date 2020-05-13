# erpnext_sambapos 
Syncs SambaPOS Sales Invoices to ERPNext. Setup is tedious for now but with enough demand and support we are willing to make it better.


[
  ![Support this Project]
  (https://www.theidealmuslimah.com/wp-content/uploads/2016/06/Support.png)
]
(https://dashboard.flutterwave.com/donate/xdf1tblhrxbk)


## Requirements
- SambaPOS with SQLExpress or SQL 2014 - 2017
- ERPNext v12

## Prepare localhost environment





Schedule Python Job on Windows
Setup the script
- Install python 3.x for windows - https://www.python.org/downloads/release/python-382/
- Install the `pyodbc` driver

	```
	pip install pyodbc
	```
	
- Install git - https://git-scm.com/download/win
- Install Frappe Client in the app root directory (sambapos_erpnext) - https://github.com/the-bantoo/erpnext_sambapos 
	
	```
	git clone https://github.com/the-bantoo/frappe-client.git
	```
	
	```
	pip install -e frappe-client
	```
	
- Setup Windows Scheduler 
	- https://www.esri.com/arcgis-blog/products/product/analytics/scheduling-a-python-script-or-model-to-run-at-a-prescribed-time/?rmedium=redirect&rsource=blogs.esri.com/esri/arcgis/2013/07/30/scheduling-a-scrip
	- https://www.reddit.com/r/learnpython/comments/c2ya1y/best_way_to_schedule_a_python_script_that_runs/erndv0o/

		Put the directory in the start-in field (without the final backslash), and JUST the filename (and extension) in the program/script field.
		For example if my file is in:
		`C:\Folder1\Folder2\python_file.py`

		Then I'll make a batch file in notepad, run.bat, in the same folder, and just type this inside it:
		python python_file.py

		To run from a very specific version of python with all the correct libraries and not messing with PATH. In this case the batch file would look like this:
		```
		SET PYTHONPATH=C:\localpython\Lib\sitepackages
		C:\localpython\python.exe python_file.py
		```


		Then in the task scheduler I'll set up my regular trigger times and in the action tab, put the info in in the following way:
		Action: start a program
		Program/script: run.bat
		Add arguments (optional): [I leave this blank, I can always put arguments in my batch file]
		Start in (option): C:\Folder1\Folder2

		General > Run whether user is logged on > Tick: Do not store password if password entry fails

## Add ERPNext Custom Fields to Sales Invoice
- restaurant_name
- restaurant_table
- Sambapos_ticket

## Configure MSSQL Database
#### Add new Columns in the following tables
- GroupUploaded to ScreenMenuCategories (table) and MenuItems (table)
  - Right click table
  - Design
  - Add new column called xUploaded type int
  - Uncheck Allow Nulls
  - Set property Default Value or Binding to 0 (zero digit) 
  - Save and close
  - Repeat for the next tables
  
- ItemUploaded and Order Uploaded to MenuItems, Orders (table)
- TicketUploaded to Tickets
  - Right click table
  - Design
  - Add new column called Modified type datetime
  - Uncheck Allow Nulls
  - Set property Default Value or Binding to (getdate())
  - Save and close

## Edit settings.py
Configure connection settings in settings.py. Make sure the erpnext values are copied exactly as they appear in your erpnext instance. 
	
## Create database views
### GroupCodesView = Item Groups
- Right click Views
- New
- Close

#### SQL

```
SELECT        GroupCode, GroupUploaded
FROM            dbo.MenuItems
WHERE        (Id IN
                             (SELECT        MIN(Id) AS Expr1
                               FROM            dbo.MenuItems AS MenuItems_1
                               GROUP BY GroupCode)) AND GroupCode <> ''
UNION
SELECT        Name AS GroupCode, [GroupUploaded]
FROM            dbo.ScreenMenuCategories
```

- CTRL + S to Save


### OrdersView = Sales Invoices/Orders
#### SQL
		
```
SELECT        o.Id AS OrderID, o.Id, o.TicketId, o.MenuItemId, o.MenuItemName, o.PortionName, o.Price, o.Quantity, o.PortionCount, o.OrderNumber, o.CreatingUserName, o.CreatedDateTime, o.LastUpdateDateTime, 
                         o.AccountTransactionTypeId, o.OrderStates, o.Price * o.Quantity AS oTotal, m.GroupCode
FROM            dbo.Orders AS o LEFT OUTER JOIN
                         dbo.MenuItems AS m ON o.MenuItemId = m.Id
WHERE        (o.OrderStates NOT LIKE '%Void%') AND (o.OrderStates NOT LIKE '%Cancel%')
```


### MenuItemView = Items
#### SQL 

```
SELECT DISTINCT o.MenuItemName, i.GroupCode, o.PortionName, o.Price, o.MenuItemId, i.ItemUploaded
FROM            dbo.OrdersView AS o LEFT OUTER JOIN
                         dbo.MenuItems AS i ON o.MenuItemId = i.Id
```




### PaidTicketView = Paid Sales Invoice
#### SQL

```
SELECT        t.TicketNumber AS TicketNo, t.TicketUid AS Uid, p.Id AS PaymentID, p.Name AS PaymentType, CONVERT(varchar(30), t.LastUpdateTime) AS Modified, t.LastModifiedUserName AS SalesPerson, t.Note, t.TotalAmount AS TotalPaid, 
                         t.RemainingAmount AS UnpaidBalance, t.TaxIncluded, t.Name, t.TicketUploaded, t.Id, COALESCE (te1.EntityName, 'Walk-in') AS Customer, COALESCE (te2.EntityName, 'Take-Away/Delivery') AS TableUsed
FROM            dbo.Tickets AS t INNER JOIN
                         dbo.Payments AS p ON t.Id = p.TicketId LEFT OUTER JOIN
                         dbo.TicketEntities AS te1 ON t.Id = te1.Ticket_Id AND te1.EntityTypeId = 1 LEFT OUTER JOIN
                         dbo.TicketEntities AS te2 ON t.Id = te2.Ticket_Id AND te2.EntityTypeId = 2
```



Ignore the Warning Popup Message on saving

### PricedUOMItem
#### SQL

```
SELECT DISTINCT o.MenuItemName, o.GroupCode, o.PortionName, o.Price, o.MenuItemId, i.ItemUploaded
FROM            dbo.OrdersView AS o LEFT OUTER JOIN
                         dbo.MenuItems AS i ON o.MenuItemId = i.Id
```

### UOMView
#### SQL

```
SELECT        Id, Name, MenuItemId AS ProductID, Multiplier, Modified
FROM            dbo.MenuItemPortions
WHERE        (Id IN
                             (SELECT        MIN(Id) AS Expr1
                               FROM            dbo.MenuItemPortions AS MenuItemPortions_1
                               GROUP BY Name))
```


## Roadmap
- Payment Types
- Deduction of (ingredient) Stock Items
- Make UOM Tree
- Updated sql transactions
	- Batch search: Get list to test against: items (done), groups (done), uoms
	- Update atrributes: Price, UOM, Group -> Update

- Automate the DB Setup in Python SQL
- Create an ERPNext App to hold configs and auto configure erpnext changes

## Here's how you can help improve this project
[Click here to learn more](https://thebantoo.com/blog/general/crowdsourced-development-support)
