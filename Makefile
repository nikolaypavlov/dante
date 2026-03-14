.PHONY: validate render stats serve watch check-sync index dist all

validate:
	uv run scripts/validate_json.py

render:
	uv run scripts/render_html.py

index:
	uv run scripts/render_html.py --index

stats:
	uv run scripts/stats.py

serve:
	python3 -m http.server 8000

watch:
	find json/ templates/ -name '*.json' -o -name '*.j2' | entr -r uv run scripts/render_html.py

check-sync:
	uv run scripts/validate_json.py --check-sync

dist:
	uv run scripts/render_html.py --dist

all: validate render index check-sync
