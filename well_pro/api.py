import frappe


@frappe.whitelist()
def hello():
    return {
        "success": True,
        "message": "Hello from my custom Frappe backend!",
        "framework": "Frappe",
    }
