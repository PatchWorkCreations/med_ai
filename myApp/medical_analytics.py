"""
Medical AI Analytics - Comprehensive metrics for NeuroMed Aira usage
This module calculates all medical AI-specific analytics.
"""
from django.db.models import Count, Sum, Q, Avg, Max, Min, F
from django.utils import timezone
from datetime import timedelta, datetime
from .models import (
    MedicalSummary, Profile, ChatSession, BetaFeedback,
    Org, OrgMembership, Patient, Encounter
)
from django.contrib.auth import get_user_model
import json

User = get_user_model()


def get_medical_analytics(start_date, end_date, prev_start_date=None, prev_end_date=None, comparison_enabled=False):
    """
    Calculate all medical AI analytics metrics.
    Returns a comprehensive context dictionary.
    """
    # Convert dates to datetime for proper filtering
    start_datetime = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
    end_datetime = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))
    
    # ========== MEDICAL SUMMARY ANALYTICS ==========
    summary_qs = MedicalSummary.objects.filter(created_at__gte=start_datetime, created_at__lte=end_datetime)
    
    # Volume over time
    total_summaries = summary_qs.count()
    summaries_per_user = summary_qs.values('user').annotate(count=Count('id')).order_by('-count')
    
    # Care setting mix
    care_setting_breakdown = summary_qs.values('care_setting').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Tone usage
    tone_breakdown = summary_qs.values('tone').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Tone by care setting
    tone_by_care_setting = {}
    for care in ['hospital', 'ambulatory', 'urgent']:
        care_summaries = summary_qs.filter(care_setting=care)
        tone_by_care_setting[care] = list(care_summaries.values('tone').annotate(
            count=Count('id')
        ).order_by('-count')[:5])
    
    # Content depth (raw_text vs summary length)
    # Calculate manually for better performance
    raw_lengths = []
    summary_lengths = []
    for summary in summary_qs[:1000]:  # Sample for performance
        raw_lengths.append(len(summary.raw_text))
        summary_lengths.append(len(summary.summary))
    
    content_stats = {
        'avg_raw_length': sum(raw_lengths) / len(raw_lengths) if raw_lengths else 0,
        'avg_summary_length': sum(summary_lengths) / len(summary_lengths) if summary_lengths else 0,
        'max_raw_length': max(raw_lengths) if raw_lengths else 0,
        'max_summary_length': max(summary_lengths) if summary_lengths else 0,
        'sample_size': len(raw_lengths)
    }
    
    # Daily summaries for trend
    daily_summaries = []
    current_date = start_date
    while current_date <= end_date:
        day_count = MedicalSummary.objects.filter(created_at__date=current_date).count()
        daily_summaries.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'date_display': current_date.strftime('%b %d'),
            'count': day_count
        })
        current_date += timedelta(days=1)
    
    # Top users (power users)
    top_users = summary_qs.values('user__username', 'user__email').annotate(
        summary_count=Count('id')
    ).order_by('-summary_count')[:10]
    
    # ========== PROFILE ANALYTICS ==========
    profile_qs = Profile.objects.filter(user__date_joined__date__gte=start_date, user__date_joined__date__lte=end_date)
    
    # User segments by profession
    profession_breakdown = profile_qs.exclude(profession='').exclude(profession__isnull=True).values('profession').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Profile completeness
    total_profiles = Profile.objects.count()
    profiles_with_display_name = Profile.objects.exclude(display_name='').exclude(display_name__isnull=True).count()
    profile_completeness = (profiles_with_display_name / total_profiles * 100) if total_profiles > 0 else 0
    
    # Language preferences
    language_breakdown = profile_qs.values('language').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Top languages
    top_languages = language_breakdown[:10]
    
    # Geo + IP info
    signup_countries = profile_qs.exclude(signup_country='').exclude(signup_country__isnull=True).values('signup_country').annotate(
        count=Count('id')
    ).order_by('-count')[:20]
    
    last_login_countries = Profile.objects.exclude(last_login_country='').exclude(last_login_country__isnull=True).values('last_login_country').annotate(
        count=Count('id')
    ).order_by('-count')[:20]
    
    # IP anomaly detection (multiple signups from same IP)
    ip_anomalies = profile_qs.exclude(signup_ip__isnull=True).values('signup_ip').annotate(
        count=Count('id')
    ).filter(count__gt=3).order_by('-count')[:10]
    
    # ========== CHAT SESSION ANALYTICS ==========
    chat_qs = ChatSession.objects.filter(created_at__gte=start_datetime, created_at__lte=end_datetime)
    
    # Session volume
    total_chat_sessions = chat_qs.count()
    sessions_per_user = chat_qs.values('user').annotate(count=Count('id')).order_by('-count')
    
    # Active users (users with sessions in period)
    active_chat_users = chat_qs.values('user').distinct().count()
    
    # Active users in last 7/30 days
    last_7_days = timezone.now() - timedelta(days=7)
    last_30_days = timezone.now() - timedelta(days=30)
    active_users_7d = ChatSession.objects.filter(created_at__gte=last_7_days).values('user').distinct().count()
    active_users_30d = ChatSession.objects.filter(created_at__gte=last_30_days).values('user').distinct().count()
    
    # Session metadata
    # Title patterns
    title_patterns = chat_qs.exclude(title='').values('title').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Tone distribution
    chat_tone_breakdown = chat_qs.values('tone').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Language used in chats
    chat_lang_breakdown = chat_qs.values('lang').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Lifecycle metrics
    # Average session duration (updated_at - created_at)
    avg_session_duration = chat_qs.annotate(
        duration_seconds=F('updated_at') - F('created_at')
    ).aggregate(avg_duration=Avg('duration_seconds'))['avg_duration']
    
    # Messages analysis
    total_messages = 0
    user_messages = 0
    assistant_messages = 0
    sessions_with_errors = 0
    
    for session in chat_qs[:1000]:  # Sample for performance
        messages = session.messages or []
        total_messages += len(messages)
        for msg in messages:
            if msg.get('role') == 'user':
                user_messages += 1
            elif msg.get('role') == 'assistant':
                assistant_messages += 1
            if msg.get('meta', {}).get('error'):
                sessions_with_errors += 1
                break
    
    avg_messages_per_session = (total_messages / total_chat_sessions) if total_chat_sessions > 0 else 0
    message_ratio = (user_messages / assistant_messages) if assistant_messages > 0 else 0
    
    # Recently archived
    archived_sessions = chat_qs.filter(archived=True).order_by('-updated_at')[:10]
    
    # Daily chat sessions
    daily_chat_sessions = []
    current_date = start_date
    while current_date <= end_date:
        day_count = ChatSession.objects.filter(created_at__date=current_date).count()
        daily_chat_sessions.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'date_display': current_date.strftime('%b %d'),
            'count': day_count
        })
        current_date += timedelta(days=1)
    
    # ========== BETA FEEDBACK ANALYTICS ==========
    feedback_qs = BetaFeedback.objects.filter(created_at__gte=start_datetime, created_at__lte=end_datetime)
    
    # Who is giving feedback
    feedback_by_role = feedback_qs.values('role').annotate(
        count=Count('id')
    ).order_by('-count')
    
    allow_contact_count = feedback_qs.filter(allow_contact=True).count()
    allow_anon_count = feedback_qs.filter(allow_anon=True).count()
    
    # Device and browser
    feedback_device_breakdown = feedback_qs.values('device').annotate(
        count=Count('id')
    ).order_by('-count')
    
    feedback_browser_breakdown = feedback_qs.values('browser').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Use cases
    use_case_breakdown = feedback_qs.values('use_case').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Input types
    input_type_breakdown = feedback_qs.values('input_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Quantitative satisfaction
    satisfaction_metrics = feedback_qs.aggregate(
        avg_ease=Avg('ease'),
        avg_speed=Avg('speed'),
        avg_accuracy=Avg('accuracy'),
        avg_clarity=Avg('clarity'),
        avg_nps=Avg('nps')
    )
    
    # NPS breakdown
    nps_by_role = feedback_qs.values('role').annotate(
        avg_nps=Avg('nps')
    ).order_by('-avg_nps')
    
    nps_by_device = feedback_qs.values('device').annotate(
        avg_nps=Avg('nps')
    ).order_by('-avg_nps')
    
    # Recent feedback
    recent_feedback = feedback_qs.order_by('-created_at')[:10]
    
    # ========== ORG/MULTI-TENANT ANALYTICS ==========
    org_qs = Org.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
    
    # Organizations
    total_orgs = Org.objects.filter(is_active=True).count()
    new_orgs = org_qs.count()
    
    # Theme/plan usage
    theme_breakdown = Org.objects.values('theme').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    plan_breakdown = Org.objects.values('plan').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Memberships & roles
    membership_qs = OrgMembership.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
    total_memberships = OrgMembership.objects.filter(is_active=True).count()
    
    role_breakdown = OrgMembership.objects.filter(is_active=True).values('role').annotate(
        count=Count('id')
    ).order_by('-count')
    
    users_per_org = OrgMembership.objects.filter(is_active=True).values('org').annotate(
        user_count=Count('user', distinct=True)
    ).order_by('-user_count')[:10]
    
    # ========== PATIENT & ENCOUNTER ANALYTICS ==========
    # Note: These are org-scoped, so we'll get all orgs
    patient_qs = Patient.all_objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
    encounter_qs = Encounter.all_objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
    
    # Patient registry
    total_patients = Patient.all_objects.count()
    new_patients = patient_qs.count()
    
    # Encounter pipeline
    encounter_by_status = encounter_qs.values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Priority breakdown
    encounter_by_priority = encounter_qs.values('priority').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Most common reasons
    top_reasons = encounter_qs.values('reason').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # ICD/CPT analytics
    icd_codes = {}
    cpt_codes = {}
    denial_reasons = {}
    
    for encounter in encounter_qs[:1000]:  # Sample for performance
        # ICD codes
        if encounter.icd:
            for code in encounter.icd:
                code_str = code.get('code', '') if isinstance(code, dict) else str(code)
                icd_codes[code_str] = icd_codes.get(code_str, 0) + 1
        
        # CPT codes
        if encounter.cpt:
            for code in encounter.cpt:
                code_str = code.get('code', '') if isinstance(code, dict) else str(code)
                cpt_codes[code_str] = cpt_codes.get(code_str, 0) + 1
        
        # Denial reasons
        if encounter.denials:
            for denial in encounter.denials:
                reason = denial.get('reason', '') if isinstance(denial, dict) else str(denial)
                denial_reasons[reason] = denial_reasons.get(reason, 0) + 1
    
    top_icd_codes = sorted(icd_codes.items(), key=lambda x: x[1], reverse=True)[:10]
    top_cpt_codes = sorted(cpt_codes.items(), key=lambda x: x[1], reverse=True)[:10]
    top_denial_reasons = sorted(denial_reasons.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Ops metrics - time from new to closed
    closed_encounters = encounter_qs.filter(status='closed')
    avg_time_to_close = None
    if closed_encounters.exists():
        time_diffs = []
        for enc in closed_encounters[:100]:  # Sample
            # Approximate - would need updated_at field for accuracy
            time_diffs.append(0)  # Placeholder
        # avg_time_to_close = sum(time_diffs) / len(time_diffs) if time_diffs else 0
    
    # ========== BUILD CONTEXT ==========
    context = {
        # Medical Summary
        'total_summaries': total_summaries,
        'summaries_per_user': list(summaries_per_user),
        'care_setting_breakdown': list(care_setting_breakdown),
        'tone_breakdown': list(tone_breakdown),
        'tone_by_care_setting': tone_by_care_setting,
        'content_stats': content_stats,
        'daily_summaries': daily_summaries,
        'top_summary_users': list(top_users),
        
        # Profile
        'profession_breakdown': list(profession_breakdown),
        'profile_completeness': round(profile_completeness, 2),
        'language_breakdown': list(language_breakdown),
        'top_languages': list(top_languages),
        'signup_countries': list(signup_countries),
        'last_login_countries': list(last_login_countries),
        'ip_anomalies': list(ip_anomalies),
        
        # Chat Session
        'total_chat_sessions': total_chat_sessions,
        'sessions_per_user': list(sessions_per_user),
        'active_chat_users': active_chat_users,
        'active_users_7d': active_users_7d,
        'active_users_30d': active_users_30d,
        'title_patterns': list(title_patterns),
        'chat_tone_breakdown': list(chat_tone_breakdown),
        'chat_lang_breakdown': list(chat_lang_breakdown),
        'avg_chat_duration': avg_session_duration.total_seconds() if avg_session_duration else 0,
        'avg_messages_per_session': round(avg_messages_per_session, 2),
        'message_ratio': round(message_ratio, 2),
        'sessions_with_errors': sessions_with_errors,
        'archived_sessions': list(archived_sessions),
        'daily_chat_sessions': daily_chat_sessions,
        
        # Beta Feedback
        'feedback_by_role': list(feedback_by_role),
        'allow_contact_count': allow_contact_count,
        'allow_anon_count': allow_anon_count,
        'feedback_device_breakdown': list(feedback_device_breakdown),
        'feedback_browser_breakdown': list(feedback_browser_breakdown),
        'use_case_breakdown': list(use_case_breakdown),
        'input_type_breakdown': list(input_type_breakdown),
        'satisfaction_metrics': satisfaction_metrics,
        'nps_by_role': list(nps_by_role),
        'nps_by_device': list(nps_by_device),
        'recent_feedback': list(recent_feedback),
        
        # Org/Multi-tenant
        'total_orgs': total_orgs,
        'new_orgs': new_orgs,
        'theme_breakdown': list(theme_breakdown),
        'plan_breakdown': list(plan_breakdown),
        'total_memberships': total_memberships,
        'role_breakdown': list(role_breakdown),
        'users_per_org': list(users_per_org),
        
        # Patient & Encounter
        'total_patients': total_patients,
        'new_patients': new_patients,
        'encounter_by_status': list(encounter_by_status),
        'encounter_by_priority': list(encounter_by_priority),
        'top_reasons': list(top_reasons),
        'top_icd_codes': top_icd_codes,
        'top_cpt_codes': top_cpt_codes,
        'top_denial_reasons': top_denial_reasons,
    }
    
    return context

