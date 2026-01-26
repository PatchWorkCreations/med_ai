"""
Adaptive Response System - Preference Inference Module

This module implements invisible preference inference and adaptive response strategies.
It learns how to speak in the moment, not who the user is.

CRITICAL PRINCIPLES:
- Modes are internal only (never exposed)
- No ML in v1 (rule-based, deterministic)
- No content personalization (only style)
- No user configuration (inferred silently)
- Single LLM pass (zero added latency)
- Medical safety rails remain absolute
"""

from typing import Dict, List, Optional
import re
from collections import Counter


class SignalExtractor:
    """Extracts behavioral signals from user interactions"""
    
    # Distress keywords (emotional support signal)
    DISTRESS_KEYWORDS = [
        'worried', 'scared', 'anxious', 'fear', 'panic', 'stress',
        'overwhelmed', 'confused', 'helpless', 'urgent', 'emergency'
    ]
    
    # Technical terms (technical depth signal)
    TECHNICAL_TERMS = [
        'diagnosis', 'pathology', 'etiology', 'symptomatology',
        'differential', 'prognosis', 'pathophysiology', 'biomarker'
    ]
    
    # Simplification requests (technical depth signal)
    SIMPLIFICATION_REQUESTS = [
        'simpler', 'explain', 'what does', 'what is', 'what means',
        'plain english', 'layman', 'simple terms', 'dumb down'
    ]
    
    @staticmethod
    def extract_message_length_signal(user_message: str) -> float:
        """Returns normalized message length (0-1)"""
        word_count = len(user_message.split())
        # Normalize: <10 words = 0.0, >50 words = 1.0
        return min(1.0, max(0.0, (word_count - 10) / 40))
    
    @staticmethod
    def extract_vocabulary_complexity(user_message: str) -> float:
        """Analyzes vocabulary complexity"""
        words = user_message.lower().split()
        if not words:
            return 0.5
        
        # Count technical terms
        technical_count = sum(1 for word in words if any(term in word for term in SignalExtractor.TECHNICAL_TERMS))
        # Count simplification requests
        simplification_count = sum(1 for word in words if any(req in word for req in SignalExtractor.SIMPLIFICATION_REQUESTS))
        
        # Technical terms increase complexity, simplification requests decrease
        complexity = (technical_count * 0.3) - (simplification_count * 0.5)
        return max(0.0, min(1.0, 0.5 + complexity))
    
    @staticmethod
    def extract_emotional_signal(user_message: str) -> float:
        """Detects emotional distress indicators"""
        message_lower = user_message.lower()
        distress_count = sum(1 for keyword in SignalExtractor.DISTRESS_KEYWORDS if keyword in message_lower)
        
        # Normalize: 0 keywords = 0.0, 2+ keywords = 1.0
        return min(1.0, distress_count / 2.0)
    
    @staticmethod
    def extract_structure_preference_signal(has_files: bool, message_length: int) -> float:
        """Infers preference for structured vs. freeform responses"""
        # Files suggest preference for structured/guided responses
        if has_files:
            return 0.8  # High structure preference
        
        # Long messages might prefer freeform
        if message_length > 30:
            return 0.3  # Lower structure preference
        
        return 0.5  # Neutral
    
    @staticmethod
    def extract_all_signals(user_message: str, has_files: bool, conversation_history: List[Dict]) -> Dict[str, float]:
        """Extracts all signals from current interaction"""
        message_length = len(user_message.split())
        
        # Follow-up frequency (from conversation history)
        follow_up_count = len([m for m in conversation_history if m.get('role') == 'user'])
        follow_up_signal = min(1.0, follow_up_count / 5.0)  # 5+ follow-ups = high verbosity preference
        
        return {
            'message_length': SignalExtractor.extract_message_length_signal(user_message),
            'vocabulary_complexity': SignalExtractor.extract_vocabulary_complexity(user_message),
            'emotional_support': SignalExtractor.extract_emotional_signal(user_message),
            'structure_preference': SignalExtractor.extract_structure_preference_signal(has_files, message_length),
            'follow_up_frequency': follow_up_signal,
        }


