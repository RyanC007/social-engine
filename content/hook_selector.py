"""
Hook selector for [YOUR NAME] Social Engine.

Picks the best opening hook from a curated, pre-filled library built on
proven viral frameworks (viral-hooks-master.txt). Every hook is designed to:
  - Position [YOUR NAME] as an authority in AI infrastructure
  - Drive subscribers and customers
  - Work on the specific platform it's assigned to

Usage:
    from content.hook_selector import suggest_hooks, apply_hook

    hooks = suggest_hooks(content_type="post", intent="contrarian")
    final_hook = apply_hook(hooks[0], topic="AI agents", cta="Follow for the playbook")
"""

from dataclasses import dataclass
from typing import Optional
import random

# Client slug constants
CLIENT_RYAN = "your_client_slug"
CLIENT_MARCELA = "your_second_client_slug"


@dataclass
class Hook:
    id: int
    template: str           # fill-in-blank version
    example: str            # pre-filled example for [YOUR NAME]'s AI authority brand
    intent: str             # contrarian | authority | curiosity | results | callout | revelation | social_proof
    best_for: list[str]     # platforms: linkedin | x | instagram | threads | youtube_shorts
    content_type: list[str] # post | article | both


# ─── Curated hooks pre-filled for [YOUR NAME]'s AI authority brand ───────────────────
# Source: viral-hooks-master.txt (1400 hooks)  - best patterns for AI/business niche
# Intent: establish [YOUR NAME] as THE authority on AI infrastructure, drive subs + customers

