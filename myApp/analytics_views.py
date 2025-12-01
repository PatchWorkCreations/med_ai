"""
Comprehensive analytics calculations for the redesigned dashboard.
This module contains helper functions to calculate all analytics metrics.
"""
from django.db.models import Count, Sum, Q, Avg, Max, Min
from django.utils import timezone
from datetime import timedelta, datetime
from .models import Visitor, UserSignup, UserSignin, PageView, Session, Event
from .analytics_utils import categorize_referer
from .medical_analytics import get_medical_analytics
from django.contrib.auth import get_user_model
import json

User = get_user_model()


def calculate_percentage_change(current, previous):
    """Calculate percentage change between two values"""
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return ((current - previous) / previous) * 100


def get_analytics_data(request, start_date, end_date, prev_start_date=None, prev_end_date=None, comparison_enabled=False):
    """
    Calculate all analytics metrics for the given date range.
    Returns a comprehensive context dictionary.
    """
    # Convert dates to datetime for proper filtering
    start_datetime = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
    end_datetime = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))
    
    # Base querysets for current period
    visitor_qs = Visitor.objects.filter(created_at__gte=start_datetime, created_at__lte=end_datetime)
    pageview_qs = PageView.objects.filter(created_at__gte=start_datetime, created_at__lte=end_datetime)
    signup_qs = UserSignup.objects.filter(created_at__gte=start_datetime, created_at__lte=end_datetime)
    signin_qs = UserSignin.objects.filter(created_at__gte=start_datetime, created_at__lte=end_datetime)
    successful_signin_qs = signin_qs.filter(success=True)
    
    # Previous period querysets (for comparison)
    if comparison_enabled and prev_start_date and prev_end_date:
        prev_start_datetime = timezone.make_aware(datetime.combine(prev_start_date, datetime.min.time()))
        prev_end_datetime = timezone.make_aware(datetime.combine(prev_end_date, datetime.max.time()))
        prev_visitor_qs = Visitor.objects.filter(created_at__gte=prev_start_datetime, created_at__lte=prev_end_datetime)
        prev_pageview_qs = PageView.objects.filter(created_at__gte=prev_start_datetime, created_at__lte=prev_end_datetime)
        prev_signup_qs = UserSignup.objects.filter(created_at__gte=prev_start_datetime, created_at__lte=prev_end_datetime)
        prev_signin_qs = UserSignin.objects.filter(created_at__gte=prev_start_datetime, created_at__lte=prev_end_datetime, success=True)
    else:
        prev_visitor_qs = None
        prev_pageview_qs = None
        prev_signup_qs = None
        prev_signin_qs = None
    
    # ========== SUMMARY CARDS ==========
    # Visitors
    unique_visitors = visitor_qs.filter(is_unique=True).count()
    total_visitors = visitor_qs.count()
    prev_unique_visitors = prev_visitor_qs.filter(is_unique=True).count() if prev_visitor_qs else 0
    visitors_change = calculate_percentage_change(unique_visitors, prev_unique_visitors) if comparison_enabled else None
    
    # Page Views
    page_views = pageview_qs.count()
    prev_page_views = prev_pageview_qs.count() if prev_pageview_qs else 0
    page_views_change = calculate_percentage_change(page_views, prev_page_views) if comparison_enabled else None
    
    # Signups
    signups = signup_qs.count()
    signups_actual = User.objects.filter(date_joined__date__gte=start_date, date_joined__date__lte=end_date).count()
    prev_signups = prev_signup_qs.count() if prev_signup_qs else 0
    signups_change = calculate_percentage_change(signups, prev_signups) if comparison_enabled else None
    
    # Signins
    signins = successful_signin_qs.count()
    prev_signins = prev_signin_qs.count() if prev_signin_qs else 0
    signins_change = calculate_percentage_change(signins, prev_signins) if comparison_enabled else None
    
    # Active Users (DAU - Daily Active Users)
    active_users = UserSignin.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
        success=True
    ).values('user').distinct().count()
    
    # Conversion Rate
    conversion_rate = (signups / unique_visitors * 100) if unique_visitors > 0 else 0
    
    # ========== TIME SERIES DATA ==========
    # Generate daily data points
    daily_stats = []
    current_date = start_date
    while current_date <= end_date:
        day_visitors = Visitor.objects.filter(created_at__date=current_date, is_unique=True).count()
        day_pageviews = PageView.objects.filter(created_at__date=current_date).count()
        day_signups = UserSignup.objects.filter(created_at__date=current_date).count()
        day_signins = UserSignin.objects.filter(created_at__date=current_date, success=True).count()
        
        daily_stats.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'date_display': current_date.strftime('%b %d'),
            'visitors': day_visitors,
            'page_views': day_pageviews,
            'signups': day_signups,
            'signins': day_signins,
        })
        current_date += timedelta(days=1)
    
    # Previous period daily stats (for comparison)
    prev_daily_stats = []
    if comparison_enabled and prev_start_date and prev_end_date:
        current_date = prev_start_date
        while current_date <= prev_end_date:
            day_visitors = Visitor.objects.filter(created_at__date=current_date, is_unique=True).count()
            day_pageviews = PageView.objects.filter(created_at__date=current_date).count()
            day_signups = UserSignup.objects.filter(created_at__date=current_date).count()
            day_signins = UserSignin.objects.filter(created_at__date=current_date, success=True).count()
            
            prev_daily_stats.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'visitors': day_visitors,
                'page_views': day_pageviews,
                'signups': day_signups,
                'signins': day_signins,
            })
            current_date += timedelta(days=1)
    
    # ========== DEVICE/BROWSER/OS BREAKDOWN ==========
    device_breakdown = visitor_qs.values('device_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    browser_breakdown = visitor_qs.exclude(browser='').values('browser').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    os_breakdown = visitor_qs.exclude(os='').values('os').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # ========== GEOGRAPHIC DATA ==========
    country_breakdown = visitor_qs.exclude(country='').values('country').annotate(
        count=Count('id')
    ).order_by('-count')[:20]
    
    # ========== TRAFFIC SOURCES ==========
    # Categorize referers (more efficient approach)
    traffic_sources = {}
    
    # Get all referers at once
    referers = visitor_qs.exclude(referer='').values_list('referer', flat=True)
    for referer in referers:
        source = categorize_referer(referer)
        traffic_sources[source] = traffic_sources.get(source, 0) + 1
    
    # Direct traffic
    direct_count = visitor_qs.filter(Q(referer='') | Q(referer__isnull=True)).count()
    if direct_count > 0:
        traffic_sources['direct'] = direct_count
    
    traffic_sources_list = [{'source': k, 'count': v} for k, v in sorted(traffic_sources.items(), key=lambda x: x[1], reverse=True)]
    
    # Top referrers
    top_referrers = visitor_qs.exclude(referer='').values('referer').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # ========== POPULAR PAGES ==========
    popular_pages = pageview_qs.values('path').annotate(
        views=Count('id')
    ).order_by('-views')[:15]
    
    # Entry pages
    entry_pages = pageview_qs.filter(entry_page=True).values('path').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Exit pages
    exit_pages = pageview_qs.filter(exit_page=True).values('path').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # ========== SESSION ANALYTICS ==========
    session_qs = Session.objects.filter(started_at__date__gte=start_date, started_at__date__lte=end_date)
    total_sessions = session_qs.count()
    avg_session_duration = session_qs.aggregate(avg=Avg('duration'))['avg'] or 0
    avg_pages_per_session = session_qs.aggregate(avg=Avg('page_count'))['avg'] or 0
    bounce_rate = (session_qs.filter(is_bounce=True).count() / total_sessions * 100) if total_sessions > 0 else 0
    
    # Returning vs New visitors
    returning_visitors = visitor_qs.filter(is_unique=False).count()
    new_visitors = unique_visitors
    
    # ========== CONVERSION FUNNEL ==========
    funnel_visitors = unique_visitors
    funnel_signups = signups
    funnel_logins = signins
    
    visitor_to_signup_rate = (funnel_signups / funnel_visitors * 100) if funnel_visitors > 0 else 0
    signup_to_login_rate = (funnel_logins / funnel_signups * 100) if funnel_signups > 0 else 0
    overall_conversion_rate = (funnel_logins / funnel_visitors * 100) if funnel_visitors > 0 else 0
    
    # ========== HOURLY ACTIVITY ==========
    hourly_activity = []
    for hour in range(24):
        hour_visitors = visitor_qs.filter(created_at__hour=hour).count()
        hourly_activity.append({
            'hour': hour,
            'hour_display': f"{hour:02d}:00",
            'visitors': hour_visitors
        })
    
    # ========== USER LIST ==========
    # Get all users with their activity stats
    from .models import Profile
    all_users = User.objects.select_related('profile').annotate(
        total_summaries=Count('summaries', distinct=True),
        total_chat_sessions=Count('chatsession', distinct=True),
        total_signins=Count('signin_records', filter=Q(signin_records__success=True), distinct=True),
        last_signin=Max('signin_records__created_at', filter=Q(signin_records__success=True))
    ).order_by('-date_joined')
    
    # Add activity stats for each user
    user_list = []
    for user in all_users:
        profile = getattr(user, 'profile', None)
        user_list.append({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name or '',
            'last_name': user.last_name or '',
            'display_name': profile.display_name if profile else '',
            'profession': profile.profession if profile else '',
            'language': profile.language if profile else 'en-US',
            'signup_date': user.date_joined,
            'last_login': user.last_login,
            'last_signin': user.last_signin,
            'is_active': user.is_active,
            'is_staff': user.is_staff,
            'signup_ip': profile.signup_ip if profile else None,
            'signup_country': profile.signup_country if profile else None,
            'last_login_ip': profile.last_login_ip if profile else None,
            'last_login_country': profile.last_login_country if profile else None,
            'total_summaries': user.total_summaries or 0,
            'total_chat_sessions': user.total_chat_sessions or 0,
            'total_signins': user.total_signins or 0,
        })
    
    # ========== RECENT ACTIVITY ==========
    recent_visitors = visitor_qs.order_by('-created_at')[:20]
    recent_signups = signup_qs.select_related('user').order_by('-created_at')[:10]
    recent_signins = successful_signin_qs.select_related('user').order_by('-created_at')[:20]
    
    # ========== SECURITY METRICS ==========
    failed_logins = signin_qs.filter(success=False).count()
    failed_logins_today = UserSignin.objects.filter(
        created_at__date=timezone.now().date(),
        success=False
    ).count()
    
    # ========== UTM CAMPAIGNS ==========
    utm_campaigns = visitor_qs.exclude(utm_campaign='').values('utm_campaign', 'utm_source', 'utm_medium').annotate(
        visitors=Count('id', distinct=True)
    ).order_by('-visitors')[:10]
    
    # Add pageview counts for campaigns
    for campaign in utm_campaigns:
        campaign_visitors = visitor_qs.filter(
            utm_campaign=campaign['utm_campaign'],
            utm_source=campaign['utm_source'],
            utm_medium=campaign['utm_medium']
        )
        campaign['pageviews'] = pageview_qs.filter(visitor__in=campaign_visitors).count()
    
    # ========== TODAY'S SUMMARY (for daily reports) ==========
    today = timezone.now().date()
    today_visitors = Visitor.objects.filter(created_at__date=today, is_unique=True).count()
    today_pageviews = PageView.objects.filter(created_at__date=today).count()
    today_signups = UserSignup.objects.filter(created_at__date=today).count()
    today_signins = UserSignin.objects.filter(created_at__date=today, success=True).count()
    today_top_pages = PageView.objects.filter(created_at__date=today).values('path').annotate(
        views=Count('id')
    ).order_by('-views')[:5]
    today_traffic_sources = {}
    for visitor in Visitor.objects.filter(created_at__date=today).exclude(referer=''):
        source = categorize_referer(visitor.referer)
        today_traffic_sources[source] = today_traffic_sources.get(source, 0) + 1
    
    # ========== MEDICAL AI ANALYTICS ==========
    medical_context = get_medical_analytics(
        start_date, end_date, prev_start_date, prev_end_date, comparison_enabled
    )
    
    # ========== BUILD CONTEXT ==========
    context = {
        # Date range info
        'start_date': start_date,
        'end_date': end_date,
        'period_days': (end_date - start_date).days + 1,
        'comparison_enabled': comparison_enabled,
        
        # Summary Cards
        'unique_visitors': unique_visitors,
        'total_visitors': total_visitors,
        'visitors_change': visitors_change,
        'page_views': page_views,
        'page_views_change': page_views_change,
        'signups': signups,
        'signups_actual': signups_actual,
        'signups_change': signups_change,
        'signins': signins,
        'signins_change': signins_change,
        'active_users': active_users,
        'conversion_rate': round(conversion_rate, 2),
        
        # Time Series
        'daily_stats': daily_stats,
        'prev_daily_stats': prev_daily_stats if comparison_enabled else [],
        
        # Breakdowns
        'device_breakdown': list(device_breakdown),
        'browser_breakdown': list(browser_breakdown),
        'os_breakdown': list(os_breakdown),
        'country_breakdown': list(country_breakdown),
        'traffic_sources': traffic_sources_list,
        'top_referrers': list(top_referrers),
        
        # Pages
        'popular_pages': list(popular_pages),
        'entry_pages': list(entry_pages),
        'exit_pages': list(exit_pages),
        
        # Session Analytics
        'total_sessions': total_sessions,
        'avg_session_duration': round(avg_session_duration, 1),
        'avg_pages_per_session': round(avg_pages_per_session, 1),
        'bounce_rate': round(bounce_rate, 2),
        'returning_visitors': returning_visitors,
        'new_visitors': new_visitors,
        
        # Conversion Funnel
        'funnel_visitors': funnel_visitors,
        'funnel_signups': funnel_signups,
        'funnel_logins': funnel_logins,
        'visitor_to_signup_rate': round(visitor_to_signup_rate, 2),
        'signup_to_login_rate': round(signup_to_login_rate, 2),
        'overall_conversion_rate': round(overall_conversion_rate, 2),
        
        # Hourly Activity
        'hourly_activity': hourly_activity,
        
        # Recent Activity
        'recent_visitors': recent_visitors,
        'recent_signups': recent_signups,
        'recent_signins': recent_signins,
        
        # Security
        'failed_logins': failed_logins,
        'failed_logins_today': failed_logins_today,
        
        # Campaigns
        'utm_campaigns': list(utm_campaigns),
        
        # Today's Summary (for daily reports)
        'today_visitors': today_visitors,
        'today_pageviews': today_pageviews,
        'today_signups': today_signups,
        'today_signins': today_signins,
        'today_top_pages': list(today_top_pages),
        'today_traffic_sources': today_traffic_sources,
        
        # User List
        'user_list': user_list,
        'total_users': len(user_list),
    }
    
    # Merge medical analytics into main context
    context.update(medical_context)
    
    return context

