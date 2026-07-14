.PHONY: test test-backend test-frontend

# Run all tests for the entire project
test: test-backend test-frontend

# Run only the Python backend tests
test-backend:
	pytest

# Run only the JavaScript frontend tests
test-frontend:
	npx playwright test
