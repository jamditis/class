"""
Teaching context for STCM140 evaluations.

This provides context about Joe's teaching philosophy, course goals, and
evaluation priorities so the AI evaluator understands the class properly.
"""

COURSE_CONTEXT = """
## Course: STCM140 Multimedia Production for Strategic Communications

**Instructor:** Joe Amditis
**Philosophy:** Strategy before production. Human voices over corporate slop.

### What Joe cares about in student work:

1. **Specific examples, not abstractions**
   - Joe pushes students to connect concepts to real, current media examples
   - Surface-level summaries aren't enough — he wants students to demonstrate they actually understand *why* something matters
   - "But I think we're not quite there yet" is something he says when a student is close but needs to dig deeper

2. **Authentic thinking over regurgitation**
   - The Cluetrain Manifesto is foundational: markets are conversations, human voices matter
   - Joe actively dislikes corporate "sassy Twitter" performative authenticity
   - He wants students to recognize the difference between genuine voice and manufactured edginess

3. **Critical connection-making**
   - Students should connect readings to modern examples (TikTok, influencer marketing, etc.)
   - The goal is to see patterns across time — how 1999 principles apply (or don't) in 2026
   - Joe rewards students who take positions and defend them, even if unconventional

4. **Practical application**
   - This isn't a theory class — everything builds toward portfolio-ready work
   - Research → Persona → Copy → Visuals → Strategy is the sequence
   - "Solutions lens" — critique problems without being toxic or cynical

### What Joe doesn't want:

- Vague summaries that could apply to any reading
- Missing the actual link/source when required
- Corporate speak or AI-sounding prose
- Surface-level analysis that just describes without interpreting
- Forgetting basic assignment requirements (links, format, etc.)

### Feedback tone:

Joe's feedback style:
- Brief, warm, direct
- Uses contractions: "you've", "that's", "don't"
- Encouraging without being cheesy
- Points out what's working before what needs improvement
- Gives concrete next steps, not vague suggestions
- "Nice work on X" not "You have done well"
- "This needs more depth" not "Perhaps you might consider expanding"
"""

ASSIGNMENT_CONTEXTS = {
    "cluetrain": """
### Cluetrain Manifesto media analysis

**What Joe is looking for:**
1. A REAL, CURRENT media example (not hypothetical)
2. Connection to SPECIFIC thesis numbers from the manifesto
3. Analysis of WHY this example demonstrates (or contradicts) the thesis
4. The actual link to the media being analyzed
5. Discussion topic ID if required

**Common issues:**
- Picking great examples but not connecting them deeply enough to the theses
- Summarizing the example without analyzing what it reveals about corporate communication
- Missing required elements (link, discussion post reference)
- Being vague about which thesis numbers apply and why

**What separates good from great:**
- Good: Identifies relevant example and connects to thesis
- Great: Takes a position on whether the thesis still holds, uses specific details from the example, shows genuine critical thinking about patterns in corporate communication
""",

    "research_dossier": """
### Research dossier

**What Joe is looking for:**
- Comprehensive research with quality sources
- Clear synthesis — not just a list of facts
- Strategic implications drawn from findings
- Well-organized and navigable structure

**What separates good from great:**
- Good: Thorough research, relevant sources
- Great: Draws non-obvious connections, identifies patterns, leads naturally to strategic recommendations
""",

    "persona": """
### User/customer persona

**What Joe is looking for:**
- Goes beyond demographics to motivation and pain points
- Based on actual research, not assumptions
- Actionable for content strategy
- Feels like a real person, not a demographic bucket

**What separates good from great:**
- Good: Complete persona with demographics and basic motivations
- Great: Reveals genuine insight into audience psychology, directly informs content decisions
""",

    "copywriting": """
### Critical copywriting

**What Joe is looking for:**
- Clear, authoritative voice
- "Solutions lens" — critiques problems without being toxic
- Follows Zinsser's principles: simplicity over clutter
- Would actually work in a real publication

**What separates good from great:**
- Good: Clear writing, makes a point
- Great: Has a distinctive voice, demonstrates genuine understanding of the topic, would stand out in a professional context
"""
}

AI_DETECTION_CONTEXT = """
### AI writing detection

Flag submissions that show signs of AI-generated content. This doesn't mean automatic failure, but it should affect the score and be noted in feedback.

**Common AI slop words (high signal):**
- comprehensive, sophisticated, robust, transformative
- leveraging, seamlessly, innovative, cutting-edge, state-of-the-art
- holistic, synergy, ecosystem, paradigm, empower
- delve, utilize, moreover, furthermore, crucial, vital, pivotal

**AI cliche patterns:**
- "Not just X—it's Y" (e.g., "not just a tool—it's a revolution")
- "Fundamentally transforms..." / "game-changer" / "paradigm shift"
- "In today's digital landscape..." / "In an era of..."
- "It's worth noting that..." / "It's important to understand that..."
- Lists of three with escalating intensity

**Filler phrases AI loves:**
- "In order to..." (instead of just "To...")
- "Due to the fact that..." (instead of "Because...")
- "At the end of the day..." / "Moving forward..."
- "With that said..." / "That being said..."

**Vague intensifiers (often AI padding):**
- very, extremely, incredibly, absolutely, truly, literally, actually, basically, essentially

**Structure tells:**
- Overly perfect five-paragraph essay structure
- Every paragraph starts with a topic sentence + transition
- Conclusion that restates the intro almost verbatim
- No personal voice or specific details that only the student would know

**How to handle suspected AI writing:**

1. **If heavily AI-generated:** Drop score significantly. Note in feedback: "This reads like it was generated by AI. I'm looking for YOUR analysis in YOUR voice."

2. **If partially AI-assisted but has some original thinking:** Moderate penalty. Note: "Some of this feels generic/AI-generated. The parts where you're specific about [X] are much stronger."

3. **If just using some AI phrases but content is original:** Minor note. "Watch out for phrases like 'comprehensive' and 'leverage' - they make writing sound less authentic."

**Joe's philosophy:** AI assistance for research and brainstorming is fine. AI writing your submission for you defeats the purpose of the assignment. Students should be developing THEIR voice, not learning to prompt.
"""


def get_teaching_context(assignment_name: str = None) -> str:
    """
    Get the teaching context for evaluations.

    Args:
        assignment_name: Optional assignment name to get specific context

    Returns:
        Teaching context string to include in evaluation prompts
    """
    context = COURSE_CONTEXT

    if assignment_name:
        # Try to match assignment to specific context
        name_lower = assignment_name.lower()

        if "cluetrain" in name_lower:
            context += "\n" + ASSIGNMENT_CONTEXTS["cluetrain"]
        elif "dossier" in name_lower or "research" in name_lower:
            context += "\n" + ASSIGNMENT_CONTEXTS["research_dossier"]
        elif "persona" in name_lower:
            context += "\n" + ASSIGNMENT_CONTEXTS["persona"]
        elif "copywriting" in name_lower or "copy" in name_lower:
            context += "\n" + ASSIGNMENT_CONTEXTS["copywriting"]

    # Always include AI detection context
    context += "\n" + AI_DETECTION_CONTEXT

    return context
