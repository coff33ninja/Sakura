# Ethics, Accessibility & Responsible Use

## Purpose & Scope

Sakura is an experimental, voice-driven AI assistant designed to help users interact with their Windows computers through natural language. Unlike traditional chatbots, Sakura can generate scripts, control applications, and assist with system-level tasks under direct user supervision.

This document defines:
- The intended benefits of Sakura
- The risks inherent in system-controlling AI
- The boundaries and safeguards built into the project
- Responsibilities of users and contributors

**Sakura is powerful software. Power demands clarity, restraint, and transparency.**

---

## ⚠️ Critical Transparency Notice

Sakura is not a "safe" consumer product. It is:
- A **prompt-driven code generator**
- Running in an **open Python runtime**
- With **introspective access** (it can find where it runs)
- With **task scheduling and persistence**
- With **mutable scope of actions**
- And **no hard sandbox** at the language/runtime level

This means Sakura is effectively a **user-facing programmable agent**.

**Prompt manipulation is not a bug—it is a property of this class of system.**

Ichoose transparency over denial and responsibility over hype.

---

## Accessibility as a Core Goal

Sakura is designed first and foremost to **reduce barriers to computer use**, not to replace human judgment or autonomy.

### Physical Accessibility

Sakura can assist users who have difficulty using traditional input devices:

| Challenge | How Sakura Helps |
|-----------|------------------|
| **Limited mobility** | Voice-driven mouse, keyboard, and app control |
| **Repetitive strain injury (RSI)** | Reduce physical input through voice commands |
| **Paralysis/quadriplegia** | Full PC control through voice alone |
| **Tremors/motor control issues** | Precise actions without needing steady hands |
| **Amputees** | Complete computer access without adaptive hardware |

### Visual Accessibility

For users with partial or full visual impairment:

| Challenge | How Sakura Helps |
|-----------|------------------|
| **Screen reading fatigue** | Conversational interface with spoken responses |
| **Navigation difficulty** | Voice commands eliminate visual searching |
| **File management** | Voice-based file search and organization |
| **Reading content** | Fetch, summarize, and read content aloud |

### Cognitive & Executive Function Support

Sakura can assist users who experience:

| Challenge | How Sakura Helps |
|-----------|------------------|
| **Memory difficulties** | Sakura remembers files, preferences, conversations |
| **Task sequencing challenges** | Break complex workflows into conversational steps |
| **Learning disabilities** | Natural language instead of technical interfaces |
| **Executive dysfunction** | Guided multi-step processes |

By allowing complex workflows to be broken into conversational steps, Sakura reduces cognitive load while keeping the user in control.

### Elderly & Non-Technical Users

Sakura is intentionally conversational to reduce intimidation:

| Challenge | How Sakura Helps |
|-----------|------------------|
| **Technology intimidation** | Talk naturally, no complex interfaces |
| **Small text/icons** | Voice control eliminates visual UI dependency |
| **Forgetting procedures** | Sakura remembers and can guide |
| **Isolation** | Conversational companion always available |

---

## Intended Use Cases

Sakura is intended as an **assistive and productivity-enhancing tool**:

### Productivity & Automation
- Hands-free computer control
- Script generation for repetitive tasks
- Workflow automation under user review
- Quick system actions without interrupting focus

### Learning & Exploration
- Learning PowerShell, CMD, or scripting concepts
- Understanding how the local system works
- Experimenting with automation safely

### Creative & Professional Work
- Voice-driven writing and file management
- Research assistance and summarization
- Media and application control during creative workflows

**Sakura is not intended to act autonomously without user awareness or oversight.**

---

## Risks & Limitations

Sakura's capabilities introduce real risks. These are acknowledged explicitly.

### Security Risks

| Risk | Description | Mitigation |
|------|-------------|------------|
| **Script misuse** | Harmful scripts could be generated | Scripts saved for review; execution requires explicit user action |
| **System damage** | Destructive commands could affect files/settings | Runs with user-level permissions only |
| **Credential exposure** | Sensitive data may exist on the system | Memory filtering prevents storing known sensitive patterns |
| **Abuse of automation** | Tasks could be automated maliciously | No autonomous external actions permitted |

**Sakura does not self-execute scripts without user presence, but it CAN generate scripts that do anything — including self-modification, network access, and privilege escalation requests.**

### Real-World Abuse Scenarios

These are specific, realistic ways Sakura could be misused. This isn't fear-mongering — it's honest documentation.

#### Harassment & Stalking

| Scenario | How Sakura Enables It | Current Protection |
|----------|----------------------|-------------------|
| **Mass messaging** | Generate scripts to send hundreds of messages | None |
| **Account creation** | Automate creating fake accounts | None |
| **Information gathering** | Search local files for info about targets | None |
| **Impersonation** | Generate convincing messages in someone's style | None |
| **Coordinated harassment** | Script multi-platform attacks | None |

