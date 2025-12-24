# Ethics, Accessibility & Responsible Use

## 🌟 Why Sakura Exists

Sakura was created to explore the potential of AI assistants that can truly help users interact with their computers through natural voice conversation. This document discusses the benefits, risks, and responsibilities that come with such powerful technology.

---

## ♿ Accessibility Benefits

### For Users with Physical Disabilities

| Challenge | How Sakura Helps |
|-----------|------------------|
| **Limited mobility** | Voice-controlled mouse, keyboard, and app control - no physical input needed |
| **Repetitive strain injury (RSI)** | Reduce mouse/keyboard usage through voice commands |
| **Paralysis/quadriplegia** | Full PC control through voice alone |
| **Tremors/motor control issues** | Precise actions without needing steady hands |
| **Amputees** | Complete computer access without adaptive hardware |

### For Users with Visual Impairments

| Challenge | How Sakura Helps |
|-----------|------------------|
| **Screen reading fatigue** | Conversational interface - ask questions, get spoken answers |
| **Navigation difficulty** | "Open Chrome", "Find my documents" - no visual searching needed |
| **File management** | Voice-based file search, organization, and management |
| **Reading content** | Can fetch and summarize web content verbally |

### For Users with Cognitive Disabilities

| Challenge | How Sakura Helps |
|-----------|------------------|
| **Memory difficulties** | Sakura remembers everything - files, preferences, past conversations |
| **Complex task sequences** | Break down tasks into simple voice commands |
| **Learning disabilities** | Natural language instead of technical interfaces |
| **Executive function challenges** | Sakura can guide through multi-step processes |

### For Elderly Users

| Challenge | How Sakura Helps |
|-----------|------------------|
| **Technology intimidation** | Talk naturally, no need to learn complex interfaces |
| **Small text/icons** | Voice control eliminates need to see small UI elements |
| **Forgetting passwords/locations** | Sakura remembers and can help retrieve |
| **Isolation** | Conversational companion that's always available |

---

## ✅ Positive Use Cases

### Productivity Enhancement
- **Automation** - Create scripts for repetitive tasks
- **Hands-free operation** - Work while cooking, exercising, etc.
- **Multi-tasking** - Control PC while doing other activities
- **Quick actions** - "Turn up volume", "Open Spotify" without interrupting workflow

### Learning & Development
- **Programming assistance** - Generate and explain scripts
- **System administration** - Learn PowerShell/CMD through natural conversation
- **Technology education** - Discover how your PC works

### Creative Work
- **Writers** - Dictate while Sakura handles file management
- **Artists** - Voice-controlled reference gathering
- **Musicians** - Hands-free media control during practice

### Professional Applications
- **Customer support** - Quick information retrieval
- **Data entry** - Voice-to-action workflows
- **Research** - Web search and content summarization

---

## ⚠️ Potential Risks & Misuse

### Security Concerns

| Risk | Description | Mitigation |
|------|-------------|------------|
| **Malicious scripts** | User could ask Sakura to create harmful scripts | Scripts saved to sandbox for review; user must explicitly execute |
| **Data exfiltration** | Could be used to find and send sensitive files | No automatic external transmission; user controls all actions |
| **System damage** | Destructive commands could harm the system | Sakura doesn't have admin privileges by default |
| **Credential theft** | Could search for password files | Sensitive patterns filtered from memory storage |

### Privacy Concerns

| Risk | Description | Mitigation |
|------|-------------|------------|
| **Voice recording** | Conversations sent to Google's servers | Standard Gemini API privacy policy applies; no local recording |
| **Memory persistence** | Sakura remembers personal information | Memory stored locally; user can delete anytime |
| **Screen content** | Screenshots could capture sensitive info | Screenshots saved locally only; user controls sharing |

### Abuse Scenarios

| Scenario | Risk Level | Notes |
|----------|------------|-------|
| **Harassment automation** | Medium | Could automate sending messages; requires user intent |
| **Cheating/academic dishonesty** | Medium | Can generate code/scripts; same as any AI tool |
| **Stalking assistance** | Low | File search is local only; no external tracking |
| **Malware creation** | Medium | Can write scripts; but so can any text editor |
| **Social engineering** | Low | No external communication without user action |

### Dependency Risks

| Risk | Description |
|------|-------------|
| **Over-reliance** | Users may forget how to perform tasks manually |
| **Skill atrophy** | Reduced practice with traditional interfaces |
| **Service dependency** | Requires internet and API access |
| **Emotional attachment** | Personality modes may create unhealthy attachment |