HOOKS = [
    # CONTRARIAN  - challenge what people believe about AI
    Hook(1,
         "[common practice] is dead. Stop focusing on it for [desired outcome].",
         "Prompting AI is dead. Stop using it as a search engine if you want real business results.",
         "contrarian", ["linkedin", "x"], ["post", "article"]),

    Hook(2,
         "[topic] is overrated. Here's what actually moves the needle.",
         "ChatGPT wrappers are overrated. Here's what actually builds an AI-powered business.",
         "contrarian", ["linkedin", "x", "instagram"], ["post"]),

    Hook(3,
         "99% of [target audience] are doing [topic] wrong. Here's the proof.",
         "99% of business owners are using AI wrong. Here's the proof.",
         "contrarian", ["linkedin", "x", "instagram"], ["post", "article"]),

    Hook(4,
         "Here's why [common advice] is holding you back from [desired outcome].",
         "Here's why 'just use ChatGPT' is holding your business back from real automation.",
         "contrarian", ["linkedin", "x"], ["post", "article"]),

    Hook(5,
         "[industry] do not want you to know this about [topic].",
         "AI consultants do not want you to know how simple real AI infrastructure actually is.",
         "contrarian", ["linkedin", "instagram"], ["post", "article"]),

    Hook(6,
         "Stop [common action] if you want [desired result].",
         "Stop buying AI tools if you want to build a business that actually scales.",
         "contrarian", ["linkedin", "x", "youtube_shorts"], ["post"]),

    # AUTHORITY  - establish [YOUR NAME] as the go-to AI infrastructure expert
    Hook(7,
         "I've spent [time] building AI systems. Here's what [target audience] get wrong.",
         "I've spent years building AI infrastructure. Here's what most business owners get completely wrong.",
         "authority", ["linkedin", "x"], ["post", "article"]),

    Hook(8,
         "My clients pay $[amount] to learn this. Today it's free.",
         "My clients pay thousands to learn this AI infrastructure framework. Today it's free.",
         "authority", ["linkedin", "instagram", "youtube_shorts"], ["post", "article"]),

    Hook(9,
         "[number] things about [niche] I wish I knew earlier.",
         "7 things about building AI infrastructure I wish I knew before wasting 6 months.",
         "authority", ["linkedin", "instagram", "x"], ["post", "article"]),

    Hook(10,
         "I worked in [niche] for [time] and learned these secrets. Here they are.",
         "I've been deep in AI infrastructure for years. Here are the secrets no one talks about.",
         "authority", ["linkedin", "x"], ["post", "article"]),

    Hook(11,
         "[number] AI tools that will save you hundreds of hours of work.",
         "8 AI infrastructure tools that will save your business hundreds of hours every month.",
         "authority", ["linkedin", "instagram", "x"], ["post"]),

    Hook(12,
         "Here's the exact [framework] you need to know as a [target audience].",
         "Here's the exact AI infrastructure framework every business owner needs to know right now.",
         "authority", ["linkedin"], ["article"]),

    # CURIOSITY  - create an irresistible knowledge gap
    Hook(13,
         "Nobody's talking about this, but [topic] is about to change everything.",
         "Nobody's talking about this, but AI agents are about to make most software subscriptions obsolete.",
         "curiosity", ["linkedin", "x", "instagram", "youtube_shorts"], ["post", "article"]),

    Hook(14,
         "Most people don't know this about [topic]. But the ones who do are winning.",
         "Most business owners don't know this about AI infrastructure. The ones who do are pulling ahead fast.",
         "curiosity", ["linkedin", "x"], ["post", "article"]),

    Hook(15,
         "What [industry insiders] don't want you to know about [topic].",
         "What Big Tech doesn't want you to know about building your own AI infrastructure.",
         "curiosity", ["linkedin", "instagram", "youtube_shorts"], ["post", "article"]),

    Hook(16,
         "Here's a secret I learned the hard way about [topic].",
         "Here's a secret I learned the hard way about building AI systems that actually stick.",
         "curiosity", ["linkedin", "x", "instagram"], ["post"]),

    Hook(17,
         "[number] things that feel illegal to know about [topic].",
         "5 things about AI automation that feel illegal to know  - and most businesses still haven't figured out.",
         "curiosity", ["instagram", "x", "youtube_shorts"], ["post"]),

    Hook(18,
         "The most underrated [skill/tool] in [year] isn't what you think.",
         "The most underrated business skill in 2025 isn't prompt engineering. Here's what it actually is.",
         "curiosity", ["linkedin", "x"], ["post", "article"]),

    # RESULTS  - show what's achievable, inspire action
    Hook(19,
         "Here's how I [achieved result] without [common barrier].",
         "Here's how I built a full AI content engine without writing a single line of code.",
         "results", ["linkedin", "instagram", "x", "youtube_shorts"], ["post", "article"]),

    Hook(20,
         "Here's how to [achieve goal] in [time frame]  - even if you're starting from zero.",
         "Here's how to build your first AI skill in 30 minutes  - even if you've never coded before.",
         "results", ["linkedin", "instagram", "x", "youtube_shorts"], ["post", "article"]),

    Hook(21,
         "[desired outcome] is not hard anymore. Here's the playbook.",
         "Automating your business with AI is not hard anymore. Here's the exact playbook.",
         "results", ["linkedin", "x"], ["post", "article"]),

    Hook(22,
         "Here's how [target audience] can [achieve outcome] with AI in [time frame].",
         "Here's how any business owner can 10x their output with AI in the next 30 days.",
         "results", ["linkedin", "instagram", "youtube_shorts"], ["article"]),

    Hook(23,
         "I made [result] by doing [action]. Here's the breakdown.",
         "I built a full AI-powered business system in a weekend. Here's the exact breakdown.",
         "results", ["linkedin", "x", "instagram"], ["post", "article"]),

    # CALLOUT  - speak directly to [YOUR NAME]'s audience
    Hook(24,
         "Business owners, stop scrolling. This is for you.",
         "Business owners, stop scrolling. If you're not building AI infrastructure yet, you're already behind.",
         "callout", ["linkedin", "x", "instagram", "youtube_shorts"], ["post"]),

    Hook(25,
         "If you work in [industry], you need to hear this right now.",
         "If you run a business of any size, you need to hear this about AI infrastructure right now.",
         "callout", ["linkedin", "x"], ["post", "article"]),

    Hook(26,
         "If you're not [doing this], you're falling behind. Here's the fix.",
         "If you're not building AI infrastructure into your business, you're falling behind. Here's the fix.",
         "callout", ["linkedin", "instagram", "x"], ["post"]),

    Hook(27,
         "[specific group], don't limit yourself to [option]. Here's why.",
         "Entrepreneurs, don't limit yourself to off-the-shelf AI tools. Here's what's possible when you build your own.",
         "callout", ["linkedin", "x"], ["post"]),

    # REVELATION  - big idea moment, drives shares
    Hook(28,
         "Everything you knew about [topic] is about to change.",
         "Everything you knew about running a lean business just changed. AI infrastructure is the reason.",
         "revelation", ["linkedin", "instagram", "youtube_shorts"], ["article"]),

    Hook(29,
         "This one shift in how you use AI will change your entire business.",
         "This one shift  - from AI user to AI builder  - will change your entire business.",
         "revelation", ["linkedin", "x", "instagram"], ["post", "article"]),

    Hook(30,
         "Here's the moment I realized [topic] was the key to [outcome].",
         "Here's the moment I realized AI infrastructure  - not AI tools  - was the key to real business leverage.",
         "revelation", ["linkedin", "x"], ["post", "article"]),

    # SOCIAL PROOF  - build trust with numbers and outcomes
    Hook(31,
         "[number] subscribers. [result]. Here's what actually worked.",
         "Growing an AI knowledge community from zero. Here's what actually moved the needle.",
         "social_proof", ["linkedin", "x"], ["post"]),

    Hook(32,
         "Here's what happened after I gave away [resource] for free.",
         "Here's what happened after I gave away my first AI skill for free. The results surprised me.",
         "social_proof", ["linkedin", "instagram", "x"], ["post"]),

    Hook(33,
         "I did [action] for [time period]. Here's exactly what I learned.",
         "I built AI systems for businesses for over a year. Here's exactly what separates the ones that work.",
         "social_proof", ["linkedin", "x"], ["post", "article"]),
]


