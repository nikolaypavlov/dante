.PHONY: validate render stats serve watch check-sync frontispicia dist all

validate:
	uv run scripts/validate_json.py

render:
	uv run scripts/render_html.py

frontispicia:
	uv run scripts/render_html.py --frontispicia

stats:
	uv run scripts/stats.py

serve:
	python3 -m http.server 8000

watch:
	find json/ templates/ static/ -name '*.json' -o -name '*.j2' -o -name '*.css' -o -name '*.js' | entr -r uv run scripts/render_html.py

check-sync:
	uv run scripts/validate_json.py --check-sync

dist:
	uv run scripts/render_html.py --dist

all: validate render frontispicia check-sync
