# AI-Powered Weekly Reports Module

**Sprint R10 MVP** - Automated weekly training report generation using Claude Sonnet 4.5
**Refactored Day 5** - Now uses existing `ai_providers/` infrastructure (removes 200 LOC duplication)

## Overview

The `reports` module provides AI-powered generation of comprehensive weekly training reports in French. It orchestrates data collection from multiple sources (Intervals.icu, training intelligence) and uses Large Language Models to synthesize insights into structured markdown reports.

Uses the project's existing `ai_providers/` infrastructure (AIProviderFactory) for all AI operations, providing immediate access to all supported providers: Claude API, Mistral AI, OpenAI, Ollama (local), and Clipboard (manual).

### Key Features

- **Two Report Types**: Factual workout history + strategic synthesis
- **5 AI Providers**: Claude API, Mistral AI (best value), OpenAI, Ollama (local/free), Clipboard
- **Multi-Source Data**: Integrates activities, wellness, metrics, and learnings
- **Validation**: Automatic markdown structure and content validation
- **CLI Interface**: Easy command-line usage with `generate-report`
- **Extensible**: Clean architecture for adding new report types

## Architecture

```
reports/
├── __init__.py              # Public API exports
├── cli.py                   # Command-line interface
├── generator.py             # Core orchestration (ReportGenerator)
├── data_collector.py        # Multi-source data aggregation
├── prompts/                 # AI prompt builders
│   ├── workout_history_prompt.py
│   └── bilan_final_prompt.py
├── validators/              # Report validation
│   └── markdown_validator.py
└── templates/               # Report structure definitions
    ├── workout_history.py
    └── bilan_final.py

# Uses existing project infrastructure:
../ai_providers/             # AI provider abstraction (all providers)
├── factory.py               # AIProviderFactory (creates providers)
├── base.py                  # AIAnalyzer interface
├── claude_api.py            # Claude Sonnet 4
├── mistral_api.py           # Mistral Large (best value)
├── openai_api.py            # OpenAI GPT-4 Turbo
├── ollama.py                # Local LLMs (free, private)
└── clipboard.py             # Manual copy/paste workflow

../config/config_base.py     # AIProvidersConfig (centralized config)
```

### Design Principles

1. **Separation of Concerns**: Data collection, prompt building, AI generation, and validation are separate
2. **Reuses Existing Infrastructure**: Uses `ai_providers/` instead of duplicating (Day 5 refactor)
3. **Testability**: All components mocked in tests (WeeklyAggregator, AIProviderFactory)
4. **Type Safety**: Pydantic models for configuration, clear interfaces
5. **Error Handling**: Graceful degradation with specific error types

## Report Types

### 1. Workout History (`workout_history`)

**Purpose**: Detailed session-by-session chronology of the training week

**Characteristics**:
- **Tone**: Factual, descriptive
- **Length**: ~2000 words
- **Structure**: Chronological session narrative
- **Focus**: What happened (activities, metrics, wellness)

**Sections**:
1. Contexte Semaine (Week context, TSS planned/realized)
2. Chronologie Complète (Session-by-session details)
3. Métriques Évolution (Physiological metrics trends)
4. Enseignements Majeurs (Key learnings, 3-5 discoveries)
5. Recommandations (Actionable next steps)

**Use Case**: Detailed reference for athletes and coaches to understand exactly what was done during the week.

### 2. Bilan Final (`bilan_final`)

**Purpose**: Strategic synthesis extracting high-level patterns and validations

**Characteristics**:
- **Tone**: Strategic, synthesis-focused
- **Length**: ~1500 words
- **Structure**: Objectives vs realized, discoveries (max 3-4)
- **Focus**: Why it matters (protocols, learnings, adaptations)

