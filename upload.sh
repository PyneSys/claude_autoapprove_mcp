#!/bin/sh

# Ask if user wants to upload to PyPI
read -p "Do you want to upload to PyPI? (y/n): " upload

if [ "$upload" = "y" ]; then
    if [ ! -d venv ]; then
        echo "venv not found!"
        exit 1
    fi
    source venv/bin/activate

    for pkg in build twine; do
        if ! python -c "import $pkg" &>/dev/null; then
            echo "Missing Python package: $pkg – installing..."
            pip install "$pkg"
        fi
    done

    # Clear dist folder
    rm -rf dist/* 2>/dev/null >/dev/null

    # Build and upload
    python -m build && \
        python -m twine upload -r pynesys dist/*
fi