class PreferenceInference:
    """Deterministic rule-based preference inference"""
    
    SMOOTHING_FACTOR = 0.2  # How much new signal affects existing profile
    
    @staticmethod
    def update_profile(profile, signals: Dict[str, float], topic_changed: bool = False):
        """
        Updates profile using weighted average (smoothing).
        
        CRITICAL: Profiles are context-sensitive, not identity-defining.
        Apply soft decay on topic change to respect that humans aren't consistent.
        """
        from .models import InteractionProfile
        
        # Verbosity inference
        if signals.get('message_length', 0.5) < 0.3:  # Short messages
            verbosity_signal = 0.2  # Low verbosity
        elif signals.get('follow_up_frequency', 0) > 0.6:  # Many follow-ups
            verbosity_signal = 0.8  # High verbosity
        else:
            verbosity_signal = 0.5  # Medium
        
        # Emotional support inference
        emotional_signal = signals.get('emotional_support', 0.5)
        
        # Technical depth inference
        if signals.get('vocabulary_complexity', 0.5) > 0.7:
            technical_signal = 0.8  # High technical depth
        elif signals.get('vocabulary_complexity', 0.5) < 0.3:
            technical_signal = 0.2  # Low technical depth
        else:
            technical_signal = 0.5
        
        # Structure preference
        structure_signal = signals.get('structure_preference', 0.5)
        
        # Apply topic change decay (context reset)
        # A user can be technical about labs but want simplicity when anxious
        # This keeps Aira feeling alive, not opinionated
        if topic_changed:
            # Soft decay on context-dependent dimensions
            profile.technical_depth *= 0.7  # Reset toward neutral
            profile.structure_preference *= 0.7  # Reset toward neutral
            # Keep emotional support and verbosity (more stable preferences)
        
        # Apply weighted average (smoothing)
        profile.verbosity_level = (profile.verbosity_level * (1 - PreferenceInference.SMOOTHING_FACTOR)) + \
                                  (verbosity_signal * PreferenceInference.SMOOTHING_FACTOR)
        
        profile.emotional_support = (profile.emotional_support * (1 - PreferenceInference.SMOOTHING_FACTOR)) + \
                                     (emotional_signal * PreferenceInference.SMOOTHING_FACTOR)
        
        profile.technical_depth = (profile.technical_depth * (1 - PreferenceInference.SMOOTHING_FACTOR)) + \
                                   (technical_signal * PreferenceInference.SMOOTHING_FACTOR)
        
        profile.structure_preference = (profile.structure_preference * (1 - PreferenceInference.SMOOTHING_FACTOR)) + \
                                        (structure_signal * PreferenceInference.SMOOTHING_FACTOR)
        
        profile.interaction_count += 1
        profile.save()
        
        return profile
    
    @staticmethod
    def get_default_profile(user=None, session_id=None):
        """Returns default profile (neutral preferences)"""
        from .models import InteractionProfile
        
        profile, _ = InteractionProfile.objects.get_or_create(
            user=user if user and user.is_authenticated else None,
            session_id=session_id if not (user and user.is_authenticated) else None,
            defaults={
                'verbosity_level': 0.5,
                'emotional_support': 0.5,
                'structure_preference': 0.5,
                'technical_depth': 0.5,
                'response_pacing': 0.5,
            }
        )
        return profile


class ResponseStrategyResolver:
    """
    Maps InteractionProfile to internal response strategies.
    
    CRITICAL: This does NOT override mode classification (_classify_mode).
    It only biases presentation within the active mode.
    """
    
    @staticmethod
    def resolve_strategies(profile, current_tone: str) -> Dict[str, str]:
        """
        Resolves which internal strategies to apply.
        
        CRITICAL: Adaptive verbosity never overrides _classify_mode().
        It only affects sentence density, bullet count, and explanation depth within the selected mode.
        """
        
        strategies = {
            'verbosity_bias': 'MEDIUM',  # LOW, MEDIUM, HIGH - NOT modes, just bias
            'style_modifiers': [],  # List of style instructions
        }
        
        # Verbosity → Bias (NOT mode override)
        if profile.verbosity_level < 0.3:
            strategies['verbosity_bias'] = 'LOW'
            strategies['style_modifiers'].append('Use concise sentences')
            strategies['style_modifiers'].append('Minimize bullet points')
        elif profile.verbosity_level > 0.7:
            strategies['verbosity_bias'] = 'HIGH'
            strategies['style_modifiers'].append('Provide more detailed explanations')
            strategies['style_modifiers'].append('Include additional context when helpful')
        else:
            strategies['verbosity_bias'] = 'MEDIUM'
        
        # Emotional Support → Additive Warmth (NOT tone override)
        # Emotional warmth is layered, never swapped.
        # EmotionalSupport tone remains explicit user intent.
        # Adaptive emotional signals may: validate feelings, soften phrasing, add reassurance
        # They may NOT: introduce coping frameworks, change medical framing, escalate reassurance beyond safety rails
        if profile.emotional_support > 0.7 and current_tone != 'EmotionalSupport':
            # High emotional need detected, but user hasn't selected EmotionalSupport tone
            # We can inject emotional warmth without changing tone
            strategies['style_modifiers'].append('Acknowledge emotions explicitly when appropriate')
            strategies['style_modifiers'].append('Use warm, validating language')
            strategies['style_modifiers'].append('Add gentle reassurance without changing medical content')
        
        # Technical Depth → Language Level
        if profile.technical_depth < 0.3:
            strategies['style_modifiers'].append('Use simple, everyday language')
            strategies['style_modifiers'].append('Avoid medical jargon unless necessary')
        elif profile.technical_depth > 0.7:
            strategies['style_modifiers'].append('Use precise medical terminology when appropriate')
            strategies['style_modifiers'].append('Include clinical context when relevant')
        
        # Structure Preference → Response Format
        if profile.structure_preference > 0.7:
            strategies['style_modifiers'].append('Structure responses with clear sections')
            strategies['style_modifiers'].append('Use bullet points for actionable items')
        elif profile.structure_preference < 0.3:
            strategies['style_modifiers'].append('Use conversational, freeform responses')
            strategies['style_modifiers'].append('Avoid excessive structure or lists')
        
        return strategies
