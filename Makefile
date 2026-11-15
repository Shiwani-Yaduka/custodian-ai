.PHONY: setup run stop test fairness simulate lint help

help:
	@python scripts/dev.py help

setup:
	@python scripts/dev.py setup

test:
	@python scripts/dev.py test

lint:
	@python scripts/dev.py lint

fairness:
	@python scripts/dev.py fairness

simulate:
	@python scripts/dev.py simulate $(ARGS)

run:
	@python scripts/dev.py run

stop:
	@python scripts/dev.py stop

