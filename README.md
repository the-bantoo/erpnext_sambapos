# erpnext_sambapos
Syncs SambaPOS Sales Invoices to ERPNext
redesign menuitems view to include missing items


SELECT        TOP (1000) i.Name, i.GroupCode, u.Name AS UOM, p.Price, i.Id, i.Modified, i.Tag, i.CustomTags, i.ItemType, i.ItemUploaded
FROM            dbo.MenuItems AS i LEFT OUTER JOIN
                         dbo.MenuItemPortions AS u ON i.Id = u.Id LEFT OUTER JOIN
                         dbo.MenuItemPrices AS p ON i.Id = p.Id


SELECT        TOP (1000) i.Name, i.ItemPortion, u.Name AS UOM, p.Price, i.Id, i., i.Tag, i.CustomTags, i.ItemType, i.ItemUploaded
FROM            dbo.ScreenMenuItems AS i LEFT OUTER JOIN
                         dbo.MenuItemPortions AS u ON i.MenuItemId = u.MenuItemId LEFT OUTER JOIN
                         dbo.MenuItemPrices AS p ON i.MenuItemId = p.Id