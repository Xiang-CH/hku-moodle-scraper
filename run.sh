echo 'Creating python virtual environment "venv"'
python3 -m venv venv

echo ""
echo "Restoring backend python packages"
echo ""

./venv/bin/python -m pip install --upgrade pip
./venv/bin/python -m pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Failed to restore backend python packages"
    exit $?
fi
./venv/bin/playwright install

./venv/bin/python addToNotion.py