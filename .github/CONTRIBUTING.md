# Contributing to Archelyst Backend

## Autonomous Development Workflow

This project uses **Claude Code for autonomous development**. Most tasks are handled automatically by Claude following the workflow defined in `.claude/commands.md`.

## How It Works

### Autonomous Operation
- Claude automatically picks up tasks from the GitHub issue backlog
- Creates feature branches and implements solutions
- Updates issue status and provides progress updates
- Runs tests and fixes failures automatically
- Continues to the next task when complete

### Manual Intervention Only For
- Breaking changes to production
- Architecture modifications
- Security/authentication changes
- External service integrations
- Budget-impacting changes

## Creating Tasks for Claude

Simply create GitHub issues with:
- Clear title describing the task
- Detailed description of requirements
- Acceptance criteria (checkboxes preferred)
- Appropriate labels: `backend`, `ai`, `data`, `api`, etc.

### Example Issue Format
```
Title: Implement FMP data provider

Description:
Create Financial Modeling Prep data provider implementation with async API calls and error handling.

Acceptance Criteria:
- [ ] FMP provider class inherits from DataProvider base
- [ ] All required methods implemented (quote, profile, historical, search)
- [ ] Async/await pattern throughout
- [ ] Comprehensive error handling with retries
- [ ] Unit tests with >90% coverage
- [ ] Integration tests pass
```

## Manual Commands

If you need to interact with Claude directly:

- `start task #123` - Start specific issue
- `complete task #123` - Mark task complete
- `next task` - Get next task from backlog
- `STOP` - Halt current work
- `PRIORITY: [description]` - Switch to urgent task
- `REVIEW NEEDED` - Pause for approval

## Development Standards

### Code Quality
- Python 3.11+ with type hints
- FastAPI async patterns
- SQLAlchemy async ORM
- Comprehensive error handling
- >90% test coverage

### Architecture Patterns
- Hot-swappable data providers
- Hot-swappable AI providers
- Service layer abstraction
- Dependency injection
- Factory patterns for providers

### Security
- Input validation with Pydantic
- API key secure storage
- Rate limiting
- SQL injection protection
- CORS configuration

## Testing

All code must include:
- Unit tests for individual functions/methods
- Integration tests for API endpoints
- Provider tests with mocked external APIs
- Performance tests for critical paths

## Performance Requirements

- Sub-2-second API response times
- Support for 1000+ concurrent users
- Intelligent caching strategies
- Efficient database queries
- Optimized AI provider usage

## Pull Request Process

Claude handles most PR creation automatically, but manual PRs should:

1. Include comprehensive tests
2. Update documentation
3. Follow code style guidelines
4. Pass all CI checks
5. Include performance considerations

## Getting Help

- Check GitHub Issues for current task status
- Review `.claude/` folder for project specifications
- Claude provides autonomous updates on progress
- For urgent issues, use manual commands above

---

**This project is powered by autonomous AI development for maximum efficiency and consistency.**