**Sections**:
1. Objectifs vs Réalisé (Planned vs actual achievement)
2. Métriques Finales (Start/end metrics comparison table)
3. Découvertes Majeures (Max 3-4 impactful findings)
4. Séances Clés (2-3 critical sessions analysis)
5. Protocoles Établis/Validés (Validated protocols)
6. Ajustements Recommandés (Strategic adjustments)
7. Enseignements Comportementaux (Behavioral insights)
8. Conclusion (2-3 sentences synthesis)

**Use Case**: Strategic reflection for coaches and athletes to extract patterns, validate protocols, and plan next training phases.

## Usage

### Command-Line Interface (CLI)

```bash
# Generate workout_history report for week S076 (uses Claude by default)
generate-report --week S076 --type workout_history

# Generate bilan_final with custom output directory
generate-report --week S076 --type bilan_final --output ~/custom/reports

# Use Mistral AI (best value - $2/1M input, $6/1M output)
generate-report --week S076 --type workout_history --provider mistral_api

# Use clipboard provider (copy prompt, no API key required)
generate-report --week S076 --type workout_history --provider clipboard

# Use OpenAI GPT-4
generate-report --week S076 --type bilan_final --provider openai

# Use local Ollama (free, unlimited, private)
generate-report --week S076 --type workout_history --provider ollama

# Enable verbose logging
generate-report --week S076 --type workout_history --verbose

# Show help
generate-report --help
```

### Python API

```python
from cyclisme_training_logs.reports import ReportGenerator
from pathlib import Path

# Initialize generator with AI provider (defaults to claude_api)
generator = ReportGenerator(ai_provider="claude_api")

# Generate workout_history report
report_path = generator.generate_report(
    week="S076",
    report_type="workout_history",
    output_dir=Path("~/data/reports")
)

print(f"Report generated: {report_path}")
# Output: /Users/user/data/reports/workout_history_s076.md
```

### Advanced Usage

```python
# Use Mistral AI (best value)
generator = ReportGenerator(ai_provider="mistral_api")
report_path = generator.generate_report(
    week="S076",
    report_type="bilan_final",
    output_dir=Path("/custom/path")
)

# Override AI provider per request
generator = ReportGenerator(ai_provider="claude_api")
report_path = generator.generate_report(
    week="S076",
    report_type="bilan_final",
    ai_provider="openai",  # Override to use OpenAI for this report
    output_dir=Path("/custom/path")
)

# Use clipboard provider (no API key required)
generator = ReportGenerator(ai_provider="clipboard")
report_path = generator.generate_report(
    week="S076",
    report_type="workout_history"
)
# Prompt is copied to clipboard, paste in claude.ai
```

## Configuration

### Environment Variables

**Claude API (default)**:
```bash
export ANTHROPIC_API_KEY="sk-ant-api03-..."
```

**OpenAI API**:
```bash
export OPENAI_API_KEY="sk-proj-..."
```

**Clipboard Provider** (no API key required):
- Copies prompt to clipboard
- Paste manually in Claude.ai or ChatGPT
- Useful for development or when API access unavailable

## Pipeline Architecture

The report generation pipeline consists of 5 steps:

### Step 1: Data Collection

**Component**: `DataCollector`

Aggregates data from multiple sources:
- **Intervals.icu**: Activities (TSS, IF, NP, HR, duration)
- **Wellness**: HRV, sleep quality, fatigue, readiness
- **Metrics**: CTL, ATL, TSB evolution
- **Intelligence**: Training learnings and patterns

**Source**: Uses `WeeklyAggregator` to collect all week data

### Step 2: Prompt Building

**Components**: `build_workout_history_prompt()`, `build_bilan_final_prompt()`

Constructs comprehensive AI prompts with:
- System instructions (role, tone, constraints)
- Week context (dates, TSS, objectives)
- Formatted data (activities, wellness, learnings)
- Output structure specification
- Quality checklist

**Key Constraints**:
- workout_history: 2000 words, factual tone, chronological
- bilan_final: 1500 words, synthesis tone, max 3-4 discoveries

