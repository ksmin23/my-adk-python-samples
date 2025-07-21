# GEMINI.md

This guide helps AI-based development tools like Gemini understand and interact with this project effectively.

## Project Overview

<!-- Briefly describe the project's purpose, key technologies, and architecture. For example: "This is a Flask web application that provides users with real-time cricket scores." -->

This project is implemented in Python.

## Development Environment Setup

This project uses `uv` to manage Python package dependencies and create virtual environments. `uv` is an extremely fast tool compatible with `pip` and `venv`.

**Installing `uv`:**
If you don't have `uv` installed, you can install it as follows:
```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Setup Steps:**

1.  **Create a virtual environment:**
    Use `uv` to create a virtual environment.
    ```bash
    uv venv
    ```

2.  **Activate the virtual environment:**
    *   **macOS/Linux:**
        ```bash
        source .venv/bin/activate
        ```
    *   **Windows:**
        ```bash
        .venv\Scripts\activate
        ```
    *(Note: `uv` creates a directory named `.venv` by default.)*

3.  **Install dependencies:**
    Use `uv` to install the dependencies listed in the `requirements.txt` file.
    ```bash
    uv pip install -r requirements.txt
    ```
    *If you are using `pyproject.toml`, you can use a command like `uv pip install -e .`.*

## Running the Application

<!-- Specify the command to run the project's main executable file here. -->
With the virtual environment activated, you can run the command below or use `uv run`.

**Example (Flask):**
```bash
# After activating the virtual environment
flask run

# Or using uv
uv run flask run
```

**Example (Standard Python Script):**
```bash
# After activating the virtual environment
python3 main.py

# Or using uv
uv run python3 main.py
```

## Running Tests

Use `uv` to run `pytest` in the virtual environment.

```bash
uv run pytest
```

## Code Style and Linting

To maintain code consistency and readability, run the linter and formatter through `uv`. This ensures that the tools installed in the virtual environment are used.

1.  **Code Formatting (Black):**
    ```bash
    uv run black .
    ```

2.  **Linting (Ruff):**
    Astral, the developers of `uv`, also develop `ruff`, so it's recommended to use them together.
    ```bash
    uv run ruff check .
    ```

## Key Files and Directories

<!-- Please modify this list to match the project's structure. -->

-   `main.py` / `app.py`: The main entry point of the application.
-   `src/` or `app/`: The directory where the core source code is located.
-   `tests/`: Contains all test code.
-   `requirements.txt` or `pyproject.toml`: Defines Python package dependencies.
-   `.venv/`: The virtual environment directory created by `uv`.
-   `Dockerfile`: Configuration file for container builds.
-   `.env.example`: Template file for environment variable settings.

## Coding Conventions

This project follows the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html) and enforces code style through `pylint` and a `pylintrc` configuration file.

-   **Indentation**: 2 spaces
-   **Line Length**: Maximum 80 characters
-   **Naming Conventions**:
    -   Functions, Variables: `snake_case`
    -   Classes: `PascalCase`
    -   Constants: `UPPERCASE_SNAKE_CASE`
-   **Docstrings**: Required for all public modules, functions, classes, and methods.
-   **Imports**: Group and sort related imports.
-   **Error Handling**: Handle specific exceptions instead of broad ones like `Exception`.
-   Adheres to the PEP 8 style guide by default.
