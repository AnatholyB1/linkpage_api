import frappe
import random
import json
from frappe.utils import nowdate
from frappe import _, msgprint, throw

@frappe.whitelist(allow_guest=True)
def getphone(userphone):
    if userphone.startswith("0"):
        userphone = userphone[1:] 

    userphone = '66'+userphone
    if userphone:
        filters = {
            'phone': userphone
        }
        document = frappe.get_all('User', filters=filters)
        if document:
            document = frappe.get_all('User', filters=filters)[0]['name']
            myDict = {}
            myDict["status"] = "error"
            myDict["message"] = "Phone Number already exists"
            return myDict
        else:
            return request_otp(userphone)

@frappe.whitelist(allow_guest=True)
def verifyotp(userphone,otp,username):
    if userphone.startswith("0"):
        userphone = userphone[1:] 

        
    userphonez = '66'+userphone
    searchnum = '0'+userphone
    cached_otp = frappe.cache().get_value(f"phone_verification_otp:{userphonez}")
    response = 0
    if not cached_otp:
        response = 1
    if cached_otp != int(otp):
        response = 1

    myDict = {} 
    if not response:
        if cached_otp == int(otp):
            myDict["status"] = "success"
            myDict["message"] = "OTP is confirmed"
            user = frappe.get_doc("User", username)
            user.phone = searchnum
            user.save(ignore_permissions=True)
            
            user = frappe.get_doc("User", username)
            
            customer =frappe.get_all("Customer", filters={"phone": ["like", searchnum]})
            if customer:
                customer =frappe.get_all("Customer", filters={"phone": ["like", searchnum]})[0]['name']
                contacts = frappe.get_all("Contact", filters={"email_id": ["like", user.email]})
                if contacts:
                    contacts = frappe.get_all("Contact", filters={"email_id": ["like", user.email]})[0]['name']
                    customer = frappe.get_doc("Customer", customer)
                    contacts = frappe.get_doc("Contact", contacts)
                    contacts.append("links",{
                            "link_doctype": "Customer",
                            "link_name": customer.name,
                    })
                    contacts.save(ignore_permissions=True)
                    customer.remove_tag('Unclaimed')
                    customer.add_tag('Claimed')
                    customer.save()
        else:
            myDict["status"] = "error"
            myDict["message"] = "Please check your OTP"      
    else:
        
        myDict["status"] = "error"
        myDict["message"] = "Please check your OTP"
               
    return myDict  


def request_otp(phone_number):
    otp = random.randint(100000, 999999)
    frappe.cache().set_value(
        f"phone_verification_otp:{phone_number}", otp, expires_in_sec=60 * 10
    )
    message = str(otp)
    return send_sms([phone_number], message)




def send_request(gateway_url, params, headers=None, use_post=False, use_json=False):
    import requests
    
    
    otp = params['otp'];
    mobiles = params['mobiles'];
    template_id = params['template_id'];
    


    if not headers:
        headers = get_headers()
    kwargs = {"headers": headers}

    if use_json:
        kwargs["json"] = params
    elif use_post:
        kwargs["data"] = params
    else:
        kwargs["params"] = params

    payload = json.dumps({
        "template_id": template_id,
        "sender": "Zaviago",
        "mobiles": mobiles,
        "otp": otp
    })
    headers = {
        'accept': 'application/json',
        'authkey': '400038AZM2Lbf564b81e95P1',
    }
    response = requests.request("POST", gateway_url, headers=headers, data=payload)  
    return response.status_code
            
            
@frappe.whitelist()
def send_sms(receiver_list, msg, sender_name="", success_msg=True):

    import json

    if isinstance(receiver_list, str):
        receiver_list = json.loads(receiver_list)
        if not isinstance(receiver_list, list):
            receiver_list = [receiver_list]

    receiver_list = validate_receiver_nos(receiver_list)

    arg = {
        "receiver_list": receiver_list,
        "message": msg,
        "success_msg": success_msg,
    }

    if frappe.db.get_single_value("SMS Settings", "sms_gateway_url"):
        return send_via_gateway(arg)
    else:
        msgprint(_("Please Update SMS Settings"))     
        
        


def send_via_gateway(arg):
    ss = frappe.get_doc("SMS Settings", "SMS Settings")
    headers = get_headers(ss)
    use_json = headers.get("Content-Type") == "application/json"

    message = frappe.safe_decode(arg.get("message"))
    args = {ss.message_parameter: message}
    for d in ss.get("parameters"):
        if not d.header:
            args[d.parameter] = d.value

    success_list = []
    for d in arg.get("receiver_list"):
        args[ss.receiver_parameter] = d
        status = send_request(ss.sms_gateway_url, args, headers, ss.use_post, use_json)
        

        if 200 <= status < 300:
            success_list.append(d)

    if len(success_list) > 0:
        args.update(arg)
        create_sms_log(args, success_list)
        myDict = {}
        myDict["status"] = "success"
        myDict["message"] = "OTP Sent"
        if arg.get("success_msg"):
            return myDict
       
       
def validate_receiver_nos(receiver_list):
    validated_receiver_list = []
    for d in receiver_list:
        if not d:
            break

        # remove invalid character
        for x in [" ", "-", "(", ")"]:
            d = d.replace(x, "")

        validated_receiver_list.append(d)

    if not validated_receiver_list:
        throw(_("Please enter valid mobile nos"))

    return validated_receiver_list       
    
    
    
def get_headers(sms_settings=None):
    if not sms_settings:
        sms_settings = frappe.get_doc("SMS Settings", "SMS Settings")

    headers = {"Accept": "text/plain, text/html, */*"}
    for d in sms_settings.get("parameters"):
        if d.header == 1:
            headers.update({d.parameter: d.value})

    return headers    
    
    
def create_sms_log(args, sent_to):
	sl = frappe.new_doc("SMS Log")
	sl.sent_on = nowdate()
	sl.message = args["message"]
	sl.no_of_requested_sms = len(args["receiver_list"])
	sl.requested_numbers = "\n".join(args["receiver_list"])
	sl.no_of_sent_sms = len(sent_to)
	sl.sent_to = "\n".join(sent_to)
	sl.flags.ignore_permissions = True
	sl.save()    