### Step 3: AI Generation

**Component**: `AIClient` (Claude, OpenAI, or Clipboard)

Sends prompt to AI provider and retrieves generated text.

**Provider Options**:
- **Claude**: Default, best quality (Sonnet 4.5)
- **OpenAI**: Alternative (GPT-4)
- **Clipboard**: Manual (copy/paste)

### Step 4: Validation

**Component**: `MarkdownValidator`

Validates generated report against template requirements:
- Title format and week number
- Required sections present
- Word count within limits
- Markdown syntax validity

**Output**: `ValidationResult` with errors, warnings, and metrics

### Step 5: File Save

Saves validated markdown to output directory with standardized naming:
- Format: `{report_type}_{week}.md`
- Example: `workout_history_s076.md`

## Error Handling

The module uses specific error types for different failure scenarios:

```python
from cyclisme_training_logs.reports.data_collector import DataCollectionError
from cyclisme_training_logs.reports.ai_client import AIClientError
from cyclisme_training_logs.reports.generator import ReportGenerationError

try:
    generator = ReportGenerator()
    report_path = generator.generate_report("S076", "workout_history")
except DataCollectionError as e:
    print(f"Failed to collect week data: {e}")
except AIClientError as e:
    print(f"AI generation failed: {e}")
except ReportGenerationError as e:
    print(f"Report generation failed: {e}")
```

**Exit Codes (CLI)**:
- `0`: Success
- `1`: Report generation error (validation, AI failure)
- `2`: Configuration error (missing API keys)
- `3`: Invalid arguments (week format, report type)

## Testing

The reports module has comprehensive test coverage:

```bash
# Run all reports tests
pytest tests/reports/ -v

# Run with coverage
pytest tests/reports/ --cov=cyclisme_training_logs/reports --cov-report=term-missing

# Run specific test file
pytest tests/reports/test_generator.py -v

# Run integration tests only
pytest tests/reports/test_integration.py -v
```

**Test Coverage** (78% overall):
- `data_collector.py`: 99%
- `generator.py`: 94%
- `prompts/`: 94-100%
- `ai_client.py`: 91%
- `validators/`: 90%

**Test Organization**:
- `test_generator.py`: ReportGenerator unit tests
- `test_data_collector.py`: DataCollector tests with mocked WeeklyAggregator
- `test_integration.py`: End-to-end tests with mocked dependencies
- `test_prompts.py`: Prompt builder tests
- `test_validators.py`: Validation logic tests
- `test_ai_client.py`: AI client tests

## Development

### Adding a New Report Type

1. **Create Template** (`templates/new_report.py`):
```python
from cyclisme_training_logs.reports.templates.base import ReportTemplate

class NewReportTemplate(ReportTemplate):
    REPORT_TYPE = "new_report"
    REQUIRED_SECTIONS = ["Section 1", "Section 2"]
    MAX_WORD_COUNT = 1000
    LANGUAGE = "fr"
```

2. **Create Prompt Builder** (`prompts/new_report_prompt.py`):
```python
def build_new_report_prompt(week_data: dict) -> str:
    """Build AI prompt for new report type."""
    # Validate required fields
    # Format data
    # Construct prompt
    return prompt
```

3. **Update Generator** (`generator.py`):
```python
from cyclisme_training_logs.reports.prompts.new_report_prompt import build_new_report_prompt

def _build_prompt(self, week_data, report_type):
    if report_type == "new_report":
        return build_new_report_prompt(week_data)
    # ...
```

4. **Add Tests**:
- Unit tests for prompt builder
- Integration test for end-to-end generation
- Validation tests for new template

### Adding a New AI Provider

1. **Implement Provider Class** (`ai_client.py`):
```python
class NewProviderClient(AIClient):
    def __init__(self, api_key: str):
        self.api_key = api_key

    def is_configured(self) -> bool:
        return self.api_key is not None

    def generate(self, prompt: str, max_tokens: int = 4096) -> str:
        # Call API
        return generated_text
```

