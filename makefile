.PHONY: setup install run

setup:
	python3 -m venv venv
	@echo "Please activate the virtual environment manually:"
	@echo "  Mac/Linux: source venv/bin/activate"
	@echo "  Windows: venv\\Scripts\\activate"

install:
	pip install -r requirements.txt

run:
	uvicorn app.main:app --reload
