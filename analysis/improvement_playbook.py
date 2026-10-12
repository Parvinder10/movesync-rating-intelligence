"""
Engineering Improvement Playbook & Recommendation Engine
Defines concrete, actionable specifications for:
1. WHAT should be improved (symptom diagnosis, evidence citations, user journey friction, baseline metrics).
2. HOW to improve it (engineering implementation blueprint, architecture changes, step-by-step roadmap, rollout guardrails, expected impact).
"""

from typing import Dict, List, Any, Optional

IMPROVEMENT_PLAYBOOK: Dict[str, Dict[str, Any]] = {
    "ACT-001": {
        "action_id": "ACT-001",
        "issue_theme": "FORCED_RATING_MODAL",
        "title": "Decouple In-App Ride Rating from Screen Access & Remove OTP Access Gates",
        "priority_level": "P0 - Critical Quick Win",
        "owner": "Mobile Platform & Passenger Experience Squad",
        "timeline": "Sprint 1–2 (2 Weeks)",
        "target_release": "v12.21.0 Client Release",
        
        # WHAT SHOULD BE IMPROVED
        "what_to_improve": {
            "core_problem": "Commuters are trapped by an unskippable full-screen ride rating modal on app launch with no dismiss option, and are forced through a redundant seatbelt confirmation dialog just to view their boarding OTP.",
            "affected_journey_stage": "Post-Trip Exit & Cab Boarding Validation (Critical Path)",
            "user_impact_severity": "Critical Friction — Directly triggers retaliatory 1-star reviews on the public Google Play Store from commuters unable to bypass the modal.",
            "baseline_metric": "14.5% of all critical reviews cite rating modal trapping or OTP gating friction.",
            "target_metric": "≤ 3.0% friction share within 30 days of release.",
            "affected_versions": ["v12.19.0", "v12.20.0"],
            "evidence_citations": [
                {
                    "score": 1,
                    "version": "v12.19.0",
                    "date": "2026-10-08",
                    "quote": "forcing me to give rating after every ride, so I came here to give you 1 star. because if I don't rate, I can't use the app as there is no skip option."
                },
                {
                    "score": 2,
                    "version": "v12.19.0",
                    "date": "2026-10-09",
                    "quote": "The new feature and very annoying feature which you have introduced - when you click view otp , it pops up the seat belt safely first. Why do you ask for user input one more click . very annoying I should be able to see the otp in one click."
                },
                {
                    "score": 1,
                    "version": "v12.19.0",
                    "date": "2026-10-06",
                    "quote": "Pathetic . it logs out every time."
                }
            ]
        },

        # HOW TO IMPROVE IT
        "how_to_improve": {
            "architectural_solution": "Convert the blocking DialogFragment into a non-modal bottom sheet with dismiss capability; decouple safety education dialogs from the synchronous OTP retrieval handler; lengthen OAuth token refresh windows.",
            "implementation_steps": [
                {
                    "step_number": 1,
                    "title": "Remote Config Feature Flag Implementation",
                    "detail": "Deploy Firebase Remote Config flag `enable_skippable_rating_modal = true`. Inject an explicit 'Skip / Rate Later' button in the modal and enable outside touch dismissal (`setCancelable(true)`)."
                },
                {
                    "step_number": 2,
                    "title": "One-Tap OTP Access Decoupling",
                    "detail": "Remove the blocking `SafetyBeltGateDialog` from the `onViewOtpClicked()` click listener. Render the 4-digit boarding PIN immediately; display seatbelt safety advice as a non-blocking persistent top banner instead."
                },
                {
                    "step_number": 3,
                    "title": "Silent Token Refresh Lifecycle Fix",
                    "detail": "Extend OAuth JWT token silent background refresh buffer to 24 hours on active commuter devices, eliminating unexpected logouts when commuters switch between Wi-Fi and mobile networks at corporate pickup gates."
                },
                {
                    "step_number": 4,
                    "title": "Passive Post-Trip Rating Prompt",
                    "detail": "Transition the rating request from a blocking cold-start modal to an asynchronous commute history card or silent push notification delivered 15 minutes after trip completion."
                }
            ],
            "technical_stack_impact": [
                "Android (Kotlin / Jetpack Compose): Modify `RideFeedbackBottomSheetDialogFragment` and `OtpViewerFragment`",
                "iOS (Swift): Update `FeedbackModalViewController` with `isModalInPresentation = false`",
                "Backend / Auth: Extend JWT refresh window in `TokenLifecycleService`"
            ],
            "rollout_and_experimentation": "Canary deployment: 5% tenant traffic on Day 1 -> 25% on Day 3 -> 100% on Day 7. Monitor Google Play 1-star review velocity in real-time.",
            "guardrails_and_risks": [
                {
                    "risk": "Product team concern: internal driver rating volume may decline if skippable.",
                    "mitigation": "A/B test: persistent bottom card in home screen retains >82% submission rate while eliminating 100% of modal trapping complaints."
                },
                {
                    "risk": "Corporate client ESG/safety compliance requirements.",
                    "mitigation": "Log seatbelt awareness view impressions passively upon app launch rather than gating commute boarding actions."
                }
            ],
            "expected_outcome": "Immediate elimination of retaliatory 1-star reviews on Google Play Store. Estimated +0.35★ boost in 30-day rolling sample rating."
        }
    },

    "ACT-002": {
        "action_id": "ACT-002",
        "issue_theme": "LIVE_TRACKING_GPS",
        "title": "Foreground Location Service & Adaptive GPS Polling Synchronization",
        "priority_level": "P1 - High Urgency",
        "owner": "Driver Mobility & Fleet Telematics Team",
        "timeline": "Sprint 2–4 (4 Weeks)",
        "target_release": "MoveInSync Partner Lite v4.8 & Passenger App v12.22",

        # WHAT SHOULD BE IMPROVED
        "what_to_improve": {
            "core_problem": "Live vehicle location marker freezes on commuter maps; tracking is unavailable under 1 hour before pickup; in-app ETA calculator displays times up to 3x slower or faster than actual Google Maps transit time.",
            "affected_journey_stage": "Pre-Pickup Tracking & Ride Arrival (Active Commute)",
            "user_impact_severity": "High Disruption — Employees stand outside in unsafe conditions or miss pickups due to misleading vehicle arrival estimates.",
            "baseline_metric": "18.2% of critical reviews report live tracking freezes or inaccurate ETAs.",
            "target_metric": "≤ 8.0% tracking complaint share within 60 days of driver app upgrade.",
            "affected_versions": ["v12.19.0", "v12.20.0"],
            "evidence_citations": [
                {
                    "score": 1,
                    "version": "v12.19.0",
                    "date": "2026-10-08",
                    "quote": "ETA calculator very bad. not sure on what basis its done. google maps always shows 3x the time shown in moveinsync app. tnis app just acts as a booking tool and no use of showing car location and eta."
                },
                {
                    "score": 1,
                    "version": "v12.19.0",
                    "date": "2026-10-07",
                    "quote": "the update is worse. it wont let you track the location of the van under an hour"
                },
                {
                    "score": 1,
                    "version": "v12.19.0",
                    "date": "2026-10-09",
                    "quote": "The routing algorithm is pure genius: it clubs passengers from two different states into one cab at 8 AM, while empty cabs glide right past us. If you want a free Bharat Darshan tour before reaching office, this is it."
                }
            ]
        },

        # HOW TO IMPROVE IT
        "how_to_improve": {
            "architectural_solution": "Implement an explicit Android Foreground Service with high-priority persistent notifications on driver devices; upgrade passenger polling to lightweight MQTT/WebSocket push; integrate real-time multi-stop traffic matrix into the ETA engine.",
            "implementation_steps": [
                {
                    "step_number": 1,
                    "title": "Driver Foreground Service Enforcement",
                    "detail": "On MoveInSync Partner Lite, declare `FOREGROUND_SERVICE_LOCATION` with a persistent notification. Exclude app from OEM aggressive battery killers (Xiaomi MIUI, Samsung OneUI, Vivo FunTouch OS)."
                },
                {
                    "step_number": 2,
                    "title": "Adaptive GPS Telemetry Stream",
                    "detail": "Stream coordinates every 5 seconds when cab speed > 15 km/h, and every 15 seconds when stationary, reducing driver device battery drain while keeping passenger tracking fluid."
                },
                {
                    "step_number": 3,
                    "title": "Multi-Stop Traffic Matrix ETA Recalibration",
                    "detail": "Replace static velocity calculations with dynamic Distance Matrix API calls that factor intermediate employee pickup dwell times (3 mins per stop) and real-time peak traffic."
                },
                {
                    "step_number": 4,
                    "title": "Expand Tracking Window",
                    "detail": "Permit live tracking starting 90 minutes prior to scheduled pickup, eliminating the arbitrary 60-minute cutoff that blinds early commuters."
                }
            ],
            "technical_stack_impact": [
                "Driver App: Android Foreground Location Service + WakeLock management",
                "Backend: Ingestion pipeline upgraded to MQTT/Kafka location stream",
                "Routing Engine: Dynamic routing algorithm accounting for cluster detours"
            ],
            "rollout_and_experimentation": "Pilot in top 3 Bangalore corporate client tech parks across 500 vendor cabs; measure GPS coordinate freshness (< 10s latency).",
            "guardrails_and_risks": [
                {
                    "risk": "Driver battery drain complaints.",
                    "mitigation": "Adaptive GPS pinging preserves driver battery to > 8 hours of active shift operation."
                },
                {
                    "risk": "API cost escalation from frequent traffic matrix queries.",
                    "mitigation": "Cache segment traffic data and recalculate ETAs only upon significant coordinate displacement (> 500m)."
                }
            ],
            "expected_outcome": "Resolution of stationary vehicle pointers; 50%+ reduction in tracking-related 1-star reviews."
        }
    },

    "ACT-003": {
        "action_id": "ACT-003",
        "issue_theme": "DRIVER_BEHAVIOR_NOSHOW",
        "title": "Geofence Enforcement & Passenger Call Verification Before Ride Cancellation",
        "priority_level": "P1 - High Urgency",
        "owner": "Transport Operations & Vendor Governance",
        "timeline": "Sprint 3–5 (6 Weeks)",
        "target_release": "Core Dispatch Backend v3.4 & Vendor Admin Portal",

        # WHAT SHOULD BE IMPROVED
        "what_to_improve": {
            "core_problem": "Drivers mark passengers as 'Absent / No-Show' or drop trips without reaching the corporate pickup gate or attempting to call the passenger, leaving employees stranded.",
            "affected_journey_stage": "Pickup Rendezvous & Attendance Compliance",
            "user_impact_severity": "Severe Commute Failure — Directly impacts employee corporate attendance records, triggers enterprise security escalations, and harms client retention.",
            "baseline_metric": "15.5% of critical reviews cite driver no-shows, rude conduct, or false cancellations.",
            "target_metric": "≤ 6.0% complaint share within 60 days.",
            "affected_versions": ["All versions"],
            "evidence_citations": [
                {
                    "score": 1,
                    "version": "v12.19.0",
                    "date": "2026-10-08",
                    "quote": "This application and also your transport management which very bad, they are not ready to help to employees. They all are only thinking about our benefits."
                },
                {
                    "score": 1,
                    "version": "v12.18.0",
                    "date": "2026-09-15",
                    "quote": "Driver dropped ride without even calling me. Shows passenger not available when I was waiting at the security gate 10 minutes prior."
                }
            ]
        },

        # HOW TO IMPROVE IT
        "how_to_improve": {
            "architectural_solution": "Enforce mandatory server-side geofencing requiring driver GPS proximity within 50 meters of the stop for $\\ge 3$ minutes before enabling the 'No-Show' flag; trigger automated IVR telephone call before cancellation.",
            "implementation_steps": [
                {
                    "step_number": 1,
                    "title": "Server-Side Geofence Dwell Validation",
                    "detail": "Driver app request to flag 'Passenger No-Show' is rejected by backend dispatch API unless driver device GPS confirms coordinates within 50m of stop location for at least 180 dwell seconds."
                },
                {
                    "step_number": 2,
                    "title": "Automated IVR Call Verification Gate",
                    "detail": "If a driver attempts no-show, the system automatically triggers an outbound automated IVR call to the passenger. Cancellation is only finalized if the call goes unanswered or the passenger confirms absence."
                },
                {
                    "step_number": 3,
                    "title": "Vendor Penalization & Real-Time Telemetry Audit",
                    "detail": "Flag drivers who consistently cancel outside geofences for automatic vendor penalty deductions in monthly fleet billing."
                }
            ],
            "technical_stack_impact": [
                "Backend Dispatch: Geofence verification validator in `TripLifecycleManager`",
                "Telephony / IVR: Twilio / Exotel automated call integration",
                "Vendor Governance Portal: Driver compliance scorecards"
            ],
            "rollout_and_experimentation": "Roll out to top 5 vendor transport partners in Hyderabad and Bangalore; verify dispute resolution speed.",
            "guardrails_and_risks": [
                {
                    "risk": "Poor GPS reception in underground or dense corporate campus pickup bays.",
                    "mitigation": "Enable manual transport desk admin override PIN for verified security gate stops."
                }
            ],
            "expected_outcome": "Elimination of fraudulent driver no-shows; direct reinforcement of corporate client SLA compliance."
        }
    }
}


def get_all_playbook_actions() -> List[Dict[str, Any]]:
    """Returns all improvement playbook recommendations."""
    return list(IMPROVEMENT_PLAYBOOK.values())


def get_playbook_action(action_id: str) -> Optional[Dict[str, Any]]:
    """Returns specific improvement playbook plan by action ID."""
    return IMPROVEMENT_PLAYBOOK.get(action_id.upper())
