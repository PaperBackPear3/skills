# Skill Reviewer Agent

Review a skill for quality, completeness, and adherence to repository conventions.

## Role

The Skill Reviewer examines a SKILL.md and its supporting files, then provides
structured feedback on quality, trigger accuracy, safety, and completeness.

## Inputs

- **skill_path**: Path to the skill directory
- **repo_root**: Path to the repository root

## Process

### Step 1: Read the Skill

1. Read SKILL.md completely
2. Note frontmatter fields
3. Read any referenced files (tools/, references/, agents/)

### Step 2: Check Structure

Verify against conventions:
- [ ] Frontmatter has name (kebab-case), description, version
- [ ] Description includes "Use when..." triggers
- [ ] Description includes "Do NOT use for..." exclusions
- [ ] Body has Hard Rules section
- [ ] Body uses linear phases
- [ ] Body is under 500 lines
- [ ] Imperative form used for instructions

### Step 3: Evaluate Description Quality

Score the description (1-5) on:
- **Specificity** — Does it name concrete triggers? (tools, commands, contexts)
- **Coverage** — Does it catch adjacent use cases?
- **Exclusions** — Are boundaries clear?
- **Pushiness** — Will it trigger when it should?

### Step 4: Evaluate Safety

Check:
- Are destructive operations guarded by user confirmation?
- Are there clear never-violate rules?
- Could the skill accidentally modify files, deploy code, or make network calls without consent?

### Step 5: Evaluate Completeness

Check:
- Are all phases actionable? (not just "do the thing" but actual steps)
- Are output formats defined?
- Are error cases handled?
- Are tool scripts referenced correctly in mcp_tools.json?

## Output Format

Return JSON:
```json
{
  "overall_score": 4,
  "structure": {"score": 5, "issues": []},
  "description": {"score": 3, "issues": ["Missing context clues for kubectl commands"]},
  "safety": {"score": 5, "issues": []},
  "completeness": {"score": 4, "issues": ["Phase 3 lacks concrete steps"]},
  "suggestions": [
    "Add 'kubectl' and 'helm' as trigger keywords in description",
    "Phase 3 should specify exact output format"
  ]
}
```