2. **Update Factory** (`ai_client.py`):
```python
def create_ai_client(provider: str) -> AIClient:
    if provider == "new_provider":
        return NewProviderClient(os.getenv("NEW_PROVIDER_API_KEY"))
    # ...
```

3. **Add Tests** (`test_ai_client.py`):
- Client initialization tests
- Generation tests with mocked API
- Configuration validation tests

## Best Practices

### Data Collection

- **Validate week format**: Always use `SXXX` format (e.g., `S076`)
- **Handle missing data gracefully**: Use default values for optional fields
- **Cache when possible**: WeeklyAggregator results are expensive

### Prompt Engineering

- **Be specific**: Clear instructions, constraints, examples
- **Use role-playing**: "You are a strategic cycling coach..."
- **Add quality checklists**: Help AI self-validate output
- **Constrain output**: Word limits, max discoveries, section requirements

### Validation

- **Fail fast**: Validate inputs before expensive operations
- **Provide context**: Include source data in validation errors
- **Log warnings**: Non-critical issues for later review
- **Return metrics**: Word count, section count for monitoring

### Error Handling

- **Use specific exceptions**: DataCollectionError, AIClientError, etc.
- **Include context**: Week number, report type in error messages
- **Log at appropriate levels**: DEBUG for details, ERROR for failures
- **Provide actionable messages**: "Set ANTHROPIC_API_KEY environment variable"

## Troubleshooting

### "Missing required field: activities"

**Cause**: DataCollector returned incomplete data structure

**Solution**:
```python
# Check WeeklyAggregator result structure
from cyclisme_training_logs.analyzers.weekly_aggregator import WeeklyAggregator

aggregator = WeeklyAggregator(week="S076", start_date=date(2026, 1, 13))
result = aggregator.aggregate()
print(result.data)  # Inspect structure
```

### "AI client 'claude' not configured"

**Cause**: Missing ANTHROPIC_API_KEY environment variable

**Solution**:
```bash
export ANTHROPIC_API_KEY="sk-ant-api03-..."
```

Or use clipboard provider:
```bash
generate-report --week S076 --type workout_history --provider clipboard
```

### "Generated report failed validation"

**Cause**: AI output doesn't match template requirements

**Solution**:
1. Check validation errors in logs
2. Inspect generated content
3. Adjust prompt constraints if needed
4. Retry generation (AI is non-deterministic)

### "Failed to collect week data"

**Cause**: WeeklyAggregator failure (missing activities, API errors)

**Solution**:
1. Verify Intervals.icu API credentials
2. Check week has activities
3. Run `weekly-analysis --week S076` to test data collection
4. Inspect aggregator logs for specific errors

## Performance

**Typical Generation Time**:
- Data collection: 2-5 seconds (Intervals.icu API calls)
- Prompt building: <100ms (string formatting)
- AI generation: 10-30 seconds (Claude API, depends on length)
- Validation: <100ms (regex matching, word count)
- **Total**: 15-40 seconds per report

**Optimization Tips**:
- Cache WeeklyAggregator results for multiple report types
- Use async for parallel report generation
- Batch multiple weeks if generating historical reports

## Version History

### v1.0.0 (Sprint R10 MVP) - 2026-01-18

Initial release with:
- Two report types (workout_history, bilan_final)
- Three AI providers (Claude, OpenAI, Clipboard)
- CLI interface (`generate-report` command)
- 80 tests, 78% coverage
- Full validation pipeline
- Comprehensive documentation

**Contributors**: Claude Sonnet 4.5 (AI pair programming)

## License

Part of cyclisme-training-logs project. All rights reserved.

## Support

For issues, questions, or feature requests, contact the development team or create an issue in the project repository.

---

**Generated with**: Claude Code - Sprint R10 MVP
**Last Updated**: 2026-01-18