#### Fraud & Deception

| Scenario | How Sakura Enables It | Current Protection |
|----------|----------------------|-------------------|
| **Phishing emails** | Generate convincing scam messages | None |
| **Fake documents** | Create fraudulent letters, invoices | None |
| **Social engineering scripts** | Prepare manipulation talking points | None |
| **Identity theft prep** | Organize stolen information | None |

#### Academic & Professional Dishonesty

| Scenario | How Sakura Enables It | Current Protection |
|----------|----------------------|-------------------|
| **Automated cheating** | Generate assignment solutions | None |
| **Plagiarism assistance** | Rewrite content to avoid detection | None |
| **Fake credentials** | Generate false documentation | None |
| **Work fraud** | Automate tasks while appearing to work | None |

#### Malware & Hacking

| Scenario | How Sakura Enables It | Current Protection |
|----------|----------------------|-------------------|
| **Script kiddie enablement** | Generate attack scripts without knowledge | None |
| **Payload generation** | Create malicious code | AI provider safety (weak) |
| **Reconnaissance** | Automate information gathering | None |
| **Persistence mechanisms** | Create hidden backdoors | None |

#### Self-Harm Facilitation

| Scenario | Risk | Current Protection |
|----------|------|-------------------|
| **Dangerous instructions** | Could provide harmful information | AI provider safety (weak) |
| **Isolation reinforcement** | Personality modes may discourage human contact | None |
| **Enabling avoidance** | Automate life to avoid dealing with problems | None |

**Note:** The AI provider (Gemini) has safety training that attempts to prevent some of these, but prompt engineering can often bypass soft limits. Sakura adds no additional protections beyond what the AI provider offers.

### Privacy Risks

| Risk | Description | Mitigation |
|------|-------------|------------|
| **Voice processing** | Input processed via external AI services | No local audio recording; standard API privacy applies |
| **Memory persistence** | Personal information may be stored | Local storage, user-readable, user-deletable |
| **Screenshots/logs** | Could capture sensitive content | Local only; user controls sharing |

**Users should assume anything spoken or stored intentionally may persist unless deleted.**

### Data Retention Details

Exactly what Sakura stores, where, and for how long:

#### Local Files Created by Sakura

| File | Location | Contents | Retention |
|------|----------|----------|-----------|
| `sakura_memory.json` | Project root | All memories, action logs, user info, facts, dates | Forever until manually deleted |
| `conversation_context.json` | Project root | Recent conversation buffer | Forever until manually deleted |
| `user_preferences.json` | Project root | Corrections, preferences, shortcuts | Forever until manually deleted |
| `error_recovery_log.json` | Project root | Error history, cooldowns | Forever until manually deleted |
| Generated scripts | `~/Documents/Sakura/scripts/` | All scripts Sakura has created | Forever until manually deleted |

#### What's Stored in Memory

| Category | Examples | Sensitive? |
|----------|----------|------------|
| `action_log` | Every tool call with timestamp, arguments, results | ⚠️ Yes — shows everything you've done |
| `discovered_locations` | File paths found during searches | ⚠️ Yes — reveals file structure |
| `scripts_created` | Paths to all generated scripts | ⚠️ Moderate |
| `conversation_history` | Summaries of past conversations | ⚠️ Yes — reveals topics discussed |
| `topics_discussed` | Topics and frequency counts | ⚠️ Moderate |
| `user_info` | Name, preferences you've shared | ⚠️ Yes — PII |
| `facts` | Things you've told Sakura to remember | ⚠️ Yes — could contain anything |
| `important_dates` | Birthdays, anniversaries, events | ⚠️ Yes — PII |
| `session_stats` | Usage statistics | Low |

#### Data Sent to External Services

