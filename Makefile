.PHONY: all zip clean check pylint check check_format fix mypy pylint
all: zip

zip: AnkiAppImporter.ankiaddon

AnkiAppImporter.ankiaddon: src/*
	rm -f $@
	rm -rf src/__pycache__
	( cd src/; zip -r ../$@ * -x meta.json )

check: check_format mypy pylint

check_format:
	python -m black --exclude=forms --check --diff --color src
	python -m isort --check --diff --color src

fix:
	python -m black --exclude=forms src
	python -m isort src

mypy:
	python -m mypy src

pylint:
	python -m pylint src

clean:
	rm -f src/*.pyc
	rm -f src/__pycache__
	rm -f AnkiAppImporter.ankiaddon