# ─── Intent and platform filters ─────────────────────────────────────────────

INTENTS = ["contrarian", "authority", "curiosity", "results", "callout", "revelation", "social_proof"]

PLATFORM_DEFAULTS = {
    "linkedin":       ["authority", "revelation", "results", "contrarian"],
    "x":              ["contrarian", "curiosity", "callout", "results"],
    "instagram":      ["curiosity", "results", "callout", "authority"],
    "youtube_shorts": ["callout", "curiosity", "results", "contrarian"],
    "facebook":       ["authority", "results", "revelation", "callout"],
    "tiktok":         ["callout", "curiosity", "results", "contrarian"],
}


# ─── [CLIENT NAME]'s hooks - strategy, operations, financials, GTM, leadership ──────

MARCELA_HOOKS = [
    # CONTRARIAN
    Hook(101,
         "[common belief] is wrong. Here's what actually drives [outcome].",
         "Tracking revenue is wrong. Here's what actually drives profitable growth.",
         "contrarian", ["linkedin", "x", "instagram"], ["post", "article"]),

    Hook(102,
         "Most [target audience] are doing [topic] backwards. Here's the right order.",
         "Most founders are building their GTM strategy backwards. Here's the right order.",
         "contrarian", ["linkedin", "x"], ["post", "article"]),

    Hook(103,
         "Stop [common action]. It's costing you [outcome].",
         "Stop building your marketing strategy before you understand your numbers. It's costing you real growth.",
         "contrarian", ["linkedin", "x", "instagram", "youtube_shorts"], ["post"]),

    Hook(104,
         "The [common metric] everyone obsesses over is the wrong one to watch.",
         "The revenue number everyone obsesses over is the wrong one to watch.",
         "contrarian", ["linkedin", "x"], ["post", "article"]),

    # AUTHORITY
    Hook(105,
         "Here's the exact [framework] that turns [problem] into [outcome].",
         "Here's the exact financial framework that turns confusion about your numbers into a clear growth plan.",
         "authority", ["linkedin", "instagram"], ["post", "article"]),

    Hook(106,
         "I've helped [number] businesses fix [problem]. Here's the pattern I always see.",
         "I've helped dozens of businesses fix their marketing operations. Here's the pattern I always see.",
         "authority", ["linkedin", "x"], ["post", "article"]),

    Hook(107,
         "[number] financial projections mistakes that are silently killing your growth.",
         "5 financial projection mistakes that are silently killing your growth.",
         "authority", ["linkedin", "instagram", "x"], ["post"]),

    Hook(108,
         "Here's what your numbers are actually telling you  - and why you're misreading them.",
         "Here's what your numbers are actually telling you  - and why most founders misread them.",
         "authority", ["linkedin", "x"], ["post", "article"]),

    # CURIOSITY
    Hook(109,
         "The [metric] nobody talks about is the one that predicts [outcome].",
         "The metric nobody talks about is the one that predicts whether your GTM strategy will actually work.",
         "curiosity", ["linkedin", "x", "instagram", "youtube_shorts"], ["post", "article"]),

    Hook(110,
         "What your [document/report] is hiding from you about your [outcome].",
         "What your P&L is hiding from you about your actual profitability.",
         "curiosity", ["linkedin", "x"], ["post", "article"]),

    Hook(111,
         "Most [target audience] don't know this about [topic]. The ones who do are winning.",
         "Most founders don't know this about marketing operations. The ones who do scale faster.",
         "curiosity", ["linkedin", "x", "instagram"], ["post", "article"]),

    # RESULTS
    Hook(112,
         "Here's how to build a [outcome] in [time frame]  - even if you've never done it before.",
         "Here's how to build a 12-month financial projection in a weekend  - even if numbers aren't your thing.",
         "results", ["linkedin", "instagram", "x", "youtube_shorts"], ["post", "article"]),

    Hook(113,
         "[desired outcome] is simpler than you think. Here's the framework.",
         "Understanding your marketing ROI is simpler than you think. Here's the framework.",
         "results", ["linkedin", "x"], ["post", "article"]),

    Hook(114,
         "I built a [system/process] that [result]. Here's exactly how.",
         "I built a GTM strategy system that cut our go-to-market time in half. Here's exactly how.",
         "results", ["linkedin", "instagram", "x"], ["post", "article"]),

    # CALLOUT
    Hook(115,
         "Founders, if you can't answer these [number] questions about your business, we need to talk.",
         "Founders, if you can't answer these 5 questions about your numbers, we need to talk.",
         "callout", ["linkedin", "x", "instagram", "youtube_shorts"], ["post"]),

    Hook(116,
         "If your [team/process] is doing [action], you're leaving [outcome] on the table.",
         "If your marketing team is running campaigns without a clear operations framework, you're leaving growth on the table.",
         "callout", ["linkedin", "x"], ["post", "article"]),

    # REVELATION
    Hook(117,
         "The reason your [strategy] isn't working has nothing to do with [common assumption].",
         "The reason your GTM strategy isn't working has nothing to do with your product.",
         "revelation", ["linkedin", "instagram", "youtube_shorts"], ["article"]),

    Hook(118,
         "This one shift in how you read your [report/data] will change every decision you make.",
         "This one shift in how you read your financial projections will change every business decision you make.",
         "revelation", ["linkedin", "x", "instagram"], ["post", "article"]),
]


