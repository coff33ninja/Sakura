# Intent Parser Module

**File:** `modules/intent_parser.py`

Better understanding of vague commands through synonyms, fuzzy matching, and context.

## Features

- Comprehensive synonym database
- Fuzzy matching for commands
- Context-aware disambiguation
- Vague command handling
- Clarification questions

## Intent Types

```python
class IntentType(Enum):
    ACTION = "action"           # Do something
    QUERY = "query"             # Get information
    NAVIGATION = "navigation"   # Go somewhere
    CONTROL = "control"         # Control something
    MEMORY = "memory"           # Remember/recall
    VAGUE = "vague"             # Unclear intent
    CONFIRMATION = "confirmation"  # Yes/no
    CORRECTION = "correction"   # Correcting
```

## Synonym Database

### Action Verbs
| Word | Synonyms |
|------|----------|
| open | launch, start, run, execute, fire up, boot |
| close | quit, exit, kill, terminate, end, stop |
| find | search, look for, locate, where is |
| show | display, list, get, tell me, what is |
| create | make, new, generate, build, write |
| delete | remove, erase, trash, get rid of |

### System Controls
| Word | Synonyms |
|------|----------|
| volume | sound, audio, loudness, speaker |
| mute | silence, quiet, hush |
| brightness | dim, bright |

### Media Controls
| Word | Synonyms |
|------|----------|
| play | resume, unpause, continue |
| pause | stop, hold, freeze |
| next | skip, forward |
| previous | back, last, prev |

## Vague Command Handling

| Input | Handling |
|-------|----------|
| "Do that thing" | Check recent context |
| "The usual" | Check user preferences |
| "Fix it" | Analyze recent errors |
| "Try again" | Retry last action |
| "Never mind" | Cancel |

## Parsed Intent

```python
@dataclass
class ParsedIntent:
    raw_input: str
    normalized_input: str
    intent_type: IntentType
    confidence: float
    tool_hint: Optional[str]
    action_hint: Optional[str]
    extracted_args: Dict
    alternatives: List[str]
    needs_clarification: bool
    clarification_question: Optional[str]
```

## Usage

```python
parser = IntentParser()
await parser.initialize()

# Parse user input
intent = await parser.parse("launch chrome")
# Returns: tool_hint="windows", action_hint="open_app", args={"app": "chrome"}

# Handle vague command
intent = await parser.parse("do that again")
# Uses recent context to determine action

# Get clarification
if intent.needs_clarification:
    print(intent.clarification_question)
    # "Did you mean: open Chrome, open Firefox, or open Edge?"
```

## Fuzzy Matching

Uses `difflib.SequenceMatcher` and `get_close_matches` for:
- Typo tolerance
- Similar command detection
- Alternative suggestions
