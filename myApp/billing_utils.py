"""
Billing utilities for subscription management and feature gating.
"""
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import requests
import logging

log = logging.getLogger(__name__)


# =============================
# Plan Capabilities & Feature Gating
# =============================

def get_user_plan(user):
    """Get user's current plan from profile."""
    if not user or not user.is_authenticated:
        return 'free'
    
    try:
        profile = user.profile
        return profile.plan or 'free'
    except Exception:
        return 'free'


def is_subscription_active(user):
    """Check if user has an active subscription."""
    if not user or not user.is_authenticated:
        return False
    
    try:
        profile = user.profile
        if profile.subscription_status == 'active':
            # Check if subscription hasn't expired
            if profile.subscription_ends_at:
                return profile.subscription_ends_at > timezone.now()
            return True
        return False
    except Exception:
        return False


def has_feature_access(user, feature):
    """
    Check if user has access to a specific feature.
    
    Args:
        user: Django User instance
        feature: Feature name (e.g., 'medical_summaries', 'voice')
    
    Returns:
        bool: True if user has access, False otherwise
    """
    plan = get_user_plan(user)
    capabilities = settings.PLAN_CAPABILITIES.get(plan, {})
    
    # Check if subscription is active (except for free plan)
    if plan != 'free' and not is_subscription_active(user):
        return False
    
    return capabilities.get(feature, False)


def get_history_days(user):
    """Get number of days of history user can access."""
    plan = get_user_plan(user)
    capabilities = settings.PLAN_CAPABILITIES.get(plan, {})
    days = capabilities.get('history_days', 0)
    
    # None means unlimited
    if days is None:
        return None
    
    # Check if subscription is active
    if plan != 'free' and not is_subscription_active(user):
        return 0
    
    return days


# =============================
# PayPal API Helpers
# =============================

def get_paypal_access_token():
    """Get PayPal OAuth access token."""
    # Check if credentials are set
    if not settings.PAYPAL_CLIENT_ID or not settings.PAYPAL_CLIENT_SECRET:
        error_msg = "PayPal credentials not configured. Please set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET in environment variables."
        log.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        response = requests.post(
            f"{settings.PAYPAL_API_BASE}/v1/oauth2/token",
            auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET),
            data={"grant_type": "client_credentials"},
            headers={"Accept": "application/json", "Accept-Language": "en_US"},
            timeout=10,
        )
        
        # Better error handling
        if response.status_code == 401:
            error_msg = f"PayPal authentication failed (401). Check your CLIENT_ID and CLIENT_SECRET. API Base: {settings.PAYPAL_API_BASE}"
            log.error(error_msg)
            log.error(f"Client ID present: {bool(settings.PAYPAL_CLIENT_ID)}, Secret present: {bool(settings.PAYPAL_CLIENT_SECRET)}")
            raise ValueError(error_msg)
        
        response.raise_for_status()
        return response.json()["access_token"]
    except requests.exceptions.RequestException as e:
        error_msg = f"PayPal API request failed: {e}"
        log.error(error_msg)
        if hasattr(e, 'response') and e.response is not None:
            log.error(f"Response status: {e.response.status_code}, Response body: {e.response.text}")
        raise ValueError(error_msg)
    except Exception as e:
        log.error(f"Failed to get PayPal access token: {e}")
        raise