def suggest_hooks(
    platform: str = "linkedin",
    intent: Optional[str] = None,
    content_type: str = "post",
    n: int = 5,
    client_slug: str = CLIENT_RYAN,
) -> list[Hook]:
    """
    Return up to n hooks suited to the given platform and content type.
    Routes to the correct hook library based on client_slug.
    If intent is None, uses the platform's preferred intent order.
    """
    # Select the correct hook library for this client
    hook_library = MARCELA_HOOKS if client_slug == CLIENT_MARCELA else HOOKS

    preferred_intents = [intent] if intent else PLATFORM_DEFAULTS.get(platform, INTENTS)

    scored = []
    for hook in hook_library:
        if platform not in hook.best_for:
            continue
        if content_type not in hook.content_type and "both" not in hook.content_type:
            continue
        intent_rank = preferred_intents.index(hook.intent) if hook.intent in preferred_intents else 99
        scored.append((intent_rank, hook))

    scored.sort(key=lambda x: x[0])
    results = [h for _, h in scored[:n]]

    # If fewer than n found, pad with random remaining hooks from the same library
    if len(results) < n:
        remaining = [h for h in hook_library if h not in results]
        random.shuffle(remaining)
        results += remaining[:n - len(results)]

    return results[:n]


def format_hook_menu(hooks: list[Hook]) -> str:
    """Return a numbered menu string for display in the terminal."""
    lines = []
    for i, h in enumerate(hooks):
        lines.append(f"  [cyan]{i + 1}[/cyan]. [{h.intent.upper()}] {h.example}")
    return "\n".join(lines)


def apply_hook(hook: Hook, post_text: str) -> str:
    """Prepend the chosen hook example to the post text."""
    return f"{hook.example}\n\n{post_text.strip()}"