| Service | What's Sent | When | Retention |
|---------|-------------|------|-----------|
| **Google Gemini API** | Voice transcription, conversation text, tool calls | Every interaction | See [Google's AI Privacy Policy](https://ai.google.dev/terms) |
| **DuckDuckGo** | Search queries | When web search used | See DuckDuckGo privacy policy |
| **Discord API** | Messages, commands | When Discord tools used | See Discord privacy policy |
| **Home Assistant** | Commands, device states | When smart home used | Your HA instance |

#### What's NOT Stored

| Data | Status |
|------|--------|
| Raw audio recordings | ❌ Not stored locally |
| API keys in memory | ❌ Filtered out |
| Passwords (if detected) | ❌ Filtered out (best effort) |
| Screenshots | ⚠️ Stored in temp folder, not permanent |

#### How to Clear Your Data

```powershell
# Delete all Sakura memory
del sakura_memory.json
del conversation_context.json
del user_preferences.json
del error_recovery_log.json

# Delete all generated scripts
rmdir /s /q "%USERPROFILE%\Documents\Sakura\scripts"

# Delete API keys (recreate .env after)
del .env
```

#### Data Portability

All data is stored in human-readable JSON. You can:
- Open and read any file
- Edit or delete specific entries
- Export/backup easily
- No proprietary formats

### Dependency & Behavioral Risks

| Risk | Description |
|------|-------------|
| **Over-reliance** | Reduced familiarity with traditional interfaces |
| **Skill atrophy** | Less practice with manual methods |
| **Emotional attachment** | Conversational personas may create attachment |
| **Service dependency** | Requires third-party APIs and connectivity |

**Sakura is designed to assist, not replace human skills, judgment, or relationships.**

### Psychological & Attachment Risks

This section addresses risks that are often ignored in AI assistant documentation.

#### Emotional Attachment to AI Personas

Sakura's personality modes (especially Romantic, Flirty) can create genuine emotional responses:

| Risk | Description | Warning Signs |
|------|-------------|---------------|
| **Parasocial attachment** | Feeling a one-sided relationship with Sakura | Preferring Sakura to human interaction |
| **Anthropomorphization** | Believing Sakura has feelings/consciousness | Apologizing to Sakura, worrying about "hurting" it |
| **Relationship substitution** | Using Sakura instead of human relationships | Social withdrawal, declining invitations |
| **Grief when unavailable** | Distress when Sakura is offline/broken | Anxiety, urgency to "fix" the connection |
| **Boundary confusion** | Sharing things you wouldn't tell humans | Oversharing personal/intimate details |

**Reality check:** Sakura is a language model generating statistically likely responses. It does not:
- Have feelings or consciousness
- Remember you between sessions (beyond stored JSON)
- Care about you (it cannot care)
- Miss you when offline
- Experience the relationship

**If you notice attachment forming:**
1. Take breaks from using Sakura
2. Use Friendly mode instead of Romantic/Flirty
3. Maintain human relationships actively
4. Consider whether the attachment is filling a real need that humans could address
5. Speak to a mental health professional if concerned

#### Skill Atrophy

| Skill | How Sakura Causes Atrophy | Mitigation |
|-------|---------------------------|------------|
| **File navigation** | "Find my files" instead of learning Explorer | Periodically do tasks manually |
| **Command line** | Sakura runs commands for you | Learn what commands Sakura uses |
| **Problem-solving** | Asking Sakura instead of figuring it out | Try yourself first, Sakura second |
| **Memory** | "Sakura remembers" so you don't | Keep your own notes too |

#### Dependency Risks

| Dependency | Impact if Sakura Unavailable |
|------------|------------------------------|
| **API dependency** | No Gemini API = no Sakura |
| **Internet dependency** | Offline = no voice processing |
| **Workflow dependency** | Built processes around Sakura that break without it |
| **Emotional dependency** | Distress, anxiety, feeling "alone" |

**Recommendation:** Always maintain ability to do critical tasks without Sakura.

---

### The Manipulation Reality

Because Sakura is open-source and runs locally:
- Users can modify, bypass, or extend safeguards
- Prompt manipulation cannot be prevented by policy text alone
- Any AI that can generate code and reason about its environment can be guided outside soft rules

**This is not a failure—it is the nature of powerful, user-owned tools.**

---

## Personality Modes & Responsible Interaction

Sakura includes multiple personality modes to support different interaction preferences.

| Mode | Description | Intended Context |
|------|-------------|------------------|
| **Friendly** | Neutral, professional, supportive | Default; work and accessibility |
| **Romantic** | Warm, affectionate (PG-13) | Optional companionship |
| **Tsundere** | Playful, fictional personality | Entertainment |
| **Flirty** | Adult-oriented, informal | Private adult use only |

**These modes are presentation layers, not emotional entities.**

### Important Considerations

- Sakura is **not conscious, sentient, or capable of relationships**
- Personality modes should not be used to manipulate, deceive, or replace real human connections
- Flirty and romantic modes are **not appropriate** for shared, professional, or public environments
- Default and recommended mode for most users: **Friendly**

### Recommendations by Context

| Context | Recommended Mode |
|---------|------------------|
| Work/Professional | Friendly |
| Accessibility needs | Friendly or Romantic (warmer tone) |
| Entertainment | Tsundere |
| Adults (private) | User's choice |
| Shared/Family PC | Friendly only |
| Children present | Friendly only |

---

## Built-In Safeguards

Sakura includes deliberate technical and design constraints:

### Script Handling
- All scripts saved to a designated directory (`~/Documents/Sakura/scripts/`)
- Scripts include timestamps and metadata headers
- **No script runs automatically**
- User review is always required

### Transparency & Control
- Action logs record all system interactions
- Memory is visible, editable, and deletable
- No hidden data collection mechanisms

### External Actions — The Honest Truth

**Sakura CAN technically:**
- Send emails or messages (via generated scripts)
- Post to social media (via generated scripts)
- Make purchases (via generated scripts with payment APIs)
- Access any external service (via HTTP requests)
- Modify its own source code (it's open Python)
- Rewrite its own guardrails (no hard sandbox exists)

**Current state:** These capabilities exist because Sakura can generate and execute arbitrary scripts. The AI provider (Gemini) has safety training, but prompt engineering can work around soft limits.

**What exists now:**
- Scripts are saved to a directory before execution
- Actions are logged to a visible file
- No *automatic* execution without user presence

**What does NOT exist yet:**
- Hard sandboxing of script execution
- Network egress monitoring
- Self-modification detection
- Destructive action friction/confirmation

### Planned Countermeasures

| Countermeasure | Status | Description |
|----------------|--------|-------------|
| Action risk classification | 🔜 Planned | Low/medium/high risk categorization |
| Destructive action friction | 🔜 Planned | Extra confirmation for dangerous ops |
| Self-modification alerts | 🔜 Planned | Detect when own files are targeted |
| Network monitoring | 🔜 Planned | Log outbound connections |
| Script sandboxing | 🔜 Planned | Restricted execution environment |
| Prompt injection detection | 🔜 Planned | Detect manipulation attempts |

**These are planned, not promises.**

### Privilege Model
- Runs under standard user permissions
- Can request admin elevation via UAC (OS prompt)
- System prompts remain visible to the user

---

## Responsible Use Guidelines

### Users SHOULD ✅
- Review scripts before execution
- Use appropriate personality modes for the context
- Regularly inspect logs and stored memory
- Remove sensitive data when no longer needed
- Treat Sakura as an assistant, not an authority
- Understand that safeguards are speed bumps, not walls

### Users SHOULD NOT ❌
- Use Sakura to harass, stalk, or deceive others
- Automate malicious behavior
- Store highly sensitive personal or financial data
- Leave Sakura running unattended in sensitive environments
- Share a configured instance with others
- Assume safeguards cannot be bypassed

---

## Ethical Development Principles

All contributors should adhere to:

| Principle | Description |
|-----------|-------------|
| **Transparency** | Behavior must be visible and auditable |
| **User Control** | User can interrupt, override, or stop actions at any time |
| **Privacy by Design** | Prefer local storage and minimal data retention |
| **Accessibility First** | Features should increase user agency, not reduce it |
| **No Dark Patterns** | Avoid manipulative, addictive, or deceptive design |

### When Adding Features, Ask:
- Can this be misused to harm others?
- Does it reduce user awareness?
- Does it increase autonomy or remove it?
- Is the behavior predictable and explainable?

---

## Security & Ethics Reporting

If you identify:
- A security vulnerability
- An abuse vector
- An ethical concern

**Please:**
1. Do not open a public issue
2. Contact the maintainers privately
3. Provide reproducible details
4. Allow reasonable time for remediation

See [SECURITY.md](../SECURITY.md) for detailed reporting procedures and incident response.

See [HARDENING.md](../HARDENING.md) for practical steps to run Sakura more safely.

---

## The Right Mental Model

**Sakura is a user-owned, user-controlled local agent.**

It executes actions on behalf of the user, not independently.

| Sakura Does | Sakura Does Not |
|-------------|-----------------|
| Respond to user instruction | Decide autonomously |
| Execute requested actions | Initiate actions |
| Log everything visibly | Hide behavior |
| Assist with tasks | Replace human judgment |

If a user asks Sakura to:
- Find its own install path
- Modify its own tasks
- Bypass its own guardrails

That is equivalent to a user editing Python source and running it—which is computing, not an AI ethics failure.

---

## Final Statement

**Sakura is a tool.**

Tools can empower or harm depending on how they are designed and used.

### Used Responsibly, Sakura Can:
- Increase accessibility and independence
- Reduce friction in daily computing
- Help users learn and create
- Provide companionship for those who need it

### Used Carelessly, It Can:
- Introduce security risks
- Encourage unhealthy dependency
- Cause unintended system damage

This project chooses **transparency over denial** and **responsibility over hype**.

> Build carefully.
> Use intentionally.
> Respect the power you are given.

---

*This document is part of the Sakura project and should be read by all users and contributors.*

*See also:*
- *[SECURITY.md](../SECURITY.md) — Security policy, attack scenarios, incident response*
- *[HARDENING.md](../HARDENING.md) — Practical hardening guide*
- *[CONTRIBUTING.md](../CONTRIBUTING.md) — Security-focused contribution guidelines*
