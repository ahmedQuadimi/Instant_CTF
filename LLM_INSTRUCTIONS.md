# LLM_INSTRUCTIONS.md

## 1. GLOBAL ENVIRONMENT & CONSTRAINTS
- **System**: Dell Latitude 5790 running Arch Linux (GNOME).
- **Communication Style**: 
    - Responses must be short, concise, and direct.
    - Use clear language; avoid jargon.
- **Strict Formatting**:
    - Do NOT use cite blocks inside code comments.
    - Use plaintext blocks for code intended for copying.
- **Logic**: Apply detailed, formal, and rigorous reasoning for all mathematical and logical components.

## 2. PROJECT-SPECIFIC TEMPLATE
- **[PROJECT_NAME]**: Brief overview of the project's purpose and scope.
- **[CORE_STACK]**: Primary languages (e.g., Go, Java, C, Python) and specific frameworks (e.g., Gin, Spring, Django).
- **[BUILD_COMMANDS]**: Exact commands for building or running the application (e.g., `make build`, `mvn clean install`).
- **[TEST_COMMANDS]**: Instructions for running the project-specific testing suite (e.g., `pytest`, `go test ./...`).

## 3. OPERATIONAL RULES
- **Directness**: Answer only the parts of the prompt asked. Do not add unrelated information or expand beyond the initial request.
- **Code Style**: Ensure code follows the repository's existing patterns and conventions.
- **Dependency Management**: Do NOT hallucinate or introduce external libraries not already present in the stack.

---
*This file acts as a persistent context layer. AI agents must prioritize these instructions for all operations within this repository.*
