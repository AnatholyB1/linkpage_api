import base64
import json
from typing import TYPE_CHECKING, Callable
import frappe
import frappe.utils
from frappe import _
from frappe.utils.password import get_decrypted_password


@frappe.whitelist(allow_guest=True)
def get_oauth2_authorize_url():
	redirect_to = 'https://library.test:8000/api/method/linkpage_api.api_calls.linehandle.login_via_line'
	provider = 'line'

	flow = get_oauth2_flow(provider)

	state = {
		"site": frappe.utils.get_url(),
		"token": frappe.generate_hash(),
		"redirect_to": 'http://localhost:5173/setup',
	}

	# relative to absolute url
	data = {
		"redirect_uri": redirect_to,
		"state": base64.b64encode(bytes(json.dumps(state).encode("utf-8"))),
	}

	oauth2_providers = get_oauth2_providers()

	# additional data if any
	data.update(oauth2_providers[provider].get("auth_url_data", {}))

	return flow.get_authorize_url(**data)

def get_oauth2_flow(provider: str):
	from rauth import OAuth2Service

	# get client_id and client_secret
	params = get_oauth_keys(provider)

	oauth2_providers = get_oauth2_providers()

	# additional params for getting the flow
	params.update(oauth2_providers[provider]["flow_params"])

	# and we have setup the communication lines
	return OAuth2Service(**params)


def get_redirect_uri(provider: str) -> str:
	keys = frappe.conf.get(f"{provider}_login")

	if keys and keys.get("redirect_uri"):
		# this should be a fully qualified redirect uri
		return keys["redirect_uri"]

	oauth2_providers = get_oauth2_providers()
	redirect_uri = oauth2_providers[provider]["redirect_uri"]

	# this uses the site's url + the relative redirect uri
	return frappe.utils.get_url(redirect_uri)

def get_oauth2_providers() -> dict[str, dict]:
	out = {}
	providers = frappe.get_all("Social Login Key", fields=["*"])
	for provider in providers:
		authorize_url, access_token_url = provider.authorize_url, provider.access_token_url
		if provider.custom_base_url:
			authorize_url = provider.base_url + provider.authorize_url
			access_token_url = provider.base_url + provider.access_token_url
		out[provider.name] = {
			"flow_params": {
				"name": provider.name,
				"authorize_url": authorize_url,
				"access_token_url": access_token_url,
				"base_url": provider.base_url,
			},
			"redirect_uri": provider.redirect_url,
			"api_endpoint": provider.api_endpoint,
		}
		if provider.auth_url_data:
			out[provider.name]["auth_url_data"] = json.loads(provider.auth_url_data)

		if provider.api_endpoint_args:
			out[provider.name]["api_endpoint_args"] = json.loads(provider.api_endpoint_args)

	return out


def get_oauth_keys(provider: str) -> dict[str, str]:
	"""get client_id and client_secret from database or conf"""

	if keys := frappe.conf.get(f"{provider}_login"):
		return {"client_id": keys["client_id"], "client_secret": keys["client_secret"]}

	return {
		"client_id": frappe.db.get_value("Social Login Key", provider, "client_id"),
		"client_secret": get_decrypted_password("Social Login Key", provider, "client_secret"),
	}