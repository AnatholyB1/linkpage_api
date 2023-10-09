import frappe
import frappe.defaults
from frappe import _, throw
from frappe.contacts.doctype.contact.contact import get_contact_name
from frappe.utils import cint
import jwt
import requests
import base64
import json


@frappe.whitelist(allow_guest=True)
def get_profile(customer):
    user = frappe.get_doc('User', customer)
    return user

@frappe.whitelist()
def update_profile(
    first_name: str = None,
    last_name: str = None,
    email: str = None,
    phone: str = None,
    birth_date: str = None,
    id_card_number: str = None
): 
    # update user
    user_name = frappe.session.user
    user = frappe.get_doc("User", user_name).update({
        "first_name": first_name if first_name else None,
        "last_name": last_name if last_name else None,
        "email": email if email else None,
        "birth_date": birth_date if birth_date else None,
        "id_card_number": id_card_number if id_card_number else None,
    })
    user.save(ignore_permissions=True)
    
    
    # update contact
    # contact = frappe.get_last_doc("Contact", filters={
    #     "user": user.name
    # }).update({
    #     "first_name": first_name if first_name else None,
    #     "last_name": last_name if last_name else None,
    #      "email_id": email if email else None,
    #     "birth_of_date": birth_date if birth_date else None,
    #     "customer_id": id_card_number if id_card_number else None,
    # })
    
    # update Customer
    # if contact.links and contact.links[0].link_doctype == "Customer":
    #     customer_name = contact.links[0].link_name
    #     customer = frappe.get_doc("Customer", customer_name).update({
    #         "doctype": "Customer",
    #         "name": customer_name,
    #         "customer_name": f"{first_name} {last_name}" if first_name or last_name else None,
    #         "customer_details": f"birth_date: {birth_date} id_card_number: {id_card_number}",
    #         "customer_primary_contact": contact.name,
    #     })
        
    #     customer.save(ignore_permissions=True)
    #     contact.save(ignore_permissions=True)


    dd = frappe.session.user
    customer = frappe.get_all("Customer", fields=['name'], filters={"email_id": dd} )
    
    if customer:
        customer = customer[0]['name']

    
    user = frappe.get_all("Sales Invoice", fields=['name', 'posting_date', 'status', 'total'], filters={"customer": customer,"redeem_loyalty_points": 1} )
    invoice_names = [invoice['name'] for invoice in user]
    delivery_notes = frappe.get_all("Rewards Status", fields=['name','status','sales_invoice_no'], filters={"sales_invoice_no": ["in", invoice_names]})
    combined_data = []

    for invoice in user:
        user_data = {
            "name": invoice['name'],
            "posting_date": invoice['posting_date'],
            "status": invoice['status'],
            "total": invoice['total'],
            "delivery_notes": []
        }
        for note in delivery_notes:
            if note['sales_invoice_no'] == invoice['name']:
                user_data['delivery_notes'].append({
                    "name": note['name'],
                    "status": note['status']
                })


        combined_data.append(user_data)

    

    return combined_data


