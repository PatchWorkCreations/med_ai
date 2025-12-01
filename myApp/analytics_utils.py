"""
Analytics utility functions for parsing user agents, IPs, and URLs
"""
import re
from urllib.parse import urlparse, parse_qs


def parse_user_agent(user_agent_string):
    """
    Parse user agent string to extract device type, browser, and OS.
    Returns dict with device_type, browser, os.
    """
    if not user_agent_string:
        return {'device_type': 'other', 'browser': 'Unknown', 'os': 'Unknown'}
    
    ua = user_agent_string.lower()
    result = {
        'device_type': 'desktop',
        'browser': 'Unknown',
        'os': 'Unknown'
    }
    
    # Detect device type
    if any(x in ua for x in ['mobile', 'android', 'iphone', 'ipod', 'blackberry', 'windows phone']):
        if 'tablet' in ua or 'ipad' in ua:
            result['device_type'] = 'tablet'
        else:
            result['device_type'] = 'mobile'
    elif 'tablet' in ua or 'ipad' in ua:
        result['device_type'] = 'tablet'
    else:
        result['device_type'] = 'desktop'
    
    # Detect browser
    if 'chrome' in ua and 'edg' not in ua:
        result['browser'] = 'Chrome'
    elif 'firefox' in ua:
        result['browser'] = 'Firefox'
    elif 'safari' in ua and 'chrome' not in ua:
        result['browser'] = 'Safari'
    elif 'edg' in ua or 'edge' in ua:
        result['browser'] = 'Edge'
    elif 'opera' in ua or 'opr' in ua:
        result['browser'] = 'Opera'
    elif 'msie' in ua or 'trident' in ua:
        result['browser'] = 'Internet Explorer'
    elif 'brave' in ua:
        result['browser'] = 'Brave'
    
    # Detect OS
    if 'windows' in ua:
        if 'phone' in ua:
            result['os'] = 'Windows Phone'
        elif 'nt 10' in ua or 'windows 10' in ua:
            result['os'] = 'Windows 10'
        elif 'nt 6.3' in ua:
            result['os'] = 'Windows 8.1'
        elif 'nt 6.2' in ua:
            result['os'] = 'Windows 8'
        elif 'nt 6.1' in ua:
            result['os'] = 'Windows 7'
        else:
            result['os'] = 'Windows'
    elif 'mac' in ua or 'darwin' in ua:
        result['os'] = 'macOS'
    elif 'iphone' in ua or 'ipad' in ua:
        result['os'] = 'iOS'
    elif 'android' in ua:
        result['os'] = 'Android'
    elif 'linux' in ua:
        result['os'] = 'Linux'
    elif 'ubuntu' in ua:
        result['os'] = 'Ubuntu'
    elif 'fedora' in ua:
        result['os'] = 'Fedora'
    
    return result


def parse_utm_params(url):
    """
    Extract UTM parameters from a URL.
    Returns dict with utm_source, utm_medium, utm_campaign, utm_term, utm_content
    """
    if not url:
        return {}
    
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        result = {}
        for key in ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content']:
            if key in params and params[key]:
                result[key] = params[key][0][:100]  # Limit length
        return result
    except Exception:
        return {}


def categorize_referer(referer_url):
    """
    Categorize referer into: direct, search, social, referral, email, other
    """
    if not referer_url:
        return 'direct'
    
    referer_lower = referer_url.lower()
    
    # Search engines
    search_engines = ['google', 'bing', 'yahoo', 'duckduckgo', 'baidu', 'yandex']
    if any(engine in referer_lower for engine in search_engines):
        return 'search'
    
    # Social media
    social_platforms = ['facebook', 'twitter', 'linkedin', 'instagram', 'pinterest', 
                        'reddit', 'youtube', 'tiktok', 'snapchat']
    if any(platform in referer_lower for platform in social_platforms):
        return 'social'
    
    # Email
    if 'mail' in referer_lower or 'email' in referer_lower:
        return 'email'
    
    # If it's a valid URL, it's a referral
    if referer_url.startswith('http'):
        return 'referral'
    
    return 'direct'


def get_country_from_request(request):
    """
    Get country code from request (uses existing middleware country_code if available)
    """
    # Try to get from request attribute (set by CountryMiddleware)
    country = getattr(request, 'country_code', None)
    if country:
        return country
    
    # Fallback: try to get from headers
    for header in ['HTTP_CF_IPCOUNTRY', 'HTTP_CLOUDFRONT_VIEWER_COUNTRY', 
                   'HTTP_X_APPENGINE_COUNTRY', 'HTTP_X_GEO_COUNTRY']:
        val = request.META.get(header)
        if val and len(val) == 2:
            return val.upper()
    
    return None

