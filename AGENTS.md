# Senior Engineering Standards

## 1. Understand Before Changing
- Inspect the existing architecture and coding conventions before implementation.
- Trace the relevant execution flow before modifying code.
- Identify the root cause before fixing a bug.
- Ask for clarification when requirements are ambiguous.

## 2. Keep Changes Minimal
- Prefer the simplest maintainable solution.
- Modify only files necessary for the task.
- Reuse existing utilities, modules, and dependencies.
- Do not create unnecessary files, abstractions, classes, or layers.
- Do not add dependencies without a clear technical reason.
- Avoid unrelated refactoring, renaming, or restructuring.
- Never overwrite or delete existing work without approval.

## 3. Python and Backend Quality
- Follow existing Python style, typing, and project conventions.
- Keep functions focused and readable.
- Separate business logic from infrastructure where appropriate.
- Handle exceptions, timeouts, and resource cleanup explicitly.
- Avoid premature abstraction and overengineering.

## 4. AI Agent Engineering
- Prefer deterministic logic for business rules and critical decisions.
- Minimize unnecessary LLM calls, agents, and tool invocations.
- Reuse existing model clients and configuration.
- Validate LLM outputs before using them.
- Enforce tool permissions and validate tool arguments.
- Handle retries, timeouts, malformed responses, and provider failures.
- Keep prompts, business logic, and infrastructure appropriately separated.
- Never let an LLM bypass application-level authorization or business rules.

## 5. Testing and Verification
- Follow TDD for meaningful behavior changes and bug fixes.
- Write focused tests for the changed behavior.
- Run targeted tests before the full test suite.
- Do not modify tests merely to hide implementation failures.
- Verify actual command output before claiming success.
- Never claim tests, builds, or checks passed without running them.

## 6. File and Dependency Discipline
- Preserve the existing project structure.
- Do not generate documentation unless requested or necessary.
- Do not create duplicate configuration or utility files.
- Keep dependency and configuration changes minimal.
- Do not introduce a new framework when existing tools are sufficient.

## 7. Communication Before Implementation
For non-trivial tasks, first provide:
- The problem and root cause, if known.
- The files likely to be affected.
- The proposed minimal implementation.
- Any important risks or trade-offs.

Wait for approval when the task is ambiguous, destructive, or requires significant architectural changes.

## 8. Completion Report
After implementation, report:
- What changed and why.
- Which files were modified or created.
- Tests and verification commands actually executed.
- Actual results, including failures.
- Remaining risks or limitations.

## Golden Rule
Write simple, reliable, production-quality code.
Do not make the codebase more complicated than the problem requires.
