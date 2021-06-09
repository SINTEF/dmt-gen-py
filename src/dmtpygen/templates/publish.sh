set -e

if [ -z "$PUBLISH_LIB" ]
then
    echo "PUBLISH_LIB environment not set"
    exit 1
fi

if $PUBLISH_LIB; then
    python -m twine upload dist/* --config-file .pypirc
    echo "Library published"
else
    echo "Library not published"
fi
