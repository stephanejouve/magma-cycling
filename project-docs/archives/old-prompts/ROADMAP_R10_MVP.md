# Cyclisme Training Logs - ROADMAP

**Project**: AI-Powered Training Analysis & Weekly Report Generation
**Last Updated**: 2026-01-18
**Maintainer**: Stéphane Jouve + Claude Sonnet 4.5

---

## Sprint R10 MVP - AI-Powered Weekly Reports ✅ COMPLETE

**Status**: Production-ready (2026-01-18)
**Duration**: 5 days (Day 1-5)
**Test Coverage**: 78% (reports module), 951 total tests passing

### Delivered Features

- ✅ **Workout History Reports**: Factual session-by-session chronicle (2000 words max)
- ✅ **Bilan Final Reports**: Strategic weekly synthesis (1500 words max)
- ✅ **AI Provider Abstraction**: Support for Claude (primary), OpenAI (alternative), Clipboard (manual)
- ✅ **CLI Interface**: `generate-report` command with full argument support
- ✅ **Python API**: `ReportGenerator` class for programmatic access
- ✅ **5-Step Pipeline**: collect → prompt → generate → validate → save
- ✅ **Markdown Validation**: Structural validation with hallucination detection
- ✅ **Comprehensive Documentation**: README, examples, completion report (1500+ lines)
- ✅ **Test Suite**: 70 reports tests (38 new), 100% of integration tests mocked

### Architecture Achievements

- Clean separation: DataCollector → PromptBuilder → AIClient → Validator → FileSaver
- Provider abstraction enables easy addition of new AI models
- Template-based validation ensures consistent report structure
- Comprehensive error handling with custom exception hierarchy

**See**: `docs/SPRINT_R10_MVP_COMPLETION.md` for full details

---

## Phase 2 - Enhanced AI Provider Support & Usability

**Target**: Q1 2026
**Focus**: Expand AI provider options, improve user experience, add batch capabilities

### Priority 1: Additional AI Providers

#### 1. **Mistral AI Support** 🎯 **REQUESTED BY USER**

**Status**: Planned
**Priority**: High
**Requested**: 2026-01-18 (User: "take it log in ROADMAP in this case")

**Implementation Plan**:
- Add `MistralAIClient` in `magma_cycling/reports/ai_clients/mistral_client.py`
- Support models: `mistral-large-2`, `mistral-medium` (or latest available)
- API integration via official Mistral Python SDK
- Environment variable: `MISTRAL_API_KEY`
- CLI flag: `--provider mistral`