---

## 🎭 Personality Modes - Use Responsibly

Sakura includes four personality modes to suit different preferences and contexts:

| Mode | Description | Best For | Caution |
|------|-------------|----------|---------|
| **Friendly** | Warm, helpful, professional | Work, general use, accessibility | Default - safest option |
| **Romantic** | Sweet, caring, affectionate (PG-13) | Companionship, emotional support | May create attachment |
| **Tsundere** | Playful anime-style personality | Entertainment, anime fans | Fictional character roleplay |
| **Flirty** | Playful, unfiltered, adult-oriented | Adults only, private use | Not for professional/public settings |

### Why Include Personality Modes?

**Positive reasons:**
- **Companionship** - For isolated or lonely users, a friendly AI can provide comfort
- **Accessibility** - Some users respond better to warmer, more personal interactions
- **Engagement** - Personality makes the assistant more enjoyable to use
- **Customization** - Different contexts call for different tones

**Considerations:**
- **Emotional attachment** - Users may develop feelings for an AI persona
- **Inappropriate use** - Flirty mode should only be used by consenting adults in private
- **Expectations** - AI cannot replace human relationships
- **Context awareness** - Use professional modes in professional settings

### Recommendations

| User Type | Recommended Mode |
|-----------|------------------|
| Work/Professional | Friendly |
| Accessibility needs | Friendly or Romantic (warmer tone) |
| Entertainment | Tsundere |
| Adults (private) | User's choice |
| Shared/Family PC | Friendly only |
| Children present | Friendly only |

**Remember:** Sakura is an AI assistant, not a replacement for human connection. Personality modes are designed to make interactions more pleasant, not to simulate real relationships.

---

## 🛡️ Built-in Safeguards

### Script Sandbox
- All scripts saved to `~/Documents/Sakura/scripts/`
- Scripts include timestamp and metadata headers
- User must review before execution
- Organized by type for easy auditing

### Memory Transparency
- All memories stored in readable JSON file
- User can view, edit, or delete any memory
- No hidden data collection
- Action log shows everything Sakura has done

### No Autonomous External Actions
- Cannot send emails without user confirmation
- Cannot post to social media
- Cannot make purchases
- Cannot access external APIs without explicit configuration

### Limited Privileges
- Runs with user-level permissions
- No automatic admin elevation
- Cannot modify system files without UAC prompt

---

## 📋 Responsible Use Guidelines

### DO ✅
- Use for accessibility and productivity
- Review scripts before executing
- Regularly check the action log
- Delete sensitive memories when no longer needed
- Keep API keys secure
- Use appropriate personality mode for context

### DON'T ❌
- Share your configured Sakura with others (contains your preferences)
- Use to automate harassment or spam
- Create malicious scripts
- Store highly sensitive information in memory
- Leave running unattended in sensitive environments
- Use flirty/romantic modes inappropriately

---

## 🤝 For Developers & Contributors

### Ethical Development Principles

1. **Transparency** - All actions are logged and visible to users
2. **User control** - User can always override, stop, or modify behavior
3. **Privacy by design** - Minimal data collection, local storage preference
4. **Accessibility first** - Features should enhance, not replace, user agency
5. **No dark patterns** - No manipulation or addictive design

### When Adding Features

Ask yourself:
- Could this feature be misused to harm others?
- Does this respect user privacy?
- Is this accessible to users with disabilities?
- Does the user maintain control?
- Is the behavior transparent and predictable?

---

## 📞 Reporting Issues

If you discover a security vulnerability or potential for misuse:

1. **Do not** create a public issue
2. Contact the maintainers privately
3. Provide detailed reproduction steps
4. Allow time for a fix before disclosure

---

## 🌈 Final Thoughts

Technology is a tool - its impact depends on how it's used. Sakura can be:

- **A lifeline** for someone with disabilities who gains independence
- **A productivity boost** for professionals and creators
- **A learning tool** for those exploring technology
- **A companion** for those who need one

Or it could be misused by those with harmful intent.

We believe the benefits far outweigh the risks when used responsibly. By being transparent about both the potential and the pitfalls, we hope to encourage thoughtful, ethical use of AI assistants.

**Build responsibly. Use thoughtfully. Help others.**

---

*This document is part of the Sakura project and should be read by all users and contributors.*