def create_paypal_order(amount, currency="USD", plan_id=None, return_url=None, cancel_url=None):
    """
    Create a PayPal order.
    
    Args:
        amount: Decimal amount
        currency: Currency code (default: USD)
        plan_id: Plan ID for metadata
        return_url: URL to redirect after successful payment
        cancel_url: URL to redirect if user cancels
    
    Returns:
        dict: PayPal order response
    """
    access_token = get_paypal_access_token()
    
    order_data = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "amount": {
                "currency_code": currency,
                "value": str(amount)
            }
        }]
    }
    
    # Add return URLs if provided
    if return_url or cancel_url:
        order_data["application_context"] = {}
        if return_url:
            order_data["application_context"]["return_url"] = return_url
        if cancel_url:
            order_data["application_context"]["cancel_url"] = cancel_url
        order_data["application_context"]["brand_name"] = "NeuroMed Aira"
        order_data["application_context"]["landing_page"] = "BILLING"
        order_data["application_context"]["user_action"] = "PAY_NOW"
    
    # Add metadata if plan_id provided
    if plan_id:
        order_data["purchase_units"][0]["custom_id"] = plan_id
        order_data["purchase_units"][0]["description"] = f"NeuroMed Aira {plan_id.capitalize()} Plan"
    
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        if plan_id:
            headers["PayPal-Request-Id"] = f"order-{plan_id}-{int(timezone.now().timestamp())}"
        
        response = requests.post(
            f"{settings.PAYPAL_API_BASE}/v2/checkout/orders",
            headers=headers,
            json=order_data,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log.error(f"Failed to create PayPal order: {e}")
        if hasattr(e, 'response') and e.response is not None:
            log.error(f"PayPal API response: {e.response.text}")
        raise


def capture_paypal_order(order_id):
    """
    Capture a PayPal order after user approval.
    
    Args:
        order_id: PayPal order ID
    
    Returns:
        dict: PayPal capture response
    """
    access_token = get_paypal_access_token()
    
    # First, check the order status to see if it's already captured
    try:
        order_details = get_paypal_order_details(order_id)
        order_status = order_details.get('status')
        
        # If already completed, return the existing data
        if order_status == 'COMPLETED':
            log.info(f"Order {order_id} already completed, returning existing data")
            return order_details
        
        # If not APPROVED, we can't capture it
        if order_status != 'APPROVED':
            error_msg = f"Cannot capture order {order_id}. Current status: {order_status}. Order must be APPROVED to capture."
            log.error(error_msg)
            raise ValueError(error_msg)
    except ValueError:
        raise
    except Exception as e:
        log.warning(f"Could not check order status before capture: {e}, proceeding with capture attempt")
    
    try:
        response = requests.post(
            f"{settings.PAYPAL_API_BASE}/v2/checkout/orders/{order_id}/capture",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            timeout=10,
        )
        
        # Better error handling for 422
        if response.status_code == 422:
            error_data = response.json() if response.text else {}
            error_msg = error_data.get('message', 'Order cannot be captured')
            details = error_data.get('details', [])
            
            # Check for specific error types
            is_instrument_declined = any(
                d.get('issue') == 'INSTRUMENT_DECLINED' 
                for d in details if isinstance(d, dict)
            )
            is_already_captured = (
                'already been captured' in error_msg.lower() or 
                any('captured' in str(d).lower() for d in details)
            )
            
            # If instrument declined, this is a payment failure - don't retry
            if is_instrument_declined:
                log.warning(f"PayPal payment declined for order {order_id}: {error_msg}")
                raise ValueError(f"Payment declined: The payment method was declined. Please try a different payment method.")
            
            # If already captured, try to get the order details
            if is_already_captured:
                try:
                    return get_paypal_order_details(order_id)
                except:
                    pass
            
            log.error(f"PayPal capture failed (422): {error_msg}, Details: {details}")
            raise ValueError(f"Order capture failed: {error_msg}")
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 422:
            error_data = e.response.json() if e.response.text else {}
            error_msg = error_data.get('message', 'Order cannot be captured')
            log.error(f"PayPal capture 422 error: {error_msg}, Full response: {e.response.text}")
            raise ValueError(f"Order capture failed: {error_msg}")
        raise
    except Exception as e:
        log.error(f"Failed to capture PayPal order: {e}")
        raise


def get_paypal_order_details(order_id):
    """Get details of a PayPal order."""
    access_token = get_paypal_access_token()
    
    try:
        response = requests.get(
            f"{settings.PAYPAL_API_BASE}/v2/checkout/orders/{order_id}",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log.error(f"Failed to get PayPal order details: {e}")
        raise


def verify_paypal_webhook(headers, body, webhook_id=None):
    """
    Verify PayPal webhook signature.
    Note: This is a simplified version. For production, implement full webhook verification.
    """
    # TODO: Implement full webhook verification using PayPal's webhook verification API
    # For now, we'll rely on HTTPS and webhook ID matching
    if webhook_id and settings.PAYPAL_WEBHOOK_ID:
        return webhook_id == settings.PAYPAL_WEBHOOK_ID
    return True  # In development, allow all webhooks


# =============================
# Plan Helpers
# =============================

def get_plan_price(plan_id):
    """Get price for a plan."""
    plan = settings.SUBSCRIPTION_PLANS.get(plan_id)
    if plan:
        return plan.get("price")
    return None


def get_plan_display(plan_id):
    """Get display information for a plan."""
    plan = settings.SUBSCRIPTION_PLANS.get(plan_id)
    if not plan:
        return None
    
    price = plan.get("price")
    if price is None:
        return f"{plan['name']} — Custom"
    
    if plan_id == "monthly":
        return f"{plan['name']} — ${price:.2f} / month"
    elif plan_id == "annual":
        return f"{plan['name']} — ${price:.2f} / year"
    
    return plan['name']

