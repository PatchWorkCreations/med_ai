"""
Billing views for PayPal subscription management.
"""
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
import json
import logging

from .models import Profile, Subscription, Payment
from .billing_utils import (
    get_user_plan,
    is_subscription_active,
    get_plan_price,
    get_plan_display,
    create_paypal_order,
    capture_paypal_order,
    get_paypal_order_details,
    verify_paypal_webhook,
)
from datetime import timedelta

log = logging.getLogger(__name__)


# =============================
# Billing Settings Page
# =============================

@login_required
def billing_settings(request):
    """Display billing settings page."""
    # Check if this is a PayPal return (with token and PayerID)
    token = request.GET.get('token')
    payer_id = request.GET.get('PayerID')
    
    # If PayPal returned with token, capture the order
    if token and payer_id:
        try:
            # Check if payment already exists for this order
            existing_payment = Payment.objects.filter(paypal_order_id=token).first()
            if existing_payment and existing_payment.status == 'completed':
                log.info(f"Payment for order {token} already exists and is completed")
                # Payment already processed, skip capture but still update subscription if needed
                capture_data = None
            else:
                # First check if order is already captured
                order_details = get_paypal_order_details(token)
                order_status = order_details.get('status')
                
                # If already completed, use existing data
                if order_status == 'COMPLETED':
                    capture_data = order_details
                elif order_status == 'APPROVED':
                    # Capture the order
                    try:
                        capture_data = capture_paypal_order(token)
                    except ValueError as e:
                        error_str = str(e)
                        # If payment declined, don't try to get order details
                        if 'Payment declined' in error_str or 'INSTRUMENT_DECLINED' in error_str:
                            log.warning(f"Payment declined for {token}: {e}")
                            capture_data = None
                        else:
                            # If capture fails for other reasons (e.g., already captured), try to get order details
                            log.warning(f"Capture failed for {token}: {e}, trying to get order details")
                            try:
                                capture_data = get_paypal_order_details(token)
                                if capture_data.get('status') != 'COMPLETED':
                                    capture_data = None
                            except:
                                capture_data = None
                else:
                    log.warning(f"Order {token} is in status {order_status}, cannot capture")
                    capture_data = None
            
            if capture_data and capture_data.get('status') == 'COMPLETED':
                # Get plan from session
                plan_id = request.session.get('pending_plan_id', 'monthly')
                
                # Calculate subscription end date
                from datetime import timedelta
                if plan_id == 'monthly':
                    period_end = timezone.now() + timedelta(days=30)
                elif plan_id == 'annual':
                    period_end = timezone.now() + timedelta(days=365)
                else:
                    period_end = None
                
                # Update user profile
                profile = request.user.profile
                profile.plan = plan_id
                profile.subscription_status = 'active'
                profile.subscription_ends_at = period_end
                if capture_data.get('payer', {}).get('payer_id'):
                    profile.paypal_customer_id = capture_data['payer']['payer_id']
                profile.save()
                
                # Create or update subscription
                subscription, created = Subscription.objects.get_or_create(
                    user=request.user,
                    defaults={
                        'plan': plan_id,
                        'status': 'active',
                        'current_period_end': period_end,
                    }
                )
                if not created:
                    subscription.plan = plan_id
                    subscription.status = 'active'
                    subscription.current_period_end = period_end
                    subscription.save()
                
                # Create payment record (only if it doesn't exist)
                if not Payment.objects.filter(paypal_order_id=token).exists():
                    purchase_unit = capture_data.get('purchase_units', [{}])[0]
                    amount = purchase_unit.get('payments', {}).get('captures', [{}])[0]
                    Payment.objects.create(
                        user=request.user,
                        subscription=subscription,
                        paypal_order_id=token,
                        paypal_transaction_id=amount.get('id'),
                        amount=float(amount.get('amount', {}).get('value', 0)),
                        currency=amount.get('amount', {}).get('currency_code', 'USD'),
                        status='completed',
                        plan_id=plan_id,
                        paid_at=timezone.now(),
                    )
                
                # Clear session
                if 'pending_order_id' in request.session:
                    del request.session['pending_order_id']
                if 'pending_plan_id' in request.session:
                    del request.session['pending_plan_id']
                request.session.modified = True
        except Exception as e:
            log.error(f"Error capturing PayPal order on return: {e}")
            # Continue to show page even if capture fails
    
    profile = request.user.profile
    current_plan = get_user_plan(request.user)
    is_active = is_subscription_active(request.user)
    
    # Get current subscription if exists
    subscription = Subscription.objects.filter(
        user=request.user,
        status__in=['active', 'past_due']
    ).first()
    
    # Get payment history
    payments = Payment.objects.filter(user=request.user).order_by('-created_at')[:10]
    
    # Check for payment error message
    payment_error = request.session.pop('payment_error', None)
    payment_success = request.GET.get('payment') == 'success' and not payment_error
    
    context = {
        'current_plan': current_plan,
        'current_plan_display': get_plan_display(current_plan),
        'is_active': is_active,
        'subscription': subscription,
        'subscription_ends_at': profile.subscription_ends_at,
        'payments': payments,
        'payment_error': payment_error,
        'payment_success': payment_success,
        'PAYPAL_CLIENT_ID': settings.PAYPAL_CLIENT_ID,
        'plans': {
            'monthly': {
                'id': 'monthly',
                'name': 'Monthly',
                'price': 1.00,  # Testing: $1 instead of $20
                'display': get_plan_display('monthly'),
            },
            'annual': {
                'id': 'annual',
                'name': 'Annual',
                'price': 199.00,
                'display': get_plan_display('annual'),
            },
            'clinical': {
                'id': 'clinical',
                'name': 'Clinical',
                'display': get_plan_display('clinical'),
            },
        },
    }
    
    return render(request, 'myApp/billing_settings.html', context)


