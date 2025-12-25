# Contributing to Sakura

Thank you for your interest in contributing to Sakura! This document outlines guidelines for contributing, with a strong emphasis on security considerations given Sakura's powerful capabilities.

## ⚠️ Security-First Development

Sakura is a system-level AI agent capable of executing arbitrary code. Every contribution must be evaluated through a security lens.

### Before You Contribute

Please read and understand:
- [SECURITY.md](SECURITY.md) — Threat model and attack scenarios
- [ETHICS_AND_ACCESSIBILITY.md](ETHICS_AND_ACCESSIBILITY.md) — Ethical guidelines
- [HARDENING.md](HARDENING.md) — Security hardening guide

---

## Contribution Guidelines

### 1. Security Review Checklist

Before submitting any PR, ask yourself:

| Question | If Yes... |
|----------|-----------|
| Does this add new file write capabilities? | Document paths, add validation |
| Does this add network access? | Document destinations, consider allowlisting |
| Does this execute external commands? | Add logging, consider sandboxing |
| Does this store user data? | Document what/where, add deletion method |
| Does this increase autonomy? | Justify why, add friction/confirmation |
| Does this reduce visibility? | Reconsider — transparency is core |
| Could this be abused for harassment? | Add safeguards or reconsider |
| Could this enable self-modification? | Extreme caution required |

### 2. Code Standards

#### All Code Must:
- Use `asyncio.Lock()` for thread safety
- Use `aiofiles` for file I/O
- Include comprehensive error handling
- Log actions to the action log
- Follow existing patterns in the codebase

#### Security-Specific Requirements:
```python
# ✅ DO: Validate paths before writing
def write_file(path: str, content: str):
    if not is_safe_path(path):
        raise SecurityError(f"Write to {path} not allowed")
    # ... write logic

# ❌ DON'T: Write to arbitrary paths
def write_file(path: str, content: str):
    with open(path, 'w') as f:  # No validation!
        f.write(content)
```

```python
# ✅ DO: Log all actions
async def execute_action(action: str, args: dict):
    await log_action(action, args)  # Always log first
    result = await perform_action(action, args)
    await log_result(action, result)
    return result

# ❌ DON'T: Silent actions
async def execute_action(action: str, args: dict):
    return await perform_action(action, args)  # No logging!
```

```python
# ✅ DO: Add friction for dangerous operations
async def delete_files(pattern: str):
    files = find_files(pattern)
    if len(files) > 10:
        # Require explicit confirmation for bulk operations
        raise ConfirmationRequired(f"About to delete {len(files)} files")
    # ... delete logic

# ❌ DON'T: Silent bulk operations
async def delete_files(pattern: str):
    for f in find_files(pattern):
        os.remove(f)  # No confirmation for bulk delete!
```

### 3. Documentation Requirements

Every new feature must include:

| Documentation | Location | Required Content |
|---------------|----------|------------------|
| Code comments | In source | What it does, security considerations |
| Tool schema | `tools/*/` | Action name, parameters, description |
| README update | `README.md` | If user-facing feature |
| Security notes | `SECURITY.md` | If adds new capabilities |
| Ethics notes | `docs/ETHICS_AND_ACCESSIBILITY.md` | If potential for misuse |

### 4. Testing Requirements

| Test Type | Required For | Location |
|-----------|--------------|----------|
| Unit tests | All new functions | `tests/` |
| Property tests | Data handling, parsing | `tests/properties/` |
| Security tests | New capabilities | `tests/security/` |

#### Security Test Examples:
```python
# Test that path validation works
def test_path_traversal_blocked():
    with pytest.raises(SecurityError):
        write_file("../../../etc/passwd", "malicious")

# Test that dangerous patterns are detected
def test_dangerous_command_flagged():
    result = analyze_command("rm -rf /")
    assert result.risk_level == "HIGH"
    assert result.requires_confirmation == True
```

---

## Pull Request Process

### 1. Before Submitting

- [ ] Read security checklist above
- [ ] Run all tests: `pytest`
- [ ] Run linting: `ruff check .`
- [ ] Update documentation if needed
- [ ] Add tests for new functionality

### 2. PR Description Template

```markdown
## Summary
[What does this PR do?]

## Security Considerations
- [ ] No new file write capabilities
- [ ] No new network access
- [ ] No new command execution
- [ ] No increased autonomy
- [ ] All actions logged
- [ ] Potential abuse scenarios considered

If any boxes unchecked, explain mitigations:
[Explanation]

## Testing
- [ ] Unit tests added
- [ ] Property tests added (if applicable)
- [ ] Security tests added (if new capabilities)
- [ ] Manual testing completed

## Documentation
- [ ] Code comments added
- [ ] README updated (if user-facing)
- [ ] SECURITY.md updated (if new capabilities)
```

### 3. Review Process

All PRs will be reviewed for:
1. **Functionality** — Does it work correctly?
2. **Security** — Does it introduce risks?
3. **Code quality** — Does it follow standards?
4. **Documentation** — Is it properly documented?
5. **Testing** — Is it adequately tested?

Security-sensitive PRs require additional review time.

---

## Feature Proposals

### Proposing New Capabilities

Before implementing significant new features, open an issue with:

```markdown
## Feature Proposal: [Name]

### Description
[What does this feature do?]

### Use Cases
[Who benefits and how?]

### Security Analysis

#### New Capabilities Introduced
- [List any new file/network/system access]

#### Potential Abuse Scenarios
- [How could this be misused?]

#### Proposed Mitigations
- [How will abuse be prevented/detected?]

### Alternatives Considered
- [Other approaches and why this one is better]
```

### Features That Require Extra Scrutiny

| Feature Type | Concern | Required |
|--------------|---------|----------|
| New tool actions | Expands attack surface | Security analysis |
| Network features | Data exfiltration risk | Destination controls |
| File operations | System damage risk | Path validation |
| Automation features | Abuse amplification | Rate limiting |
| Persistence features | Stealth risk | Visibility requirements |
| Self-modification | Guardrail bypass | Extreme caution |

---

## Reporting Security Issues

**Do NOT open public issues for security vulnerabilities.**

See [SECURITY.md](SECURITY.md) for responsible disclosure process.

---

## Code of Conduct

### IExpect Contributors To:

- Prioritize user safety over feature velocity
- Be transparent about risks and limitations
- Consider abuse scenarios proactively
- Document security implications
- Respect user privacy and autonomy

### IWill Not Accept:

- Features designed to deceive users
- Hidden or undocumented capabilities
- Removal of safety friction without justification
- Code that reduces transparency
- Features that primarily enable abuse

---

## Development Setup

```powershell
# Clone the repository
git clone https://github.com/coff33ninja/sakura-ai.git
cd sakura-ai

# Create virtual environment
uv venv --python 3.12 .venv
.\.venv\Scripts\activate

# Install dependencies
uv pip install -r requirements.txt

# Install dev dependencies
uv pip install pytest pytest-asyncio hypothesis ruff

# Run tests
pytest

# Run linting
ruff check .
```

---

## Questions?

- Open a GitHub issue for general questions
- See [SECURITY.md](SECURITY.md) for security concerns
- Review existing issues before creating new ones

---

*Thank you for contributing responsibly to Sakura!*
