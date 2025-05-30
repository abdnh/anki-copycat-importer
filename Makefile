.PHONY: all zip ankiweb vendor ruff-format ruff-check ruff-fix fix mypy lint test sourcedist clean

all: zip ankiweb

UV_RUN = uv run --

zip:
	$(UV_RUN) python -m ankiscripts.build --type package --qt all --exclude user_files/**/*

ankiweb:
	$(UV_RUN) python -m ankiscripts.build --type ankiweb --qt all --exclude user_files/**/*

vendor:
	$(UV_RUN) python -m ankiscripts.vendor

ruff-format:
	$(UV_RUN) pre-commit run -a ruff-format

ruff-check:
	$(UV_RUN) ruff check

ruff-fix:
	$(UV_RUN) pre-commit run -a ruff-check

fix: ruff-format ruff-fix

mypy:
	-$(UV_RUN) pre-commit run -a mypy

lint: mypy ruff-check

test:
	$(UV_RUN) python -m  pytest --cov=src --cov-config=.coveragerc

sourcedist:
	$(UV_RUN) python -m ankiscripts.sourcedist

clean:
	rm -rf build/
