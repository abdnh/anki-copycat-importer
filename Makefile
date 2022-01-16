.PHONY: all zip clean
all: zip

zip: AnkiAppImporter.ankiaddon

AnkiAppImporter.ankiaddon: src/*
	rm -f $@
	rm -rf src/__pycache__
	( cd src/; zip -r ../$@ * )

clean:
	rm -f src/*.pyc
	rm -f src/__pycache__
	rm -f AnkiAppImporter.ankiaddon