# =============================
# API Endpoints
# =============================

@login_required
@require_http_methods(["GET"])
def subscription_status(request):
    """Get current subscription status."""
    profile = request.user.profile
    current_plan = get_user_plan(request.user)
    is_active = is_subscription_active(request.user)
    
    subscription = Subscription.objects.filter(
        user=request.user,
        status__in=['active', 'past_due']
    ).first()
    
    return JsonResponse({
        'plan': current_plan,
        'plan_display': get_plan_display(current_plan),
        'status': profile.subscription_status,
        'is_active': is_active,
        'subscription_ends_at': profile.subscription_ends_at.isoformat() if profile.subscription_ends_at else None,
        'subscription_id': subscription.paypal_subscription_id if subscription else None,
    })


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def create_checkout_session(request):
    """
    Create a PayPal checkout order.
    
    Request body: {"plan_id": "monthly" | "annual"}
    """
    try:
        data = json.loads(request.body)
        plan_id = data.get("plan_id")
        
        if plan_id not in ["monthly", "annual"]:
            return JsonResponse({"error": "Invalid plan_id"}, status=400)
        
        # Get plan price
        price = get_plan_price(plan_id)
        if price is None:
            return JsonResponse({"error": "Plan not found"}, status=404)
        
        # Check if PayPal is configured
        if not settings.PAYPAL_CLIENT_ID or not settings.PAYPAL_CLIENT_SECRET:
            return JsonResponse({
                "error": "PayPal is not configured. Please contact support.",
                "detail": "PayPal credentials are missing"
            }, status=503)
        
        # Build return URLs (PayPal doesn't support placeholders - use actual URLs)
        from django.urls import reverse
        base_url = request.build_absolute_uri('/').rstrip('/')
        return_url = f"{base_url}{reverse('billing_settings')}?payment=success"
        cancel_url = f"{base_url}{reverse('billing_settings')}?payment=cancelled"
        
        # Create PayPal order
        try:
            order = create_paypal_order(
                amount=price, 
                currency="USD", 
                plan_id=plan_id,
                return_url=return_url,
                cancel_url=cancel_url
            )
        except ValueError as e:
            # Handle configuration errors
            return JsonResponse({
                "error": str(e),
                "detail": "PayPal configuration error"
            }, status=503)
        
        # Store order ID in session for later reference
        request.session['pending_order_id'] = order['id']
        request.session['pending_plan_id'] = plan_id
        request.session.modified = True
        
        # Find approval link
        approval_url = None
        for link in order.get('links', []):
            if link.get('rel') == 'approve':
                approval_url = link.get('href')
                break
        
        if not approval_url:
            return JsonResponse({"error": "No approval URL found"}, status=500)
        
        return JsonResponse({
            "checkout_url": approval_url,
            "order_id": order['id'],
        })
    
    except Exception as e:
        log.error(f"Error creating checkout session: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def capture_order(request):
    """
    Capture PayPal order after user approval.
    
    Request body: {"orderID": "paypal_order_id"}
    """
    try:
        data = json.loads(request.body)
        order_id = data.get("orderID")
        
        if not order_id:
            return JsonResponse({"error": "orderID required"}, status=400)
        
        # Check order status first
        try:
            order_details = get_paypal_order_details(order_id)
            order_status = order_details.get('status')
            
            # If already completed, use existing data
            if order_status == 'COMPLETED':
                capture_data = order_details
            elif order_status == 'APPROVED':
                # Capture the order
                try:
                    capture_data = capture_paypal_order(order_id)
                except ValueError as e:
                    error_str = str(e)
                    # If payment declined, return user-friendly error
                    if 'Payment declined' in error_str or 'INSTRUMENT_DECLINED' in error_str:
                        return JsonResponse({
                            "error": "Payment Declined",
                            "message": "Your payment method was declined. Please try a different payment method or contact your bank.",
                            "details": str(e)
                        }, status=402)  # 402 Payment Required
                    else:
                        # Other errors (like already captured)
                        return JsonResponse({
                            "error": str(e),
                            "details": "Order may already be captured or there was an issue processing the payment"
                        }, status=400)
            else:
                return JsonResponse({
                    "error": f"Order is in status {order_status}. Cannot capture.",
                    "details": order_details
                }, status=400)
        except ValueError as e:
            # Handle capture errors
            error_str = str(e)
            if 'Payment declined' in error_str or 'INSTRUMENT_DECLINED' in error_str:
                return JsonResponse({
                    "error": "Payment Declined",
                    "message": "Your payment method was declined. Please try a different payment method or contact your bank.",
                    "details": str(e)
                }, status=402)
            else:
                return JsonResponse({
                    "error": str(e),
                    "details": "Order may already be captured"
                }, status=400)
        
        # Check if capture was successful
        status = capture_data.get('status')
        if status not in ['COMPLETED', 'APPROVED']:
            log.error(f"PayPal capture failed. Status: {status}, Response: {capture_data}")
            return JsonResponse({
                "error": f"Payment not completed. Status: {status}",
                "details": capture_data
            }, status=400)
        
        # Get order details
        order_details = get_paypal_order_details(order_id)
        
        # Extract payment information
        purchase_unit = capture_data.get('purchase_units', [{}])[0]
        amount = purchase_unit.get('payments', {}).get('captures', [{}])[0]
        payer = capture_data.get('payer', {})
        
        # Get plan from session or order metadata
        plan_id = request.session.get('pending_plan_id', 'monthly')
        
        # Calculate subscription end date
        if plan_id == 'monthly':
            period_end = timezone.now() + timedelta(days=30)
        elif plan_id == 'annual':
            period_end = timezone.now() + timedelta(days=365)
        else:
            period_end = None
        
        # Update user profile
        profile = request.user.profile
        profile.plan = plan_id
        profile.subscription_status = 'active'
        profile.subscription_ends_at = period_end
        if payer.get('payer_id'):
            profile.paypal_customer_id = payer['payer_id']
        profile.save()
        
        # Create or update subscription
        subscription, created = Subscription.objects.get_or_create(
            user=request.user,
            defaults={
                'plan': plan_id,
                'status': 'active',
                'current_period_end': period_end,
            }
        )
        if not created:
            subscription.plan = plan_id
            subscription.status = 'active'
            subscription.current_period_end = period_end
            subscription.save()
        
        # Create payment record (only if it doesn't exist)
        payment, created = Payment.objects.get_or_create(
            paypal_order_id=order_id,
            defaults={
                'user': request.user,
                'subscription': subscription,
                'paypal_transaction_id': amount.get('id'),
                'amount': float(amount.get('amount', {}).get('value', 0)),
                'currency': amount.get('amount', {}).get('currency_code', 'USD'),
                'status': 'completed',
                'plan_id': plan_id,
                'paid_at': timezone.now(),
            }
        )
        
        # If payment already existed, update it
        if not created and payment.status != 'completed':
            payment.status = 'completed'
            payment.paid_at = timezone.now()
            payment.save()
        
        # Clear session
        if 'pending_order_id' in request.session:
            del request.session['pending_order_id']
        if 'pending_plan_id' in request.session:
            del request.session['pending_plan_id']
        request.session.modified = True
        
        return JsonResponse({
            "status": "success",
            "message": "Payment completed successfully",
            "order_id": order_id,
            "subscription": {
                "plan": plan_id,
                "status": "active",
                "ends_at": period_end.isoformat() if period_end else None,
            }
        })
    
    except Exception as e:
        log.error(f"Error capturing order: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def paypal_webhook(request):
    """
    Handle PayPal webhook events.
    
    Events handled:
    - PAYMENT.CAPTURE.COMPLETED
    - PAYMENT.CAPTURE.DENIED
    - BILLING.SUBSCRIPTION.CANCELLED
    - BILLING.SUBSCRIPTION.EXPIRED
    """
    try:
        # Get webhook headers
        webhook_id = request.headers.get('Paypal-Webhook-Id')
        webhook_signature = request.headers.get('Paypal-Transmission-Sig')
        
        # Verify webhook (simplified - implement full verification in production)
        # For now, we'll process the webhook
        
        body = json.loads(request.body)
        event_type = body.get('event_type')
        
        log.info(f"PayPal webhook received: {event_type}")
        
        # Handle different event types
        if event_type == 'PAYMENT.CAPTURE.COMPLETED':
            # Payment was captured successfully
            resource = body.get('resource', {})
            order_id = resource.get('supplementary_data', {}).get('related_ids', {}).get('order_id')
            
            if order_id:
                payment = Payment.objects.filter(paypal_order_id=order_id).first()
                if payment and payment.status != 'completed':
                    payment.status = 'completed'
                    payment.paid_at = timezone.now()
                    payment.save()
        
        elif event_type == 'PAYMENT.CAPTURE.DENIED':
            # Payment was denied
            resource = body.get('resource', {})
            order_id = resource.get('supplementary_data', {}).get('related_ids', {}).get('order_id')
            
            if order_id:
                payment = Payment.objects.filter(paypal_order_id=order_id).first()
                if payment:
                    payment.status = 'failed'
                    payment.save()
        
        elif event_type == 'BILLING.SUBSCRIPTION.CANCELLED':
            # Subscription was cancelled
            resource = body.get('resource', {})
            subscription_id = resource.get('id')
            
            if subscription_id:
                subscription = Subscription.objects.filter(paypal_subscription_id=subscription_id).first()
                if subscription:
                    subscription.status = 'canceled'
                    subscription.save()
                    
                    # Update user profile
                    profile = subscription.user.profile
                    profile.subscription_status = 'canceled'
                    profile.save()
        
        elif event_type == 'BILLING.SUBSCRIPTION.EXPIRED':
            # Subscription expired
            resource = body.get('resource', {})
            subscription_id = resource.get('id')
            
            if subscription_id:
                subscription = Subscription.objects.filter(paypal_subscription_id=subscription_id).first()
                if subscription:
                    subscription.status = 'inactive'
                    subscription.save()
                    
                    # Update user profile
                    profile = subscription.user.profile
                    profile.subscription_status = 'inactive'
                    profile.plan = 'free'
                    profile.save()
        
        return JsonResponse({"status": "ok"})
    
    except Exception as e:
        log.error(f"Error processing PayPal webhook: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def billing_history(request):
    """Get billing/payment history."""
    payments = Payment.objects.filter(user=request.user).order_by('-created_at')
    
    history = []
    for payment in payments:
        history.append({
            'id': payment.id,
            'amount': float(payment.amount),
            'currency': payment.currency,
            'status': payment.status,
            'plan_id': payment.plan_id,
            'created_at': payment.created_at.isoformat(),
            'paid_at': payment.paid_at.isoformat() if payment.paid_at else None,
            'order_id': payment.paypal_order_id,
        })
    
    return JsonResponse({'payments': history})


@login_required
@require_http_methods(["POST"])
def cancel_subscription(request):
    """
    Cancel user's subscription.
    Note: Subscription remains active until end of billing period.
    """
    try:
        subscription = Subscription.objects.filter(
            user=request.user,
            status='active'
        ).first()
        
        if not subscription:
            return JsonResponse({"error": "No active subscription found"}, status=404)
        
        # Mark as canceled (will remain active until period_end)
        subscription.status = 'canceled'
        subscription.save()
        
        # Update profile
        profile = request.user.profile
        profile.subscription_status = 'canceled'
        profile.save()
        
        # TODO: Cancel PayPal subscription if paypal_subscription_id exists
        # For one-time payments, we just mark as canceled
        
        return JsonResponse({
            "status": "success",
            "message": "Subscription canceled. Access will continue until the end of the billing period.",
            "ends_at": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
        })
    
    except Exception as e:
        log.error(f"Error canceling subscription: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def contact_clinical(request):
    """Handle clinical plan contact request and send email."""
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        company = data.get('company', '').strip()
        phone = data.get('phone', '').strip()
        message = data.get('message', '').strip()
        
        # Validate required fields
        if not name or not email or not message:
            return JsonResponse({
                "error": "Name, email, and message are required"
            }, status=400)
        
        # Get user info
        user = request.user
        user_email = user.email
        user_name = user.get_full_name() or user.username
        
        # Prepare email content
        from .emailer import send_via_resend
        
        # Email to sales team
        email_subject = f"Clinical Plan Inquiry from {name}"
        email_body = f"""
New Clinical Plan Inquiry

Contact Information:
- Name: {name}
- Email: {email}
- Phone: {phone or 'Not provided'}
- Company: {company or 'Not provided'}

User Account:
- User: {user_name} ({user_email})
- User ID: {user.id}

Message:
{message}

---
This inquiry was submitted through the billing settings page.
"""
        
        # Send email to sales team
        sales_email = getattr(settings, 'CLINICAL_SALES_EMAIL', 'sales@neuromedai.org')
        email_sent = send_via_resend(
            to=sales_email,
            subject=email_subject,
            text=email_body,
            reply_to=email,  # Allow direct reply to the inquirer
        )
        
        if not email_sent:
            log.error(f"Failed to send clinical plan inquiry email for user {user.id}")
            return JsonResponse({
                "error": "Failed to send email. Please try again or contact us directly."
            }, status=500)
        
        # Send confirmation email to user
        confirmation_subject = "Thank you for your Clinical Plan inquiry"
        confirmation_body = f"""
Hi {name},

Thank you for your interest in our Clinical Plan. We've received your inquiry and our team will get back to you within 24-48 hours.

Your inquiry details:
- Company: {company or 'Not provided'}
- Message: {message[:200]}{'...' if len(message) > 200 else ''}

If you have any urgent questions, please feel free to contact us directly at {sales_email}.

Best regards,
NeuroMed Aira Team
"""
        
        send_via_resend(
            to=email,
            subject=confirmation_subject,
            text=confirmation_body,
        )
        
        return JsonResponse({
            "status": "success",
            "message": "Your inquiry has been sent successfully. We'll get back to you soon!"
        })
    
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        log.error(f"Error processing clinical plan contact: {e}")
        return JsonResponse({
            "error": "An error occurred. Please try again or contact us directly."
        }, status=500)

