
PYTHON_VERSION ?= 3.11.9

# Poetry
POETRY := PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring poetry

.PHONY: install install-dev clean run lint format test pre-commit \
        check-pyenv check-poetry

install: check-pyenv check-poetry
	pyenv install -s $(PYTHON_VERSION)
	pyenv local $(PYTHON_VERSION)
	$(POETRY) env use $$(pyenv which python)
	$(POETRY) install --only main --no-root

install-dev: install
	$(POETRY) install --only dev --no-root
	$(POETRY) run pre-commit install || true

clean: check-poetry
	$(POETRY) env remove --all || true
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	rm -f .python-version

pre-commit: install-dev
	$(POETRY) run pre-commit run -a || true

# Check if pyenv is installed
check-pyenv:
	@if ! command -v pyenv >/dev/null 2>&1; then \
		echo "Error: pyenv is not installed. Please install it first:"; \
		echo "$$PYENV_INSTALL_INSTRUCTIONS"; \
		exit 1; \
	fi

# Check if poetry is installed
check-poetry:
	@if ! command -v poetry >/dev/null 2>&1; then \
		echo "Error: poetry is not installed. Please install it first:"; \
		echo "$$POETRY_INSTALL_INSTRUCTIONS"; \
		exit 1; \
	fi

# Installation instructions
define PYENV_INSTALL_INSTRUCTIONS
# Install pyenv dependencies
sudo apt-get update
sudo apt-get install -y make build-essential libssl-dev zlib1g-dev \
libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev \
libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev python3-openssl git

# Install pyenv
curl https://pyenv.run | bash

# Add pyenv to PATH (add these lines to your ~/.bashrc or ~/.zshrc)
export PYENV_ROOT="$$HOME/.pyenv"
export PATH="$$PYENV_ROOT/bin:$$PATH"
eval "$$(pyenv init --path)"

# Reload your shell
source ~/.bashrc
endef
export PYENV_INSTALL_INSTRUCTIONS

define POETRY_INSTALL_INSTRUCTIONS
# Option 1: Install poetry using apt
sudo apt-get install -y python3-poetry

# Option 2: Install poetry using the official installer
curl -sSL https://install.python-poetry.org | python3 -

# Option 3: Install poetry using pip
pip install poetry
endef
export POETRY_INSTALL_INSTRUCTIONS
