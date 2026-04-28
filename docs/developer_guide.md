# Developer Guide

## Backend Extension Points

- Add a parser: implement `ParserAdapter` in `backend/app/parsers/`
- Add an external source: create a client in `backend/app/external_sources/`
- Add rule logic: extend `RuleEngine` in `backend/app/services/rules.py`
- Add LLM provider: implement `BaseLLMClient` in `backend/app/llm/`
- Adjust prompts: edit files under `prompts/` and update `PROMPT_DIR` or `PROMPT_LANG` if needed
- Adjust task chat behavior: update `TaskService.create_chat_reply` and the `chat` prompt templates

## Testing

- Backend: `pytest backend/tests`
- Frontend: `cd frontend && npm test`

## Data and Artifacts

- Uploads: `data/uploads`
- Parsed documents: `data/parsed`
- Reports: `data/reports`
- Trace: `data/traces`
- Mock assets: `data/mock`

## Replacing Components

- Parser backend: set `PARSER_BACKEND`
- LLM provider: set `LLM_PROVIDER`, `BASE_URL`, `API_KEY`, `MODEL_NAME`
- Prompt templates: set `PROMPT_DIR`, then edit `prompts/action/system.zh-CN.md` and `prompts/action/user.zh-CN.md`
- Chat prompt templates: edit `prompts/chat/system.zh-CN.md` and `prompts/chat/user.zh-CN.md`
- Database: change `DATABASE_URL`

## Notes

- The current runner uses in-process background tasks for simplicity.
- The app automatically ensures runtime directories and local tables at startup.
- Alembic is still included for explicit migration workflows.