**Rationale**:
- Mistral offers competitive pricing vs Claude/OpenAI
- Strong French language support (important for this project's French reports)
- Additional provider diversity reduces vendor lock-in
- User explicitly requested this feature

**Effort Estimate**: 1-2 days (following existing AIClient pattern)

**Dependencies**:
- `mistralai` Python SDK
- Mistral API key acquisition
- Prompt testing/tuning for Mistral models

**Test Requirements**:
- Unit tests for `MistralAIClient` (mocked API)
- Integration tests with mocked responses
- Manual quality testing with real API (compare to Claude baseline)

#### 2. **Local LLM Support** (Ollama, LM Studio)

**Status**: Planned
**Priority**: Medium
**Target**: Q1 2026

**Implementation Plan**:
- Add `LocalAIClient` supporting Ollama API-compatible endpoints
- Support for open models: Mistral 7B/8x7B, Llama 3.1, etc.
- Configurable endpoint URL and model name
- Environment variables: `LOCAL_LLM_ENDPOINT`, `LOCAL_LLM_MODEL`

**Benefits**:
- Zero API costs for users with GPU access
- Data privacy (no external API calls)
- Offline operation capability

**Challenges**:
- Quality varies significantly by model
- Requires user hardware setup
- Prompt engineering may need model-specific tuning

### Priority 2: Usability Enhancements

#### 1. **Multi-Language Support**

**Status**: Planned
**Priority**: Medium

- Parameterize report language in prompts (currently hardcoded French)
- Support: French (default), English, Spanish, Italian
- CLI flag: `--language fr|en|es|it`
- Update prompt templates to accept language parameter

#### 2. **Custom Templates**

**Status**: Planned
**Priority**: Medium

- Allow user-defined report structures via YAML/JSON templates
- Custom section names, ordering, and required fields
- Template validation on load
- CLI flag: `--template path/to/template.yaml`

#### 3. **Batch Generation**

**Status**: Planned
**Priority**: High

- Generate reports for multiple weeks in parallel
- CLI: `generate-report --weeks S070-S076 --type workout_history`
- Async/parallel execution with progress tracking
- Summary report of batch results (successes/failures)

**Benefits**:
- Catch up on missing reports efficiently
- Bulk regeneration after prompt improvements
- Faster workflow for multi-week analysis

#### 4. **Interactive Editing**

**Status**: Planned
**Priority**: Low

- Review generated report before final save
- In-terminal editor integration (via $EDITOR)
- Option to regenerate with feedback
- CLI flag: `--interactive`

### Priority 3: Output & Integration

#### 1. **Additional Output Formats**

**Status**: Planned
**Priority**: Medium

- PDF export (via markdown → pandoc/weasyprint)
- HTML export with custom styling
- CLI flag: `--format md|pdf|html`

#### 2. **Report Versioning**

**Status**: Planned
**Priority**: Low

- Track report revisions (v1, v2, etc.)
- Git-like history of edits and regenerations
- Compare versions side-by-side
- Restore previous versions

#### 3. **Analytics Dashboard**

**Status**: Planned
**Priority**: Low

- Track report generation statistics
- AI costs per report, cumulative costs
- Quality metrics (validation scores, word counts)
- Export analytics as CSV/JSON

---

## Phase 3 - Advanced Intelligence & Automation

**Target**: Q2 2026
**Focus**: AI-powered insights, historical context, automated workflows

### 1. **RAG Integration** (Retrieval-Augmented Generation)

**Status**: Concept
**Priority**: High

**Vision**: AI accesses past reports to provide continuity and context

**Implementation**:
- Vector database (ChromaDB/FAISS) for past reports
- Semantic search for relevant historical insights
- Prompt augmentation with retrieved context
- Example: "As noted in S070 report, Z2 protocol improved..."

**Benefits**:
- Longitudinal insights (week-over-week trends)
- Avoid repeating past recommendations
- Recognize patterns across training cycles

### 2. **Fine-Tuned Model**

**Status**: Concept
**Priority**: Low

**Vision**: Custom model trained on cycling training vocabulary and report style

**Considerations**:
- Requires corpus of high-quality reports (50-100+ examples)
- Fine-tuning cost and maintenance effort
- May improve consistency and domain knowledge
- Vendor-specific (Claude, OpenAI, Mistral each have different processes)

### 3. **Automated Weekly Workflow**

**Status**: Concept
**Priority**: Medium

**Vision**: Fully automated report generation on schedule

**Implementation**:
- Cron job / scheduled task for weekly generation
- Email delivery of reports
- Slack/Discord notifications on completion
- Error alerting (missing data, API failures)

### 4. **Web UI**

**Status**: Concept
**Priority**: Medium

**Vision**: Browser-based interface for non-technical users

**Features**:
- Report generation form (week selector, report type, provider)
- Real-time generation progress
- Report preview and download
- Historical report browser
- User authentication and multi-user support

**Tech Stack Consideration**:
- FastAPI backend (reuses existing Python codebase)
- React/Vue frontend
- WebSocket for real-time updates

---

## Technical Debt & Maintenance

### Known Limitations (from R10 MVP)

1. **No Retry Logic**: API failures not retried (rely on client library defaults)
2. **Validation Strictness**: May reject valid reports with minor structural variations
3. **AI Determinism**: Slight output variations between runs (inherent to LLMs)
4. **Rate Limits**: No explicit rate limit handling
5. **Cache Missing**: WeeklyAggregator results not cached (repeated queries)

### Critical Technical Debt 🚨

#### 1. **Duplicate AI Provider Infrastructure** - PRIORITY: HIGH

**Issue**: Sprint R10 MVP created a parallel AI provider system instead of using existing infrastructure

**Current State**:
- **Existing System** (Production-ready):
  - `magma_cycling/ai_providers/` - Complete AI provider infrastructure
  - `AIProviderFactory` - Factory pattern for provider creation
  - `AIAnalyzer` base class - Abstract interface for all providers
  - **All providers implemented**: clipboard, claude_api, mistral_api, openai, ollama
  - `AIProvidersConfig` in config_base.py - Centralized config management

- **Reports Module** (Duplicate):
  - `magma_cycling/reports/ai_client.py` - New parallel system
  - `ClaudeClient`, `OpenAIClient` classes - Duplicate implementations
  - `create_ai_client()` factory - Duplicate factory pattern
  - Only 2 providers: claude, openai (missing mistral, ollama, clipboard)

**Problem**:
- Code duplication (~200 LOC)
- Mistral support exists in main system but not in reports
- Two config systems for same providers
- Maintenance burden (changes must be made twice)
- Inconsistent provider naming (claude vs claude_api)

**Root Cause**:
- Sprint R10 implemented in isolation without architecture review
- Missing discovery phase: "do not reinvent wheel at very sprint buddy" (User feedback)
- Fast 5-day sprint prioritized delivery over integration

**Resolution Path** (MOA Decision Required):

**Option A: Refactor Reports to Use Existing Infrastructure** (Recommended)
- Adapt reports module to use `AIProviderFactory`
- Bridge interface difference: `analyze_session()` vs `generate()`
- Benefits: Single source of truth, Mistral/Ollama support immediately available
- Effort: 1-2 days refactoring + testing
- Risk: Medium (changes core reports pipeline)

**Option B: Keep Separate, Document Rationale**
- Document why reports needs separate implementation
- Add Mistral/Ollama to reports/ai_client.py
- Benefits: No risk to working system
- Effort: 1 day per new provider
- Risk: Low (maintains status quo)
- Cost: Ongoing maintenance duplication

**Option C: Merge Systems into Unified Provider Layer**
- Create new unified interface compatible with both use cases
- Migrate both systems to unified interface
- Benefits: Long-term maintainability, single provider system
- Effort: 3-5 days (major refactor)
- Risk: High (affects multiple modules)

**Recommended Action**: Option A - Refactor reports to use existing `ai_providers/`

**User Feedback**:
- "oupsy this bullet may address to the project MOA" (2026-01-18)
- "do not reinvent wheel at very sprint buddy" (2026-01-18)

**Logged**: 2026-01-18
**Status**: ✅ RESOLVED (2026-01-18)

**Resolution**: Option A implemented - Reports module refactored to use AIProviderFactory
- Removed ai_client.py (~200 LOC)
- Updated generator.py to use AIProviderFactory.create()
- All 57 tests passing
- Mistral AI and Ollama support now available in reports
- Commit: 62d29fc "refactor: Integrate reports module with existing ai_providers infrastructure"

### Refactoring Candidates

1. **Prompt Management**: Consider external prompt files (YAML/JSON) vs Python strings
2. **Validation Flexibility**: Make section name matching more flexible (fuzzy matching?)
3. **Error Messages**: Add suggestion hints to error messages
4. **Logging**: Structured logging (JSON) for production monitoring

---

## Community & Contributions

### Contributing Guidelines

**How to Propose Features**:
1. Open GitHub issue with `[Feature Request]` prefix
2. Describe use case and expected behavior
3. Reference this ROADMAP if applicable

**How to Add AI Providers**:
1. Follow `magma_cycling/reports/ai_clients/base.py` interface
2. Add unit tests with mocked API
3. Update `README.md` with provider documentation
4. Add to `--provider` CLI choices

### Future Research Areas

1. **Prompt Engineering**: Comparative study of prompt variants (A/B testing)
2. **Model Comparison**: Quality benchmarking across Claude/OpenAI/Mistral/Llama
3. **Validation Metrics**: Quantitative report quality scoring
4. **Cost Analysis**: Cost vs quality tradeoffs across providers

---

## Decision Log

### Why Claude Sonnet 4.5 as Primary?

**Decision Date**: Sprint R10 Day 1 (2026-01-14)

**Rationale**:
- Best-in-class for long-form text generation
- Strong French language support
- Excellent prompt adherence (structured outputs)
- Competitive pricing for 2000-word outputs

**Trade-offs Considered**:
- Claude more expensive than GPT-4o for some use cases
- Anthropic API has usage quotas (rate limits)
- Single vendor dependency (mitigated by provider abstraction)

### Why Mistral Not in R10 MVP?

**Decision Date**: Sprint R10 Day 5 (2026-01-18)

**Rationale**:
- MVP focused on proving core pipeline with 2 providers (Claude, OpenAI)
- Clipboard provider offers manual fallback
- 5-day sprint timeline prioritized depth over breadth
- Provider abstraction makes future addition straightforward

**User Feedback**: User requested Mistral support on Day 5 → logged in Phase 2 Priority 1

---

## Version History

| Version | Date       | Changes                                           |
|---------|------------|---------------------------------------------------|
| 1.2     | 2026-01-18 | Technical debt RESOLVED                          |
|         |            | - Reports module refactored to use ai_providers/ |
|         |            | - Removed ~200 LOC duplication                   |
|         |            | - Mistral AI and Ollama now available in reports |
|         |            | - All 57 tests passing                           |
| 1.1     | 2026-01-18 | Added critical technical debt item               |
|         |            | - Documented duplicate AI provider infrastructure |
|         |            | - 3 resolution options proposed for MOA          |
|         |            | - Logged user feedback on architecture           |
| 1.0     | 2026-01-18 | Initial ROADMAP created                          |
|         |            | - Sprint R10 MVP marked COMPLETE                 |
|         |            | - Mistral AI support logged (user request)       |
|         |            | - Phase 2 and Phase 3 features outlined          |

---

## Contact & Feedback

**Project Owner**: Stéphane Jouve
**Repository**: (Add GitHub URL when available)
**Issues**: (Add GitHub Issues URL when available)

For questions, feature requests, or bug reports, please open a GitHub issue.

---

**Last Updated**: 2026-01-18
**Next Review**: 2026-02-01 (Sprint R11 planning)
